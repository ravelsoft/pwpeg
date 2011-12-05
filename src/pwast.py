
class AstNode(object):
    def __repr__(self):
        return "<{0}>".format(self.__class__.__name__)


class AstPredicate(AstNode):
    def __init__(self, code):
        self.code = code


class AstRule(AstNode):
    def __init__(self, label, rule, action):
        self.label = label
        self.rule = rule
        self.action = action


class AstCode(AstNode):
    def __init__(self, code):
        self.code = code


class AstRuleGroup(AstNode):
    def __init__(self, rules):
        self.rules = rules


class AstFile(AstNode):

    def __init__(self, code, rules):
        self.code = code
        self.rules = rules

