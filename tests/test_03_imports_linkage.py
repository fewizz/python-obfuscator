import ast
from obfuscator_v2.types import Package
from obfuscator_v2._01_wrap_name_ids import wrap_name_ids
from obfuscator_v2._02_collect_members import collect_members
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
        wrap_name_ids(m)
        collect_members(m)

    link_imports(root)

    assert "A_0" in b.members
    assert isinstance(b.members["A_0"], ast.ClassDef)

    assert "A_1" in b.members
    assert isinstance(b.members["A_1"], ast.ClassDef)
