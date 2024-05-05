import ast
from .types import Module, ClassDef, FunctionDef, AsyncFunctionDef, Name


def members(node: Module | ClassDef | FunctionDef | AsyncFunctionDef):
    result = dict[
        str,
        Module | ClassDef | FunctionDef | AsyncFunctionDef | Name
    ]()

    if (
        node.owner is not None
        and isinstance(
            node.owner,
            Module | ClassDef | FunctionDef | AsyncFunctionDef
        )
    ):
        result = result | members(node.owner)

    class Visitor(ast.NodeVisitor):

        def visit_ClassDef(self, node: ast.ClassDef):
            if isinstance(node, ClassDef):
                result[node.name] = node
            else:
                assert isinstance(node, ast.ClassDef)

        def visit_FunctionDef(self, node):
            if isinstance(node, FunctionDef):
                result[node.name] = node
            else:
                assert isinstance(node, ast.FunctionDef)

        def visit_AsyncFunctionDef(self, node):
            if isinstance(node, AsyncFunctionDef):
                result[node.name] = node
            else:
                assert isinstance(node, ast.AsyncFunctionDef)

    Visitor().generic_visit(node)

    return result
