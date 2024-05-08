import sys
from pathlib import Path
import ast
import shutil
from .types import Package
from .link import link
from .obfuscate import obfuscate

# Первый аргумент программы - файл исходного кода
if len(sys.argv) <= 1:
    print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
    exit(1)

# Стадия 1

# Исходная директория
dir_path = Path(sys.argv[1])
assert dir_path.is_dir()

# Конечная директория
dst_dir_path = Path(sys.argv[2])

# Корневой пакет
root_package = Package(owner=None, name=dir_path.name)

for file_path in dir_path.glob("**/*.*"):
    if file_path.suffix == ".py":
        with open(str(file_path), "rb") as f:
            # Создание АСД
            bytes = f.read()
            node = ast.parse(source=bytes)
    else:
        node = None

    path_parts = file_path.relative_to(dir_path).with_suffix("").parts
    package = root_package

    while len(path_parts) > 1:
        package = package.get_or_add_package(name=path_parts[0])
        path_parts = path_parts[1:]

    if node is not None:
        assert len(path_parts) > 0
        package.add_module(name=path_parts[0], **node.__dict__)
    else:
        package.other_files.add(file_path)

# Стадия 2
link(root_package)

# Стадия 3
obfuscate(root_package)

# Стадия 4

print("\nwriting\n")

# Удаление конечной директории, если она существует
shutil.rmtree(dst_dir_path, ignore_errors=True)

# Удаление создание директорий и поддиректорий, копиравание не ".py" файлов
for p in root_package.walk_packages():
    dst_path = dst_dir_path / "/".join(s.data for s in p.parts()[1:])
    dst_path.mkdir(parents=True, exist_ok=True)

    for other_file in p.other_files:
        shutil.copyfile(other_file, dst_path/other_file.name)

# Обратное преобразование АСД в исходный код, запись в файл
for node in root_package.walk():
    path_parts = node.parts()[1:]
    path_parts = "/".join(s.data for s in path_parts)

    with open(dst_dir_path/f"{path_parts}.py", "wb") as f:
        bytes = ast.unparse(node).encode("utf-8")
        f.write(bytes)
