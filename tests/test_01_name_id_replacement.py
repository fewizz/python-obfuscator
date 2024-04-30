import ast
from collections import UserString
from obfuscator_v2._01_wrap_name_ids import wrap_name_ids
from obfuscator_v2.types import Package


def test_name_id_replacement():
    node = ast.parse("""
a = 0

class SomeClass:
    some_field = 1

    def some_method(self):
        pass
""")
    p = Package("")
    node = p.add_module([], node, "")

    wrap_name_ids(node)

    assignment = node.body[0]
    assert isinstance(assignment, ast.Assign)

    target = assignment.targets[0]
    assert isinstance(target, ast.Name)
    assert isinstance(target.id, UserString)
    assert target.id.data == "a"
