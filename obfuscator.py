import ast
from dataclasses import dataclass, field


@dataclass
class Entity:
    parent: "None | Entity" = None
    name: str | None = None
    translated_name: str | None = None


@dataclass
class EntityWithScope(Entity):
    parent: "None | EntityWithScope" = None
    scope: dict[str, Entity] = field(default_factory=dict)
    node: ast.Module | ast.ClassDef | ast.FunctionDef | None = None

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


def handle_expression(expr: ast.expr, scope: EntityWithScope) -> None:
    if isinstance(expr, ast.Name):
        # имя встречалось в области видимости
        if expr.id in scope:
            e = scope[expr.id]
            # для данного имени имеется имя транслированное
            if e.translated_name is not None:
                expr.id = e.translated_name

    elif isinstance(expr, ast.Call):
        handle_expression(expr.func, scope)
        for e in expr.args:
            handle_expression(e, scope)
        for e in expr.keywords:
            handle_expression(e.value, scope)

    elif isinstance(expr, ast.Attribute):
        handle_expression(expr.value, scope)

    elif isinstance(expr, ast.BinOp):
        handle_expression(expr.left, scope)
        handle_expression(expr.right, scope)

    elif isinstance(expr, ast.UnaryOp):
        handle_expression(expr.operand, scope)

    elif isinstance(expr, ast.BoolOp):
        handle_expressions(expr.values, scope)

    elif isinstance(expr, ast.Compare):
        handle_expression(expr.left, scope)
        handle_expressions(expr.comparators, scope)

    elif isinstance(expr, ast.GeneratorExp):
        handle_expression(expr.elt, scope)
        for gen in expr.generators:
            handle_expression(gen.target, scope)
            handle_expression(gen.iter, scope)
            handle_expressions(gen.ifs, scope)

    elif isinstance(expr, ast.List):
        for e in expr.elts:
            handle_expression(e, scope)

    elif isinstance(expr, ast.Subscript):
        handle_expression(expr.value, scope)
        handle_expression(expr.slice, scope)

    elif isinstance(expr, ast.Slice):
        if expr.lower is not None:
            handle_expression(expr.lower, scope)
        if expr.upper is not None:
            handle_expression(expr.upper, scope)
        if expr.step is not None:
            handle_expression(expr.step, scope)

    elif isinstance(expr, ast.IfExp):
        handle_expression(expr.test, scope)
        handle_expression(expr.body, scope)
        handle_expression(expr.orelse, scope)

    elif isinstance(expr, ast.JoinedStr):
        handle_expressions(expr.values, scope)

    elif isinstance(expr, ast.FormattedValue):
        handle_expression(expr.value, scope)
        if expr.format_spec is not None:
            handle_expression(expr.format_spec, scope)

    elif isinstance(expr, ast.ListComp | ast.SetComp):
        handle_expression(expr.elt, scope)

        for gen in expr.generators:
            handle_expression(gen.target, scope)
            handle_expression(gen.iter, scope)
            handle_expressions(gen.ifs, scope)

    elif isinstance(expr, ast.DictComp):
        handle_expression(expr.key, scope)
        handle_expression(expr.value, scope)

        for gen in expr.generators:
            handle_expression(gen.target, scope)
            handle_expression(gen.iter, scope)
            handle_expressions(gen.ifs, scope)

    elif isinstance(expr, ast.Dict):
        for k in expr.keys:
            if k is not None:
                handle_expression(k, scope)
        handle_expressions(expr.values, scope)

    elif isinstance(expr, ast.Tuple):
        handle_expressions(expr.elts, scope)
        handle_expressions(expr.dims, scope)

    elif isinstance(expr, ast.Set):
        handle_expressions(expr.elts, scope)

    elif isinstance(expr, ast.Yield):
        if expr.value is not None:
            handle_expression(expr.value, scope)

    elif isinstance(expr, ast.YieldFrom):
        handle_expression(expr.value, scope)

    elif isinstance(expr, ast.Await):
        handle_expression(expr.value, scope)

    elif isinstance(expr, ast.Starred):
        handle_expression(expr.value, scope)

    elif isinstance(expr, ast.Lambda):
        handle_args(expr.args, scope=scope)
        handle_expression(expr.body, scope)

    elif isinstance(expr, (ast.Constant,)):
        pass

    else:
        raise TypeError(expr)


