import ast
from collections import UserString
from .types import Module, Attribute, Name, ClassDef, FunctionDef, Package


def _bind_with_globals(node: Module):
    by_name = {g._name: g for g in node.members()}

    class Visitor(ast.NodeVisitor):

        def visit_Attribute(self, node: Attribute):
            if (
                isinstance(node.value, Name)
                and UserString(node.value.name) in by_name
            ):
                g = by_name[UserString(node.value.name)]

                if isinstance(g, Name):
                    node._attr = g._name
                elif isinstance(g, ClassDef | FunctionDef):
                    members = g.members(particular_name=node.attr)
                    if len(members) > 0:
                        node._attr = members[-1]._name
                elif isinstance(g, Module):
                    members = g.members(particular_name=node.attr)
                    last = members[-1]
                    assert not isinstance(last, Module | Package)
                    node._attr = last._name
                elif isinstance(g, Package):
                    init_globals = None

                    if UserString("__init__") in g.subs:
                        init = g.get(["__init__"])
                        assert isinstance(init, Module)
                        init_globals = {g._name: g for g in init.members()}

                    if init_globals is not None and node.attr in init_globals:
                        node._attr = init_globals[UserString(node.attr)]._name
                    else:
                        module_or_package = g.get([node.attr])
                        node._attr = module_or_package._name
                else:
                    raise TypeError()

            return super().generic_visit(node)

    Visitor().visit(node)


def bind_with_globals(root_package: Package):
    for node in root_package.walk():
        _bind_with_globals(node)
