import re
from .pwpeg import *

from functools import wraps
from itertools import chain


def _AllBut(but, escape=None, skip=None):
    """ matches everything *but* the but parameter until it finds it,
        unless it is escaped.

        warning; this rule is very slow compared to its regexp version
        and should only be used in token streams to get results more
        interesting than a list of single characters.

        Args:
            but: the rule that we do not want to match.
            escape: an escape rule to allow the but rule to be in the results.
            skip: a custom skip; by default it is reset to None.
        Results:
            the corresponding Rule.
    """

    if escape:
        return OneOrMore(
            Either(
                Rule(escape, but).set_action(lambda escape, but: but),
                Rule(Not(but), Any())
            )
        ).set_skip(skip)
    else:
        return OneOrMore(Not(but), Any()).set_skip(skip)

AllBut = FunctionRule(_AllBut)
AllBut.set_name("All But")


def _Balanced(start, end, escape):
    """
    """

    balanced_inside = FunctionRule()

    def __balanced_inside():
        return Either(
            # Recurse on a balanced expression
            Rule(start, Optional(balanced_inside), end).set_action(lambda s, m, e: [s] + (m or []) + [e]),

            # Or simply gobble up characters that neither start nor end or their
            # backslashed version.
            AllBut.instanciate(Either(start, end), escape)
        )

    balanced_inside.set_fn(__balanced_inside)

    return Rule(start, ZeroOrMore(balanced_inside), end).set_action(lambda s, l, e: [s] + list(chain(*l)) + [e]).set_skip(None)

Balanced = FunctionRule(_Balanced)
Balanced.set_name("Balanced")


def _DelimitedBy(delimiter, escape):
    """
    """

    return delimiter, AllBut(delimiter, escape), delimiter
DelimitedBy = FunctionRule(_DelimitedBy).set_skip(None)


def _RepeatingSeparated(rule, separator, at_least, at_most):
    """
    """
    def _repeat_action(first, rest):
        rest.insert(0, first)
        return rest

    if at_most == -1:
        # This is just so that it is equal to -1 in the end.
        at_most = 0

    if at_least == 0:
        return Optional(Rule(
            rule,
            Repetition(0, at_most - 1,
                separator,
                rule
            ).set_action(lambda l: map(lambda e: e[1], l))
        ).set_action(_repeat_action))

    return Rule(
        rule,
        Repetition(at_least - 1, at_most - 1,
            separator,
            rule
        ).set_action(lambda res: map(lambda x: x[1], res))
    ).set_action(_repeat_action)

RepeatingSeparated = FunctionRule(_RepeatingSeparated)

def _ZeroOrMoreSeparated(rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, 0, -1)
ZeroOrMoreSeparated = FunctionRule(_ZeroOrMoreSeparated)


def _OneOrMoreSeparated(rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, 1, -1)
OneOrMoreSeparated = FunctionRule(_OneOrMoreSeparated)


def _ExactlySeparated(how_much, rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, how_much, how_much)
ExactlySeparated = FunctionRule(_ExactlySeparated)


def _RepetitionSeparated(at_least, at_most, rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, at_least, at_most)
RepetitionSeparated = FunctionRule(_RepetitionSeparated)


re_more_indent = re.compile("[ \t]+")
re_lead = re.compile("^[ \t]+")
to_eol = Rule(re.compile("[ \t]*"))
empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))


def _associative(right=True):

    def _wrapped(production, operator, builder=None):
        ''' Parse sub-expressions separated by a binary operator zero or
            more times, and return the tree of their associativity in the
            polish style notation (operator first.)

            The builder is a callable taking three arguments; (operator, left, right)
            that is called to build nodes if the desired result is more complicated
            than tuples.

            Ex: for an input of tokens "a+b-c" and the rule
            RightAssociative(re.compile('\w+'), Either('+', '-')), the result shall be
            ('+', 'a', ('-', 'b', 'c')) if no builder was provided.

            In the case there is no operators, then the result is the matched
            element instead of a list.
            Ex: for an input of token 'a', the result is 'a', not ['a']

            Args:
                production: the production rule.
                operator: the operator rule.
                builder: a callable(op, lhs, rhs)
            Returns:
                the resulting tree or a single matched elements if there was no operator.
        '''

        # Default builder
        builder = builder if builder else lambda op, lhs, rhs: (op, lhs, rhs)

        def left_assoc(lst, idx=0):
            idx = 1
            l = len(lst)
            tmpbuild = builder(lst[idx], lst[idx - 1], lst[idx + 1])

            while idx < l - 2:
                idx += 2
                tmpbuild = builder(lst[idx], tmpbuild, lst[idx + 1])

            return tmpbuild

        def right_assoc(lst):
            idx = len(lst) - 3
            tmpbuild = builder(lst[idx + 1], lst[idx], lst[idx + 2])

            while idx > 0:
                idx -= 2
                tmpbuild = builder(lst[idx + 1], lst[idx], tmpbuild)

            return tmpbuild

        def action(first, lst):
            if not lst:
                return first

            newlst = [first]
            # First flatten the list, which is a series of [[op, operand], ...]
            for item in lst:
                newlst += item

            return right_assoc(newlst) if right else left_assoc(newlst)

        return Rule(production, ZeroOrMore(operator, production)).set_action(action)

    return _wrapped

RightAssociative = FunctionRule(_associative(right=True))
LeftAssociative = FunctionRule(_associative(right=False))

####################################################################
#       Regexp Helpers

def delimitedby_regexp(char, escape):
    '''
        Create a regular expression describing a string delimited by a delimiter
        with an escape character to match the delimiter inside it.

        To match a correctly formed string; delimitedby_regexp('\'', '\\') will
        create a regexp matching anything between two single quotes, where \\' will
        escape it.

        Args:
            char: a regular expression representing a delimiter. Beware that if a
                range is specified, then the other end will also be a range.
                ['"] for instance will match strings like 'hello" or "hello'
            escape: A regular expression for an escape sequence.
        Returns:
            a regular expression
    '''
    return re.compile(u("{0}({1}{0}|(?!{0}).)*{0}").format(re.escape(char), re.escape(escape)), re.DOTALL)


def allbut_regexp(patterns, escape):
    '''
        Match anything but *but* the provided patterns.

        Args:
            patterns: a list of regular expression patterns that we
                don't want to match.
            escape: an escape pattern allowing one of the forbidden
                pattern to still be matched.
        Returns:
            a regular expression.
    '''
    if not isinstance(patterns, list):
        patterns = [patterns]
    return re.compile("({1}({0})|(?!({0})).)+".format("|".join([re.escape(s) for s in patterns]), re.escape(escape)), re.DOTALL)
