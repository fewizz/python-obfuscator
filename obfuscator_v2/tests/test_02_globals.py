import ast
from obfuscator_v2.types import Package, ClassDef, FunctionDef, Name
from obfuscator_v2._01 import extend_types
from obfuscator_v2._02_bind_globals import collect_members


def test_globals():
    node = ast.parse("""
some_field = 0

if 0 > 1:
    scoped_field = 42

class some_class:
    ...

def some_method(self):
    ...

""")
    p = Package("")
    node = p.add_module([], node, "")

    extend_types(node)
    collect_members(node)

    globals = node.members()

    assert isinstance(
        next(g for g in globals if g.name == "some_field"),
        Name
    )

    assert isinstance(
        next(g for g in globals if g.name == "some_class"),
        ClassDef
    )

    assert isinstance(
        next(g for g in globals if g.name == "some_method"),
        FunctionDef
    )

    assert isinstance(
        next(g for g in globals if g.name == "scoped_field"),
        Name
    )


def test_duplicate_field():
    node = ast.parse("""
some_field = 0
some_field = 1
""")
    p = Package("")
    node = p.add_module([], node, "")

    extend_types(node)
    collect_members(node)

    name_0 = node.body[0]
    name_1 = node.body[1]

    assert isinstance(name_0, ast.Assign) and isinstance(name_1, ast.Assign)

    name_0, name_1 = name_0.targets[0], name_1.targets[0]

    assert isinstance(name_0, Name) and isinstance(name_1, Name)

    assert name_0._name is name_1._name
