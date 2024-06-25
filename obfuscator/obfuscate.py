from .types import (
    Package, Module, ClassDef, FunctionDef, AsyncFunctionDef, Name, arg, alias
)
from .members import members


# Получение обфусцированного имени.
def next_obfuscated_name() -> str:
    import uuid
    return "_" + str(uuid.uuid4()).replace("-", "_")


handled_nodes = set()


def handle_node(
    node: Package | ClassDef | Module | FunctionDef | AsyncFunctionDef
    | Name | arg | alias
):
    # Вершина уже обрабатывалась, пропуск
    if node in handled_nodes:
        return
    handled_nodes.add(node)

    # 1. Обфускация имени

    if (  # Если вершина есть пакет или класс
        isinstance(node, Package | ClassDef)
    ) or (  # , либо модуль, кроме "__init__",
        isinstance(node, Module) and not node.name_ptr.data == "__init__"
    ) or (  # , либо функция, определенная в модуле или другой функции
        isinstance(node, FunctionDef | AsyncFunctionDef | Name)
        and isinstance(node.owner, Module | FunctionDef | AsyncFunctionDef)
    ):
        # , то обфусцировать имя
        node.name_ptr.data = next_obfuscated_name()

    #  2. Обфускация дочерних вершин

    if not isinstance(node, Name | arg | alias):
        for m in members(node).values():
            handle_node(m)


def obfuscate(root_package: Package):
    for node in root_package.walk():
        # Обработка пакета модуля (тип Package)
        handle_node(node.owner)

        # Обработка самого модуля (тип Module)
        handle_node(node)
