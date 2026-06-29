import asyncio
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sse_starlette.sse import EventSourceResponse
from .worldsim_db import get_session, init_db
from .worldsim_init import initialize_world
from .worldsim_engine import run_tick
from .worldsim_models import HexCell, Nation, PolicyAction, ResourceDeposit, TradeRoute, WorldEvent, WorldState
from .worldsim_worldwill import intervene, get_chain

app = FastAPI(title="WorldSim M1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class InterventionIn(BaseModel):
    tool_type: str
    hex_id: str

@app.on_event("startup")
async def startup():
    await init_db()

@app.post("/api/world/init")
async def api_init(session: AsyncSession = Depends(get_session)):
    return await initialize_world(session)

@app.post("/api/world/reset")
async def api_reset(session: AsyncSession = Depends(get_session)):
    return await initialize_world(session)

@app.post("/api/world/tick")
async def api_tick(session: AsyncSession = Depends(get_session)):
    try: return await run_tick(session)
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get("/api/world/state")
async def api_state(session: AsyncSession = Depends(get_session)):
    return await session.get(WorldState, "world")

@app.get("/api/world/replay/{tick_number}")
async def api_replay(tick_number: int, session: AsyncSession = Depends(get_session)):
    state = await session.get(WorldState, "world")
    if not state or state.snapshot.get("tick_number") != tick_number:
        raise HTTPException(404, "snapshot not found")
    return state.snapshot

@app.get("/api/world/map")
async def api_map(session: AsyncSession = Depends(get_session), limit: int = 9600):
    return (await session.execute(select(HexCell).limit(limit))).scalars().all()

@app.get("/api/world/nations")
async def api_nations(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Nation))).scalars().all()

@app.get("/api/world/nation/{nation_id}")
async def api_nation(nation_id: str, session: AsyncSession = Depends(get_session)):
    nation = await session.get(Nation, nation_id)
    if not nation:
        raise HTTPException(404, "nation not found")
    return nation

@app.get("/api/world/events")
async def api_events(session: AsyncSession = Depends(get_session), page: int = 1, limit: int = 50):
    offset = max(0, page - 1) * limit
    return (await session.execute(select(WorldEvent).order_by(WorldEvent.tick_number.desc()).offset(offset).limit(limit))).scalars().all()

@app.get("/api/world/events/stream")
async def api_events_stream():
    async def event_generator():
        yield {"event": "ready", "data": "WorldSim event stream connected"}
        while True:
            await asyncio.sleep(15)
            yield {"event": "heartbeat", "data": "{}"}
    return EventSourceResponse(event_generator())

@app.get("/api/world/trade-routes")
async def api_trade_routes(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(TradeRoute))).scalars().all()

@app.get("/api/nation/{nation_id}/decisions/{year}/{month}")
async def api_nation_decisions(nation_id: str, year: int, month: int, session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(PolicyAction).where(PolicyAction.nation_id == nation_id, PolicyAction.year == year, PolicyAction.month == month))).scalars().all()

@app.get("/api/world/policies")
async def api_policies(session: AsyncSession = Depends(get_session), limit: int = 100):
    return (await session.execute(select(PolicyAction).order_by(PolicyAction.tick_number.desc()).limit(limit))).scalars().all()

@app.get("/api/world/deposits")
async def api_deposits(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(ResourceDeposit))).scalars().all()

@app.post("/api/world/intervene")
async def api_intervene(body: InterventionIn, session: AsyncSession = Depends(get_session)):
    try: return await intervene(session, body.tool_type, body.hex_id)
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get("/api/world/intervention/{intervention_id}/chain")
async def api_chain(intervention_id: str, session: AsyncSession = Depends(get_session)):
    return await get_chain(session, intervention_id)
