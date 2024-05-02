import ast
from typing import Generator
from collections import abc, UserString


class Module(ast.Module):
    _name: UserString

    def __init__(
        self,
        module: ast.Module,
        name: str,
        package: "Package"
    ):
        super().__init__(**module.__dict__)
        self._name = UserString(name)
        self.package = package

    def full_path(self):
        return self.package.full_path() + [self._name.data]

    def full_name(self):
        return ".".join(self.full_path())

    def members(self, particular_name: str | None = None):
        result = list[ClassDef | FunctionDef | Name | Module | Package]()

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ClassDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_FunctionDef(self, node: FunctionDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_Name(self, node: Name):
                if particular_name and particular_name != node.id:
                    return
                result.append(node)

            def visit_ImportFrom(self, node):
                if not isinstance(node, ImportFrom):
                    return
                result.extend((n._entity for n in node.names))

        Visitor().visit(self)
        return result


class Package:

    def __init__(self, name: str | UserString, base: "Package | None" = None):
        if isinstance(name, str):
            self._name = UserString(name)
        else:
            self._name = name
        self.subs = dict[UserString, "Module | Package"]()
        self.base = base

    def add_module(
        self,
        package_path: abc.Sequence[str],
        node: ast.Module,
        name: str
    ) -> Module:
        if len(package_path) > 0:
            package_name = package_path[0]
            _name = UserString(package_name)

            if package_name not in self.subs:
                self.subs[_name] = Package(
                    name=_name,
                    base=self
                )

            package = self.subs[_name]
            assert isinstance(package, Package)
            return package.add_module(
                package_path=package_path[1:],
                node=node,
                name=name
            )
        else:
            assert name not in self.subs
            node = Module(
                module=node,
                name=name,
                package=self
            )
            self.subs[node._name] = node
            return node

    def get(self, path: list[str]) -> "Package | Module":
        assert len(path) > 0

        if len(path) > 1:
            sub = self.subs[UserString(path[0])]
            assert isinstance(sub, Package)
            return sub.get(path[1:])
        else:
            return self.subs[UserString(path[0])]

    def walk(self) -> Generator["Module", None, None]:
        for sub in self.subs.values():
            if isinstance(sub, Module):
                yield sub
            else:
                yield from sub.walk()

    def full_path(self) -> list[str]:
        if self.base is None:
            result = list[str]()
        else:
            result = self.base.full_path()
        result.append(self._name.data)
        return result


class Name(ast.Name):
    _name: UserString

    def __init__(self, base, name: str | UserString, ctx: ast.expr_context):
        self.base = base

        if isinstance(name, str):
            name = UserString(name)
        self._name = name
        self.ctx = ctx

    @property
    def id(self):
        return self._name.data

    @property  # For consistency
    def name(self):
        return self._name.data


class ClassDef(ast.ClassDef):
    _base: "Module | ClassDef | FunctionDef"
    _name: UserString
    bases: list["ClassDef | ast.expr"]

    def __init__(
        self,
        base: "Module | ClassDef | FunctionDef",
        node: ast.ClassDef
    ):
        super().__init__(**node.__dict__)
        self._base = base

    @property
    def name(self):
        return self._name.data

    @name.setter
    def name(self, value: str):
        self._name = UserString(value)

    def members(self, particular_name: str | None = None, bases: bool = True):
        result = self._base.members()

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ClassDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_FunctionDef(self, node: FunctionDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_Name(self, node: Name):
                if particular_name and particular_name != node.id:
                    return
                result.append(node)

        for s in self.body:
            Visitor().visit(s)

        return result


class FunctionDef(ast.FunctionDef):
    _name: UserString

    def __init__(self, base, node: ast.FunctionDef):
        self.base = base
        super().__init__(**node.__dict__)

    @property
    def name(self):
        return self._name.data

    @name.setter
    def name(self, value: str):
        self._name = UserString(value)

    def members(
        self, particular_name: str | None = None
    ):
        result = list["Module | ClassDef | FunctionDef | Name"]()

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ClassDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_FunctionDef(self, node: FunctionDef):
                if particular_name and particular_name != node.name:
                    return
                result.append(node)

            def visit_Name(self, node: Name):
                if particular_name and particular_name != node.id:
                    return
                result.append(node)

        for s in self.body:
            Visitor().visit(s)

        return result


class alias(ast.AST):

    def __init__(
        self,
        entity: Package | Module | ClassDef | FunctionDef | Name,
        asname: str | None
    ):
        self._entity = entity
        self.asname = asname

    @property
    def name(self):
        return self._entity._name.data


class ImportFrom(ast.ImportFrom):
    _base: Module
    _from: Module | Package
    names: list[alias]

    def __init__(self, base, _from, names: list[alias]):
        self._base = base
        self._from = _from
        self.names = names

    def _branching_module_path(self):
        base_path = self._base.full_path()
        from_path = self._from.full_path()

        result = list[str]()
        for b, f in zip(base_path, from_path):
            if b != f:
                break
            result.append(b)

        return result

    @property
    def module(self):
        f = self._from.full_path()
        b = self._branching_module_path()
        result = f[len(b):]
        return ".".join(result) if len(result) else None

    @property
    def level(self):
        base = self._base.full_path()
        brch = self._branching_module_path()
        diff = len(base) - len(brch)
        assert diff >= 0
        return diff


class Attribute(ast.Attribute):
    _attr: UserString

    def __init__(self, base, node: ast.Attribute):
        self.base = base
        self._attr = None  # type: ignore
        super().__init__(**node.__dict__)

    @property
    def attr(self):
        return self._attr.data

    @attr.setter
    def attr(self, value: str):
        if self._attr is None:
            self._attr = UserString(value)
        else:
            self._attr.data = value
