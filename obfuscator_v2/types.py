import ast
from typing import Generator
from dataclasses import dataclass, field
from collections import abc, UserString


class Module(ast.Module):

    def __init__(
        self,
        module: ast.Module,
        name: str,
        package: "Package"
    ):
        super().__init__(**module.__dict__)
        self.name = name
        self.package = package
        self.members = dict[str, ast.ClassDef | ast.FunctionDef | ast.Name]()

    def full_path(self):
        return self.package.full_path() + [self.name]


@dataclass
class Package:
    name: str
    base: "Package | None" = None
    subs: dict[str, "Module | Package"] = field(default_factory=dict)

    def add_module(
        self,
        package_path: abc.Sequence[str],
        node: ast.Module,
        name: str
    ) -> Module:
        if len(package_path) > 0:
            package_name = package_path[0]
            if package_name not in self.subs:
                self.subs[package_name] = Package(
                    name=package_name,
                    base=self
                )

            package = self.subs[package_name]
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
            self.subs[node.name] = node
            return node

    def get(self, path: list[str]) -> "Package | Module":
        assert len(path) > 0

        if len(path) > 1:
            sub = self.subs[path[0]]
            assert isinstance(sub, Package)
            return sub.get(path[1:])
        else:
            return self.subs[path[0]]

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
        result.append(self.name)
        return result


class Name(ast.Name):
    _id: UserString

    def __init__(self, node: ast.Name):
        super().__init__(**node.__dict__)

    @property
    def id(self):
        return self._id.data

    @id.setter
    def id(self, value: str):
        self._id = UserString(value)


class ClassDef(ast.ClassDef):
    _name: UserString

    def __init__(self, node: ast.ClassDef):
        super().__init__(**node.__dict__)

    @property
    def name(self):
        return self._name.data

    @name.setter
    def name(self, value: str):
        self._name = UserString(value)


class FunctionDef(ast.FunctionDef):
    _name: UserString

    def __init__(self, node: ast.FunctionDef):
        super().__init__(**node.__dict__)

    @property
    def name(self):
        return self._name.data

    @name.setter
    def name(self, value: str):
        self._name = UserString(value)


class alias(ast.alias):
    _name: UserString

    def __init__(self, node: ast.alias):
        super().__init__(**node.__dict__)

    @property
    def name(self):
        return self._name.data

    @name.setter
    def name(self, value: str):
        self._name = UserString(value)


class ImportFrom(ast.ImportFrom):
    _module: Module

    def __init__(self, node: ast.ImportFrom):
        super().__init__(**node.__dict__)
        self.names = [alias(a) for a in node.names]
