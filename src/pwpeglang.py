"""
    @author Christophe Eymard <christophe.eymard@ravelsoft.com>
"""

from pwpeg import *
import re

re_regexp = re.compile("/(\\/|[^/])+/[idsmlux]+")
re_lead = re.compile("^[ \t]+")


class DeferredValue(object):

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
ARROW = "->"
SPACES = re.compile("[ \t]*")
EOL = "\n"

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"))

to_eol = Rule(re.compile("[^\n]*\n?"))

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

regexp = Rule(re_regexp)


@Rule
def leading_indent(indent):

    if indent.isset():
        return re.compile("[ \t]{1}".format(indent.value()))

    # The first time around, we eat all the spaces.
    # Only after does this rule only eat the leading spaces.
    return re_lead


@Rule
def indented_line(indent):

    def action_set_indentation(lead, line, opt):
        ind = len(lead)
        
        indent.set_if_unset(ind)

        # the empty lines are just squizzed out of the parsed text.
        return line

    return leading_indent(indent), to_eol, Optional(empty_lines), action_set_indentation


@Rule
def indented_block(indentation=DeferredValue(1)):

    def _action_concatenate(first_line, others):
        lst = [first_line] + others
        return "".join(lst)

    return indented_line(indentation), ZeroOrMore(indented_line(indentation)), _action_concatenate


starting_code = Rule("%%", "%%")

