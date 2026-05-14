import logging
from fastapi import FastAPI
import uvicorn
from fastapi_mcp import FastApiMCP

#message to display in the terminal
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")

#create a FastAPI instance 
app = FastAPI(title="Ping Pong API")

#indicate that the function becomes a FastAPI endpoint
@app.get("/ping")
def ping():
    """
    this is a ping tool that returns 'pong' when called.
    use when user writes ping
    """
    #show a log of type warning (of type info it does not show in the terminal)
    logging.warning("PING reçu")
    return "pong"

@app.get("/pingping")
def pingping(user_prompt: str) -> str:
    """ 
    This is a pingping tool that takes a user prompt and returns it with 'pongpong: ' prefixed.
    use when user writes pingping
    """
    #show a log of type warning (of type info it does not show in the terminal)
    logging.warning(f"PINGPING reçu: {user_prompt}")
    # f is a string where you can insert Python variables directly into the string
    return f"pongpong: {user_prompt}"

#connect the FastAPI application to the MCP (Model Control Protocol) to allow it to be 
# used as a tool in a larger system.

mcp = FastApiMCP(app) #convert the FastAPI application into an MCP tool
mcp.mount() #acitivate the MCP tool, making it available for use in the larger system.

if __name__ == "__main__":
    #uvicorn is an ASGI server implementation for Python, used to run FastAPI applications.
    uvicorn.run(app, host="127.0.0.1", port=8010)