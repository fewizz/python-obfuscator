import ast
from .types import (
    Package, Module, ClassDef, FunctionDef, AsyncFunctionDef, Name,
    ImportFrom, arg
)


def members(
    node: Package | Module | ClassDef | FunctionDef | AsyncFunctionDef
) -> dict[
    str,
    Package | Module | ClassDef | FunctionDef | AsyncFunctionDef | Name | arg
]:
    if isinstance(node, Package):
        result = {e.name_ptr.data: e for e in node.entries}
        if "__init__" in result:
            init_members = members(result["__init__"])
            result.update(init_members)  # type: ignore
        return result  # type: ignore

    if (
        node.owner is not None
        and isinstance(
            node.owner,
            Module | ClassDef | FunctionDef | AsyncFunctionDef
        )
    ):
        result = members(node.owner)
    else:
        result = dict[
            str,
            Package | Module | ClassDef | FunctionDef | AsyncFunctionDef
            | Name | arg
        ]()

    class Visitor(ast.NodeVisitor):

        def visit_Name(self, node):
            if (
                isinstance(node, Name)
                and type(node.ctx) is ast.Store
                and node.name_ptr.data not in result
            ):
                result[node.name_ptr.data] = node

        def visit_ImportFrom(self, node):
            if isinstance(node, ImportFrom):
                for what in node.what:
                    if what.asname is not None:
                        name = what.asname.data
                    else:
                        name = what.entity.name_ptr.data
                    entity = what.entity
                    result[name] = entity
            else:
                assert isinstance(node, ast.ImportFrom)

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

        def visit_arg(self, node: arg):
            if isinstance(node, arg):
                result[node.arg] = node

    Visitor().generic_visit(node)

    return result
