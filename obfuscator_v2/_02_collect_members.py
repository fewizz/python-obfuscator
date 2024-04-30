import ast
from obfuscator_v2.types import Module


class MembersVisitor(ast.NodeVisitor):
    def __init__(self, module_node: Module):
        self.module_node = module_node

    def visit_ClassDef(self, node: ast.ClassDef):
        self.module_node.members[node.name] = node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.module_node.members[node.name] = node

    def visit_Assign(self, node: ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.module_node.members[t.id] = t


def collect_members(module_node: Module):
    MembersVisitor(module_node).visit(module_node)
