import ast
import sys

import tagged
import pyalect

from htm import htm_parse

if sys.version_info < (3, 6):
    raise RuntimeError("The HTM dialect requires Python>=3.6")


class Transpiler(pyalect.Transpiler):
    def __init__(self, dialect):
        self.dialect = dialect

    def transform_ast(self, node):
        return NodeTransformer().visit(node)


class NodeTransformer(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "html":
                if (
                    node.keywords
                    or len(node.args) != 1
                    or not isinstance(node.args[0], ast.Str)
                ):
                    raise RuntimeError(
                        "html expects a string as its sole positional argument"
                    )
                else:
                    htm_string = node.args[0].s
                expr = make_htm_expr(htm_string)
                new_call_node = ast.parse(expr).body[0].value
                return ast.copy_location(new_call_node, node)
        return node


def make_htm_expr(text):
    src = ""
    is_first_child = True
    strings, exprs = tagged.split(text)
    for op_type, *data in htm_parse(strings):
        if op_type == "OPEN":
            is_first_child = True
            src += "html("
            value, tag = data
            src += (exprs[tag] if value else repr(tag)) + ", {"
        elif op_type == "CLOSE":
            if is_first_child:
                src += "}, ["
            src += "])"
        elif op_type == "SPREAD":
            value, item = data
            src += "**" + (exprs[item] if value else item) + ", "
        elif op_type == "PROP_SINGLE":
            attr, value, item = data
            src += repr(attr) + ": (" + (exprs[item] if value else repr(item)) + "), "
        elif op_type == "PROP_MULTI":
            attr, items = data
            src += (
                repr(attr)
                + ": ("
                + "+".join(
                    repr(value) if is_text else "str(%s)" % exprs[value]
                    for (is_text, value) in items
                )
                + "), "
            )
        elif op_type == "CHILD":
            if is_first_child:
                is_first_child = False
                src += "}, ["
            value, item = data
            src += values[item] if value else repr(item) + ","
        else:
            raise BaseException("unknown op")
    return src


if "html" not in pyalect.registered():
    pyalect.register("html", Transpiler)
