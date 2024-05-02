import ast
from collections import UserString
from .types import (
    Module, Name, ClassDef, FunctionDef, AsyncFunctionDef,
    ImportFrom, Package, alias, Attribute
)


class ModuleGlobalsTransformer(ast.NodeTransformer):
    def __init__(
        self,
        node: Module | ClassDef | FunctionDef | AsyncFunctionDef,
        root_package: Package,
        handled_modules: set[Module],
        globals: dict[
            str, Name | Module | ClassDef | FunctionDef | AsyncFunctionDef
        ] | None = None
    ):
        self.node = node
        self.entities = dict[
            str,
            Name | Module | ClassDef | FunctionDef | AsyncFunctionDef
        ]()
        self.root_package = root_package
        self.handled = handled_modules
        if globals is None:
            globals = dict[
                str, Name | Module | ClassDef | FunctionDef | AsyncFunctionDef
            ]()
        self.globals = globals

    def visit(self, node):
        if isinstance(node, Module):
            if node in self.handled:
                return node
            super().visit(node)
            self.handled.add(node)
            return node
        else:
            return super().visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level == 0:
            from_where = None
        else:
            _l = node.level
            from_where = self.node.owning_module()
            while _l > 0:
                _l -= 1
                from_where = from_where.owner

            assert isinstance(from_where, Package)

        if node.module is not None:
            path = node.module.split(".")
            if (
                from_where is None and
                path[0] == self.root_package.name_ptr.data
            ):
                from_where = self.root_package
                path = path[1:]

            if from_where is None:
                return node

            while len(path) > 0:
                assert isinstance(from_where, Package)
                from_where = from_where.get(path[0])
                path = path[1:]

        if from_where is None:
            return node

        what = list[alias]()

        for a in node.names:
            _from_where = from_where

            if isinstance(_from_where, Package):
                e = _from_where.try_get_module(a.name)
                if e is not None:
                    ModuleGlobalsTransformer(
                        node=e,
                        root_package=self.root_package,
                        handled_modules=self.handled
                    ).visit(e)
                    what.append(alias(entity=e, asname=a.asname))
                    self.entities[a.asname or a.name] = e
                    continue
                else:
                    _from_where = _from_where.try_get_module("__init__")
                    assert _from_where is not None

            assert isinstance(_from_where, Module)

            ModuleGlobalsTransformer(
                node=_from_where,
                root_package=self.root_package,
                handled_modules=self.handled,
            ).visit(_from_where)
            globals = _from_where.globals()

            if a.name in globals:
                e = globals[a.name]
            else:
                e = _from_where.owner.get(name=a.name)

            what.append(alias(entity=e, asname=a.asname))

            if isinstance(e, Package):
                e = e.try_get_module("__init__")
                assert isinstance(e, Module)
                ModuleGlobalsTransformer(
                    node=e,
                    root_package=self.root_package,
                    handled_modules=self.handled
                ).visit(e)

            self.entities[a.asname or a.name] = e

        return ImportFrom(
            owner=self.node,
            from_where=from_where,
            what=what
        )

    def visit_Name(self, node: ast.Name):
        name = Name(id=node.id, ctx=node.ctx)

        if type(node.ctx) is ast.Store and node.id not in self.entities:
            self.entities[node.id] = name
        else:
            scope = self.globals | self.entities
            if node.id in scope:
                e = scope[node.id]
                if isinstance(e, Module) and e.name_ptr.data == "__init__":
                    e = e.owner
                name.name_ptr = e.name_ptr

        return name

    def visit_Attribute(self, node):
        if isinstance(node, Attribute):
            return node

        assert type(node) is ast.Attribute
        super().generic_visit(node)

        scope = self.entities | self.globals
        entity = node.value
        attr_name = UserString(node.attr)

        if isinstance(node.value, Name) and node.value.id in scope:
            entity = scope[node.value.id]
            # if (
            #     isinstance(entity, Module)
            #     and entity.name_ptr.data == "__init__"
            # ):
            #     entity = entity.owner
            assert isinstance(entity, Name | Module | ClassDef | FunctionDef)

            if isinstance(entity, Module):
                attr_name = entity.globals()[node.attr].name_ptr

        node = Attribute(entity=entity, attr=attr_name, ctx=node.ctx)

        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        assert type(node) is ast.ClassDef

        _node = ClassDef(self.node, **node.__dict__)
        self.entities[_node.name_ptr.data] = _node

        ModuleGlobalsTransformer(
            node=_node,
            root_package=self.root_package,
            handled_modules=self.handled,
            globals=self.entities | self.globals
        ).generic_visit(_node)

        return _node

    def visit_FunctionDef(self, node):
        if not isinstance(node, FunctionDef):
            node = FunctionDef(self.node, **node.__dict__)
            self.entities[node.name_ptr.data] = node
        assert isinstance(node, FunctionDef)
        return node

    def visit_AsyncFunctionDef(self, node):
        if not isinstance(node, AsyncFunctionDef):
            node = AsyncFunctionDef(self.node, **node.__dict__)
            self.entities[node.name_ptr.data] = node
        assert isinstance(node, AsyncFunctionDef)
        return node
