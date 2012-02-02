"""
    @author Christophe Eymard <christophe@ravelsoft.com>
"""

from re import _pattern_type
import inspect
import sys

if sys.version_info >= (3, 0):
    # Python 3 removed entirely the unicode type, so to have
    # the input isinstance() still work, we just remap it to str (which
    # is unicode anyways)
    unicode = str


class SyntaxError(Exception):
    """ The way the input is parsed is by trial and error.

        When SyntaxError is caught by the parser, it goes up the caller
        chain to get to the first Choice() it finds to keep looking
        for a match.
    """
    def __init__(self, error, advanced="", suberrors=[]):
        super(SyntaxError, self).__init__(error)
        self.suberrors = suberrors
        self.advanced = advanced + "".join([e.advanced for e in suberrors])

    def fullmessage(self):
        return self.message +"\n" + "\n".join([ "\n".join(["   " + line for line in e.fullmessage().split("\n")]) for e in self.suberrors])

    def complete(self):
        column = len(self.advanced.split("\n")[-1])
        nlines = self.advanced.count("\n")

        return "Line {0}, column {1}, {2}\n".format(nlines, column, self.fullmessage())


class IgnoreResult(object):
    """ This class is used by the parsing rules to determine wether to add the
        result of some parsing to the general result.

        Typically, the And and Not rules return this as well as and advancement
        of 0 when they match.
    """


class Results(list):
    """
    """

    def __init__(self, name):
        self.name = name
        self.dict = {}

    def __repr__(self):
        return "{0}:{1}".format(self.name, super(Results, self).__repr__())

    def add(self, name, value):
        self.dict[name] = len(self)
        self.append(value)

    def get(self, name, default=None):
        return self[self.dict[name]]


class Rule(object):
    """ A Grammar rule.
    """

    @staticmethod
    def getrule(obj):
        """ Get the rule object corresponding to a given type.
        """

        if isinstance(obj, bytes):
            return StringRule(obj.decode('utf-8'))

        if isinstance(obj, unicode):
            return StringRule(obj)

        if isinstance(obj, _pattern_type):
            return RegexpRule(obj)

        if callable(obj):
            return Predicate(obj)

        return obj


    def __init__(self, *args):
        self.name = ""

        if len(args) > 0:
            self.set_subrules(*args)


    def set_subrules(self, *args):
        if len(args) == 0:
            raise Exception("Can not have empty rules")

        self.subrules = [Rule.getrule(r) for r in args]
        self.name = self.__class__.__name__
        self.post_subrule_name(", ".join([s.name for s in self.subrules]))
        return self

    def post_subrule_name(self, subrules_names):
        pass

    def set_skip(self, skip):
        self.skip = Rule.getrule(skip)
        return self

    def set_name(self, name):
        self.name = name
        return self


    def parse(self, input, currentresults=None, skip=None):
        """ Execute the rules
        """

        advanced = 0
        results = Results(self.name)

        adv_before = 0
        adv_after = 0

        if skip is None and "skip" in self.__dict__: skip = self.skip

        for i, r in enumerate(self.subrules):
            subrule_result = None

            if skip:
                try:
                    adv, res = skip.parse(input[advanced:])
                    adv_before = advanced
                    advanced += adv
                    adv_after = advanced
                except SyntaxError as e:
                    # Nothing to skip.
                    pass

            try:
                subrule_result = r.parse(input[advanced:], results, skip)
            except SyntaxError as e:
                raise SyntaxError("In rule <{0}>:".format(self.name), input[:advanced], [e])

            # If everything went according to plan, the subrule_result is a tuple
            # with the number of consumed characters and the result of the processing
            # of the rule.
            sub_adv, sub_processed_result = subrule_result

            advanced += sub_adv

            if sub_processed_result is not IgnoreResult:
                results.append(sub_processed_result)

        # Restoring advancement before skip if skipping was the last thing we did.
        if advanced == adv_after: advanced = adv_before

        if "action" in self.__dict__ and self.action:
            return advanced, self.action(*results)

        if len(results) == 1:
            # When a rule does not send more than one result,
            # we simplify it so that we don't have to always manipulate
            # arrays.
            return advanced, results[0]

        return advanced, results


    def set_action(self, fn):
        """ Add an action function to the rules.

            This is to be used when the processor function is not directly given to
            the rule in its constructor.
        """

        if inspect.getargspec(fn)[2]:
            raise Exception("Actions can't take kwargs")

        self.action = fn
        return self


