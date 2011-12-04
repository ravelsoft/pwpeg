"""
    @author Christophe Eymard <christophe@ravelsoft.com>
"""

from re import _pattern_type
import inspect
import sys

if sys.version_info >= (3, 0):
    # Python 3 removed entirely the unicode type, so to have
    # the text isinstance() still work, we just remap it to str (which
    # is unicode anyways)
    unicode = str


class SyntaxError(Exception):
    """ The way the text is parsed is by trial and error.

        When SyntaxError is caught by the parser, it goes up the caller
        chain to get to the first Choice() it finds to keep looking
        for a match.
    """


class IgnoreResult(object):
    """ This class is used by the parsing rules to determine wether to add the
        result of some parsing to the general result.

        Typically, the And and Not rules return this as well as and advancement
        of 0 when they match.
    """


def rule(*args, **kwargs):
    if len(args) == 1:
        return Rule(args[0])
    return lambda x: Rule(x, *args, **kwargs)


class Rule(object):
    """ A Grammar rule.
    """

    class ArmedRule(object):
        """ A Grammar rule which rules expression has been evaluated.
            Calling it like a function calls its parse() method with
            the right rules.

            The fact we have to arm rules is to allow the rules to be
            directly parametrizable.
        """

        def __init__(self, rule, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.rule = rule

        def __call__(self, text, skip=None):
            return self.rule.parse(text, rules=self.rule.rulefn(*self.args, **self.kwargs), skip=skip)


    def __call__(self, *args, **kwargs):
        """ Shortcut to create an ArmedRule out of the current rule.
        """

        return Rule.ArmedRule(self, *args, **kwargs)


    def __init__(self, *args, **kwargs):

        if len(args) == 0:
            print(args, kwargs)
            raise Exception("Can not have empty rules")

        if callable(args[0]) and not isinstance(args[0], Rule) and not isinstance(args[0], Rule.ArmedRule):
            # Passing a rule function
            self.rulefn = args[0]
            self.name = args[0].__name__

        elif len(args) == 1 and isinstance(args[0], tuple):
            self.rulefn = lambda: args[0]
            self.name = self.__class__.__name__

        else:
            self.rulefn = lambda: args
            self.name = self.__class__.__name__

        self.set_skip(kwargs.get("skip"))


    def set_skip(self, skip):
        if skip is not None:
            if not isinstance(skip, Rule):
                skip = Rule(skip)()
            else:
                skip = skip()

        self.skip = skip


    def _parse_terminal(self, text, terminal):
        """ Try to match a string in the input.
        """

        if text.startswith(terminal):
            return (len(terminal), terminal)
        return False


    def _parse_regexp(self, text, reg):
        """ Try to match a regexp and returns its entire match.
        """

        m = reg.match(text)
        if m and len(m.group(0)) > 0:
            return len(m.group(0)), m.group(0)
        return False


    def parse(self, text, rules=None, skip=None):
        """ Execute the rules
        """

        # The rule's skipping rule has precedence over the given skip parameter
        skip = self.skip or skip

        advanced = 0
        results = []

        if not isinstance(rules, tuple):
            rules = (rules,)
        
        for i, r in enumerate(rules):
            subrule_result = None

            if skip:
                try:
                    adv, res = skip(text[advanced:])
                    advanced += adv
                except SyntaxError as e:
                    # Nothing to skip.
                    pass

            # We are checking a simple text terminal
            if isinstance(r, unicode) or isinstance(r, str):
                subrule_result = self._parse_terminal(text[advanced:], r)

            # We have to handle a regexp.
            elif isinstance(r, _pattern_type):
                subrule_result = self._parse_regexp(text[advanced:], r)

            # We have an armed rule, which technically means that the rule function of
            # the rule has already been evaluated.
            elif isinstance(r, Rule.ArmedRule):
                subrule_result = r(text[advanced:], skip=skip)

            # We have a rule that hasn't be armed. We assume that it's rule function doesn't
            # take arguments.
            elif isinstance(r, Rule):
                r = r()
                subrule_result = r(text[advanced:], skip=skip)

            # Otherwise, this is just a construct that does some checking of its own.
            else:
                # The construct is called with the results we have so far.
                # It will raise SyntaxError if it returns false.
                res = r(*results)

                if res is False:
                    raise SyntaxError("Check returned false")

                # If this function was the last rule, it means it was actually a processor
                # function given as a lambda, so we return its results.
                if i == len(rules) - 1:
                    return advanced, res

                continue

            if subrule_result is False:
                # FIXME We should keep in Either a list of all the tried combination
                # that failed, as well as the position where the failing was
                # found.

                # The subrule_result returning false is only when matching a terminal
                # or a regular expression.
                raise SyntaxError(repr(r))

            # If everything went according to plan, the subrule_result is an tuple
            # with the number of consumed characters and the result of the processing
            # of the rule.
            sub_adv, sub_processed_result = subrule_result

            advanced += sub_adv

            if sub_processed_result is not IgnoreResult:
                results.append(sub_processed_result)

        if len(results) == 1:
            return advanced, results[0]

        return advanced, results


    def set_processor(self, fn):
        """ Add a processor function to the rules.
            
            This is to be used when the processor function is not directly given to
            the rule in its constructor.
        """

        rulesfn = self.rulesfn
        self.rulesfn = lambda *args, **kwargs: rulesfn(*args, **kwargs) + (fn,)
        return fn

    def __repr__(self):
        return "<{0}>".format(self.name)



class Repetition(Rule):
    """ A set of rules that can be repeated, like {m,n} in regular expressions.
    """


    def __init__(self, _from, _to, *args, **kwargs):
        self._from = _from
        self._to = _to
        super(Repetition, self).__init__(*args, **kwargs)


    def parse(self, text, rules, skip=None):
        times = 0
        _from, _to = self._from, self._to

        advance = 0

        result = []

        while advance < len(text) and (_to == -1 or times < _to):
            try:
                # Get the results.
                adv, res = super(Repetition, self).parse(text[advance:], rules, skip)
            except SyntaxError as e:
                break

            # Parsing was successful, so we add it to the result.
            advance += adv

            if res is not IgnoreResult:
                result.append(res)

            # We repeated one more time !
            times += 1

        if _from != -1 and times < _from:
            raise SyntaxError("Rule needs to be repeated at least {0} times".format(_from))

        return advance, result



class OneOrMore(Repetition):
    """ A Repetition that acts like the + in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(OneOrMore, self).__init__(1, -1, *args, **kwargs)



class ZeroOrMore(Repetition):
    """ A Repetition that acts like the * in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(ZeroOrMore, self).__init__(0, -1, *args, **kwargs)




class Optional(Repetition):
    """ The equivalent of the ? in regular expressions.
    """

    def __init__(self, *args, **kwargs):
        super(Optional, self).__init__(0, 1, *args, **kwargs)


    def parse(self, text, rules, skip=None):
        adv, res = super(Optional, self).parse(text, rules, skip)

        if len(res) == 0:
            return None

        return res[0]



class Not(Rule):
    """ Look ahead in the input. If no syntax error is received, then
        raise a SyntaxError.

        This rule is used to check that a rule does not apply on the input
        following the current position.

        It does *not* advance the parser position.
    """

    def parse(self, text, rules, skip):
        try:
            super(Not, self).parse(text, rules, skip)
            raise SyntaxError("Matched input that should not have been matched")
        except SyntaxError as e:
            # Couldn't match the next rule, which is what we want, so
            # we return a result that won't advance the parser.
            return 0, IgnoreResult
                


class And(Rule):
    """ Look ahead in the input. If its rules can be applied, then continue
        parsing from the same place we were before executing this rule.

        This rule is used to check that the following input contains a rule we
        want.

        It does *not* advance the parser position.
    """

    
    def parse(self, text, rules, skip):
        # Try to parse our rules
        super(And, self).parse(text, rules, skip)

        # If there was no error, we don't advance, which is what we want.
        # A syntax error is raised otherwise in our super() parse.
        return 0, IgnoreResult



class Either(Rule):
    """ Try parsing with several rules and return the result of the first
        one that works.

        The rules are given to the constructor as its arguments.
    """

    def __init__(self, *args, **kwargs):
        self.set_skip(kwargs.get("skip"))
        self.rules = []

        for a in args:
            if isinstance(a, Rule):
                self.rules.append(a)
            else:
                self.rules.append(Rule(a))

        self.rulefn = lambda: None
        self.name = "Either"


    def parse(self, text, rules, skip):
        skip = self.skip or skip

        for rule in self.rules:
            try:
                r = rule()
                return r(text, skip)
            except SyntaxError as e:
                # FIXME should store the error

                # We continue since the SyntaxError just means that we didn't match and
                # must try the next choice.
                continue

        raise SyntaxError("None of the provided choices matched")



class R(Rule):
    """ A proxy Rule to call rules not yet defined in the scope.

        What it does is by using the `inspect` module, it stores a reference
        to the module where it is instanciated as well as the name of the rule
        in said module. 
        
        When the rule is to be used for parsing, it fetches it from the module
        and executes it.

        This means that this Rule can be used to refer to rules that will be
        defined later in the code, or even the current rule if we need
        recursion.
    """
    
    def __init__(self, rulename, *args, **kwargs):

        c = inspect.currentframe()
        self.gl = c.f_back.f_globals
        self.name = rulename


    def parse(self, *args, **kwargs):
        raise Exception("This method should never be called directly.")


    def __call__(self, *args, **kwargs):
        """ Return the result of calling the real rule after fetching
            it from its global object.
        """

        return self.gl[self.name](*args, **kwargs)



class Parser(object):
    """ A parser that parses a text input.

        It is given a top-level rule with which it will start the parsing,
        as well as a skip rule which will be checked agains before executing
        any rule, useful to remove white spaces and comments.
    """

    def __init__(self, toprule):

        if not isinstance(toprule, Rule):
            toprule = Rule(toprule)

        self.toprule = toprule


    def parse(self, text, *args, **kwargs):
        """ Parse the given input and return the result of the parsing.

            An Exception will be raised if the parsing does not use the
            integrality of the text.
        """

        parse = self.toprule(*args, **kwargs)
        result = parse(text)

        if result[0] != len(text):
            raise Exception("Finished parsing, but all the input was not consumed by the parser. Leftovers: {0}".format(text[result[0]:]))

        # Everything went fine, sending the results.
        return result[1]


    def partial_parse(self, text, *args, **kwargs):
        """ Parse the given input and return only the result of the parsing,
            which is a tuple containing the (number of consumed characters, result of parsing).

            It can be used on some inputs on which we know the grammar can't or won't consume
            the totality of the input.
        """

        parse = self.toprule(*args, **kwargs)
        return parse(text)

