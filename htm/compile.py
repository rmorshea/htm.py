import ast
import astor
import functools
from tagged import split
from htm import htm_parse


class Rewrite(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)

        if node.func.__class__.__name__ != "Name" or node.func.id != "html":
            return node
        if len(node.args) != 1 or node.args[0].__class__.__name__ != "Str":
            return node

        strings, exprs = split(node.args[0].s)
        ops = htm_parse(strings)

        func_node = ast.Attribute(value=node.func, attr="_eval", ctx=ast.Load())
        ops_node = to_ast(ops)
        exprs_node = ast.List(elts=[ast.parse(expr, mode="eval") for expr in exprs], ctx=ast.Load())

        new_node = ast.Call(func=func_node, args=[ops_node, exprs_node], keywords=[])
        return ast.copy_location(new_node, node)


@functools.singledispatch
def to_ast(value):
    raise TypeError("unknown type")
to_ast.register(str, lambda s: ast.Str(s=s))
to_ast.register(int, lambda n: ast.Num(n=n))
to_ast.register(bool, lambda b: ast.NameConstant(b))
to_ast.register(tuple, lambda t: ast.Tuple(elts=[to_ast(e) for e in t], ctx=ast.Load()))
to_ast.register(list, lambda l: ast.Tuple(elts=[to_ast(e) for e in l], ctx=ast.Load()))


def compile(source):
    root = ast.parse(source)
    root = Rewrite().visit(root)
    return astor.to_source(root)


if __name__ == "__main__":
    import sys
    sys.stdout.write(compile(sys.stdin.read()))
