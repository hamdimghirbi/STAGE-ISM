import logging
from fastmcp import FastMCP

#msg afficher ds le terminal 
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")

#creer un serveur mcp 
mcp = FastMCP("pingping-server")

#indique que la fct devient un mcp serveur 
@mcp.tool()
def ping():
    """
    this is a ping tool that returns 'pong' when called.
    use when user writes ping
    """
     #affiche un log de type warning( de tupe info ca saffiche pas ds el terminal)
    logging.warning("PING reçu")
    return "pong"

@mcp.tool()
def pingping(user_prompt: str) -> str:
    """ 
    This is a pingping tool that takes a user prompt and returns it with 'pongpong: ' prefixed.
    use when user writes pingping
    """
    #affiche un log de type warning( de tupe info ca saffiche pas ds el terminal)
    logging.warning(f"PINGPING reçu: {user_prompt}")
    # f c une chaine ou tu peux inserer des variables python directement dans la chaine 
    return f"pongpong: {user_prompt}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", 
            host="127.0.0.1", 
            port=8010, 
# J’ai mis path="/mcp" pour créer une route dédiée au serveur MCP, 
# ce qui aide à éviter les conflits avec d'autres endpoints et
# à organiser les routes de manière plus claire
            path="/mcp")