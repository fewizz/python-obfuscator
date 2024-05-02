import ast
from collections import UserString
from obfuscator_v2._01 import extend_types
from obfuscator_v2.types import Package, Name


def test_types_extension():
    node = ast.parse("""
a = 0

class SomeClass:
    some_field = 1

    def some_method(self):
        pass
""")
    p = Package("")
    node = p.add_module([], node, "")

    extend_types(node)

    assignment = node.body[0]
    assert isinstance(assignment, ast.Assign)

    target = assignment.targets[0]
    assert isinstance(target, Name)
    assert isinstance(target.id, str)
    assert isinstance(target._name, UserString)
    assert target.id == "a"
    assert target._name.data == "a"
