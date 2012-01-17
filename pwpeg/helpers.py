import re
from pwpeg import *

class LaterValue(object):
    """
    """

    def __init__(self, default):
        self.default = default

    def set_if_unset(self, value):
        if not self.isset():
            self._value = value

    def value(self):
        if not self.isset():
            return self.default
        return self._value

    def isset(self):
        return "_value" in self.__dict__

@rule
def AllBut(but, escape="\\"):
    """
    """

    if not isinstance(but, list):
        but = [but]

    _not = "|".join([re.escape(b) for b in but])

    if escape:
        escaped = [escape + re.escape(a) for a in but]
    else:
        escaped = []

    escaped.append(".")
    _valid = "|".join(escaped)
    regexp = "((?!{_not})({_valid}))+".format(_not=_not, _valid=_valid)

    return re.compile(regexp, re.DOTALL)

@rule(skip=None)
def Balanced(start, end, escape="\\"):
    """
    """

    balanced_inside = None

    @rule
    def __balanced_inside():
        return Either(
            # Recurse on a balanced expression
            (start, balanced_inside, end, Action(lambda s, m, e: s + m + e)),

            # Or simply gobble up characters that neither start nor end or their
            # backslashed version.
            AllBut([start, end])
        )

    balanced_inside = __balanced_inside

    return start, ZeroOrMore(balanced_inside), end, Action(lambda s, l, e: (s, "".join(l), e))

@rule
def DelimitedBy(char, escape='\\'):
    """
    """

    return char, AllBut(char, escape), char

@rule
def __repeating_separated(rules, separator, at_least, at_most):
    """
    """

    def __action(first, rest):
        rest.insert(0, first)
        return rest

    if at_most == -1:
        # This is just so that it is equal to -1 in the end.
        at_most = 0

    if at_least == 0:
        return Optional(rules, Repetition(0, at_most - 1, separator, rules, Action(lambda _1, r: r)), Action(__action))

    return rules, Repetition(at_least - 1, at_most - 1, separator, rules, Action(lambda _1, _2: _2)), Action(__action)

@rule
def ZeroOrMoreSeparated(rules, sep):
    return __repeating_separated(rules, sep, 0, -1)

@rule
def OneOrMoreSeparated(rules, sep):
    return __repeating_separated(rules, sep, 1, -1)

@rule
def ExactlySeparated(how_much, rules, sep):
    return __repeating_separated(rules, sep, how_much, how_much)

@rule
def RepetitionSeparated(at_least, at_most, rules, sep):
    return __repeating_separated(rules, sep, at_least, at_most)

re_lead = re.compile("^[ \t]+")
to_eol = Rule(re.compile("[ \t]*"))
empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

@rule(skip=None)
def IndentedBlock(grammar_rule, indentation=1):
    """
    """

    indent = LaterValue(indentation)

    @rule
    def __leading_indent():

        if indent.isset():
            # Since we know how many leading spaces our indentation is at,
            # we want to match its exact number.
            pattern = "[ \t]{{{0}}}".format(indent.value())
            return re.compile(pattern)

        # The first time around, we eat all the spaces.
        # Only after does this rule only eat the leading spaces.
        return re_lead


    @rule
    def __indented_line():

        def action_set_indentation(lead, line, eol, opt):
            ind = len(lead)

            indent.set_if_unset(ind)

            # the empty lines are just squizzed out of the parsed text.
            return lead, line

        if indentation == 0:
            return grammar_rule, Optional(to_eol), Optional(empty_lines), Action(lambda a, b, c: ("", a))
        return __leading_indent(), grammar_rule, Optional(to_eol), Optional(empty_lines), Action(action_set_indentation)

    return OneOrMore(__indented_line)

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

@rule
def LeftAssociative(op_rule, sub_rule, action=None):

    def reverse(leftmost, lst, idx=-1):
        """ Recursive function to make what we parsed as a left-associative succession of operators.
        """
        return la_tree_from_list_leftmost(leftmost, lst, action, idx)

    if action:
        return Rule(sub_rule, ZeroOrMore(op_rule, sub_rule), Action(reverse))
    else:
        return Rule(sub_rule, ZeroOrMore(op_rule, sub_rule))

@rule
def RightAssociative(op_rule, sub_rule, action=None):

    def _act(left, opt, idx=0):
        """ Recursive function to make what we parsed as a left-associative succession of operators.
        """

        return action(left) if not opt else action(left, opt[0], opt[1])

    self_recurse = R("RightAssociative", op_rule, sub_rule, action)

    if action:
        return Rule(sub_rule, Optional(op_rule, self_recurse), Action(_act))
    else:
        return Rule(sub_rule, Optional(op_rule, self_recurse))

