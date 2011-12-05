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
EOL = "\n"

############################

space_and_comments = re.compile("(\s+|#.*$)*", re.M)

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"))

to_eol = Rule(re.compile("[^\n]*\n?"), lambda x: x.trim())

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

regexp = Rule(re_regexp)

starting_code = Rule("%%", "%%")

#############################

@rule(skip=None)
def balanced(start, end):
    return Either(
        # Recurse on a balanced expression
        (start, R("balanced", start, end), end, lambda s, m, e: s + m + e),

        # Or simply gobble up characters that neither start nor end or their
        # backslashed version.
        re.compile("({0}|{1}|.)*".format('\\' + re.escape(start), '\\' + re.escape(end)))
    )

@rule
def delimited(char):
    return char, re.compile("({0}|.)*".format('\\' + re.escape(char)), char

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

    return leading_indent(indent), to_eol, Optional(empty_lines), action_set_indentation


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
    (re.compile("\\[^ \t\n\[\]\|\)]+"), lambda s: "'" + s.replace('\'', '\\\'') + "'")
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

external_rulename = Either(
    (DOLLAR, identifier),
    (DOLLAR, balanced_paren),
    skip=None
)

predicate = Rule(
    Either(AMPS, EXCL), balanced_braces
)

rulename = Rule(identifier, Optional(balanced_paren))

ruleargs = Rule(identifier, value, ZeroOrMore(COMMA, identifier, value))

ruledecl = Rule(
    rulename, Optional(ruleargs)
)

grammarrule = Rule(
    ruldecl, EQUAL, productions
)

toplevel = Rule(Optional(starting_code), OneOrMore(grammarrule), skip=space_and_comments)

parser = Parser(toplevel)

