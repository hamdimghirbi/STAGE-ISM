from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastmcp.server.openapi import OpenAPITool
import httpx
from fastmcp.server.openapi import RouteMap, RouteType
import jsonref

import json
from mcp.types import TextContent
from fastmcp.server.openapi import FastMCPOpenAPI

from fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.requests import Request

from app.config import settings
from app.db import create_db_and_tables
from app.enums import ACTIVITY_BY_CATEGORY, CraCategory, ExpenseType, Status
from app.routers import auth as auth_router
from app.routers import cra as cra_router
from app.routers import cra_tracking as cra_tracking_router
from app.routers import expenses as expenses_router
from app.seed import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_demo_data()
    yield


app = FastAPI(
    title='CRA Mock API',
    version='0.1.0',
    description='Simplified mock backend for CRA / Expenses / CRA Tracking pages.',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router.router, prefix='/api/auth', tags=['auth'])
app.include_router(cra_router.router, prefix='/api/cra', tags=['cra'])
app.include_router(cra_tracking_router.router, prefix='/api/cra-tracking', tags=['cra-tracking'])
app.include_router(expenses_router.router, prefix='/api/expenses', tags=['expenses'])


@app.get('/healthz', tags=['meta'])
def healthz() -> dict:
    return {'status': 'ok'}


@app.get('/api/enums', tags=['meta'])
def get_enums() -> dict:
    return {
        'cra_categories': [c.value for c in CraCategory],
        'cra_activities': {
            cat.value: [a.value for a in acts] for cat, acts in ACTIVITY_BY_CATEGORY.items()
        },
        'expense_types': [t.value for t in ExpenseType],
        'statuses': [s.value for s in Status],
    }




# Token storage — cannot use a simple variable in async, dict content can be modified
_token = {"value": ""}


# Injects JWT token automatically into every request
# Without this, all tools would get 401 Unauthorized
class DynamicAuthTransport(httpx.AsyncBaseTransport):
    def __init__(self, app):
        self._transport = httpx.ASGITransport(app=app)
    async def handle_async_request(self, request):
        if _token["value"]:
            request.headers["Authorization"] = f"Bearer {_token['value']}"
        return await self._transport.handle_async_request(request)


# Patch OpenAPITool to wrap results in TextContent
original_execute = OpenAPITool._execute_request

async def patched_execute_request(self, *args, **kwargs):
    result = await original_execute(self, *args, **kwargs)
    if isinstance(result, (dict, list)):
        return json.dumps(result)
    return result

OpenAPITool._execute_request = patched_execute_request


# All tools use this client — token injected automatically
http_client = httpx.AsyncClient(
    transport=DynamicAuthTransport(app),
    base_url="http://fastapi"
)


# Auto-generate all tools from FastAPI OpenAPI spec
# jsonref resolves $ref, exclude_operations removes auto-generated login
# route_maps forces GET routes to be tools instead of resources
mcp = FastMCP.from_openapi(
    openapi_spec=jsonref.replace_refs(app.openapi()),
    client=http_client,
    exclude_operations=["login_api_auth_login_post"],
    route_maps=[
        RouteMap(methods=["GET", "POST", "PUT", "DELETE"], pattern=".*", route_type=RouteType.TOOL)
    ]
)


# Manual login — from_openapi does not support OAuth2 form data
# Stores token so DynamicAuthTransport injects it automatically after login
@mcp.tool()
async def login(email: str, password: str) -> str:
    """Login to Portalite and get JWT token. Always call this first."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://fastapi"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password}
        )
        result = resp.json()
        _token["value"] = result["access_token"]
        return json.dumps(result)


# Mount MCP on FastAPI via SSE
app.mount("/mcp", mcp.sse_app())