import ast
from collections import UserString
from .types import (
    Module, Name, ClassDef, FunctionDef, AsyncFunctionDef,
    ImportFrom, Package, alias, Attribute
)
from .members import members


level = 0
transforming = set[Module]()


class Transformer(ast.NodeTransformer):
    def __init__(
        self,
        node: Module | ClassDef | FunctionDef | AsyncFunctionDef,
        root_package: Package,
        transformed_modules: set[Module],
        deferred: list[FunctionDef | AsyncFunctionDef]
    ):
        self.node = node
        self.root_package = root_package
        self.handled_modules = transformed_modules
        self.deferred = deferred  # list[FunctionDef | AsyncFunctionDef]()

    def visit_Module(self, node: Module):
        global level

        full_name = '.'.join(p.data for p in node.path())
        if node in self.handled_modules:
            print(f"{'  '*level}skipping module \"{full_name}\"")
            return node

        assert node not in transforming
        transforming.add(node)

        assert self.node is node

        print(f"{'  '*level}module \"{full_name}\"")
        level += 1

        self.generic_visit(node)
        self.handled_modules.add(node)

        for deferred in self.deferred:
            Transformer(
                node=deferred,
                root_package=self.root_package,
                transformed_modules=self.handled_modules,
                deferred=self.deferred
            ).visit(deferred)

        level -= 1

        return node

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
                    Transformer(
                        node=e,
                        root_package=self.root_package,
                        transformed_modules=self.handled_modules,
                        deferred=list()
                    ).visit(e)
                    what.append(alias(entity=e, asname=a.asname))
                    continue
                else:
                    _from_where = _from_where.try_get_module("__init__")
                    assert _from_where is not None

            assert isinstance(_from_where, Module)

            Transformer(
                node=_from_where,
                root_package=self.root_package,
                transformed_modules=self.handled_modules,
                deferred=list()
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
                Transformer(
                    node=e,
                    root_package=self.root_package,
                    transformed_modules=self.handled_modules,
                    deferred=list()
                ).visit(e)

        return ImportFrom(
            owner=self.node,
            from_where=from_where,
            what=what
        )

    def visit_Name(self, node: ast.Name):
        assert type(node) is ast.Name
        new_node = Name(id=node.id, ctx=node.ctx)

        scope = members(self.node)

        if type(node.ctx) is ast.Store and node.id not in scope:
            scope[node.id] = new_node
        else:
            if node.id in scope:
                e = scope[node.id]
                if isinstance(e, Module) and e.name_ptr.data == "__init__":
                    e = e.owner
                new_node.name_ptr = e.name_ptr

        return new_node

    def visit_Attribute(self, node: ast.Attribute):
        assert type(node) is ast.Attribute
        self.generic_visit(node)

        scope = members(self.node)  # self.entities | self.globals
        entity = node.value
        attr_name = UserString(node.attr)

        if isinstance(node.value, Name) and node.value.id in scope:
            entity = scope[node.value.id]
            assert isinstance(entity, Name | Module | ClassDef | FunctionDef)

            if isinstance(entity, Module):
                attr_name = entity.globals()[node.attr].name_ptr

        new_node = Attribute(entity=entity, attr=attr_name, ctx=node.ctx)
        return new_node

    def visit_ClassDef(self, node: ast.ClassDef):
        assert type(node) is ast.ClassDef

        global level
        print(f"{'  '*level}class \"{node.name}\"")
        level += 1

        node = ClassDef(owner=self.node, **node.__dict__)

        Transformer(
            node=node,
            root_package=self.root_package,
            transformed_modules=self.handled_modules,
            deferred=self.deferred
        ).generic_visit(node)

        level -= 1

        return node

    def visit_FunctionDef(self, node: ast.FunctionDef | FunctionDef):
        if node is self.node:
            assert type(node) is FunctionDef

            global level
            print(f"{'  '*level}function \"{node.name}\"")
            level += 1

            self.generic_visit(node)

            level -= 1
        elif type(node) is ast.FunctionDef:
            node = FunctionDef(owner=self.node, **node.__dict__)
            self.deferred.append(node)

        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | AsyncFunctionDef
    ):
        if node is self.node:
            assert type(node) is AsyncFunctionDef
            self.generic_visit(node)
        elif type(node) is ast.AsyncFunctionDef:
            node = AsyncFunctionDef(owner=self.node, **node.__dict__)
            self.deferred.append(node)

        return node

    def generic_visit(self, node):
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                # new_values = []
                for idx, value in enumerate(old_value):
                    # if isinstance(value, ast.AST):
                    value = self.visit(value)
                    if value is None:
                        continue
                    else:
                        old_value[idx] = value
                        # elif not isinstance(value, ast.AST):
                        #     raise RuntimeError()
                        #     new_values.extend(value)
                        #     continue
                    # new_values.append(value)
                # old_value[:] = new_values
            elif isinstance(old_value, ast.AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node
