import sys
import pathlib
import ast
import shutil
from .types import Package, Module, ClassDef

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

transformed_modules = set[Module]()

for node in root_package.walk():
    from .transformer import Transformer
    Transformer(
        node=node,
        root_package=root_package,
        transformed_modules=transformed_modules,
        deferred=list()
    ).visit(node)


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


for node in root_package.walk():
    for name, g in node.globals().items():
        if isinstance(g, ClassDef):
            g.name_ptr.data = next_name()


for node in root_package.walk():
    path = node.path()[1:]
    path = "/".join(s.data for s in path)
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/f"{path}.py", "wb") as f:
        f.write(ast.unparse(node).encode("utf-8"))

for path, bytes in non_py_file_paths.items():
    ((dst_dir_path/path).parent).mkdir(parents=True, exist_ok=True)
    with open(dst_dir_path/path, "wb") as f:
        f.write(bytes)
