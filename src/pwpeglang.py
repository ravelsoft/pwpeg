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

    def set(self, value):
        if not self.isset():
            self._value = value

    def value(self):
        if not self.isset():
            return self.default
        return self._value

    def isset(self):
        return "_value" in self.__dict__


ARROW = "->"
EOL = "\n"

identifier = Rule(re.compile("[a-zA-Z_][a-zA-Z0-9_]*"))

to_eol = Rule(re.compile("[^\n]*"))

empty_lines = Rule(re.compile("([ \t]*\n)*", re.M))

regexp = Rule(re_regexp)


@Rule
def leading_indent(indent):

    if indent.isset():
        return re.compile("[ \t]{1}".format(indent.value()))
    return re_lead


@Rule
def indented_line(indent):

    def set_indentation(lead, line, opt):
        ind = len(lead)
        
        indent.set(ind) # The current level indentation is in fact only set once.
        return line

    return leading_indent(indent), to_eol, Optional(empty_lines), set_indentation


@Rule
def indented_block():
    indentation = DeferredValue(1)
    # FIXME concatenate the blocks
    return indented_line(indentation), ZeroOrMore(indented_line(indentation))


starting_code = Rule("%%", "%%")

