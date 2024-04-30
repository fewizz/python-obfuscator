import ast
from . import EntityWithScope
from . import next_name


def handle_args(args: ast.arguments, scope: EntityWithScope):
    from . handle_expressions import handle_expression

    for arg in args.args + args.kwonlyargs:
        translated_name = next_name()
        scope.create_entity(
            name=arg.arg, translated_name=translated_name
        )
        arg.arg = translated_name
        if arg.annotation is not None:
            handle_expression(arg.annotation, scope=scope)
