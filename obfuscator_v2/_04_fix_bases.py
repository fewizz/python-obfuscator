import ast
from .types import Module, ClassDef, Name, Attribute


def fix_bases(node: Module):

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ClassDef):
            members = {m._name: m for m in node._base.members()}

            for idx, b in enumerate(node.bases):
                if isinstance(b, ClassDef):
                    continue

                if isinstance(b, Name):
                    if b._name == node._name or b._name not in members:
                        continue
                    m = members[b._name]
                    assert isinstance(m, ClassDef)
                    node.bases[idx] = m
                elif isinstance(b, Attribute) and isinstance(b.value, Name):
                    m = members[b.value._name]
                    assert isinstance(m, Module)
                    _members = {m._name: m for m in m.members()}
                    m = _members[b._attr]
                    assert isinstance(m, ClassDef)
                    node.bases[idx] = m
                else:
                    raise TypeError()

            super().generic_visit(node)

    Visitor().visit(node)
