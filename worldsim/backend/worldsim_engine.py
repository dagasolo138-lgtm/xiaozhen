import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import Nation, WorldState
from .worldsim_economy import assert_nation_invariants, collect_tax, consume_resources, extract_resources, pay_army_maintenance, produce_goods
from .worldsim_events import add_event, generate_m1_events, scan_m1_thresholds
from .worldsim_policies import choose_rule_policies, execute_policy
from .worldsim_terrain import monthly_regen
from .worldsim_trade import resolve_trades
from .worldsim_worldwill import get_undiscovered_deposits, propagate_resource_discovery, trace_links

async def _advance_month(state: WorldState) -> None:
    state.tick_number += 1
    state.month += 1
    if state.month > 12:
        state.month = 1
        state.year += 1

async def _save_world_snapshot(session: AsyncSession, state: WorldState, nations: list[Nation]) -> dict:
    state.snapshot = {"tick_number": state.tick_number, "year": state.year, "month": state.month, "nation_ids": [n.id for n in nations]}
    return state.snapshot

async def run_tick(session: AsyncSession) -> dict:
    state = await session.get(WorldState, "world")
    if not state or not state.initialized:
        raise ValueError("world not initialized")

    started = time.perf_counter()
    current_year = state.year
    current_month = state.month
    current_tick = state.tick_number + 1

    terrain_events = await monthly_regen(session, month=current_month)

    nations = (await session.execute(select(Nation))).scalars().all()
    for nation in nations:
        nation.trade_balance = 0.0
        await extract_resources(nation, current_tick, session)
        await consume_resources(nation, session)
        await produce_goods(nation, session)
        await collect_tax(nation, session)
        await pay_army_maintenance(nation, session)

    trade_events = await resolve_trades(current_tick=current_tick, session=session)

    discovery_events = []
    for deposit in await get_undiscovered_deposits(session):
        discovery_events.extend(await propagate_resource_discovery(deposit=deposit, current_tick=current_tick, session=session))

    decisions = []
    for nation in nations:
        decisions.append((nation, await choose_rule_policies(nation)))

    policy_events = []
    for nation, decision_list in decisions:
        for decision in decision_list:
            before_count = len(policy_events)
            await execute_policy(session, nation, decision, current_tick)
            if len(policy_events) == before_count:
                pass

    random_events = await generate_m1_events(session, current_tick, year=current_year, month=current_month)
    threshold_events = await scan_m1_thresholds(session, current_tick, year=current_year, month=current_month)
    all_events = terrain_events + trade_events + discovery_events + policy_events + random_events + threshold_events

    for event in all_events:
        await trace_links(event=event, current_tick=current_tick, session=session)

    await _advance_month(state)
    for nation in nations:
        nation.current_year = state.year
        nation.current_month = state.month
        assert_nation_invariants(nation)
    snapshot = await _save_world_snapshot(session, state, nations)
    tick_event = await add_event(session, current_tick, "TICK", "月份推进", f"世界推进到第{state.tick_number}月。", year=state.year, month=state.month)
    all_events.append(tick_event)
    await session.commit()
    return {"tick_number": state.tick_number, "elapsed_ms": round((time.perf_counter()-started)*1000, 2), "events": [event.id for event in all_events], "snapshot": snapshot}
