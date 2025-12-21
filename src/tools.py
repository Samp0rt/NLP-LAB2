import ast
import math
from datetime import datetime, timedelta

def validate_code(code: str) -> str:
    """Validates Python code syntax and reports issues."""
    try:
        ast.parse(code)
        return "✅ Code is syntactically valid."
    except SyntaxError as e:
        return f"❌ Syntax error: {e.msg} at line {e.lineno}"


def safe_execute(expression: str) -> str:
    """Safely executes simple Python expressions (no imports/classes)."""
    safe_globals = {"__builtins__": {}}
    try:
        result = eval(expression, safe_globals)
        return f"✅ Result: {result}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def calculator(expression: str) -> str:
    """
    Evaluate a math expression using functions from the math module.
    Returns the result as a string or an error message.
    """
    try:
        result = eval(expression, {"__builtins__": None}, math.__dict__)
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"







