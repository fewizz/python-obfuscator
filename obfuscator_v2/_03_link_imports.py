import ast
from collections import UserString
from obfuscator_v2.types import Module, Package, ImportFrom, alias


class ImportLinker(ast.NodeTransformer):
    def __init__(
        self,
        root_package: Package,
        module_node: Module,
        processed_modules: set[str]
    ):
        self.root_package = root_package
        self.module_node = module_node
        self.processed_modules = processed_modules

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.processed_modules.add(self.module_node.full_name())

        if node.level == 0:
            _from = None
        else:
            _from = self.module_node.package
            _level = node.level - 1
            while _level > 0:
                assert _from.base is not None
                _from = _from.base
                _level -= 1

        if node.module is not None:
            path = node.module.split(".")
            if _from is not None:
                _from = _from.get(path)
            elif path[0] == self.root_package._name:
                _from = self.root_package
                path = path[1:]
                if len(path) > 0:
                    _from = _from.get(path)

        if _from is not None:
            names = list[alias]()

            def ensure_module_handled(module: Module):
                if module.full_name() not in self.processed_modules:
                    ImportLinker(
                        root_package=self.root_package,
                        module_node=module,
                        processed_modules=self.processed_modules
                    ).visit(module)

            init_globals = None

            if isinstance(_from, Module):
                ensure_module_handled(_from)
            elif "__init__" in _from.subs:
                init = _from.subs[UserString("__init__")]
                assert isinstance(init, Module)
                ensure_module_handled(init)
                init_globals = {g._name: g for g in init.members()}

            from_globals = None
            if isinstance(_from, Module):
                from_globals = {g._name: g for g in _from.members()}

            for n in node.names:
                if init_globals is not None and n.name in init_globals:
                    names.append(alias(
                        entity=init_globals[n.name],
                        asname=n.asname
                    ))
                elif isinstance(_from, Module):
                    assert from_globals is not None
                    mem = from_globals[UserString(n.name)]
                    names.append(alias(
                        entity=mem,
                        asname=n.asname
                    ))
                else:
                    names.append(alias(
                        entity=_from.get([n.name]),
                        asname=n.asname
                    ))

            return ImportFrom(
                base=self.module_node,
                _from=_from,
                names=names
            )
        else:
            return node


def link_imports(root_package: Package):
    processed_modules = set[str]()

    for node in root_package.walk():
        if node.full_name() not in processed_modules:
            ImportLinker(
                root_package=root_package,
                module_node=node,
                processed_modules=processed_modules
            ).visit(node)
