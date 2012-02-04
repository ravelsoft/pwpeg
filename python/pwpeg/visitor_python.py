from itertools import chain

from visitor import Visitor, indent

class PythonVisitor(Visitor):

    def __init__(self):
        super(PythonVisitor, self).__init__()
        self.nbfn = 0

    def compile_function(self, code, ctx, fnpattern="fn"):
        args = ", ".join(ctx.labels)

        if code.count("\n") == 0 and not code.startswith("return"):
            return "lambda {0}: ({1}) ".format(args, code)

        fname = "{0}_{1}".format(fnpattern, self.nbfn)
        self.nbfn += 1
        fbody = "def {0}({1}):\n{2}".format(fname, args, indent(code))

        ctx.functions.append(fbody)
        return fname

    def compile(self, node):
        self.visit(node)

        res = [
            "#!/usr/bin/env python",
            ""
            "from pwpeg import *",
            "from pwpeg.helpers import *",
            ""
        ]

        if self.code_start:
            res.append("\n##############################################################\n# Start of included code")
            res.append(self.code_start)
            res.append("\n# End of included code\n##############################################################")


        has_skips = False

        res.append("\n# Forward declaration of Regular rules")
        for name, sr in sorted(self.rules_simple.items()):
            res.append("{0} = Rule().set_name(\"{1}\")".format(name, sr.name))
            if sr.skip: has_skips = True
        res.append("")

        res.append("\n# Forward declaration of Function rules")
        for name, fr in sorted(self.rules_function.items()):
            res.append("{0} = FunctionRule().set_name(\"{1}\")".format(name, fr.name))
            if fr.skip: has_skips = True
        res.append("")

        if has_skips:
            res.append("\n# Skips")
            for name, r in sorted(chain(self.rules_simple.items(), self.rules_function.items())):
                if r.skip:
                    res.append("{0}.set_skip({1})".format(name, r.skip.name))
            res.append("")

        res.append("\n# Function Rules implementation")
        for name, fr in sorted(self.rules_function.items()):
            res.append("def _{0}{1}:".format(name, fr.args))
            for fn in fr.ctx.functions:
                res.append(indent(fn))
                res.append("")

            res.append("    return " + indent(fr.code)[4:])
            res.append("{0}.set_fn(_{0})\n".format(name))
        res.append("")

        res.append("\n# Simple Rules implementation")
        for name, sr in sorted(self.rules_simple.items()):
            for fn in sr.ctx.functions:
                res.append(fn)
                res.append("")

            if sr.code.startswith("Rule("):
                res.append("{0}.set_productions(".format(name) + sr.code[5:] + "\n")
            else:
                res.append("{0}.set_productions(".format(name) + sr.code + ")\n")
        res.append("")


        if self.code_end:
            res.append("\n##############################################################\n# Start of included code")
            res.append(self.code_end)
            res.append("\n# End of included code\n##############################################################")

        return "\n".join(res)

