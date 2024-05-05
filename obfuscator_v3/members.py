import ast
from .types import (
    Package, Module, ClassDef, FunctionDef, AsyncFunctionDef, Name,
    ImportFrom
)


def members(node: Module | ClassDef | FunctionDef | AsyncFunctionDef):
    result = dict[
        str,
        Package | Module | ClassDef | FunctionDef | AsyncFunctionDef | Name
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

        def visit_ImportFrom(self, node):
            if isinstance(node, ImportFrom):
                for what in node.what:
                    if what.asname is not None:
                        name = what.asname.data
                    else:
                        name = what.entity.name_ptr.data
                    entity = what.entity
                    if isinstance(entity, Package):
                        init = entity.try_get_module("__init__")
                        if init is not None:
                            entity = init
                    result[name] = entity

        def visit_ClassDef(self, node):
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
