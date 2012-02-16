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
    return re_regexp.sub(lambda m: _regexp_action(m.group(0)[1:-1], m.group(2)), t)

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
    delimitedby_regexp_escapes("'", '\\.'),
    delimitedby_regexp_escapes('"', '\\.'),
    # Backslash quoted string
    Rule(re.compile("\\\\[^ \t\n\[\]\|\)]+")).set_action(lambda s: "'" + s[1:].replace('\'', '\\\'').replace('\\', '\\\\') + "'").set_name("Backslashed String")
).set_skip(None)
string.set_name("String")


regexp = Rule(
    #DelimitedBy.instanciate('/', '\\').set_action(lambda delimiter, escape, result: "".join(result)),
    delimitedby_regexp('/', '\\'),
    Optional(re.compile('[idsmlux]+'))
).set_skip(None).set_action(lambda d, f: _regexp_action(d[1:-1], f))
regexp.set_name("Regexp")


anything_inline = Rule(
    re.compile("[^\n]*")
)
anything_inline.set_name("Anything Inline")

blanks = Rule(re.compile("[ \t]+")).set_name("Blanks")

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
    ).set_name("*Multi Line Action").set_action(lambda sp, arrow, more_space, eol, code: "\n".join([t[1] for t in code]))

action_multi_line = FunctionRule(_action_multi_line).set_skip(None)
#action_multi_line = _action_multi_line()
action_multi_line.set_name("Multi Line Action")

###############################
# -> action
action_single_line = Rule(
    ARROW,
    to_eol
).set_action(lambda arrow, line: line.strip()).set_skip(None).set_name("Single Line Action")

action_single_line.set_skip(None)

###############################
# {}, ->, -> \n
action = Either(
    action_multi_line,
    action_single_line
).set_name("Action")


#######################################################

###############################
# &{ return True }
predicate = Rule(
    balanced_braces
).set_action(lambda p: AstPredicate(concat(p[1:-1])))
predicate.set_name("Predicate")

###############################
# rule_ident
# rule_ident(balanced_paren, args)
rule_identifier = Rule(
    identifier,
    Optional(balanced_paren)
).set_action(lambda i, b: AstRuleDeclaration(i).set_args(replace_regexps(concat(b))))
rule_identifier.set_name("Rule Identifier")


###############################
# identifier:
label = Rule(identifier, COLON).set_action(lambda name, _2: name).set_name("Production Label")

###############################
# *, +, ?, <2>, <2,>, <,2>
repetition = Either(
    Rule("*").set_action(lambda x: (0, -1)),
    Rule("+").set_action(lambda x: (1, -1)),
    Rule("?").set_action(lambda x: (0,  1)),
    Rule("<", number, ">").set_action(lambda l, n, r: (n, n)),
    Rule("<", Optional(number), ",", Optional(number), ">").set_action(lambda l, fr, c, to, r: (-1 if fr is None else fr, -1 if to is None else to) )
)
repetition.set_name("Repetition Modifier")

rule_declaration = Rule().set_name("Rule Declaration")
production_group = Rule().set_name("Production Group")

###############################
# [ rule1 | rule2 ]
production_group_choices = Rule(
    OneOrMoreSeparated.instanciate(production_group, PIPE),
).set_action(lambda productions: AstProductionChoices(productions))
production_group_choices.set_name("Production Group Choices")


production = Rule(
    Optional(label),
    # The following is to prevent the parser from eating up a rule name
    # that serves in a subsequent rule declaration.
    # ie:  myrule* myrule2+     next_rule = ...
    # we prevent eating that:   ^^^^^^^^^
    Not(rule_declaration),
    Either(
        Either(
            regexp,
            string,
        ).set_action(lambda r: AstProduction(r)),
        Rule(rule_identifier).set_action(lambda d: AstRuleCall(d)).set_name("Rule Call"),
        Rule(LBRACKET, production_group_choices, RBRACKET).set_action(lambda _1, alts, _2: alts).set_name("Rule Choices")
    ),
    Optional(repetition)
)
production.set_action(lambda label, rule, rep: rule.set_label(label).set_repetition(rep))
production.set_name("Production")


###############################
# !rule &rule
# Basically, this is a look-ahead
look_ahead = Rule(
    Either("!", "&"),
    production,
    Optional(repetition)
)
look_ahead.set_action(lambda symbol, prod, rep: AstLookAhead(prod.set_repetition(rep), symbol))
look_ahead.set_name("Look Ahead")


###############################
# A single production rule
production_group.set_productions(
    OneOrMore(Either(
        look_ahead,
        production,
        predicate
    )),
    Optional(action)
).set_action(lambda rules, a: AstProductionGroup(rules).set_action(a))


####################### Rule declaration ###########################

###############################
# rule_name =
# rule_name(args) =
rule_declaration.set_productions(
    rule_identifier,
    Optional(Rule("skip", production).set_action(lambda _, rule: rule)),
    EQUAL
).set_name("Rule Declaration")
rule_declaration.set_action(lambda decl, skip, equal: decl.set_skip(skip))

grammarrule = Rule(
    rule_declaration,
    production_group_choices
).set_action(lambda decl, rules: decl.set_productions(rules))
grammarrule.set_name("Grammar Rule")

toplevel = Rule(
    Optional(code),
    OneOrMore(grammarrule),
    Optional(code),
    Optional(blanks)
)

toplevel.set_action(lambda code, rules, endcode, blanks: AstFile(code.strip() if code else "", rules, endcode.strip() if endcode else ""))
toplevel.set_skip(space_and_comments)
toplevel.set_name("Top Level")
