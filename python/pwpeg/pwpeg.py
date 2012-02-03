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
u = unicode


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

        return u("Line {0}, column {1}, {2}\n").format(nlines, column, self.fullmessage())


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
        return u("{0}:{1}").format(self.name, super(Results, self).__repr__())

    def add(self, name, value):
        self.dict[name] = len(self)
        self.append(value)

    def get(self, name, default=None):
        return self[self.dict[name]]


class Input(object):
    def __init__(self, input):
        self.input = text
        self.pos = 0
        self.line = 0
        self.column = 0

    def advance(self, n):
        self.pos += n

    def rewind(self, n):
        self.pos -= n

class TextInput(Input):
    def startswith(self, s):
        if self.input.startswith(s, self.pos):
            self.advance(s)
            return s
        return None

    def match(self, re):
        m = re.match(self.input, self.pos)
        if not m:
            return None
        self.advance(m.group())

    def advance(self, s):
        l = len(s)
        self.newlines += n.count("\n")
        self.column = l - n.rfind("\n") - 1
        self.pos += l

    def rewind(self, n):
        self.newlines -= n.count("\n", self.pos, self.pos - n)
        self.pos -= n
        self.column = self.pos - self.input.rfind("\n", 0, self.pos) - 1

class TokenInput(Input):
    # FIXME Create token input.
    pass


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
        self.action = None
        self.name = ""
        self.productions = None

        if len(args) > 0:
            self.set_productions(*args)


    def set_productions(self, *args):
        if len(args) == 0:
            raise Exception("Can not have empty rules")

        if len(args) > 1 or not isinstance(args[0], Rule):
            self.productions = [Rule.getrule(r) for r in args]
        else:
            self.productions = args

        self.name = self.__class__.__name__
        self.post_subrule_name(", ".join([s.name for s in self.productions]))
        return self

    def post_subrule_name(self, productions_names):
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

        if "skip" in self.__dict__: skip = self.skip

        if not self.productions:
            raise Exception("There are no productions defined for " + self.name)

        for i, r in enumerate(self.productions):
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
                raise SyntaxError(u("In {0}:").format(self.name), input[:advanced], [e])

            # If everything went according to plan, the subrule_result is a tuple
            # with the number of consumed characters and the result of the processing
            # of the rule.
            sub_adv, sub_processed_result = subrule_result

            advanced += sub_adv

            if sub_processed_result is not IgnoreResult:
                results.append(sub_processed_result)

        # Restoring advancement before skip if skipping was the last thing we did.
        if advanced == adv_after: advanced = adv_before

        if self.action:
            return advanced, self.action(*results)

        if len(results) == 1:
            # When a rule does not send more than one result,
            # we simplify it so that we don't have to always manipulate
            # arrays.
            return advanced, results[0]

        return advanced, results


    def __repr__(self):
        return self.name


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
        self.string = unicode(string)
        self.name = "\"" + self.string + "\""

    def parse(self, input, currentresults=None, skip=None):
        if input.startswith(self.string):
            return len(self.string), self.string
        raise SyntaxError(u("Expected {0}, but found \"{1}\"...").format(self.name, input[:5]))


class RegexpRule(Rule):
    def __init__(self, regexp):
        self.regexp = regexp
        self.name = "/" + self.regexp.pattern + "/"

    def parse(self, input, currentresults=None, skip=None):
        m = self.regexp.match(input)
        if m:
            return len(m.group()), m.group()
        raise SyntaxError(u("Expected {0}, but found \"{1}\"...").format(self.name, input[:5]))


class Predicate(Rule):
    def __init__(self, fn):
        self.fn = fn
        self.name = u("Predicate {0}").format(fn.__name__)

    def parse(self, input, currentresults=[], skip=None):
        if self.fn(*currentresults) is False:
            # None actually is a valid result.
            raise SyntaxError(u("{0} was not satisfied").format(self.name))
        return 0, IgnoreResult


