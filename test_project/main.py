
from fastmcp import FastMCP

mcp = FastMCP("demo-server-v2")

@mcp.tool()
def ping() -> str:
    """
    Simple ping tool. Use ONLY when user says exactly 'ping' with no other text.
    Returns 'pong'.
    """
    return "pong"

@mcp.tool()
def pingping(user_prompt: str) -> str:
    """
    Pingping tool. Use when user mentions 'pingping' or sends any message that is NOT just 'ping'.
    Takes the user's message and returns it prefixed with 'pongpong: '.
    """
    return f"pongpong: {user_prompt}"

if __name__ == "__main__":
    mcp.run(transport="stdio")