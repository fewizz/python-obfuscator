import ast
# from collections import UserString
from obfuscator_v2.types import Module, Name, ClassDef, FunctionDef, ImportFrom


class NameIDReplaceVisitor(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name):
        # node.id = UserString(node.id)  # type: ignore
        return Name(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        return ClassDef(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        return FunctionDef(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        return ImportFrom(node)


def wrap_name_ids(module_node: Module):
    NameIDReplaceVisitor().visit(module_node)
