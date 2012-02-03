from visitor import Visitor

class PythonVisitor(Visitor):

    def visit_Rule(self, node):
        pass

    def visit_AstFile(self, node):

        return "{0}\n{1}".format(node.code, node.endcode)