def handle_expressions(exprs: list[ast.expr], scope: EntityWithScope) -> None:
    for expr in exprs:
        handle_expression(expr, scope)


def handle_statements(
    stmts: list[ast.stmt],
    scope: EntityWithScope,
    module: EntityWithScope,
    modules: dict[str, EntityWithScope]
) -> None:
    # Ноды, которые должны быть обработаны позже
    deferred_stmnts = list[tuple[EntityWithScope, list[ast.stmt]]]()
    deferred_exprs = list[tuple[EntityWithScope, list[ast.expr]]]()

    for stmt in stmts:
        if isinstance(stmt, ast.ClassDef):
            translated_name = next_name()
            class_scope = scope.create_entity_with_scope(
                name=stmt.name, translated_name=translated_name
            )
            stmt.name = translated_name

            handle_statements(stmt.body, class_scope, module, modules)
            handle_expressions(exprs=stmt.bases, scope=class_scope)
            handle_expressions(exprs=stmt.decorator_list, scope=class_scope)

        elif isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            translated_name = next_name()
            func_scope = scope.create_entity_with_scope(
                name=stmt.name, translated_name=translated_name
            )
            stmt.name = translated_name

            handle_args(stmt.args, scope=func_scope)

            deferred_exprs.append((func_scope, stmt.decorator_list))
            deferred_stmnts.append((func_scope, stmt.body))

        elif isinstance(stmt, ast.Assign):
            handle_expression(expr=stmt.value, scope=scope)

            for expr in stmt.targets:
                if isinstance(expr, ast.Name) and expr.id not in scope:
                    translated_name = next_name()
                    scope.create_entity(
                        name=expr.id, translated_name=translated_name
                    )
                    expr.id = translated_name
                else:
                    handle_expression(expr=expr, scope=scope)

        elif isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id not in scope
            ):
                translated_name = next_name()
                scope.create_entity(
                    name=stmt.target.id, translated_name=translated_name
                )
                stmt.target.id = translated_name
            else:
                handle_expression(stmt.target, scope)

            handle_expression(stmt.annotation, scope)

            if stmt.value is not None:
                handle_expression(stmt.value, scope)

        elif isinstance(stmt, ast.If):
            handle_expression(stmt.test, scope)
            handle_statements(stmt.body, scope, module, modules)
            handle_statements(stmt.orelse, scope, module, modules)

        elif isinstance(stmt, ast.Try):
            handle_statements(stmt.body, scope, module, modules)
            handle_statements(stmt.orelse, scope, module, modules)
            handle_statements(stmt.finalbody, scope, module, modules)

        elif isinstance(stmt, ast.Expr):
            handle_expression(stmt.value, scope)

        elif isinstance(stmt, ast.Return):
            if stmt.value is not None:
                handle_expression(stmt.value, scope)

        elif isinstance(stmt, ast.Raise):
            if stmt.exc is not None:
                handle_expression(stmt.exc, scope)
            if stmt.cause is not None:
                handle_expression(stmt.cause, scope)

        elif isinstance(stmt, ast.While):
            handle_expression(stmt.test, scope)
            handle_statements(stmt.body, scope, module, modules)
            handle_statements(stmt.orelse, scope, module, modules)

        elif isinstance(stmt, ast.For):
            handle_expression(stmt.target, scope)
            handle_expression(stmt.iter, scope)
            handle_statements(stmt.body, scope, module, modules)
            handle_statements(stmt.orelse, scope, module, modules)

        elif isinstance(stmt, ast.Assert):
            handle_expression(stmt.test, scope)
            if stmt.msg is not None:
                handle_expression(stmt.msg, scope)

        elif isinstance(stmt, ast.With):
            for i in stmt.items:
                handle_expression(i.context_expr, scope)
                if i.optional_vars is not None:
                    handle_expression(i.optional_vars, scope)
            handle_statements(stmt.body, scope, module, modules)

        elif isinstance(stmt, ast.Match):
            handle_expression(stmt.subject, scope)
            for case in stmt.cases:
                if case.guard is not None:
                    handle_expression(case.guard, scope)
                handle_statements(case.body, scope, module, modules)

        elif isinstance(stmt, ast.Delete):
            handle_expressions(stmt.targets, scope)

        elif isinstance(stmt, ast.AugAssign):
            handle_expression(stmt.target, scope)
            handle_expression(stmt.value, scope)

        elif isinstance(stmt, ast.Nonlocal | ast.Global):
            for idx, id in enumerate(stmt.names):
                if id in scope:
                    e = scope[id]
                    if e.translated_name is not None:
                        stmt.names[idx] = e.translated_name

        elif isinstance(stmt, ast.Import):
            pass

        elif isinstance(stmt, ast.ImportFrom):
            assert module.name is not None

            if stmt.level == 0:
                assert stmt.module is not None
                begin = stmt.module
            else:
                begin = ".".join(module.name.split(".")[:-stmt.level])
                if stmt.module is not None:
                    if begin != "":
                        begin += "." + stmt.module
                    else:
                        begin = stmt.module

            if begin in modules:
                module = modules[begin]
                if module.translated_name is None:
                    module.translated_name = next_name()
                    assert isinstance(module.node, ast.Module)

                    handle_statements(
                        module.node.body,
                        scope=module,
                        module=module,
                        modules=modules
                    )

                for name in stmt.names:
                    assert name.name.count(".") == 0
                    if name.name in module:
                        entity = module[name.name]
                        assert entity.translated_name is not None
                        scope.scope[name.name] = entity
                        name.name = entity.translated_name

                stmt.level = 1
                stmt.module = module.translated_name

        elif isinstance(stmt, (
            ast.Pass, ast.Continue, ast.Break
        )):
            pass

        else:
            raise TypeError(stmt)

    for scope, exprs in deferred_exprs:
        handle_expressions(exprs, scope)

    for scope, stmts in deferred_stmnts:
        handle_statements(stmts, scope, module, modules)


