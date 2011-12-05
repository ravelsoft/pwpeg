"""
    @author Christophe Eymard <christophe.eymard@ravelsoft.com>
"""

from pwpeg import *
import re

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


PIPE = "|"
SPACE = re.compile("\s*")
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
    return start, balanced_inside(start, end, escape), end, Action(lambda _1, _2, _3: _1 + _2 + _3)

@rule
def delimited(char, escape='\\'):
    return char, re.compile("({0}|[^{1}])*".format(escape + re.escape(char), re.escape(char))), char

@rule
def repeating_delimited(rule, delim):
    return rule, ZeroOrMore(delim, rule, Action(lambda _1, _2: rule)), Action(lambda first, n: [first] + n)

############################

space_and_comments = re.compile("(\s+|#.*$)*", re.M)

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"), name="Identifier")

to_eol = Rule(re.compile("[^\n]*\n?"), lambda x: x.trim())

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

regexp = Rule(re_regexp)

starting_code = Rule("%%", "%%")

#################################################################################

@rule
def leading_indent(indent):

    if indent.isset():
        # Since we know how many leading spaces our indentation is at,
        # we want to match its exact number.
        return re.compile("[ \t]{0}".format(indent.value()))

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
        return "".join(lst)

    return indented_line(indentation), ZeroOrMore(indented_line(indentation)), _action_concatenate

##############################################################################################

balanced_paren      = balanced("(", ")")
balanced_braces     = balanced("{", "}")
balanced_brackets   = balanced("[", "]")

string = Either(
    delimited('\''), 
    delimited('"'),
    (re.compile("\\[^ \t\n\[\]\|\)]+"), Action(lambda s: "'" + s.replace('\'', '\\\'') + "'"))
)

regexp = Rule(
    delimited('/'), Optional(re.compile('[idsmlux]+')),
    skip=None
)

action = Either(
    balanced(LBRACE, RBRACE),
    Rule(ARROW, Optional(LINE_SPACE), EOL, indented_block, skip=None),
    (ARROW, to_eol)
)

external_rule = Either(
    (DOLLAR, identifier),
    (DOLLAR, balanced_paren),
    skip=None
)

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

label = Rule(identifier, COLON, Action(lambda _1, _2: _1), name="Production Label")

full_rule = Rule(Optional(label), real_rule, Not(EQUAL), name="Full Rule")

either_rule = Rule(
    LBRACKET, repeating_delimited(full_rule, PIPE), RBRACKET, Action(lambda _1, rules, _2: rules)
)

rule_repeat = OneOrMore(full_rule)

rules = Rule(
    repeating_delimited(rule_repeat, PIPE),
    name="Rules+"
)

####################### Rule declaration ###########################

rulearg = Rule(identifier, real_rule)

ruledecl = Rule(
    rulename, Optional(repeating_delimited(rulearg, COMMA)),
    name="Rule Declaration"
)

grammarrule = Rule(
    ruledecl, EQUAL, rules,
    name="Grammar Rule"
)

toplevel = Rule(Optional(starting_code), OneOrMore(grammarrule), skip=space_and_comments, name="Top Level")

parser = Parser(toplevel)

#####################################################

# p2 = Parser(repeating_delimited('a', ','))
# print(p2.parse('a,a,a'))

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

