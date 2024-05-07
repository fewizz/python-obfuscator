import ast
from collections import UserString
from .types import (
    Module, Name, ClassDef, FunctionDef, AsyncFunctionDef,
    ImportFrom, Package, Attribute, arg, alias
)
from .members import members


level = 0
transforming = set[Module]()


class Transformer(ast.NodeTransformer):
    def __init__(
        self,
        node: Module | ClassDef | FunctionDef | AsyncFunctionDef,
        root_package: Package,
        transformed_modules: set["Transformer"],
        deferred: list[FunctionDef | AsyncFunctionDef]
    ):
        self.node = node
        self.root_package = root_package
        self.handled_modules = transformed_modules
        self.deferred = deferred

    def visit_Module(self, node: Module):
        global level

        full_name = '.'.join(p.data for p in node.path())
        if node in (t.node for t in self.handled_modules):
            print(f"{'  '*level}skipping module \"{full_name}\"")
            return node

        assert node not in transforming
        transforming.add(node)

        assert self.node is node

        print(f"{'  '*level}module \"{full_name}\"")
        level += 1

        self.generic_visit(node)

        self.handled_modules.add(self)

        level -= 1

        return node

    def resolve_deferred(self):
        assert isinstance(self.node, Module)

        global level
        full_name = '.'.join(p.data for p in self.node.path())

        print(f"{'  '*level}module (deferred) \"{full_name}\"")
        level += 1

        for deferred in self.deferred:
            Transformer(
                node=deferred,
                root_package=self.root_package,
                transformed_modules=self.handled_modules,
                deferred=self.deferred
            ).visit(deferred)

        level -= 1

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

            e = None

            if isinstance(_from_where, Package):
                e = _from_where.try_get(a.name)

                if isinstance(e, Module):
                    Transformer(
                        node=e,
                        root_package=self.root_package,
                        transformed_modules=self.handled_modules,
                        deferred=list()
                    ).visit(e)
                elif e is None:
                    init = _from_where.try_get_module("__init__")
                    assert isinstance(init, Module)
                    Transformer(
                        node=init,
                        root_package=self.root_package,
                        transformed_modules=self.handled_modules,
                        deferred=list()
                    ).visit(init)
                    _from_where = init
                else:
                    assert isinstance(e, Package)
                    for m in e.entries:
                        if isinstance(m, Module):
                            Transformer(
                                node=m,
                                root_package=self.root_package,
                                transformed_modules=self.handled_modules,
                                deferred=list()
                            ).visit(m)

            if e is None:
                assert isinstance(_from_where, Module)

                Transformer(
                    node=_from_where,
                    root_package=self.root_package,
                    transformed_modules=self.handled_modules,
                    deferred=list()
                ).visit(_from_where)

                scope = members(_from_where)
                assert a.name in scope

                e = scope[a.name]

            assert not isinstance(e, arg)

            what.append(alias(entity=e, asname=a.asname))

        return ImportFrom(
            owner=self.node,
            what=what
        )

    def visit_Name(self, node: ast.Name):
        assert type(node) is ast.Name
        new_node = Name(owner=self.node, id=node.id, ctx=node.ctx)

        scope = members(self.node)

        if type(node.ctx) is ast.Store and node.id not in scope:
            scope[node.id] = new_node
        elif node.id in scope:
            e = scope[node.id]
            new_node.name_ptr = e.name_ptr

        return new_node

    def visit_Attribute(self, node: ast.Attribute):
        assert type(node) is ast.Attribute
        self.generic_visit(node)

        scope = members(self.node)
        left = node.value
        right = UserString(node.attr)

        if (
            isinstance(left, Name)
            and left.id in scope
            and not isinstance(scope[left.id], arg)
        ):
            left = scope[left.id]
            if not isinstance(left, Name | arg):
                left_scope = members(left)
                if right.data in left_scope:
                    right = left_scope[right.data]

        elif (
            isinstance(left, Attribute)
            and isinstance(left.right, ClassDef | Module)
        ):
            right_scope = members(left.right)
            if right.data in right_scope:
                right = right_scope[right.data]

        new_node = Attribute(left=left, right=right, ctx=node.ctx)
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

    def visit_arg(self, node: ast.arg):
        assert isinstance(node, ast.arg)
        self.generic_visit(node)
        return arg(**node.__dict__)

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

    # different order of visiting

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        assert isinstance(node, ast.GeneratorExp)
        new_node = ast.GeneratorExp(**node.__dict__)
        new_node.generators[:] = (self.visit(g) for g in new_node.generators)
        new_node.elt = self.visit(new_node.elt)
        return new_node

    def visit_SetComp(self, node: ast.SetComp):
        assert isinstance(node, ast.SetComp)
        new_node = ast.SetComp(**node.__dict__)
        new_node.generators[:] = (self.visit(g) for g in new_node.generators)
        new_node.elt = self.visit(new_node.elt)
        return new_node

    def visit_ListComp(self, node: ast.ListComp):
        assert isinstance(node, ast.ListComp)
        new_node = ast.ListComp(**node.__dict__)
        new_node.generators[:] = (self.visit(g) for g in new_node.generators)
        new_node.elt = self.visit(new_node.elt)
        return new_node

    def visit_DictComp(self, node: ast.DictComp):
        assert isinstance(node, ast.DictComp)
        new_node = ast.DictComp(**node.__dict__)
        new_node.generators[:] = (self.visit(g) for g in new_node.generators)
        new_node.key = self.visit(new_node.key)
        new_node.value = self.visit(new_node.value)
        return new_node

    def visit_Assign(self, node: ast.Assign):
        assert isinstance(node, ast.Assign)
        new_node = ast.Assign(**node.__dict__)
        new_node.value = self.visit(new_node.value)
        new_node.targets[:] = (self.visit(t) for t in new_node.targets)
        return new_node
