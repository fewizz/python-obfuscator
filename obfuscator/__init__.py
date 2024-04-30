from dataclasses import dataclass, field
import ast


@dataclass
class Entity:
    parent: "None | Entity" = None
    name: str | None = None
    translated_name: str | None = None


@dataclass
class EntityWithScope(Entity):
    parent: "None | EntityWithScope" = None
    scope: dict[str, Entity] = field(default_factory=dict)

    # Содержится ли в в данной области видимости, или в области видимости
    # родительских сущностей, сущность с именем key
    def __contains__(self, key: str) -> bool:
        if key in self.scope:
            return True
        if self.parent is not None:
            return key in self.parent
        return False

    # Получение объекта сущности в данной области видимости,
    # или в области видимости родительских сущностей по имени key
    def __getitem__(self, key: str) -> "Entity":
        # В этой области?
        if key in self.scope:
            return self.scope[key]
        # Нет, тогда запрашиваем из родительской сущности
        if self.parent is not None:
            return self.parent[key]
        raise KeyError()

    # создание сущности в данной области видимости
    def _create_entity(
        self,
        name: str,
        translated_name: str,
        type: type["Entity | EntityWithScope"]
    ):
        e = type(
            parent=self,
            name=name,
            translated_name=translated_name
        )
        self.scope[name] = e
        return e

    def create_entity(
        self, name, translated_name
    ) -> Entity:
        return self._create_entity(name, translated_name, Entity)

    def create_entity_with_scope(
        self, name, translated_name
    ) -> "EntityWithScope":
        return self._create_entity(
            name, translated_name, EntityWithScope
        )  # type: ignore


@dataclass(kw_only=True)
class Module(EntityWithScope):
    node: ast.Module


@dataclass
class Class(EntityWithScope):
    pass


class Ctx:
    module_node_and_scope_by_name = dict[
        str, tuple[ast.Module, Module]
    ]()


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
