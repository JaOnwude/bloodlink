"""Aggregates every route module into a single router.

New route modules are registered here, so ``main.py`` stays unchanged as the API grows.
"""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    auth,
    components,
    donors,
    health,
    hospitals,
    pledges,
    requests,
    stats,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(donors.router)
api_router.include_router(hospitals.router)
api_router.include_router(admin.router)
api_router.include_router(requests.router)
api_router.include_router(pledges.router)
api_router.include_router(components.router)
api_router.include_router(stats.router)