class StringRule(Rule):
    def __init__(self, string):
        self.string = string
        self.name = "\"" + self.string + "\""

    def parse(self, input, currentresults=None, skip=None):
        if input.startswith(self.string):
            return len(self.string), self.string
        raise SyntaxError("Expected {0}, but found \"{1}\"...".format(self.name, input[:5]))


class RegexpRule(Rule):
    def __init__(self, regexp):
        self.regexp = regexp
        self.name = "/" + self.regexp.pattern + "/"

    def parse(self, input, currentresults=None, skip=None):
        m = self.regexp.match(input)
        if m:
            return len(m.group()), m.group()
        raise SyntaxError("Expected {0}, but found \"{1}\"...".format(self.name, input[:5]))


class Predicate(Rule):
    def __init__(self, fn):
        self.fn = fn
        self.name = "Predicate {0}".format(fn.__name__)

    def parse(self, input, currentresults=[], skip=None):
        if self.fn(*currentresults) is False:
            # None actually is a valid result.
            raise SyntaxError("{0} was not satisfied".format(self.name))
        return 0, IgnoreResult


class ParametrizableRule(Rule):
    """ A rule that takes arguments.
    """

    def __init__(self, fn=None):
        if fn:
            self.set_fn(fn)
            self.name = "Param rule {0}".format(fn.__name__)
        else:
            self.fn = None
            self.name = "Param rule <no function>"
        self.action = None

    def set_fn(self, fn):
        args, varargs, keywords, defaults = inspect.getargspec(fn)
        if varargs or keywords or defaults:
            raise Exception("Parametrizable rules functions can only take simple args")

        self.fn = fn
        return self

    def instanciate(self, *args):
        subrules = [Rule.getrule(a) for a in self.fn(*args)]
        r = Rule(*subrules)

        if self.action:
            r.set_action(lambda *a: self.action( *(args + a) ))

        if "skip" in self.__dict__:
            r.set_skip(self.skip)

        return r

    def parse(self, input, currentresults=None, skip=None):
        # Works if the rule doesn't need any arguments
        r = Rule(*self.fn())

        if "skip" in self.__dict__:
            r.set_skip(self.skip)

        return r.parse(input, currentresults)


class Repetition(Rule):
    """ A set of rules that can be repeated, like {m,n} in regular expressions.
    """


    def __init__(self, _from, _to, *args):
        self._from = _from
        self._to = _to
        super(Repetition, self).__init__(*args)


    def parse(self, input, currentresults=None, skip=None):
        results = []

        times = 0
        _from, _to = self._from, self._to

        advance = 0
        last_error = []

        while advance < len(input) and (_to == -1 or times < _to):
            try:
                # Get the resultss.
                adv, res = super(Repetition, self).parse(input[advance:], currentresults, skip)
            except SyntaxError as e:
                last_error.append(e.suberrors[0])
                break

            # Parsing was successful, so we add it to the results.
            advance += adv

            if res is not IgnoreResult:
                results.append(res)

            # We repeated one more time !
            times += 1

        if _from != -1 and times < _from:
            raise SyntaxError("Rule needs to be repeated at least {0} times ({1})".format(_from, self.name), input[:advance], last_error)

        return advance, results



