import ast
import sys
import os
import shutil
import pathlib
from . import next_name, Ctx, Module
from .handle_statements import handle_statements

# Первый аргумент программы - файл исходного кода
if len(sys.argv) <= 1:
    print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
    exit(1)

dir_path = pathlib.Path(sys.argv[1])
dst_dir_path = pathlib.Path(sys.argv[2])

assert dir_path.is_dir()

ctx = Ctx()

for py_path in dir_path.glob("**/*.py"):
    with open(str(py_path), "rb") as f:
        # Создание АСД
        node: ast.Module = ast.parse(source=f.read())

    module_name = py_path.relative_to(dir_path.parent).with_suffix("").parts
    # if module_name[-1] == "__init__":
    #    module_name = module_name[:-1]
    module_name = ".".join(module_name)

    node_and_scope = (node, Module(name=module_name, node=node))

    ctx.module_node_and_scope_by_name[module_name] = node_and_scope
    if module_name.endswith(".__init__"):
        ctx.module_node_and_scope_by_name[
            module_name.removesuffix(".__init__")
        ] = node_and_scope

shutil.rmtree(dst_dir_path, ignore_errors=True)
dst_dir_path.mkdir(parents=True)

for name, (node, scope) in ctx.module_node_and_scope_by_name.items():
    if scope.translated_name is None:
        scope.translated_name = next_name()

        handle_statements(
            ctx,
            stmts=node.body,
            scope=scope,
            module=scope
        )

    # Преобразование АСД обратно в исходный код
    # print()
    # print("File", name, " -> ", scope.translated_name)
    # print(ast.unparse(scope.node))
    os.makedirs("result", exist_ok=True)
    with open(dst_dir_path/f"{scope.translated_name}.py", "w") as f:
        f.write(ast.unparse(node))
