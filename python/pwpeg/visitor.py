
class Visitor(object):
    def __init__(self):
        self.ctx = dict(
            rules=set(),
            param_rules=set(),
            tokens=set()
        )

    def visit(self, node):
        nodename = node.__class__.__name__
        methodname = "visit_{0}".format(nodename)

        if hasattr(self, methodname):
            return getattr(self, methodname)(node)

        raise Exception("There is no '{0}' method in this visitor.".format(methodname))