class OneOrMore(Repetition):
    """ A Repetition that acts like the + in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(OneOrMore, self).__init__(1, -1, *args, **kwargs)

    def post_subrule_name(self, subn):
        self.name = "[{0}]+".format(subn)


class ZeroOrMore(Repetition):
    """ A Repetition that acts like the * in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(ZeroOrMore, self).__init__(0, -1, *args, **kwargs)



class Exactly(Repetition):
    """ A Repetition that wants to match excatly `times` elements.
    """

    def __init__(self, times, *args, **kwargs):
        super(Exactly, self).__imit__(times, times, *args, **kwargs)



class Optional(Repetition):
    """ The equivalent of the ? in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(Optional, self).__init__(0, 1, *args, **kwargs)


    def parse(self, input, currentresults=None, skip=None):
        adv, res = super(Optional, self).parse(input, currentresults, skip)

        if len(res) == 0:
            return 0, None

        return adv, res[0]

    def post_subrule_name(self, sn):
        self.name = sn + "?"


class Not(Rule):
    """ Look ahead in the input. If no syntax error is received, then
        raise a SyntaxError.

        This rule is used to check that a rule does not apply on the input
        following the current position.

        It does *not* advance the parser position.
    """

    def parse(self, input, currentresults=None, skip=None):
        try:
            adv, res = super(Not, self).parse(input, currentresults, skip)
        except SyntaxError as e:
            # Couldn't match the next rule, which is what we want, so
            # we return a result that won't advance the parser.
            return 0, IgnoreResult
        raise SyntaxError("In <{0}> Matched \"{0}\"".format(self.name, input[adv]))

    def post_subrule_name(self, subrules):
        self.name = "Not " + subrules



class And(Rule):
    """ Look ahead in the input. If its rules can be applied, then continue
        parsing from the same place we were before executing this rule.

        This rule is used to check that the following input contains a rule we
        want.

        It does *not* advance the parser position.
    """


    def parse(self, input, currentresults=None, skip=None):
        # Try to parse our rules
        super(And, self).parse(input, rules, skip)

        # If there was no error, we don't advance, which is what we want.
        # A syntax error is raised otherwise in our super() parse.
        return 0, IgnoreResult

    def post_subrule_name(self, sn):
        self.name = "Look-Ahead {0}".format(sn)



class Either(Rule):
    """ Try parsing with several rules and return the result of the first
        one that works.

        The rules are given to the constructor as its arguments.
    """

    def parse(self, input, currentresults=None, skip=None):
        all_errors = []

        for rule in self.subrules:
            try:
                return rule.parse(input, currentresults, skip)
            except SyntaxError as e:
                all_errors.append(e)
                # FIXME should store the error

                # We continue since the SyntaxError just means that we didn't match and
                # must try the next choice.
                continue

        raise SyntaxError("In <{0}> None of the provided choices matched".format(self.name), "", all_errors)

    def post_subrule_name(self, subn):
        self.name = "Either - {0}".format(subn)


class Parser(object):
    """ A parser that parses a input input.

        It is given a top-level rule with which it will start the parsing,
        as well as a skip rule which will be checked agains before executing
        any rule, useful to remove white spaces and comments.
    """

    def __init__(self, toprule):

        if not isinstance(toprule, Rule):
            toprule = Rule(toprule)

        self.toprule = toprule


    def parse(self, input):
        """ Parse the given input and return the result of the parsing.

            An Exception will be raised if the parsing does not use the
            integrality of the input.
        """

        result = self.toprule.parse(input, None)

        if result[0] != len(input):
            raise Exception("Finished parsing, but all the input was not consumed by the parser. Leftovers: '{0}'".format(input[result[0]:]))

        # Everything went fine, sending the results.
        return result[1]


    def partial_parse(self, input, *args, **kwargs):
        """ Parse the given input and return only the result of the parsing,
            which is a tuple containing the (number of consumed characters, result of parsing).

            It can be used on some inputs on which we know the grammar can't or won't consume
            the totality of the input.
        """

        return self.toprule.parse(input, None)

