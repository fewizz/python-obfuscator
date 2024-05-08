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
    # Если сущность - пакет, возвращаем список его модулей
    if isinstance(node, Package):
        result = {e.name_ptr.data: e for e in node.entries}
        # если пакет содержит модуль __init__, включаем его сущности
        if "__init__" in result:
            init_members = members(result["__init__"])
            result.update(init_members)  # type: ignore
        return result  # type: ignore

    # Включаем елементы родительской сущности, если необходимо
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

    # Визитор, обходящий все дерево и включающий все сущности,
    # входящие в область видимости данной сущности
    class Visitor(ast.NodeVisitor):

        def visit_Name(self, node):
            assert isinstance(node, Name | ast.Name)
            if (
                isinstance(node, Name)
                and type(node.ctx) is ast.Store
                and node.name_ptr.data not in result
            ):
                result[node.name_ptr.data] = node

        def visit_ImportFrom(self, node):
            assert isinstance(node, ImportFrom | ast.ImportFrom)
            if isinstance(node, ImportFrom):
                for what in node.what:
                    if what.asname is not None:
                        name = what.asname.data
                    else:
                        name = what.entity.name_ptr.data
                    entity = what.entity
                    result[name] = entity

        def visit_ClassDef(self, node):
            assert isinstance(node, ClassDef | ast.ClassDef)
            if isinstance(node, ClassDef):
                result[node.name] = node

        def visit_FunctionDef(self, node):
            assert isinstance(node, FunctionDef | ast.FunctionDef)
            if isinstance(node, FunctionDef):
                result[node.name] = node

        def visit_AsyncFunctionDef(self, node):
            assert isinstance(node, AsyncFunctionDef | ast.AsyncFunctionDef)
            if isinstance(node, AsyncFunctionDef):
                result[node.name] = node

        def visit_arg(self, node: arg):
            if isinstance(node, arg):
                result[node.arg] = node

    Visitor().generic_visit(node)

    return result
