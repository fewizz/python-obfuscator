import ast
# from collections import UserString
from obfuscator_v2.types import Module, Name, ClassDef, FunctionDef, Attribute


def extend_types(module_node: Module):
    class NameIDReplaceVisitor(ast.NodeTransformer):
        def __init__(self, base):
            self.base = base

        def visit_Name(self, node: ast.Name):
            result = Name(base=self.base, name=node.id, ctx=node.ctx)
            NameIDReplaceVisitor(base=result).generic_visit(result)
            return result

        def visit_ClassDef(self, node: ast.ClassDef):
            result = ClassDef(base=self.base, node=node)
            NameIDReplaceVisitor(base=result).generic_visit(result)
            return result

        def visit_FunctionDef(self, node: ast.FunctionDef):
            result = FunctionDef(base=self.base, node=node)
            NameIDReplaceVisitor(base=result).generic_visit(result)
            return result

        def visit_Attribute(self, node: ast.Attribute):
            result = Attribute(base=self.base, node=node)
            NameIDReplaceVisitor(base=result).generic_visit(result)
            return result

    NameIDReplaceVisitor(base=module_node).visit(module_node)
