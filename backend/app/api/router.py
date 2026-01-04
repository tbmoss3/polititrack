"""Main API router that combines all endpoint routers."""

from fastapi import APIRouter

from app.api import politicians, votes, bills, finance, stocks, map

api_router = APIRouter()

api_router.include_router(politicians.router, prefix="/politicians", tags=["politicians"])
api_router.include_router(votes.router, prefix="/votes", tags=["votes"])
api_router.include_router(bills.router, prefix="/bills", tags=["bills"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(map.router, prefix="/map", tags=["map"])
