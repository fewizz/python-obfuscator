import ast
from obfuscator_v2.types import Module, Package


class ImportLinker(ast.NodeVisitor):
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
        if node.level == 0:
            begin = None
        else:
            begin = self.module_node.package
            node.level -= 1
            while node.level > 0:
                assert begin.base is not None
                begin = begin.base
                node.level -= 1

        if node.module is not None:
            path = node.module.split(".")
            if begin is not None:
                begin = begin.get(path)
            elif path[0] == self.root_package.name:
                begin = self.root_package
                path = path[1:]
                if len(path) > 0:
                    begin = begin.get(path)

        if begin is not None:
            what = list()

            if isinstance(begin, Module):
                if begin.name not in self.processed_modules:
                    ImportLinker(
                        root_package=self.root_package,
                        module_node=begin,
                        processed_modules=self.processed_modules
                    ).visit(begin)

                for n in node.names:
                    # TODO asname
                    mem = begin.members[n.name]
                    what.append(mem)
                    self.module_node.members[n.name] = mem
            else:
                if "__init__" in begin.subs:
                    init = begin.subs["__init__"]
                    assert isinstance(init, Module)
                    if begin.name not in self.processed_modules:
                        ImportLinker(
                            root_package=self.root_package,
                            module_node=init,
                            processed_modules=self.processed_modules
                        ).visit(init)
                else:
                    init = None

                for n in node.names:
                    # TODO asname
                    if init is not None and n.name in init.members:
                        what.append(init.members[n.name])
                    else:
                        what.append(begin.get([n.name]))

            # print(
            #     self.module_node.name,
            #     "from", begin.name, ":",
            #     [w.name for w in what]
            # )

        self.processed_modules.add(self.module_node.name)


def link_imports(root_package: Package):
    processed_modules = set[str]()

    for node in root_package.walk():
        ImportLinker(
            root_package=root_package,
            module_node=node,
            processed_modules=processed_modules
        ).visit(node)
