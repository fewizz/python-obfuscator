import ast
from obfuscator_v2.types import Package, ClassDef
from obfuscator_v2._01 import extend_types
from obfuscator_v2._02_bind_globals import collect_members
from obfuscator_v2._03_link_imports import link_imports


def test_imports_linkage():
    root = Package("root")

    a = ast.parse("""
class A_0:
    ...

class A_1:
    ...
""")

    b = ast.parse("""
from .a import A_0
from root.a import A_1

class C(A_0, A_1):
    ...
""")

    a = root.add_module([], a, "a")
    b = root.add_module([], b, "b")

    for m in root.walk():
        extend_types(m)
        collect_members(m)

    link_imports(root)

    assert isinstance(
        next(g for g in b.members() if g.name == "A_0"),
        ClassDef
    )

    assert isinstance(
        next(g for g in b.members() if g.name == "A_1"),
        ClassDef
    )
