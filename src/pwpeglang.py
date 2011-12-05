"""
    @author Christophe Eymard <christophe.eymard@ravelsoft.com>
"""

import re

from pwpeg import *
from pwast import *

re_regexp = re.compile("/(\\/|[^/])+/[idsmlux]+")
re_lead = re.compile("^[ \t]+")

class LaterValue(object):

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

def concat(arr):
    res = []
    for a in arr:
        if isinstance(a, list): 
            res.append(_concat(a))
        else:
            res.append(a)

    return "".join(res)

PIPE = "|"
SPACE = Rule(re.compile("\s*"), name="Whitespaces")
LINE_SPACE = re.compile("[ \t]*")
LPAREN = "("
RPAREN = ")"
LBRACKET = "["
RBRACKET = "]"
LBRACE = "{"
RBRACE = "}"
ARROW = "->"
DOLLAR = "$"
AMPS = "&"
EXCL = "!"
EQUAL = "="
COLON = ":"
COMMA = ","
EOL = "\n"

#############################

@rule
def balanced_inside(start, end, escape="\\"):
    return Either(
        # Recurse on a balanced expression
        (start, R("balanced", start, end), end, Action(lambda s, m, e: s + m + e)),

        # Or simply gobble up characters that neither start nor end or their
        # backslashed version.
        re.compile("({0}|{1}|[^{2}{3}])*".format(escape + re.escape(start), escape + re.escape(end), re.escape(start), re.escape(end)))
    )

@rule(skip=None)
def balanced(start, end, escape="\\"):
    return start, balanced_inside(start, end, escape), end

@rule
def delimited(char, escape='\\'):
    return char, re.compile("({0}|[^{1}])*".format(escape + re.escape(char), re.escape(char))), char

@rule
def repeating_delimited(rule, delim):
    return rule, ZeroOrMore(delim, rule, Action(lambda _1, _2: _2)), Action(lambda first, n: [first] + n)

############################

space_and_comments = re.compile("(\s+|#.*$)*", re.M)

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"), name="Identifier")

to_eol = Rule(re.compile("[^\n]*", re.M))

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

regexp = Rule(re_regexp)

starting_code = Rule("%%", "%%")

#################################################################################

@rule
def leading_indent(indent):

    if indent.isset():
        # Since we know how many leading spaces our indentation is at,
        # we want to match its exact number.
        pattern = "[ \t]{{{0}}}".format(indent.value())
        return re.compile(pattern)

    # The first time around, we eat all the spaces.
    # Only after does this rule only eat the leading spaces.
    return re_lead


@rule
def indented_line(indent):

    def action_set_indentation(lead, line, opt):
        ind = len(lead)
 
        indent.set_if_unset(ind)

        # the empty lines are just squizzed out of the parsed text.
        return line

    return leading_indent(indent), to_eol, Optional(empty_lines), Action(action_set_indentation)


@rule(skip=None)
def indented_block(indentation=LaterValue(1)):

    def _action_concatenate(first_line, others):
        lst = [first_line] + others
        return "\n".join(lst)

    return indented_line(indentation), ZeroOrMore(indented_line(indentation)), Action(_action_concatenate)

##############################################################################################

balanced_paren      = balanced("(", ")")
balanced_braces     = balanced("{", "}")
balanced_brackets   = balanced("[", "]")

# Re-concatenate the string.
string = Either(
    (delimited('\''), Action(lambda x: "".join(x))),
    (delimited('"'), Action(lambda x: "".join(x))),
    # Backslash quoted string
    (re.compile("\\[^ \t\n\[\]\|\)]+"), Action(lambda s: "'" + s.replace('\'', '\\\'') + "'"))
)

regexp = Rule(
    delimited('/'), Optional(re.compile('[idsmlux]+')),
    skip=None
)

action = Either(
    balanced(LBRACE, RBRACE),
    Rule(Optional(SPACE), ARROW, Optional(LINE_SPACE), EOL, indented_block, skip=None, name="Multi Line Action"),
    Rule(ARROW, to_eol, skip=None, name="Single Line Action")
)

external_rule = Either(
    (DOLLAR, identifier),
    (DOLLAR, balanced_paren),
    skip=None
)

#######################################################

predicate = Rule(
    Either(AMPS, EXCL), balanced_braces
)


rulename = Rule(identifier, Optional(balanced_paren), name="Rule Name")

real_rule = Rule(Either(
    regexp,
    string,
    rulename,
    external_rule,
    R("either_rule")
), name="Real Rule")

label = Rule(identifier, COLON, Action(lambda name, _2: name), name="Production Label")


full_rule = Rule(Optional(label), Not(R("ruledecl")), real_rule, Optional(action), name="Full Rule")

either_rule = Rule(
    LBRACKET, repeating_delimited(full_rule, PIPE), RBRACKET, Action(lambda _1, rules, _2: rules)
)

rule_repeat = OneOrMore(Either(full_rule, predicate))

rules = Rule(
    repeating_delimited(rule_repeat, PIPE),
    name="Rules+"
)

####################### Rule declaration ###########################

rulearg = Rule(identifier, real_rule, name="Rule Argument")

ruledecl = Rule(
    rulename, Optional(repeating_delimited(rulearg, COMMA)), EQUAL,
    name="Rule Declaration"
)

grammarrule = Rule(
    ruledecl, rules,
    name="Grammar Rule"
)

toplevel = Rule(Optional(starting_code), OneOrMore(grammarrule), skip=space_and_comments, name="Top Level")

###################### <<< ACTIONS >>>

def _predicate_action(op, braced_code):
    code = braced_code[1].strip()
    if op == EXCL:
        code = "not({0})".format(code)
    return AstPredicate(code)

predicate.set_action(_predicate_action)

#####################################################

parser = Parser(toplevel)

#####################################################

if __name__ == "__main__":
    from optparse import OptionParser
    optparser = OptionParser()

    options, args = optparser.parse_args()

    for a in args:
        f = open(a, "r")
        s = f.read()
        f.close()
        adv, res = parser.partial_parse(s)
        left = s[adv:]
        print(res)
        if left:
            print("\n---\n")
            print(left)

