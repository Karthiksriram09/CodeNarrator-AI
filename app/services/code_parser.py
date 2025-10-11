import ast

def parse_code_structure(filepath: str):
    """Parses a Python file and returns its functions and classes."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    structure = {
        'functions': [],
        'classes': []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            structure['functions'].append(node.name)
        elif isinstance(node, ast.ClassDef):
            structure['classes'].append(node.name)

    return structure
