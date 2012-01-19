#!/usr/bin/env python
"""
    @author Christophe Eymard <christophe.eymard@ravelsoft.com>
"""

import re

from .pwpeg import *
from .helpers import *
from .pwast import *

re_regexp = re.compile("/(\\/|[^/])+/([idsmlux]+)?")

def _regexp_action(contents, flags):
    args = []

    args.append('\'' + contents.replace('\'', '\\\'') + '\'')

    if flags:
        fs = []
        for f in flags:
            fs.append("re.{0}".format(f.upper()))
        fs = " & ".join(fs)
        args.append(fs)

    return "re.compile({0})".format(", ".join(args))

def replace_regexps(t):
    # print t
    res = re_regexp.sub(lambda m: _regexp_action(m.group(0)[1:-1], m.group(2)), t)
    #import sys
    #sys.exit()
    # print res
    return res

def concat(arr):
    if arr is None or len(arr) == 0:
        return ""

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
STAR = "*"
QUESTION = "?"
PLUS = "+"
EOL = "\n"

############################

space_and_comments = re.compile("(\s+|#.*$)*", re.M)

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"), name="Identifier")

to_eol = Rule(re.compile("[^\n]*", re.M))

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

number = Rule(re.compile("-?[0-9]+"), Action(lambda n: int(n)))

starting_code = Rule("%%", re.compile("((?!%%).)*", re.DOTALL), "%%", Action(lambda b, t, e: t))

##############################################################################################

balanced_paren      = Balanced("(", ")")
balanced_braces     = Balanced("{", "}")
balanced_brackets   = Balanced("[", "]")

# Re-concatenate the string.
string = Either(
    (DelimitedBy('\''), Action(lambda x: "".join(x))),
    (DelimitedBy('"'), Action(lambda x: "".join(x))),
    # Backslash quoted string
    (re.compile("\\\\[^ \t\n\[\]\|\)]+"), Action(lambda s: "'" + s[1:].replace('\'', '\\\'').replace('\\', '\\\\') + "'")),
    skip=None
)

regexp = Rule(
    DelimitedBy('/'), Optional(re.compile('[idsmlux]+')), Action(lambda d, f: _regexp_action(d[1], f)),
    skip=None
)

re_anything_inline = Rule(re.compile("[^\n]*", re.M))

action = Either(
    Rule(Balanced(LBRACE, RBRACE),
            Action(lambda b: b[1].strip()),
        name="Brace Action"),

    Rule(Optional(SPACE), ARROW, Optional(LINE_SPACE), EOL, IndentedBlock(re_anything_inline),
            Action(lambda sp, arrow, more_space, eol, code: "\n".join([t[1] for t in code])),
        skip=None, name="Multi Line Action"),

    Rule(ARROW, to_eol,
            Action(lambda arrow, line: line.strip()),
        skip=None, name="Single Line Action")
)

external_rule = Either(
    (DOLLAR, identifier, Action(lambda d, i: i)),
    (DOLLAR, balanced_paren, Action(lambda d, b: concat(b))),
    skip=None
)

#######################################################

predicate = Rule(
    "&", balanced_braces, Action(lambda _0, p: AstPredicate(p[1]))
)


rulename = Rule(identifier, Optional(balanced_paren),
    Action(lambda i, b: i + replace_regexps(concat(b))),
    name="Rule Name")

either_rule = ForwardRule()
real_rule = Rule(Either(
    regexp,
    string,
    Rule(rulename, Action(lambda x: AstRuleCall(x))),
    external_rule,
    either_rule
), Action(lambda r: AstRuleSingle(r)),
name="Real Rule")

label = Rule(identifier, COLON, Action(lambda name, _2: name), name="Production Label")

repetition = Rule(Either(
    ("*", Action(lambda x: (0, -1))),
    ("+", Action(lambda x: (1, -1))),
    ("?", Action(lambda x: (0,  1))),
    ("<", number, ">", Action(lambda l, n, r: (n, n))),
    ("<", Optional(number), ",", Optional(number), ">", Action(lambda l, fr, c, to, r: (-1 if fr is None else fr, -1 if to is None else to) ))
))

ruledecl = ForwardRule()
rules = ForwardRule()

full_rule = Rule(Optional(label), Not(ruledecl), real_rule, Optional(repetition),
        Action(lambda label, rule, rep: rule.set_label(label).set_repetition(rep)),
    name="Full Rule")

match_rule = Rule(Either("!", "&"), real_rule, Optional(repetition),
        Action(lambda sym, rule, rep: rule.set_repetition(rep).set_matching(sym)),
    name="Matching Rule")

either_rule.set_rule(Rule(
    LBRACKET, OneOrMoreSeparated(rules, PIPE), RBRACKET,
        Action(lambda _1, rules, _2: AstRuleEither(rules))
))

rule_repeat = Rule(OneOrMore(Either(match_rule, full_rule, predicate)), Optional(action),
    Action(lambda x, a: AstRuleGroup(x, a)))

rules.set_rule(Rule(
    OneOrMoreSeparated(rule_repeat, PIPE), Action(lambda x: AstRuleEither(x)),
    name="Rules+"
))

####################### Rule declaration ###########################

ruleskip = Rule("skip", real_rule,
        Action(lambda id, rule: (id, rule)),
    name="Rule Argument")

ruledecl.set_rule(Rule(
    rulename, Optional("skip", real_rule, Action(lambda _, rule: rule)), EQUAL,
    name="Rule Declaration"
))

grammarrule = Rule(
    ruledecl, rules, Action(lambda decl, rules: AstRuleDecl(decl[0], rules, skip=decl[1])),
    name="Grammar Rule"
)

toplevel = Rule(Optional(starting_code), OneOrMore(grammarrule),
        Action(lambda code, rules: AstFile(code, rules)),
    skip=space_and_comments, name="Top Level")

