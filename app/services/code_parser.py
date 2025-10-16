import ast
from .summarizer import summarize_code_snippet

def parse_code_structure(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)

    results = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', start + 5)
            snippet = "\n".join(lines[start:end])
            summary = summarize_code_snippet(snippet)
            results.append({
                "function": node.name,
                "code": snippet,
                "summary": summary
            })
    return results
