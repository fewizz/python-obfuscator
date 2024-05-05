import ast
from typing import Generator
from collections import UserString


class Name(ast.expr):
    name_ptr: UserString
    ctx: ast.expr_context

    def __init__(self, id: str | UserString, ctx):
        if isinstance(id, str):
            id = UserString(id)
        self.name_ptr = id
        self.ctx = ctx

    @property
    def id(self):
        return self.name_ptr.data


class Package:

    def __init__(self, owner: "Package | None", name: str):
        self.owner = owner
        self.name_ptr = UserString(name)
        self.entries = set[Package | Module]()

    def add_module(self, name: str, *args, **kwargs):
        assert next(
            (e for e in self.entries if e.name_ptr == name),
            None
        ) is None
        m = Module(owner=self, name=name, *args, **kwargs)
        self.entries.add(m)
        return m

    def try_get_module(self, name: str):
        return next(
            (
                e for e in self.entries
                if isinstance(e, Module) and e.name_ptr == name
            ),
            None
        )

    def get_or_add_package(self, name: str):
        p = next((e for e in self.entries if e.name_ptr == name), None)
        if p is not None:
            assert isinstance(p, Package)
            return p
        p = Package(owner=self, name=name)
        self.entries.add(p)
        return p

    def get(self, name: str):
        return next(e for e in self.entries if e.name_ptr == name)

    def path(self) -> list[UserString]:
        if self.owner is not None:
            result = self.owner.path()
        else:
            result = list()
        result.append(self.name_ptr)
        return result

    def walk(self) -> Generator["Module", None, None]:
        for e in self.entries:
            if isinstance(e, Module):
                yield e
            else:
                yield from e.walk()


class Module(ast.Module):
    owner: Package
    name_ptr: UserString

    def __init__(self, owner: Package, name: str, *args, **kwargs):
        self.owner = owner
        self.name_ptr = UserString(name)
        super().__init__(*args, **kwargs)

    def owning_module(self):
        return self

    def path(self):
        return self.owner.path() + [self.name_ptr]

    # def globals(self):
    #     globals = dict[
    #         str,
    #         "Name | Module | ClassDef | FunctionDef | AsyncFunctionDef"
    #     ]()

    #     class Visitor(ast.NodeVisitor):
    #         def visit_ImportFrom(self, node: ImportFrom):
    #             if not isinstance(node, ImportFrom):
    #                 return
    #             for alias in node.what:
    #                 name = alias.entity.name_ptr.data

    #                 if alias.asname is not None:
    #                     name = alias.asname.data

    #                 assert isinstance(name, str)

    #                 e = alias.entity

    #                 if isinstance(e, Package):
    #                     e = e.try_get_module("__init__")
    #                     assert e is not None

    #                 globals[name] = e

    #         def visit_Name(self, node: Name):
    #             if type(node.ctx) is ast.Store:
    #                 globals[node.name_ptr.data] = node

    #         def visit_ClassDef(self, node: ClassDef):
    #             globals[node.name_ptr.data] = node

    #         def visit_FunctionDef(self, node: FunctionDef):
    #             globals[node.name_ptr.data] = node

    #         def visit_FunctionAsyncDef(self, node: AsyncFunctionDef):
    #             globals[node.name_ptr.data] = node

    #     Visitor().visit(self)

    #     return globals


class alias(ast.AST):
    asname: UserString | None

    def __init__(
        self,
        entity: "Module | Package | Name | ClassDef | FunctionDef | AsyncFunctionDef",  # noqa
        asname: str | None
    ):
        self.entity = entity
        self.asname = UserString(asname) if asname is not None else None

    @property
    def name(self):
        return self.entity.name_ptr.data


class ImportFrom(ast.stmt):
    from_where: Package | Module
    what: list[alias]

    def __init__(
        self,
        owner: "Module | ClassDef | FunctionDef | AsyncFunctionDef",
        from_where: Package | Module,
        what: list[alias]
    ):
        self.owner = owner
        self.from_where = from_where
        self.what = what

    def _branch_path(self):
        owner_path = self.owner.owning_module().path()
        from_path = self.from_where.path()

        result = list[UserString]()
        for b, f in zip(owner_path, from_path):
            if b != f:
                break
            result.append(b)

        return result

    @property
    def level(self):
        branch_path_len = len(self._branch_path())
        owner_path_len = len(self.owner.owning_module().path())
        diff = owner_path_len - branch_path_len
        assert diff >= 0
        return diff

    @property
    def module(self):
        from_path = self.from_where.path()
        branch_path = self._branch_path()
        result = from_path[len(branch_path):]
        return ".".join(s.data for s in result) if len(result) else None

    @property
    def names(self):
        return self.what


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


class Attribute(ast.expr):

    def __init__(
        self,
        left: ast.expr | Package | Module | ClassDef | FunctionDef
        | AsyncFunctionDef | Name,
        right: str | UserString | Module | Package | ClassDef | FunctionDef
        | Name | AsyncFunctionDef,
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
        if isinstance(e, Module) and e.name_ptr.data == "__init__":
            e = e.owner

        if isinstance(e, Name | Module | Package | ClassDef | FunctionDef):
            return Name(e.name_ptr, ctx=ast.Load())

        return e
