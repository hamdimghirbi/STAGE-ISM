from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
