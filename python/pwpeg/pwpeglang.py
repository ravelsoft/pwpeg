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
            res.append(concat(a))
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

number = Rule(re.compile("-?[0-9]+")).set_action(lambda n: int(n))

code = Rule("%%", re.compile("((?!%%).)*", re.DOTALL), "%%").set_action(lambda b, t, e: t)

##############################################################################################

balanced_paren      = Balanced.instanciate("(", ")", "\\")
balanced_braces     = Balanced.instanciate("{", "}", "\\")
balanced_brackets   = Balanced.instanciate("[", "]", "\\")

# Re-concatenate the string.
string = Either(
    delimitedby_regexp("'", '\\'),
    delimitedby_regexp('"', '\\'),
    # Backslash quoted string
    Rule(re.compile("\\\\[^ \t\n\[\]\|\)]+")).set_action(lambda s: "'" + s[1:].replace('\'', '\\\'').replace('\\', '\\\\') + "'")
).set_skip(None)


regexp = Rule(
    #DelimitedBy.instanciate('/', '\\').set_action(lambda delimiter, escape, result: "".join(result)),
    delimitedby_regexp('/', '\\'),
    Optional(re.compile('[idsmlux]+'))
).set_skip(None).set_action(lambda d, f: _regexp_action(d, f))



###############################
# { return result }
action_braced = Rule(
    Balanced.instanciate(LBRACE, RBRACE, "\\")
    ).set_action(lambda b: b[1].strip())
action_braced.set_name("Braced Action")


anything_inline = Rule(
    re.compile("[^\n]*")
)
anything_inline.set_name("Anything Inline")

blanks = re.compile("[ \t]+")

###############################
# ->
#   expr1
#   return action
def _action_multi_line():
    return Rule(
        Optional(SPACE),
        ARROW,
        Optional(LINE_SPACE),
        EOL,
        ZeroOrMore(
            Either(
                Rule(MemoRule(blanks), anything_inline, EOL),
                Rule(blanks, EOL),
            )
        )
    )

action_multi_line = FunctionRule(_action_multi_line)
action_multi_line.set_action(lambda sp, arrow, more_space, eol, code: "\n".join([t[1] for t in code]))
action_multi_line.set_skip(None).set_name("Multi Line Action")

###############################
# -> action
action_single_line = Rule(
    ARROW,
    to_eol
).set_action(lambda arrow, line: line.strip()).set_skip(None).set_name("Single Line Action")

###############################
# {}, ->, -> \n
action = Either(
    action_braced,
    action_multi_line,
    action_single_line
)

###############################
# $myrule
# $(somerule from elsewhere)
#
# No checking is performed on these rules.
external_rule = Either(
    Rule(DOLLAR, identifier).set_action(lambda d, i: i),
    Rule(DOLLAR, balanced_paren).set_action(lambda d, b: concat(b))
).set_skip(None)

#######################################################

###############################
# &{ return True }
predicate = Rule(
    "&",
    balanced_braces
).set_action(lambda _0, p: AstPredicate(p[1]))


rulename = Rule(
    identifier,
    Optional(balanced_paren)
).set_action(lambda i, b: i + replace_regexps(concat(b))).set_name("Rule Name")

either_rule = Rule()

real_rule = Either(
    regexp,
    string,
    Rule(rulename).set_action(lambda x: AstRuleCall(x)),
    external_rule,
    either_rule
).set_action(lambda r: AstRuleSingle(r))
real_rule.set_name("Real Rule")

label = Rule(identifier, COLON).set_action(lambda name, _2: name).set_name("Production Label")

repetition = Either(
    Rule("*").set_action(lambda x: (0, -1)),
    Rule("+").set_action(lambda x: (1, -1)),
    Rule("?").set_action(lambda x: (0,  1)),
    Rule("<", number, ">").set_action(lambda l, n, r: (n, n)),
    Rule("<", Optional(number), ",", Optional(number), ">").set_action(lambda l, fr, c, to, r: (-1 if fr is None else fr, -1 if to is None else to) )
)
repetition.set_name("Repetition Modifier")

ruledecl = Rule().set_name("Rule Declaration")
rules = Rule().set_name("Rules Repetition")

full_rule = Rule(
    Optional(label),
    Not(ruledecl),
    real_rule,
    Optional(repetition)
)
full_rule.set_action(lambda label, rule, rep: rule.set_label(label).set_repetition(rep))
full_rule.set_name("Full Rule")

###############################
# !rule &rule
# Not or Look Ahead
match_rule = Rule(
    Either("!", "&"),
    real_rule,
    Optional(repetition)
)
match_rule.set_action(lambda sym, rule, rep: rule.set_repetition(rep).set_matching(sym))
match_rule.set_name("Matching Rule")

either_rule.set_subrules(
    LBRACKET,
    OneOrMoreSeparated.instanciate(rules, PIPE),
    RBRACKET
).set_action(lambda _1, rules, _2: AstRuleEither(rules))
either_rule.set_name("Rule Choices")

production_rule = Rule(
    OneOrMore(Either(
        match_rule,
        full_rule,
        predicate
    )),
    Optional(action)
).set_action(lambda x, a: AstRuleGroup(x, a))
production_rule.set_name("Production Rule")

rules.set_subrules(
    OneOrMoreSeparated.instanciate(production_rule, PIPE)
).set_action(lambda x: AstRuleEither(x))
rules.set_name("Production Rules")


####################### Rule declaration ###########################

ruledecl.set_subrules(
    rulename,
    Optional("skip", real_rule).set_action(lambda _, rule: rule),
    EQUAL
).set_name("Rule Declaration")

grammarrule = Rule(
    ruledecl,
    rules
).set_action(lambda decl, rules: AstRuleDecl(decl[0], rules).set_skip(None))
grammarrule.set_name("Grammar Rule")

toplevel = Rule(
    Optional(code),
    OneOrMore(grammarrule),
    Optional(code)
)

toplevel.set_action(lambda code, rules, endcode: AstFile(code, rules, endcode))
toplevel.set_skip(space_and_comments)
toplevel.set_name("Top Level")
