import ast
from obfuscator_v2.types import Package
from obfuscator_v2._01_wrap_name_ids import wrap_name_ids
from obfuscator_v2._02_collect_members import collect_members


def test_members_collection():
    node = ast.parse("""
some_field = 0

class some_class:
    ...

def some_method(self):
    ...

""")
    p = Package("")
    node = p.add_module([], node, "")

    wrap_name_ids(node)
    collect_members(node)

    assert "some_field" in node.members
    assert isinstance(node.members["some_field"], ast.Name)

    assert "some_class" in node.members
    assert isinstance(node.members["some_class"], ast.ClassDef)

    assert "some_method" in node.members
    assert isinstance(node.members["some_method"], ast.FunctionDef)
