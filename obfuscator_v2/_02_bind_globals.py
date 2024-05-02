import ast
from collections import UserString
from obfuscator_v2.types import Module, ClassDef, FunctionDef, Name


def collect_members(module_node: Module):
    globals = module_node.members()
    by_name = dict[UserString, ClassDef | FunctionDef | Name]()

    for g in globals:
        assert isinstance(g, ClassDef | FunctionDef | Name)

        if isinstance(g, Name):
            if type(g.ctx) is ast.Store:
                by_name[g._name] = g
            elif g._name in by_name:
                rep = by_name[g._name]
                g._name = rep._name
        else:
            if g._name not in by_name:
                by_name[g._name] = g
            else:
                rep = by_name[g._name]
                g._name = rep._name
