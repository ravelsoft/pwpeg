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
    def __init__(self, error, input, suberrors=[]):
        self.suberrors = suberrors
        self.line = input.line
        self.column = input.column
        self.pos = input.pos
        super(SyntaxError, self).__init__(error + "({0}:{1})".format(self.line, self.column))


    def fullmessage(self):
        return unicode(self) + "\n" + "\n".join([ "\n".join(["   " + line for line in e.fullmessage().split("\n")]) for e in self.suberrors])


class IgnoreResult(object):
    """ This class is used by the parsing rules to determine wether to add the
        result of some parsing to the general result.

        Typically, the And and Not rules return this as well as and advancement
        of 0 when they match.
    """


class Results(list):
    """
    """

    def __init__(self, name=""):
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
        self.input = input
        self.pos = 0
        self.line = 1
        self.column = 1

    def rewind(self, n):
        self.pos -= n

    def rewind_to(self, pos):
        self.rewind(self.pos - pos)

    def has_next(self):
        return self.pos < len(self.input)

    def current(self):
        return self.input[self.pos] if self.has_next() else None


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
        matched = m.group()
        self.advance(matched)
        return matched

    def advance(self, s):
        if not s: return

        l = len(s)
        self.line += s.count("\n")
        self.column = l - s.rfind("\n") - 1
        self.pos += l

    def rewind(self, n):
        """
        """

        self.line -= self.input.count("\n", self.pos - n, self.pos)
        self.pos -= n
        self.column = self.pos - self.input.rfind("\n", 0, self.pos)



class TokenInput(Input):
    # FIXME Create token input.

    def match(self, reg): raise Exception("Token Inputs can't match regexps")
    def startswith(self, txt): raise Exception("Token Inputs can't match strings")


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
        """
        """

        if len(args) == 0:
            raise Exception("Can not have empty rules")

        if len(args) > 1 or not isinstance(args[0], Rule):
            self.productions = [Rule.getrule(r) for r in args]
        else:
            self.productions = args

        self.name = "_"
        self.post_subrule_name(", ".join([s.name for s in self.productions]))
        return self

    def post_subrule_name(self, productions_names):
        self.name = productions_names

    def set_skip(self, skip):
        self.skip = Rule.getrule(skip)
        return self

    def set_name(self, name):
        self.name = name
        return self


    def parse(self, input, currentresults=None, skip=None):
        """ Execute the rules
        """
        results = Results(self.name)

        if "skip" in self.__dict__: skip = self.skip

        if not self.productions:
            raise Exception("There are no productions defined for " + self.name)

        pos_save = input.pos

        for r in self.productions:
            subrule_result = None

            if skip:
                try:
                    skip.parse(input, Results())
                except SyntaxError as e:
                    # Nothing to skip.
                    pass

            try:
                r.parse(input, results, skip)
            except SyntaxError as e:
                input.rewind_to(pos_save)
                raise SyntaxError(u("In {0} ").format(self.name), input, [e])

        if self.action:
            currentresults.append(self.action(*results))
            return

        if len(results) == 1:
            currentresults.append(results[0])
        else:
            currentresults.append(results)


    def __repr__(self):
        return self.name


    def set_action(self, fn):
        """ Add an action function to the rules.

            This is to be used when the processor function is not directly given to
            the rule in its constructor.
        """
        if not fn:
            return self

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
            currentresults.append(self.string)
        else:
            raise SyntaxError(u("Expected {0}, but found \"{1}\"").format(self.name, input.current()), input)


class RegexpRule(Rule):
    def __init__(self, regexp):
        self.regexp = regexp
        self.name = "/" + self.regexp.pattern + "/"

    def parse(self, input, currentresults=None, skip=None):
        match = input.match(self.regexp)
        if match is not None:
            currentresults.append(match)
        else:
            raise SyntaxError(u("Expected {0}, but found \"{1}\"").format(self.name, input.current()), input)


class Predicate(Rule):
    def __init__(self, fn):
        self.fn = fn
        self.name = u("Predicate {0}").format(fn.__name__)

    def parse(self, input, currentresults=[], skip=None):
        if self.fn(*currentresults) is False:
            # None actually is a valid result.
            raise SyntaxError(u("{0} was not satisfied").format(self.name), input)


class FunctionRule(Rule):
    """ A rule that takes arguments.

        Beware, set_skip and set_action should NOT be set directly on this rule.
    """

    class InstanciatedRule(Rule):
        def __init__(self, fn, name, args):
            self.fn = fn
            self.name = name
            self.args = args
            self.action = None
            self.rule = None
            # self.skip = None

        def parse(self, input, currentresults, skip):
            if not self.rule:
                self.rule = self.fn(*self.args).set_name("*" + self.name)

                if hasattr(self, "skip") and not hasattr(self.rule, "skip"):
                    self.rule.set_skip(self.skip)

            results = Results(self.name)
            self.rule.parse(input, results, skip)
            if self.action:
                currentresults.append(self.action(*results))
                return
            if len(results) == 1:
                currentresults.append(results[0])
            else:
                currentresults.append(results)


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
        # r = self.fn(*args).set_name(self.name + arg_names)
        r = FunctionRule.InstanciatedRule(self.fn, self.name + arg_names, args)

        if self.action:
            r.set_action(self.action)

        if "skip" in self.__dict__:
            r.set_skip(self.skip)

        return r

    def parse(self, input, currentresults=None, skip=None):
        # Works if the rule doesn't need any arguments
        rule = self.instanciate()
        rule.parse(input, currentresults, skip)



