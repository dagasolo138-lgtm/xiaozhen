from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import CausalLink, HexCell, InterventionRecord, ResourceDeposit, WORLD_WILL_STAGE_1_TOOLS, WorldState
from .worldsim_events import add_event
from .worldsim_policies import create_resource_deposit

async def intervene(session: AsyncSession, tool_type: str, hex_id: str) -> InterventionRecord:
    state = (await session.get(WorldState, "world")) or WorldState()
    if state.world_will_max_stage < 1 or tool_type not in WORLD_WILL_STAGE_1_TOOLS:
        raise ValueError("tool unavailable")
    cell = await session.get(HexCell, hex_id)
    if not cell: raise ValueError("hex not found")
    iid=f"intervention_{uuid4().hex}"
    rec=InterventionRecord(id=iid,tick_number=state.tick_number,year=state.year,month=state.month,stage=1,intervention_type=tool_type,tool_type=tool_type,hex_ids=[hex_id],hex_id=hex_id,parameters={},immediately_visible_to=[cell.nation_id] if cell.nation_id else [],discovered_by=[cell.nation_id] if cell.nation_id else [],payload={})
    session.add(rec)
    seq=1
    if tool_type in {"IRON","STONE","TIMBER"}:
        dep, event = await create_resource_deposit(session, state, cell, tool_type, iid)
        rec.triggered_event_ids = [event.id]
        target_type,target_id="ResourceDeposit",dep.id
        caused_event_id = event.id
    elif tool_type == "FERTILE_SOIL":
        cell.fertility = min(1.0, cell.fertility+.25); cell.resource_food += 2
        event = await add_event(session,state.tick_number,"LAND_CHANGE","土地突然肥沃", "一片土地在自然变化后变得更适合耕作。",cell.nation_id,hex_id,"intervention",iid,year=state.year,month=state.month)
        rec.triggered_event_ids = [event.id]
        target_type,target_id="HexCell",hex_id
        caused_event_id = event.id
    else:
        cell.terrain = "RIVER"; cell.passable = True; cell.resource_food += 1
        event = await add_event(session,state.tick_number,"WATER_SOURCE","新水源出现", "当地出现了稳定水源。",cell.nation_id,hex_id,"intervention",iid,year=state.year,month=state.month)
        rec.triggered_event_ids = [event.id]
        target_type,target_id="HexCell",hex_id
        caused_event_id = event.id
    rec.causal_summary = f"{tool_type} altered {hex_id}"
    session.add(CausalLink(id=f"cause_{uuid4().hex}",source_intervention_id=iid,caused_event_id=caused_event_id,causal_type="DIRECT",lag_ticks=0,causal_note=f"{tool_type} altered {hex_id}",intervention_id=iid,sequence=seq,link_type="created",target_type=target_type,target_id=target_id,description=f"{tool_type} altered {hex_id}"))
    await session.commit(); await session.refresh(rec); return rec

async def get_chain(session: AsyncSession, intervention_id: str):
    links=(await session.execute(select(CausalLink).where(CausalLink.intervention_id==intervention_id).order_by(CausalLink.sequence))).scalars().all()
    return links

async def get_undiscovered_deposits(session: AsyncSession):
    return (await session.execute(select(ResourceDeposit).where(ResourceDeposit.discovered == False))).scalars().all()

async def propagate_resource_discovery(deposit: ResourceDeposit, current_tick: int, session: AsyncSession):
    cell = await session.get(HexCell, deposit.hex_id)
    if not cell or not cell.nation_id:
        return []
    deposit.discovered = True
    deposit.discovered_by = sorted(set([*deposit.discovered_by, cell.nation_id]))
    event = await add_event(session, current_tick, "RESOURCE_DISCOVERY", f"发现{deposit.resource_type}资源", f"当地发现可开发的{deposit.resource_type}资源点。", cell.nation_id, deposit.hex_id, "deposit", deposit.id)
    return [event]

async def trace_links(event, current_tick: int, session: AsyncSession) -> None:
    if not event.source_intervention_ids:
        return
    for intervention_id in event.source_intervention_ids:
        links=(await session.execute(select(CausalLink).where(CausalLink.intervention_id==intervention_id))).scalars().all()
        seq=max((link.sequence for link in links), default=0)+1
        session.add(CausalLink(id=f"cause_{uuid4().hex}", source_intervention_id=intervention_id, source_event_id=event.id, caused_event_id=event.id, causal_type="DIRECT", lag_ticks=0, causal_note=event.description, intervention_id=intervention_id, sequence=seq, link_type="event", target_type="WorldEvent", target_id=event.id, description=event.description))
