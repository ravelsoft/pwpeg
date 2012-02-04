from . import helpers, pwpeg


class AstNode(object):
    def __repr__(self):
        return "{0}".format(self.__class__.__name__)

    def accept(self, visitor, *args, **kwargs):
        methodname = "visit_" + self.__class__.__name__
        return getattr(visitor, methodname)(self, *args, **kwargs)


class AstProduction(AstNode):
    def __init__(self, code=None, repetition=None):
        self.label = ""
        self.code = code
        self.repetition = None
        self.matching = None

    def set_label(self, label):
        self.label = label
        return self

    def set_repetition(self, repetition):
        self.repetition = repetition
        return self

    def set_matching(self, matching):
        self.matching = matching
        return self

    def __repr__(self):
        label = ""
        repetition = self.repetition or ""
        if self.label:
            label = self.label + ":"
        return "{0}{1}{2}".format(label, self.code, repetition)


class AstRuleCall(AstProduction):
    def __init__(self, decl=None, repetition=None):
        self.decl = decl
        self.label = decl.label
        self.repetition = None
        self.code= ""


class AstLookAhead(AstProduction):
    def __init__(self, production, symbol):
        super(AstLookAhead, self).__init__()
        self.production = production
        self.symbol = symbol


class AstPredicate(AstProduction):
    def __init__(self, code):
        super(AstPredicate, self).__init__()
        self.code = code

    def __repr__(self):
        return "{{{0}}}".format(self.code)



class AstProductionGroup(AstProduction):
    def __init__(self, rules):
        super(AstProductionGroup, self).__init__()
        self.rules = rules
        self.action = None

    def set_action(self, action):
        self.action = action
        return self

    def __repr__(self):
        rules = " ".join([repr(r) for r in self.rules])

        action = ""

        if self.action:
            action = " ({0})".format(repr(self.action))

        return "{0}{1}".format(rules, action)


class AstProductionChoices(AstProductionGroup):
    def __repr__(self):
        rules = " | ".join([repr(r) for r in self.rules])

        action = ""

        if self.action:
            action = " ({0})".format(repr(self.action))

        return "{0}{1}".format(rules, action)



class AstRuleDeclaration(AstNode):
    def __init__(self, name):
        self.name = name
        self.args = None
        self.productions = None
        self.skip = None
        self.label = name

    def set_productions(self, productions):
        self.productions = productions
        return self

    def set_args(self, args):
        self.args = args
        return self

    def set_skip(self, skip):
        self.skip = skip
        return self

    def __repr__(self):
        return "{0}{1}".format(self.name, self.args)


class AstCode(AstNode):
    def __init__(self, code):
        self.code = code

    def __repr__(self, ctx=dict(), indent=0):
        code = ""
        if self.code:
            code = self.code[:10]
            if len(self.code) > 10:
                code += "..."
        return code


class AstFile(AstNode):

    def __init__(self, code_start, rules, code_end):
        self.code_start = code_start or ""
        self.rules = rules
        self.code_end = code_end or ""

    def __repr__(self):
        return "{0}{1}{2}".format(self.code_start, self.rules, self.code_end)
