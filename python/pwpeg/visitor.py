def indent(txt):
    return "\n".join(["    " + t for t in txt.split("\n")])

class Context(object):
    def __init__(self):
        self.labels = []
        self.predicates = []
        self.action = None
        self.functions = []

    def add_rule(self, rule):
        if rule.label:
            self.labels.append(rule.label)
        else:
            self.labels.append("_{0}".format(len(self.labels)))

    def merge(self, ctx):
        self.functions += ctx.functions


class Visitor(object):
    def __init__(self):
        self.rules = dict()
        self.rules_simple = dict()
        self.rules_function = dict()
        self.code_start = ""
        self.code_end = ""
        self.tokens = set()

    def visit(self, node, *args, **kwargs):
        return node.accept(self, *args, **kwargs)

    #######################################################################

    def visit_Repetition(self, node):
        if node.repetition:
            _from, _to = node.repetition
            repeat = "Repetition({0}, {1}, {{0}})".format(_from, _to)

            if _from == 0 and _to == -1:
                repeat = "ZeroOrMore({0})"
            if _from == 1 and _to == -1:
                repeat = "OneOrMore({0})"
            if _from == 0 and _to == 1:
                repeat = "Optional({0})"

            return repeat.format(node.code)
        else:
            return node.code

    def visit_AstLookAhead(self, node, ctx):
        nctx = Context()
        return ("Not(" if node.symbol == "!" else "And(") + self.visit(node.production, nctx) + ")"

    def visit_AstPredicate(self, node, ctx):
        return self.compile_function(node.code, ctx)

    def visit_AstRuleCall(self, node, ctx):
        ctx.add_rule(node)
        node.code = node.decl.name + (".instanciate" + node.decl.args if node.decl.args else "")
        return self.visit_Repetition(node)

    def visit_AstProduction(self, node, ctx):
        ctx.add_rule(node)
        return self.visit_Repetition(node)

    def visit_AstProductionGroup(self, node, ctx):
        node.labels = []

        c = Context()
        subnodes = [self.visit(p, c) for p in node.rules]
        if len(subnodes) > 1:
            node.code = "Rule(\n" + ",\n".join(map(indent, subnodes)) + "\n)"
        else:
            node.code = subnodes[0]

        if node.action:
            node.code += ".set_action({0})".format(self.compile_function(node.action, c, "action"))

        ctx.merge(c)

        return self.visit_Repetition(node)

    def visit_AstProductionChoices(self, node, ctx):
        res = []

        ctx.add_rule(node)

        c = Context()

        if len(node.rules) > 1:
            res.append("Either(")
            res.append(",\n".join(map(indent, [self.visit(p, c) for p in node.rules])))
            res.append(")")
        else:
            res.append(self.visit(node.rules[0], c))

        node.code = "\n".join(res)

        if node.action:
            node.code += ".set_action({0})".format(self.compile_function(node.action, c, "action"))

        ctx.merge(c)
        return self.visit_Repetition(node)

    def visit_AstRuleDeclaration(self, node):
        if node.name in self.rules:
            raise Exception("Can't redefine existing rule {0}".format(node.name))

        if node.args:
            self.rules_function[node.name] = node
        else:
            self.rules_simple[node.name] = node

        self.rules[node.name] = node
        node.ctx = Context()
        node.code = self.visit(node.productions, node.ctx)

    def visit_AstFile(self, node):
        for r in node.rules:
            self.visit(r)
        self.code_start = node.code_start
        self.code_end = node.code_end
