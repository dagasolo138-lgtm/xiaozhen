from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import Nation, PolicyAction, ResourceDeposit
from .worldsim_validator import validate_policy
from .worldsim_economy import consume_resource_fifo, transfer_workforce, assign_extractors_to_deposit

PHASE_1_POLICY_KEYS = {"raise_farm_tax","lower_trade_tax","open_market","monopolize_iron_trade","ban_food_export","build_granary","conscript_troops","disband_troops","train_elite_units","build_fortifications","stockpile_weapons","build_roads","repair_walls","build_armory","develop_resource_deposit"}

async def choose_rule_policies(n: Nation) -> list[str]:
    picks = ["raise_farm_tax" if n.stock_food < 3000 else "open_market", "build_roads"]
    if n.pop_farmers > 3000: picks.append("conscript_troops")
    if n.stock_iron < 500: picks.append("develop_resource_deposit")
    return picks[:6]

async def execute_policy(session: AsyncSession, n: Nation, key: str, tick: int) -> None:
    ok, reason = await validate_policy(session, n, key)
    effects = {}
    if ok:
        if key == "raise_farm_tax": n.tax_rate = min(.3, n.tax_rate+.02); effects={"tax_rate":n.tax_rate}
        elif key == "lower_trade_tax": n.trade_tax_rate = max(0, n.trade_tax_rate-.01); effects={"trade_tax_rate":n.trade_tax_rate}
        elif key == "open_market": n.trade_tax_rate = max(0, n.trade_tax_rate-.005); effects={"trade_tax_rate":n.trade_tax_rate}
        elif key == "conscript_troops": transfer_workforce(n,"pop_farmers","pop_conscripts",100); effects={"farmers":-100,"conscripts":100}
        elif key == "disband_troops": transfer_workforce(n,"pop_conscripts","pop_farmers",50); effects={"farmers":50,"conscripts":-50}
        elif key == "build_roads": await apply_road_project(n, 1); effects={"road_level":n.road_level}
        elif key == "build_granary": ok = await consume_resource_fifo(session,n,"TIMBER",80,tick,key); storage = await apply_capital_storage(session, n, 500.0) if ok else 0; effects={"timber":-80,"storage_cap_food_added":storage}
        elif key == "build_fortifications": ok = await consume_resource_fifo(session,n,"STONE",100,tick,key); changed = await apply_border_fortification(session, n, 0.05) if ok else 0; effects={"stone":-100,"fortified_hexes":changed}
        elif key == "stockpile_weapons": ok = await consume_resource_fifo(session,n,"IRON",40,tick,key); n.army_quality = min(1.0, n.army_quality + 0.01) if ok else n.army_quality; effects={"iron":-40,"army_quality":n.army_quality}
        elif key == "train_elite_units": ok = await consume_resource_fifo(session,n,"IRON",30,tick,key); n.stock_gold -= 50 if ok else 0; n.army_quality = min(1.0, n.army_quality + 0.03) if ok else n.army_quality; effects={"iron":-30,"gold":-50,"army_quality":n.army_quality}
        elif key == "monopolize_iron_trade": n.trade_tax_rate = min(0.3, n.trade_tax_rate + 0.02); n.prestige = min(1.0, n.prestige + 0.01); effects={"trade_tax_rate":n.trade_tax_rate,"prestige":n.prestige}
        elif key == "ban_food_export": n.stability = min(1.0, n.stability + 0.01); n.trade_balance -= 10; effects={"stability":n.stability,"trade_balance":n.trade_balance}
        elif key == "develop_resource_deposit":
            dep = (await session.execute(select(ResourceDeposit).where(ResourceDeposit.discovered == True, ResourceDeposit.developed_by == None))).scalars().first()
            ok = bool(dep and await assign_extractors_to_deposit(n, dep, 100)); effects={"deposit_id": dep.id if dep else None, "farmers":-100, "extractors":100}
        elif key == "repair_walls": ok = await consume_resource_fifo(session,n,"STONE",50,tick,key); capital_ok = await apply_capital_fortification(session, n, 0.1) if ok else False; effects={"stone":-50,"capital_fortified":capital_ok}
        elif key == "build_armory": ok = await consume_resource_fifo(session,n,"STONE",80,tick,key); ok = ok and await consume_resource_fifo(session,n,"TIMBER",60,tick,key); n.army_quality = min(1.0, n.army_quality + 0.01) if ok else n.army_quality; effects={"stone":-80,"timber":-60,"army_quality":n.army_quality}
        elif key in PHASE_1_POLICY_KEYS: effects={"noted": True}
    session.add(PolicyAction(id=f"policy_{uuid4().hex}", year=n.current_year, month=n.current_month, tick_number=tick, nation_id=n.id, policy_key=key, action_key=key, status="applied" if ok else "rejected", reject_reason=None if ok else reason, effects_applied=effects if ok else {}, reason=reason if not ok else "ok"))

