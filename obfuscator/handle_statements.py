import ast
from . import EntityWithScope, next_name, Ctx, Class
from . handle_expressions import handle_expressions, handle_expression
from . handle_args import handle_args


def handle_statements(
    ctx: Ctx,
    stmts: list[ast.stmt],
    scope: EntityWithScope,
    module: EntityWithScope
) -> None:
    # Ноды, которые должны быть обработаны позже
    deferred_stmnts = list[tuple[EntityWithScope, list[ast.stmt]]]()
    deferred_exprs = list[tuple[EntityWithScope, list[ast.expr]]]()

    for stmt in stmts:

        if isinstance(stmt, ast.ClassDef):
            translated_name = next_name()
            class_scope: Class = scope._create_entity(
                name=stmt.name, translated_name=translated_name, type=Class
            )  # type: ignore
            stmt.name = translated_name

            handle_statements(ctx, stmt.body, class_scope, module)
            handle_expressions(exprs=stmt.bases, scope=class_scope)
            handle_expressions(exprs=stmt.decorator_list, scope=class_scope)

        elif isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            # translated_name = next_name()
            func_scope = scope.create_entity_with_scope(
                name=stmt.name, translated_name=stmt.name  # translated_name
            )
            # stmt.name = translated_name

            handle_args(stmt.args, scope=func_scope)

            deferred_exprs.append((func_scope, stmt.decorator_list))
            deferred_stmnts.append((func_scope, stmt.body))

        elif isinstance(stmt, ast.Assign):
            handle_expression(expr=stmt.value, scope=scope)

            if not isinstance(scope, Class):
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
                not isinstance(scope, Class)
                and isinstance(stmt.target, ast.Name)
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
            handle_statements(ctx, stmt.body, scope, module)
            handle_statements(ctx, stmt.orelse, scope, module)

        elif isinstance(stmt, ast.Try):
            handle_statements(ctx, stmt.body, scope, module)
            handle_statements(ctx, stmt.orelse, scope, module)
            handle_statements(ctx, stmt.finalbody, scope, module)
            for handler in stmt.handlers:
                if handler.type is not None:
                    handle_expression(handler.type, scope)
                handle_statements(ctx, handler.body, scope, module)

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
            handle_statements(ctx, stmt.body, scope, module)
            handle_statements(ctx, stmt.orelse, scope, module)

        elif isinstance(stmt, ast.For):
            handle_expression(stmt.target, scope)
            handle_expression(stmt.iter, scope)
            handle_statements(ctx, stmt.body, scope, module)
            handle_statements(ctx, stmt.orelse, scope, module)

        elif isinstance(stmt, ast.Assert):
            handle_expression(stmt.test, scope)
            if stmt.msg is not None:
                handle_expression(stmt.msg, scope)

        elif isinstance(stmt, ast.With):
            for i in stmt.items:
                handle_expression(i.context_expr, scope)
                if i.optional_vars is not None:
                    handle_expression(i.optional_vars, scope)
            handle_statements(ctx, stmt.body, scope, module)

        elif isinstance(stmt, ast.Match):
            handle_expression(stmt.subject, scope)
            for case in stmt.cases:
                if case.guard is not None:
                    handle_expression(case.guard, scope)
                handle_statements(ctx, case.body, scope, module)

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
                begin_splitted = module.name.split(".")[:-stmt.level]
                if stmt.module is not None:
                    begin_splitted += stmt.module.split(".")
                begin = ".".join(begin_splitted)

            if begin in ctx.module_node_and_scope_by_name:
                module_node, module_scope = \
                    ctx.module_node_and_scope_by_name[begin]

                if module_scope.translated_name is None:
                    module_scope.translated_name = next_name()
                    assert isinstance(module_node, ast.Module)

                    handle_statements(
                        ctx,
                        module_node.body,
                        scope=module_scope,
                        module=module_scope
                    )

                for name in stmt.names:
                    assert name.name.count(".") == 0
                    sub_module = f"{begin}.{name.name}"
                    if sub_module in ctx.module_node_and_scope_by_name:
                        sub_node, sub_scope = \
                            ctx.module_node_and_scope_by_name[sub_module]

                        if sub_scope.translated_name is None:
                            sub_scope.translated_name = next_name()
                            assert isinstance(sub_node, ast.Module)

                            handle_statements(
                                ctx,
                                sub_node.body,
                                scope=sub_scope,
                                module=sub_scope
                            )

                        scope.scope[name.name] = sub_scope
                        name.name = sub_scope.translated_name

                    elif name.name in module_scope:
                        entity = module_scope[name.name]
                        assert entity.translated_name is not None
                        scope.scope[name.name] = entity
                        name.name = entity.translated_name

                stmt.level = 1
                stmt.module = None

        elif isinstance(stmt, (
            ast.Pass, ast.Continue, ast.Break
        )):
            pass

        else:
            raise TypeError(stmt)

    for scope, exprs in deferred_exprs:
        handle_expressions(exprs, scope)

    for scope, stmts in deferred_stmnts:
        handle_statements(ctx, stmts, scope, module)
