import ast
import sys
import pathlib
import shutil
from .types import Package

# Первый аргумент программы - файл исходного кода
if len(sys.argv) <= 1:
    print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
    exit(1)

dir_path = pathlib.Path(sys.argv[1])
dst_dir_path = pathlib.Path(sys.argv[2])

assert dir_path.is_dir()


root_package = Package(name=dir_path.name)

for py_path in dir_path.glob("**/*.py"):
    with open(str(py_path), "rb") as f:
        # Создание АСД
        node: ast.Module = ast.parse(source=f.read())

    path = py_path.relative_to(dir_path).with_suffix("").parts
    module_name = path[-1]
    package_path = path[:-1]

    root_package.add_module(package_path, node=node, name=module_name)

# Replacement of ast.Name's id str to UserString

for node in root_package.walk():
    from ._01_wrap_name_ids import wrap_name_ids
    wrap_name_ids(node)


for node in root_package.walk():
    from ._02_collect_members import collect_members
    collect_members(node)


from ._03_link_imports import link_imports  # noqa
link_imports(root_package=root_package)


shutil.rmtree(dst_dir_path, ignore_errors=True)

for node in root_package.walk():
    # class NameIDUnReplaceVisitor(ast.NodeVisitor):
    #     def visit_Name(self, node: ast.Name):
    #         assert isinstance(node.id, UserString)
    #         node.id = node.id.data
    # NameIDUnReplaceVisitor().visit(node)

    # print(node.name, node.members)

    # ast.unparse(node)

    path = node.full_path()[1:]
    path = "/".join(path)
    (dst_dir_path/path).mkdir(parents=True)
    with open(dst_dir_path/f"{path}.py", "w") as f:
        f.write(ast.unparse(node))
