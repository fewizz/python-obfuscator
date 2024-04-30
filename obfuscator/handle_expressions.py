import ast
from . import EntityWithScope
from .handle_args import handle_args


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
        if isinstance(expr.value, ast.Name) and expr.value.id in scope:
            value_entity = scope[expr.value.id]
            if (
                isinstance(value_entity, EntityWithScope)
                and expr.attr in value_entity
            ):
                attr = value_entity[expr.attr]
                assert attr.translated_name is not None
                expr.attr = attr.translated_name
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
