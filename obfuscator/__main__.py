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
src_dir_path = Path(sys.argv[1])
assert src_dir_path.is_dir()  # Должна быть директорией

# Директория назначения
dst_dir_path = Path(sys.argv[2])

# Создание корневого пакета
root_package = Package(owner=None, name=src_dir_path.name)
# и его наполнение
for file_path in src_dir_path.glob("**/*.*"):

    # Получение имен всех подпакетов
    parts = file_path .relative_to(src_dir_path).with_suffix("").parts

    if "__pycache__" in parts:
        continue

    # Поиск (или создание) соответствующего подпакета
    package = root_package
    while len(parts) > 1:
        package = package.get_or_add_package(name=parts[0])
        parts = parts[1:]
    assert len(parts) > 0

    if file_path.suffix == ".py":
        # Если файл - модуль, создается его АСД,
        # и добавляется в соответствующий пакет
        with open(str(file_path), "rb") as f:
            package.add_module(
                name=parts[0],
                node=ast.parse(source=f.read())
            )
    else:
        # Иначе файл добавляется в пакет как сторонний
        package.other_files.add(file_path)


# Стадия 2
link(root_package)

# Стадия 3
obfuscate(root_package)

# Стадия 4
print("\nwriting\n")

# Рекурсивное удаление директории назначения, если она существует
shutil.rmtree(dst_dir_path, ignore_errors=True)

# Удаление создание директорий и поддиректорий,
# копирование иных (не .py) файлов
for p in root_package.walk_packages():
    dst_path = dst_dir_path / "/".join(s.data for s in p.parts()[1:])
    dst_path.mkdir(parents=True, exist_ok=True)

    for other_file in p.other_files:
        assert dst_path.exists()
        shutil.copyfile(other_file, dst_path/other_file.name)

# Обратное преобразование АСД в исходный код, запись в файл
for node in root_package.walk():
    parts = node.parts()[1:]
    parts = "/".join(s.data for s in parts)

    with open(dst_dir_path/f"{parts}.py", "wb") as f:
        f.write(ast.unparse(node).encode("utf-8"))
