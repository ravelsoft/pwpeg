from visitor import Visitor

class PythonVisitor(Visitor):

    def visit_Rule(self, node):
        pass

    def visit_AstFile(self, node):
        return node.code