class FunctionRule(Rule):
    """ A rule that takes arguments.
    """

    def __init__(self, fn=None):
        if fn:
            self.set_fn(fn)
            self.name = fn.__name__
        else:
            self.fn = None
            self.name = "Param rule <no function>"
        self.action = None

    def set_fn(self, fn):
        args, varargs, keywords, defaults = inspect.getargspec(fn)
        if keywords:
            raise Exception("Function rules functions can only take simple args")

        self.fn = fn
        self.name = fn.__name__
        return self

    def instanciate(self, *args):
        arg_names = u("({0})").format(", ".join([repr(a) for a in args]))
        r = self.fn(*args).set_name(self.name + arg_names)

        if self.action:
            r.set_action(self.action)

        if "skip" in self.__dict__:
            r.set_skip(self.skip)

        return r

    def parse(self, input, currentresults=None, skip=None):
        # Works if the rule doesn't need any arguments
        r = self.instanciate()

        if "skip" in self.__dict__:
            r.set_skip(self.skip)

        return r.parse(input, currentresults, skip)


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
            raise SyntaxError(u("{1} needs to be repeated at least {0} times").format(_from, self.name), input[:advance], last_error)

        return advance, results

    def post_subrule_name(self, sn):
        self.name = sn + u("<{0}, {1}>").format(self._from, self._to)



class OneOrMore(Repetition):
    """ A Repetition that acts like the + in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(OneOrMore, self).__init__(1, -1, *args, **kwargs)

    def post_subrule_name(self, subn):
        self.name = u("[{0}]+").format(subn)


class ZeroOrMore(Repetition):
    """ A Repetition that acts like the * in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(ZeroOrMore, self).__init__(0, -1, *args, **kwargs)

    def post_subrule_name(self, subn):
        self.name = u("[{0}]*").format(subn)


class Exactly(Repetition):
    """ A Repetition that wants to match excatly `times` elements.
    """

    def __init__(self, times, *args, **kwargs):
        super(Exactly, self).__imit__(times, times, *args, **kwargs)

    def post_subrule_name(self, subn):
        self.name = u("[{0}]<{1}>").format(subn, self._from)


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
        self.name = "[" + sn + "]?"


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
        raise SyntaxError(u("In <{0}> Matched \"{0}\"").format(self.name, input[adv]))

    def post_subrule_name(self, productions):
        self.name = "Not " + productions



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
        self.name = u("Look-Ahead {0}").format(sn)



class Either(Rule):
    """ Try parsing with several rules and return the result of the first
        one that works.

        The rules are given to the constructor as its arguments.
    """

    def parse(self, input, currentresults=None, skip=None):
        all_errors = []

        for rule in self.productions:
            try:
                adv, res = rule.parse(input, currentresults, skip)
                if self.action:
                    return adv, self.action(res)
                return adv, res
            except SyntaxError as e:
                all_errors.append(e)
                # FIXME should store the error

                # We continue since the SyntaxError just means that we didn't match and
                # must try the next choice.
                continue

        raise SyntaxError(u("In [{0}], none of the provided choices matched").format(self.name), "", all_errors)

    def post_subrule_name(self, subn):
        self.name = u("either {0}").format(subn)

class Any(Rule):
    def __init__(self):
        self.name = "Any"

    def parse(self, input, currentresults=None, skip=None):
        if skip is None and "skip" in self.__dict__: skip = self.skip

        advanced = 0

        if skip:
            try:
                adv, res = skip.parse(input[advanced:])
                adv_before = advanced
                advanced += adv
                adv_after = advanced
            except SyntaxError as e:
                # Nothing to skip.
                pass

        if not input[advanced:]:
            raise SyntaxError("Want anything, but no more input", input[:advanced])

        return advanced + 1, input[advanced]

class MemoRule(Rule):
    """ A rule that memorizes itself for future uses.
    """

    def __init__(self, *args):
        self.memorized = False
        super(MemoRule, self).__init__(*args)

    def parse(self, input, currentresults=None, skip=None):
        """
        """
        if not self.memorized:
            # act = self.__dict__.get("action", None)
            # if act: del self.__dict__["action"]

            adv, res = super(MemoRule, self).parse(input, currentresults, skip)
            if not isinstance(res, list) and not isinstance(res, tuple):
                super(MemoRule, self).__init__(res)
            else:
                super(MemoRule, self).__init__(*res)
            self.memorized = True

            # return (adv, act(*res)) if act else (adv, res)
            return adv, res
        else:
            adv, res = super(MemoRule, self).parse(input, currentresults, skip)
            return adv, res


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

        result = self.toprule.parse(input)

        if result[0] != len(input):
            raise Exception(u("Finished parsing, but all the input was not consumed by the parser. Leftovers: '{0}'").format(input[result[0]:]))

        # Everything went fine, sending the results.
        return result[1]


    def partial_parse(self, input, *args, **kwargs):
        """ Parse the given input and return only the result of the parsing,
            which is a tuple containing the (number of consumed characters, result of parsing).

            It can be used on some inputs on which we know the grammar can't or won't consume
            the totality of the input.
        """

        return self.toprule.parse(input)

