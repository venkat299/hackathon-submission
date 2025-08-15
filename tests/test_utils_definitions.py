import ast
import pathlib


def test_no_duplicate_util_functions():
    source = pathlib.Path('utils.py').read_text()
    tree = ast.parse(source)
    function_names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    for func in ['get_simulation_timestamp', 'log_event', 'distill_context']:
        assert function_names.count(func) == 1, f"{func} defined {function_names.count(func)} times"
