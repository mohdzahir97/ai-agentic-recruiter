"""Mounts every v1 router under one prefix."""
from fastapi import APIRouter

from app.api.v1 import ai, applications, auth, candidates, health, jobs, recruiter

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(recruiter.router)
api_router.include_router(applications.router)
api_router.include_router(ai.router)