def handle_args(args: ast.arguments, scope: EntityWithScope):
    for arg in args.args + args.kwonlyargs:
        translated_name = next_name()
        scope.create_entity(
            name=arg.arg, translated_name=translated_name
        )
        arg.arg = translated_name


if __name__ == "__main__":
    import sys
    import os
    import shutil

    # Первый аргумент программы - файл исходного кода
    if len(sys.argv) <= 1:
        print("usage: python ast_obfuscate.py `.py file_to_obfuscate`")
        exit(1)

    dir_path = sys.argv[1]
    dir_path = dir_path.removesuffix("/")
    dir_path = dir_path.removesuffix("\\")

    package_name = os.path.basename(dir_path)

    module_scope_by_name = dict[str, EntityWithScope]()

    for root_dir, subdirs, files in os.walk(dir_path):
        for file in files:
            if not file.endswith(".py"):
                continue

            with open(os.path.join(root_dir, file), "rb") as f:
                # Создание АСД
                node: ast.Module = ast.parse(source=f.read())

            module_name = os.path.relpath(
                path=os.path.join(root_dir, file),
                start=dir_path
            ).removesuffix(".py").replace("/", ".").replace("\\", ".")

            module_scope_by_name[module_name] = EntityWithScope(
                name=module_name,
                node=node
            )

    shutil.rmtree("result", ignore_errors=True)

    for name, scope in module_scope_by_name.items():
        scope = module_scope_by_name[name]
        assert isinstance(scope.node, ast.Module)

        if scope.translated_name is None:
            scope.translated_name = next_name()

            handle_statements(
                stmts=scope.node.body,
                scope=scope,
                module=scope,
                modules=module_scope_by_name
            )

        # Преобразование АСД обратно в исходный код
        # print()
        # print("File", name, " -> ", scope.translated_name)
        # print(ast.unparse(scope.node))
        os.makedirs("result", exist_ok=True)
        with open(f"result/{scope.translated_name}.py", "w") as f:
            f.write(ast.unparse(scope.node))
