from app.tools.learning_resource_tool import LearningResourceTool

_TOOLS = {"learning_resource": LearningResourceTool()}


def get_tool(name: str):
    if name not in _TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    return _TOOLS[name]


def list_tools() -> tuple[str, ...]:
    return tuple(_TOOLS)
