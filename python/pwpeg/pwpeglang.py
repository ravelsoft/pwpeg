#!/usr/bin/env python
"""
    @author Christophe Eymard <christophe.eymard@ravelsoft.com>
"""

import re

from .pwpeg import *
from .pwpeg import OneOrMore as _r1, ZeroOrMore as _r0, Optional as _opt, Action as _act

from .helpers import *
from .helpers import OneOrMoreSeparated as _r1_sep

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
SPACE = Rule(re.compile("\s*")).set_name("Whitespaces")
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

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*")).set_name("Identifier")

to_eol = Rule(re.compile("[^\n]*", re.M))

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

number = Rule(re.compile("-?[0-9]+"), _act(lambda n: int(n)))

starting_code = Rule("%%", re.compile("((?!%%).)*", re.DOTALL), "%%", _act(lambda b, t, e: t))

##############################################################################################

balanced_paren      = Balanced("(", ")")
balanced_braces     = Balanced("{", "}")
balanced_brackets   = Balanced("[", "]")

# Re-concatenate the string.
string = Either(
    # 'hello'
    (DelimitedBy('\''), _act(lambda x: "".join(x))),

    # "hello"
    (DelimitedBy('"'), _act(lambda x: "".join(x))),

    # \hello
    (
        re.compile("\\\\[^ \t\n\[\]\|\)]+"),
        # Transform it to 'hello'
        _act(lambda s: "'" + s[1:].replace('\'', '\\\'').replace('\\', '\\\\') + "'")
    )
).set_skip(None)

## A Regular expression.
regexp = Rule(DelimitedBy('/'),
    # /hey[a-z]\w+/gi
    _opt(re.compile('[idsmlux]+')),
    _act(lambda d, f: _regexp_action(d[1], f))
).set_skip(None)

re_anything_inline = Rule(re.compile("[^\n]*", re.M))

## Action for rules.
## They always come in last.
action = Either(
    ##########################
    # { return stuff }
    Rule(Balanced(LBRACE, RBRACE),
            _act(lambda b: b[1].strip())
    ).set_name("Brace _act"),

    ##########################
    # ->
    #     stuff
    #     return more stuff
    Rule(_opt(SPACE), ARROW, _opt(LINE_SPACE), EOL, IndentedBlock(re_anything_inline),
            _act(lambda sp, arrow, more_space, eol, code: "\n".join([t[1] for t in code]))
    ).set_skip(None).set_name("Multi Line _act"),

    ##########################
    # -> my_result()
    Rule(ARROW, to_eol,
            _act(lambda arrow, line: line.strip())
    ).set_skip(None).set_name("Single Line _act")
)

## An external rule just allows us to use anything that may have been
## declared/imported in the %% %% section.
external_rule = Either(
    # $variable
    (DOLLAR, identifier, _act(lambda d, i: i)),

    # The following goes completely unchecked.
    # $(expr + expr)
    (DOLLAR, balanced_paren, _act(lambda d, b: concat(b)))
).set_skip(None)

#######################################################

## &{ return True }
predicate = Rule(
    "&", balanced_braces, _act(lambda _0, p: AstPredicate(p[1]))
)

# rule_ident(...)
rulename = Rule(
    identifier,
    _opt(balanced_paren),
    _act(lambda i, b: i + replace_regexps(concat(b)))
).set_name("Rule Name")

either_rule = ForwardRule()

real_rule = Rule(Either(
    regexp,
    string,
    Rule(rulename, _act(lambda x: AstRuleCall(x))),
    external_rule,
    either_rule
), _act(lambda r: AstRuleSingle(r))).set_name("Real Rule")

label = Rule(identifier, COLON, _act(lambda name, _2: name)).set_name("Production Label")

repetition = Rule(Either(
    ("*", _act(lambda x: (0, -1))),
    ("+", _act(lambda x: (1, -1))),
    ("?", _act(lambda x: (0,  1))),
    ("<", number, ">", _act(lambda l, n, r: (n, n))),
    ("<", _opt(number), ",", _opt(number), ">", _act(lambda l, fr, c, to, r: (-1 if fr is None else fr, -1 if to is None else to) ))
))

ruledecl = ForwardRule()
rules = ForwardRule()

full_rule = Rule(_opt(label), Not(ruledecl), real_rule, _opt(repetition),
        _act(lambda label, rule, rep: rule.set_label(label).set_repetition(rep))).set_name("Full Rule")

match_rule = Rule(Either("!", "&"), real_rule, _opt(repetition),
        _act(lambda sym, rule, rep: rule.set_repetition(rep).set_matching(sym))).set_name("Matching Rule")

either_rule.set_rule(Rule(
    LBRACKET, _r1_sep(rules, PIPE), RBRACKET,
        _act(lambda _1, rules, _2: AstRuleEither(rules))
))

rule_repeat = Rule(_r1(Either(match_rule, full_rule, predicate)), _opt(action),
    _act(lambda x, a: AstRuleGroup(x, a))
).set_name("Rule Repetition")

rules.set_rule(Rule(
        _r1_sep(rule_repeat, PIPE), _act(lambda x: AstRuleEither(x))
    ).set_name("Rules+")
)

####################### Rule declaration ###########################

ruleskip = Rule(
        "skip",
        real_rule,
        _act(lambda id, rule: (id, rule))
).set_name("Rule Argument")

# Setting for forward rule.
ruledecl.set_rule(Rule(
    rulename, _opt("skip", real_rule, _act(lambda _, rule: rule)), EQUAL
).set_name("Rule Declaration"))

grammarrule = Rule(
        ruledecl,
        rules,
        _act(lambda decl, rules: AstRuleDecl(decl[0], rules).set_skip(decl[1]))
).set_name("Grammar Rule")

toplevel = Rule(_opt(starting_code), _r1(grammarrule),
        _act(lambda code, rules: AstFile(code, rules))
).set_skip(space_and_comments).set_name("Top Level")

