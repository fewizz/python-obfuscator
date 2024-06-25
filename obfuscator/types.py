import ast
from pathlib import Path
from typing import Generator
from collections import UserString


class Name(ast.expr):

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        id: str | UserString,
        ctx: ast.expr_context
    ):
        self.owner = owner
        if isinstance(id, str):
            id = UserString(id)
        self.name_ptr = id
        self.ctx = ctx

    @property
    def id(self):
        return self.name_ptr.data


class Package:
    """Абстракция пакета модулей"""

    def __init__(self, owner: "Package | None", name: str):
        """Args:
            owner: Если есть родитель, пакет считается подпакетом
            name: Имя пакета"""
        self.owner = owner
        self.name_ptr = UserString(name)

        self.entries = set[Package | Module]()
        """Содержащиеся в пакете модули или подпакеты"""

        self.other_files = set[Path]()
        """Иные файлы"""

    def add_module(self, name: str, node: ast.Module):
        """Создает, добавляет и возвращает модуль с именем name"""
        assert next(
            (e for e in self.entries if e.name_ptr == name),
            None
        ) is None
        m = Module(owner=self, name=name, **node.__dict__)
        self.entries.add(m)
        return m

    def try_get_module(self, name: str):
        """Возвращает модуль, либо None"""
        return next(
            (
                e for e in self.entries
                if isinstance(e, Module) and e.name_ptr == name
            ),
            None
        )

    def get_or_add_package(self, name: str):
        """Возможно создает, и возвращает подпакет с именем name"""
        p = self.try_get(name)
        if p is not None:
            assert isinstance(p, Package)
            return p
        p = Package(owner=self, name=name)
        self.entries.add(p)
        return p

    def get(self, name: str):
        """Получение подпакета или модуля по имени"""
        return next(e for e in self.entries if e.name_ptr == name)

    def try_get(self, name: str):
        return next(
            (e for e in self.entries if e.name_ptr == name),
            None
        )

    def parts(self) -> list[UserString]:
        """Возвращает в виде списка имена пакетов по иерархии,
        начиная с корневого пакета"""
        if self.owner is not None:
            result = self.owner.parts()
        else:
            result = list()
        result.append(self.name_ptr)
        return result

    def walk(self) -> Generator["Module", None, None]:
        """Рекурсивное получение всех модулей, и модулей подпакетов"""
        for e in self.entries:
            if isinstance(e, Module):
                yield e
            else:
                yield from e.walk()

    def walk_packages(self) -> Generator["Package", None, None]:
        yield self
        for e in self.entries:
            if isinstance(e, Package):
                yield from e.walk_packages()


class Module(ast.Module):
    owner: Package
    name_ptr: UserString

    def __init__(self, owner: Package, name: str, *args, **kwargs):
        self.owner = owner
        self.name_ptr = UserString(name)
        super().__init__(*args, **kwargs)

    def owning_module(self):
        return self

    def parts(self):
        return self.owner.parts() + [self.name_ptr]

    def move_to(self, package: Package):
        prev_owner = self.owner
        prev_owner.entries.remove(self)

        self.owner = package
        package.entries.add(self)


class alias:

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        entity: "Module | Package | ClassDef | FunctionDef | AsyncFunctionDef | Name",  # noqa
        asname: str
    ):
        self.owner = owner
        self.entity = entity
        self.name_ptr = UserString(asname)

    @property
    def name(self):
        return self.name_ptr.data

    @property
    def asname(self):
        return None


class ImportFrom(ast.stmt):

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        what: list["alias | Package | Module | ClassDef | FunctionDef | AsyncFunctionDef | Name"]  # noqa
    ):
        self.owner = owner
        self.what = what

    def from_where(self):
        first = self.what[0]
        if isinstance(first, alias):
            _from = first.entity.owner
        else:
            _from = first.owner
        assert isinstance(_from, Package | Module)
        return _from

    def _branch_path(self):
        owner_path = self.owner.owning_module().parts()
        from_path = self.from_where().parts()

        result = list[UserString]()
        for b, f in zip(owner_path, from_path):
            if b != f:
                break
            result.append(b)

        return result

    @property
    def level(self):
        branch_path_len = len(self._branch_path())
        owner_path_len = len(self.owner.owning_module().parts())
        diff = owner_path_len - branch_path_len
        assert diff >= 0
        return diff

    @property
    def module(self):
        from_path = self.from_where().parts()
        branch_path = self._branch_path()
        result = from_path[len(branch_path):]
        result = ".".join(s.data for s in result) if len(result) else None
        return result

    @property
    def names(self):
        return [
            ast.alias(
                name=e.name_ptr.data,
                asname=None
            ) if not isinstance(e, alias)
            else ast.alias(
                name=e.entity.name_ptr.data,
                asname=e.name_ptr.data
            )
            for e in self.what
        ]


class ClassDef(ast.ClassDef):
    name_ptr: UserString

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        *args,
        **kwargs
    ):
        self.owner = owner
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self.name_ptr.data

    @name.setter
    def name(self, value: str):
        self.name_ptr = UserString(value)

    def owning_module(self):
        o = self.owner
        while not isinstance(o, Module):
            o = o.owner
        return o


class FunctionDef(ast.FunctionDef):
    name_ptr: UserString

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        *args,
        **kwargs
    ):
        self.owner = owner
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self.name_ptr.data

    @name.setter
    def name(self, value: str):
        self.name_ptr = UserString(value)

    def owning_module(self):
        o = self.owner
        while not isinstance(o, Module):
            o = o.owner
        return o


class AsyncFunctionDef(ast.AsyncFunctionDef):
    name_ptr: UserString

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        *args,
        **kwargs
    ):
        self.owner = owner
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self.name_ptr.data

    @name.setter
    def name(self, value: str):
        self.name_ptr = UserString(value)

    def owning_module(self):
        o = self.owner
        while not isinstance(o, Module):
            o = o.owner
        return o


class arg(ast.arg):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def arg(self):
        return self.name_ptr.data

    @arg.setter
    def arg(self, value: str):
        self.name_ptr = UserString(value)


class Attribute(ast.expr):

    def __init__(
        self,
        left: ast.expr | Package | Module | ClassDef
        | FunctionDef | AsyncFunctionDef | Name | arg | alias,
        right: str | UserString | Package | Module | ClassDef
        | FunctionDef | AsyncFunctionDef | Name | arg | alias,
        ctx: ast.expr_context
    ):
        self.left = left
        if isinstance(right, str):
            right = UserString(right)
        self.right = right
        self.ctx = ctx

    @property
    def attr(self):
        return self.name_ptr.data

    @property
    def name_ptr(self) -> UserString:
        if isinstance(self.right, UserString):
            return self.right
        else:
            return self.right.name_ptr

    @property
    def value(self):
        e = self.left

        if isinstance(
            e,
            Package | Module | ClassDef | FunctionDef | AsyncFunctionDef | Name
        ):
            return ast.Name(id=e.name_ptr.data, ctx=ast.Load())

        return e
