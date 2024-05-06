import sys
import pathlib
import ast
import shutil
from .types import (
    Package, Module, ClassDef, FunctionDef, AsyncFunctionDef, Name, arg
)
from .members import members

# Первый аргумент программы - файл исходного кода
if len(sys.argv) <= 1:
    print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
    exit(1)

dir_path = pathlib.Path(sys.argv[1])
dst_dir_path = pathlib.Path(sys.argv[2])

assert dir_path.is_dir()


root_package = Package(owner=None, name=dir_path.name)

non_py_file_paths = dict[pathlib.Path, bytes]()

for py_path in dir_path.glob("**/*.*"):
    with open(str(py_path), "rb") as f:
        # Создание АСД
        bytes = f.read()
        if py_path.suffix == ".py":
            node: ast.Module = ast.parse(source=bytes)
            path = py_path.relative_to(dir_path).with_suffix("").parts
            package = root_package

            while len(path) > 1:
                package = package.get_or_add_package(name=path[0])
                path = path[1:]

            package.add_module(name=path[0], **node.__dict__)
        else:
            non_py_file_paths[py_path.relative_to(dir_path)] = bytes

shutil.rmtree(dst_dir_path, ignore_errors=True)

from .transformer import Transformer  # noqa
transformed_modules = set[Transformer]()

for node in root_package.walk():
    Transformer(
        node=node,
        root_package=root_package,
        transformed_modules=transformed_modules,
        deferred=list()
    ).visit(node)

print("\nresolving deferred\n")

for t in transformed_modules:
    t.resolve_deferred()


print("\nrenaming\n")


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

    return "obfuscated_" + ''.join(name_chars)


renamed_nodes = set[
    Package | Module | ClassDef | FunctionDef | AsyncFunctionDef | Name | arg
]()


def handle_node(
    node: Package | ClassDef | Module | FunctionDef | AsyncFunctionDef
    | Name | arg
):
    if node in renamed_nodes:
        return
    renamed_nodes.add(node)

    if isinstance(node, Module | ClassDef):
        if not (
            isinstance(node, Module) and node.name_ptr.data == "__init__"
        ):
            node.name_ptr.data = next_name()
        for m in members(node).values():
            handle_node(m)
    if isinstance(node, FunctionDef | AsyncFunctionDef):
        for m in members(node).values():
            handle_node(m)
    if (
        #  (isinstance(node, Name) and type(node.ctx) is ast.Store)
        #  or
        isinstance(node, Package)
    ):
        node.name_ptr.data = next_name()


for node in root_package.walk():
    # Обработка пакета модуля
    handle_node(node.owner)

    # Обработка модуля
    handle_node(node)


for node in root_package.walk():
    path = node.path()[1:]
    path = "/".join(s.data for s in path)
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/f"{path}.py", "wb") as f:
        f.write(ast.unparse(node).encode("utf-8"))

for path, bytes in non_py_file_paths.items():
    if path.suffix in (".pyc",):
        continue
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/path, "wb") as f:
        f.write(bytes)