async def run_rule_ai_policies(session: AsyncSession, tick: int) -> None:
    nations = (await session.execute(select(Nation))).scalars().all()
    for n in nations:
        for key in await choose_rule_policies(n):
            if key in PHASE_1_POLICY_KEYS:
                await execute_policy(session,n,key,tick)

async def apply_owned_plain_fertility(session: AsyncSession, nation: Nation, delta: float) -> int:
    from .worldsim_models import HexCell
    cells = (await session.execute(select(HexCell).where(HexCell.nation_id == nation.id, HexCell.terrain == "PLAIN"))).scalars().all()
    for cell in cells:
        cell.fertility = max(0.0, min(1.0, cell.fertility + delta))
    return len(cells)

async def apply_owned_food_yield_modifier(session: AsyncSession, nation: Nation, delta: float) -> int:
    from .worldsim_models import HexCell
    cells = (await session.execute(select(HexCell).where(HexCell.nation_id == nation.id, HexCell.terrain == "PLAIN"))).scalars().all()
    for cell in cells:
        cell.resource_food = max(0.0, cell.resource_food + delta)
    return len(cells)

async def apply_border_fortification(session: AsyncSession, nation: Nation, amount: float) -> int:
    from .worldsim_models import HexCell
    from .worldsim_terrain import offset_neighbors
    cells = (await session.execute(select(HexCell).where(HexCell.nation_id == nation.id))).scalars().all()
    by_id = {cell.id: cell for cell in (await session.execute(select(HexCell))).scalars().all()}
    changed = 0
    for cell in cells:
        is_border = any((neighbor := by_id.get(f"{q}_{r}")) is None or neighbor.nation_id != nation.id for q, r in offset_neighbors(cell.q, cell.r))
        if is_border:
            cell.fortification = min(1.0, cell.fortification + amount)
            changed += 1
    return changed

async def apply_capital_fortification(session: AsyncSession, nation: Nation, amount: float) -> bool:
    from .worldsim_models import HexCell, Settlement
    capital = (await session.execute(select(Settlement).where(Settlement.nation_id == nation.id, Settlement.kind == "CAPITAL"))).scalars().first()
    if not capital:
        return False
    cell = await session.get(HexCell, capital.hex_id)
    if not cell:
        return False
    cell.fortification = min(1.0, cell.fortification + amount)
    return True

async def apply_road_project(nation: Nation, levels: int = 1) -> None:
    nation.road_level = max(0, nation.road_level + levels)

async def create_resource_deposit(session: AsyncSession, state, cell, resource_type: str, intervention_id: str):
    from .worldsim_events import add_event
    from .worldsim_models import ResourceDeposit
    dep = ResourceDeposit(id=f"deposit_{state.tick_number}_{cell.id}_{uuid4().hex[:6]}", hex_id=cell.id, resource_type=resource_type, reserves=1200.0, max_reserves=1200.0, quality=.75, extraction_difficulty=.25, regen_rate=.05 if resource_type == "TIMBER" else 0, discovered_by=[cell.nation_id] if cell.nation_id else [], discovered=True, development_level=0, placed_by_player=True, placed_tick=state.tick_number, placed_year=state.year, placed_month=state.month, created_tick=state.tick_number, source_intervention_id=intervention_id)
    session.add(dep)
    event = await add_event(session, state.tick_number, "RESOURCE_DISCOVERY", f"发现{resource_type}资源", f"当地发现可开发的{resource_type}资源点。", cell.nation_id, cell.id, "intervention", intervention_id, year=state.year, month=state.month)
    return dep, event

async def create_natural_resource_deposit(session: AsyncSession, tick: int, cell, resource_type: str):
    from .worldsim_models import ResourceDeposit
    dep = ResourceDeposit(id=f"deposit_{tick}_{cell.id}_{uuid4().hex[:6]}", hex_id=cell.id, resource_type=resource_type, reserves=800.0, max_reserves=800.0, quality=.55, extraction_difficulty=.35, regen_rate=.03 if resource_type == "TIMBER" else 0, discovered=False, placed_by_player=False, placed_tick=tick, placed_year=1, placed_month=1, created_tick=tick)
    session.add(dep)
    return dep


async def apply_capital_storage(session: AsyncSession, nation: Nation, amount: float) -> float:
    from .worldsim_models import Settlement
    capital = (await session.execute(select(Settlement).where(Settlement.nation_id == nation.id, Settlement.kind == "CAPITAL"))).scalars().first()
    if not capital:
        return 0.0
    capital.storage_cap_food += amount
    return amount
