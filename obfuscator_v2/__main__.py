import ast
import sys
import pathlib
import shutil
from .types import Package, ClassDef, Name

# Первый аргумент программы - файл исходного кода
if len(sys.argv) <= 1:
    print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
    exit(1)

dir_path = pathlib.Path(sys.argv[1])
dst_dir_path = pathlib.Path(sys.argv[2])

assert dir_path.is_dir()


root_package = Package(name=dir_path.name)

non_py_file_paths = dict[pathlib.Path, bytes]()

for py_path in dir_path.glob("**/*.*"):
    with open(str(py_path), "rb") as f:
        # Создание АСД
        bytes = f.read()
        if py_path.suffix == ".py":
            node: ast.Module = ast.parse(source=bytes)
            path = py_path.relative_to(dir_path).with_suffix("").parts
            module_name = path[-1]
            package_path = path[:-1]

            root_package.add_module(package_path, node=node, name=module_name)
        else:
            non_py_file_paths[py_path.relative_to(dir_path)] = bytes


# Replacement of ast.Name's id str to UserString

for node in root_package.walk():
    from ._01 import extend_types
    extend_types(node)


for node in root_package.walk():
    from ._02_bind_globals import collect_members
    collect_members(node)


from ._03_link_imports import link_imports  # noqa
link_imports(root_package=root_package)


for node in root_package.walk():
    from ._04_fix_bases import fix_bases
    fix_bases(node)


from ._05_bind_with_globals import bind_with_globals  # noqa
bind_with_globals(root_package=root_package)


# Получение обфусцированного имени.
# По мере вызовов метода, возвращаются элементы последовательности:
# a, b, c, ..., z, aa, ab, ..., az, ba, bb, ..., zz, aaa, ...,  и т.д.
def next_name(_name_idx: list[int] = [0]) -> str:
    name_chars = list()
    name_idx: int = _name_idx[0]

    while True:
        name_chars.append(chr(ord('a') + (name_idx % 26)))
        name_idx //= 26
        if name_idx == 0:
            break

    _name_idx[0] += 1

    return ''.join(name_chars)


for node in root_package.walk():
    for name, value in {g._name: g for g in node.members()}.items():
        if not isinstance(value, ClassDef | Name):
            continue
        if isinstance(value, Name) and type(value.ctx) is not ast.Store:
            continue
        value._name.data = next_name()


for node in root_package.walk():
    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef):
            for idx, b in enumerate(node.bases):
                if isinstance(b, ClassDef):
                    node.bases[idx] = Name(
                        base=node, name=b._name, ctx=ast.Load()
                    )
            super().generic_visit(node)
    Visitor().visit(node)

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
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/f"{path}.py", "w") as f:
        f.write(ast.unparse(node))

for path, bytes in non_py_file_paths.items():
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/path, "wb") as f:
        f.write(bytes)
