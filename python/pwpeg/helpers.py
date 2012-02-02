import re
from .pwpeg import *

from functools import wraps


def _AllBut(but, escape):
    """
    """

    return OneOrMore(
        Either(
            Rule(escape, but).set_action(lambda escape, but: but),
            Rule(Not(but), Any())
        )
    )

AllBut = ParametrizableRule(_AllBut).set_skip(None)
AllBut.set_name("All But")


def _Balanced(start, end, escape):
    """
    """

    balanced_inside = ParametrizableRule()

    def __balanced_inside():
        return Either(
            # Recurse on a balanced expression
            Rule(start, Optional(balanced_inside), end).set_action(lambda s, m, e: [s] + (m or []) + [e]),

            # Or simply gobble up characters that neither start nor end or their
            # backslashed version.
            AllBut.instanciate(Either(start, end), escape)
        )

    balanced_inside.set_fn(__balanced_inside)

    return Rule(start, ZeroOrMore(balanced_inside), end).set_action(lambda s, l, e: [s] + l + [e])

Balanced = ParametrizableRule(_Balanced).set_skip(None)
Balanced.set_name("Balanced")


def _DelimitedBy(char, escape):
    """
    """

    return char, AllBut.instanciate(char, escape), char
DelimitedBy = ParametrizableRule(_DelimitedBy).set_skip(None)

def _RepeatingSeparated(rule, separator, at_least, at_most):
    """
    """
    if at_most == -1:
        # This is just so that it is equal to -1 in the end.
        at_most = 0

    if at_least == 0:
        return Optional(rule, Repetition(0, at_most - 1, separator, rule)).set_action(lambda _1, r: r)

    return Rule(rule, Repetition(at_least - 1, at_most - 1, separator, rule).set_action(lambda _1, _2: _2))

RepeatingSeparated = ParametrizableRule(_RepeatingSeparated)

def _repeat_action(rule, separator, at_lesat, at_most, first, rest):
    rest.insert(0, first)
    return rest
RepeatingSeparated.set_action(_repeat_action)

def _ZeroOrMoreSeparated(rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, 0, -1)
ZeroOrMoreSeparated = ParametrizableRule(_ZeroOrMoreSeparated)


def _OneOrMoreSeparated(rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, 1, -1)
OneOrMoreSeparated = ParametrizableRule(_OneOrMoreSeparated)


def _ExactlySeparated(how_much, rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, how_much, how_much)
ExactlySeparated = ParametrizableRule(_ExactlySeparated)


def _RepetitionSeparated(at_least, at_most, rules, sep):
    return RepeatingSeparated.instanciate(rules, sep, at_least, at_most)
RepetitionSeparated = ParametrizableRule(_RepetitionSeparated)


re_more_indent = re.compile("[ \t]+")
re_lead = re.compile("^[ \t]+")
to_eol = Rule(re.compile("[ \t]*"))
empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))


def la_tree_from_list_leftmost(leftmost, lst, action, idx=-1):
    return action(
        la_tree_from_list_leftmost(leftmost, lst, action, idx - 1),
        lst[idx][0],
        lst[idx][1]) if lst and idx >= -len(lst) else action(leftmost)

def ra_tree_from_list_rightmost(rightmost, lst, action, idx=0):
    """
    """

    return action(lst[idx][0],
                  lst[idx][1],
                  ra_tree_from_list_rightmost(rightmost, lst, action, idx + 1)) if lst and idx < len(lst) else action(rightmost, None, None)


def _LeftAssociative(op_ParametrizableRule, sub_ParametrizableRule):

    def reverse(leftmost, lst, idx=-1):
        """ Recursive function to make what we parsed as a left-associative succession of operators.
        """
        return la_tree_from_list_leftmost(leftmost, lst, action, idx)

    return Rule(sub_ParametrizableRule, ZeroOrMore(op_ParametrizableRule, sub_ParametrizableRule)).set_action(reverse)
LeftAssociative = ParametrizableRule(_LeftAssociative)

def _RightAssociative(op_ParametrizableRule, sub_ParametrizableRule):

    def _act(left, opt, idx=0):
        """ Recursive function to make what we parsed as a left-associative succession of operators.
        """

        return action(left) if not opt else action(left, opt[0], opt[1])

    self_recurse = R("RightAssociative", op_ParametrizableRule, sub_ParametrizableRule, action)

    return Rule(sub_ParametrizableRule, Optional(op_ParametrizableRule, self_recurse)).set_action(_act)
RightAssociative = ParametrizableRule(_RightAssociative)

####################################################################
#       Regexp Helpers

def delimitedby_regexp(char, escape):
    return re.compile(u("{0}({1}{0}|(?!{0}).)*{0}").format(re.escape(char), re.escape(escape)))

def allbut_regexp(char, escape):
    return re.compile(u("({1}{0}|(?!{0}).)*").format(re.escape(char), re.escape(escape)))
