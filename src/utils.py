import re
from typing import Any, Dict, List, Tuple
from .tools import validate_code, safe_execute, calculator


def apply_tools(model_output: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parse, execute, and inline all tool calls found in model_output.

    Args:
        model_output: Text that may contain <TOOL_CALL>_[...] markers.

    Returns:
        A tuple:
            - processed text with tool calls replaced by [Result: ...]
            - list of executed tool calls with their results
    """
    calls = extract_tool_calls(model_output)
    executed: List[Dict[str, Any]] = []
    processed = model_output

    for call in calls:
        tool_name = call["tool"]
        args = call["arguments"]

        result = run_tool(tool_name, args)
        executed.append(
            {
                "tool": tool_name,
                "arguments": args,
                "result": result,
            }
        )

        original_call = f"<TOOL_CALL>_[{tool_name}]({args})"
        processed = processed.replace(original_call, f"[Result: {result}]")

    return processed, executed


def get_available_tools() -> str:
    """
    Return a human-readable list of all available tools.
    """
    lines = ["Available tools:"]
    for tool_name, tool_info in AVAILABLE_TOOLS.items():
        lines.append(f"- {tool_name}: {tool_info['description']}")
    return "\n".join(lines)


def run_tool(tool_name: str, arguments: str) -> str:
    """
    Execute a tool by name using the provided argument string.

    Args:
        tool_name: Name of a tool from AVAILABLE_TOOLS.
        arguments: Argument string passed directly to the tool function.

    Returns:
        Result of the tool call as a string, or an error message.
    """
    tool_info = AVAILABLE_TOOLS.get(tool_name)
    if tool_info is None:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        func = tool_info["function"]
        result = func(arguments)
        return str(result)
    except Exception as exc:
        return f"Error executing {tool_name}: {exc}"


def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    Find tool calls in the form <TOOL_CALL>_[tool_name](arguments).

    Args:
        text: Model output that may contain tool call markers.

    Returns:
        A list of dicts with:
            - "tool": tool name as string
            - "arguments": raw argument string
    """
    pattern = r'<TOOL_CALL>_\[([^\]]+)\]\(([^)]*)\)'
    matches = re.findall(pattern, text)

    calls: List[Dict[str, Any]] = []
    for tool_name, args in matches:
        calls.append(
            {
                "tool": tool_name.strip(),
                "arguments": args.strip(),
            }
        )
    return calls


AVAILABLE_TOOLS = {
    "validate_code": {
        "name": "validate_code",
        "description": (
            "Checks Python code for syntax errors. "
            "Input: full code snippet as a string. "
            "Output: message indicating whether the code is syntactically valid "
            "or describing the syntax error."
        ),
        "function": validate_code,
    },
    "safe_execute": {
        "name": "safe_execute",
        "description": (
            "Safely evaluates simple Python expressions without imports or class definitions. "
            "Input: expression string (e.g. '1 + 2 * 3'). "
            "Output: result of the expression or an error message."
        ),
        "function": safe_execute,
    },
    "calculator": {
        "name": "calculator",
        "description": (
            "Evaluates mathematical expressions using the math module "
            "(e.g. 'sin(pi/2) + log(10)'). "
            "Input: expression as string. "
            "Output: result as string or an error message."
        ),
        "function": calculator,
    },
}