class Repetition(Rule):
    """ A set of rules that can be repeated, like {m,n} in regular expressions.
    """


    def __init__(self, _from, _to, *args):
        self._from = _from
        self._to = _to
        self.rule = Rule(*args)
        super(Repetition, self).__init__()
        self.post_subrule_name(self.rule.name)


    def parse(self, input, currentresults=None, skip=None):
        results = Results(self.name)

        times = 0
        _from, _to = self._from, self._to

        save_pos = input.pos
        last_error = []

        while input.has_next() and (_to == -1 or times < _to):
            try:
                # Get the resultss.
                self.rule.parse(input, results, skip)
                times += 1
            except SyntaxError as e:
                last_error.append(e.suberrors[0])
                break


        if _from != -1 and times < _from:
            input.rewind_to(save_pos)
            raise SyntaxError(u("{1} needs to be repeated at least {0} times").format(_from, self.name), input, last_error)

        if self.action:
            # Actions in repetitions are in the form of lists.
            currentresults.append(self.action(results))
        else:
            currentresults.append(results)

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
        results = Results()
        super(Optional, self).parse(input, results, skip)

        if len(results[0]) == 0:
            currentresults.append(None)
        else:
            currentresults.append(results[0][0])

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
        save_pos = input.pos
        results = Results()
        try:
            # Results are ignored.
            super(Not, self).parse(input, results, skip)
        except SyntaxError as e:
            # Couldn't match the next rule, which is what we want, so
            # we just restore the parser's position so it will continue
            # parsing as normal.
            return
        input.rewind_to(save_pos)
        raise SyntaxError(u("In <{0}> Matched \"{1}\"").format(self.name, results), input)

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
        results = Results() # We're going to ignore any results.
        save_pos = input.pos
        # Try to parse our rules
        super(And, self).parse(input, results, skip)

        # If there was no error, we don't advance, which is what we want.
        # A syntax error is raised otherwise in our super() parse.
        input.rewind_to(save_pos)

    def post_subrule_name(self, sn):
        self.name = u("Look-Ahead {0}").format(sn)



class Either(Rule):
    """ Try parsing with several rules and return the result of the first
        one that works.

        The rules are given to the constructor as its arguments.
    """

    def parse(self, input, currentresults=None, skip=None):
        all_errors = []
        results = Results()

        for rule in self.productions:
            try:
                rule.parse(input, results, skip)
                res = results[0]

                if self.action:
                    currentresults.append(self.action(res))
                else:
                    currentresults.append(res)
                return
            except SyntaxError as e:
                all_errors.append(e)
                # We continue since the SyntaxError just means that we didn't match and
                # must try the next choice.
                continue

        raise SyntaxError(u("In [{0}], none of the provided choices matched").format(self.name), input, all_errors)

    def post_subrule_name(self, subn):
        self.name = u("either({0})").format(subn)


class Any(Rule):
    def __init__(self):
        self.name = "Any"

    def parse(self, input, currentresults=None, skip=None):
        if skip is None and "skip" in self.__dict__: skip = self.skip

        save_pos = input.pos

        if skip:
            try:
                skip.parse(input, Results())
            except SyntaxError as e:
                # Nothing to skip.
                pass

        if not input.has_next():
            input.rewind_to(save_pos)
            raise SyntaxError("Want anything, but no more input", input)

        any = input.current()
        input.advance(any)
        currentresults.append(any)

class MemoRule(Rule):
    """ A rule that memorizes itself for future uses.
    """

    def __init__(self, rule):
        self.memorized = None
        self.rule = rule
        self.name = "Memorizing({0})".format(rule.name)

    def parse(self, input, currentresults=None, skip=None):
        """
        """
        if not self.memorized:
            # act = self.__dict__.get("action", None)
            # if act: del self.__dict__["action"]
            self.rule.parse(input, currentresults, skip)

            res = currentresults[len(currentresults) - 1]
            if not isinstance(res, list) and not isinstance(res, tuple):
                self.memorized = Rule(res)
            else:
                self.memorized = Rule(*res)
        else:
            # The rule is now memorized, and we can execute it.
            self.memorized.parse(input, currentresults, skip)


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

        input = TextInput(input)
        results = Results()
        self.toprule.parse(input, results, None)

        if input.has_next():
            raise Exception(u("Finished parsing, but all the input was not consumed by the parser. Leftovers: '{0}'").format(input.input[input.pos:]))

        # Everything went fine, sending the results.
        if len(results) == 1:
            return results[0]
        return results


    def partial_parse(self, input, *args, **kwargs):
        """ Parse the given input and return only the result of the parsing,
            which is a tuple containing the (number of consumed characters, result of parsing).

            It can be used on some inputs on which we know the grammar can't or won't consume
            the totality of the input.
        """

        return self.toprule.parse(input)

