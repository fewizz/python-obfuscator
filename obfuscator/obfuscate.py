from .types import (
    Package, Module, ClassDef, FunctionDef, AsyncFunctionDef, Name, arg
)
from .members import members


# Получение обфусцированного имени.
# По мере вызовов метода, возвращаются элементы последовательности:
# a, b, c, ..., z, aa, ab, ..., az, ba, bb, ..., zz, aaa, ...,  и т.д.
def next_name(_name_idx: list[int] = [0]) -> str:
    # name_chars = list()
    # name_idx: int = _name_idx[0]

    # while True:
    #     name_chars.append(chr(ord('a') + (name_idx % 26)))
    #     name_idx //= 26
    #     if name_idx == 0:
    #         break

    # _name_idx[0] += 1

    # return "obfuscated_" + ''.join(name_chars)
    import uuid
    return "_" + str(uuid.uuid4()).replace("-", "_")


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
        (
            isinstance(node, Name)
            and isinstance(node.owner, FunctionDef | AsyncFunctionDef)
        )
        or
        isinstance(node, Package)
    ):
        node.name_ptr.data = next_name()


def obfuscate(root_package: Package):
    for node in root_package.walk():
        # Обработка пакета модуля
        handle_node(node.owner)

        # Обработка модуля
        handle_node(node)
