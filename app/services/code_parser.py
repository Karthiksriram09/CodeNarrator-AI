import ast
from .summarizer import summarize_code_snippet

def parse_code_structure(filepath: str):
    """Parses a Python file and returns functions + explanations."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)

    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', start + 5)
            lines = source.splitlines()[start:end]
            snippet = "\n".join(lines)
            try:
                summary = summarize_code_snippet(snippet)
            except Exception as e:
                summary = f"Error summarizing: {e}"
            results.append({
                "function": node.name,
                "summary": summary
            })
    return results
