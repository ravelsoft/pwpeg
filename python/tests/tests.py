#!/usr/bin/env python

import sys
from os.path import dirname, join
sys.path.append(join(dirname(__file__), ".."))
import re

from pwpeg import *

def test(rules, texts, errors=[]):
    if isinstance(rules, list):
        p = Parser(Rule(*[Rule.getrule(r) for r in rules]))
    else:
        p = Parser(Rule.getrule(rules))

    for t in texts:
        try:
            res = p.parse(t)
        except Exception as e:
            print("{0} should parse '{1}'' ({2})".format(p.toprule, t, unicode(e)))

    for t in errors:
        try:
            res = p.parse(t)
            print("{0} shouldn't parse '{1}'".format(p.toprule, t))
        except Exception as e:
            pass

# Since we're using a lot of regexps, let's just simplify their
# declaration.
_ = lambda s: re.compile(s)

test("a",
    ["a"], ["b", ""])

test(Optional("a"),
    ["a", ""], ["b", "ba", "ab"])

test(OneOrMore("a"),
    ["a", "aa", "aaaa"], ["", "b", "ab", "ba"])

test(_("a+"),
    ["a", "aa", "aaaa"], ["", "b", "ab", "ba"])

test(ZeroOrMore("a"),
    ["", "a", "aa", "aaaa"], ["b", "ab", "ba"])

test(Repetition(1, 3, "a"),
    ["a", "aa", "aaa"], ["b", "", "aaaa"])

test([OneOrMore("a"), "b"],
    ["aaaab", "ab"], ["b"])

# Now starting slightly more complicated tests

ident = _("\w+")
lparen = "("
rparen = ")"
spaces = "\s+"

test([ident, lparen, ZeroOrMore(ident), rparen],
    ["a(b)"], ["a a(b)"])

test(["a", Either("b", "c")],
    ["ac", "ab"], ["aa"])

test(["a", OneOrMore(Either("b", "c"))],
    ["abbbb", "ac", "abcbc"], ["aaaa"])

balanced=Rule()
balanced.set_productions(OneOrMore(Either(
    Rule(lparen, rparen),
    Rule(lparen, balanced, rparen)
)))
test(balanced,
    ["()()()", "(()()(()()))"], ["(", ")", "(()"])

test(Either(
    Either(
        "a",
        "b"
    ),
    Either(
        "c",
        "d"
    )
), ["a", "b", "c", "d"], ["aa", "", "e"])