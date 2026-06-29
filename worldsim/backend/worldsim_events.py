from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import Nation, WorldEvent

async def add_event(session: AsyncSession, tick:int, event_type:str, title:str, description:str, nation_id=None, hex_id=None, source_type=None, source_id=None, year:int=1, month:int=1, severity:str="INFO", cascade_effects=None) -> WorldEvent:
    nation_ids = [nation_id] if nation_id else []
    source_intervention_ids = [source_id] if source_type == "intervention" and source_id else []
    ev = WorldEvent(id=f"event_{uuid4().hex}", year=year, month=month, tick_number=tick, event_type=event_type, severity=severity, nation_ids=nation_ids, title=title, description=description, cascade_effects=cascade_effects or {}, source_intervention_ids=source_intervention_ids, nation_id=nation_id, hex_id=hex_id, source_type=source_type, source_id=source_id)
    session.add(ev); return ev

async def generate_m1_events(session: AsyncSession, tick:int, year:int=1, month:int=1) -> list[WorldEvent]:
    """Deterministic M1 random-event hook; keeps future systems out of Tick."""
    return []

async def scan_m1_thresholds(session: AsyncSession, tick:int, year:int=1, month:int=1) -> list[WorldEvent]:
    events: list[WorldEvent] = []
    nations=(await session.execute(select(Nation))).scalars().all()
    for n in nations:
        if n.stock_food < 1000:
            events.append(await add_event(session,tick,"ECONOMY_ALERT","粮食告急",f"{n.name}粮食库存低于警戒线。",n.id,year=year,month=month,severity="WARNING"))
    return events

async def run_threshold_events(session: AsyncSession, tick:int) -> None:
    await scan_m1_thresholds(session, tick)
