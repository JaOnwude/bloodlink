"""Aggregates every route module into a single router.

New route modules are registered here, so ``main.py`` stays unchanged as the API grows.
"""

from fastapi import APIRouter

from app.api.routes import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
