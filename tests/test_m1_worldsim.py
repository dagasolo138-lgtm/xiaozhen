import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlmodel import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_worldsim.db")

from worldsim.backend.worldsim_db import async_session, init_db  # noqa: E402
from worldsim.backend.worldsim_engine import run_tick  # noqa: E402
from worldsim.backend.worldsim_init import initialize_world  # noqa: E402
from worldsim.backend.worldsim_models import CausalLink, HexCell, InterventionRecord, Nation, ResourceDeposit, ResourceFlowLedger, WorldEvent, WorldState  # noqa: E402
from worldsim.backend.worldsim_policies import apply_border_fortification, apply_capital_fortification, apply_owned_food_yield_modifier, apply_owned_plain_fertility, apply_road_project, execute_policy  # noqa: E402
from worldsim.backend.worldsim_terrain import offset_distance, offset_neighbors  # noqa: E402
from worldsim.backend.worldsim_trade import resolve_trades  # noqa: E402
from worldsim.backend.worldsim_worldwill import get_chain, intervene  # noqa: E402


def _assert_nation_invariants(nation: Nation) -> None:
    workforce = (
        nation.pop_farmers
        + nation.pop_craftsmen
        + nation.pop_warriors
        + nation.pop_nobles
        + nation.pop_conscripts
        + nation.pop_extractors
    )
    assert workforce == nation.pop_adults
    assert nation.army_size == nation.pop_warriors + nation.pop_conscripts


def test_odd_row_offset_hex_helpers_are_symmetric():
    assert len(offset_neighbors(10, 10)) == 6
    assert len(offset_neighbors(10, 11)) == 6
    assert offset_distance(10, 10, 10, 10) == 0
    for q, r in offset_neighbors(10, 10):
        assert offset_distance(10, 10, q, r) == 1
        assert offset_distance(q, r, 10, 10) == 1


@pytest.mark.asyncio
async def test_m1_semantic_executors_mutate_only_expected_state():
    await init_db()
    async with async_session() as session:
        await initialize_world(session)
        nation = await session.get(Nation, "agrarian")
        assert nation is not None

        old_road = nation.road_level
        await apply_road_project(nation, 1)
        assert nation.road_level == old_road + 1

        fertility_count = await apply_owned_plain_fertility(session, nation, 0.01)
        food_count = await apply_owned_food_yield_modifier(session, nation, 0.1)
        assert fertility_count >= 0
        assert food_count >= 0

        fortified = await apply_border_fortification(session, nation, 0.01)
        capital_ok = await apply_capital_fortification(session, nation, 0.01)
        assert fortified > 0
        assert capital_ok

        fortified_cells = (await session.execute(select(HexCell).where(HexCell.nation_id == nation.id, HexCell.fortification > 0))).scalars().all()
        assert fortified_cells


@pytest.mark.asyncio
async def test_init_tick_trade_and_invariants():
    await init_db()
    async with async_session() as session:
        await initialize_world(session)
        last_result = None
        for _ in range(3):
            result = await run_tick(session)
            assert result["elapsed_ms"] < 1000
            assert result["events"]
            assert result["snapshot"]["tick_number"] == result["tick_number"]
            last_result = result
        assert last_result is not None

        state = await session.get(WorldState, "world")
        assert state is not None
        assert state.year >= 1
        assert state.month >= 1
        assert state.snapshot["nation_ids"]
        assert state.snapshot["tick_number"] == last_result["tick_number"]

        nations = (await session.execute(select(Nation))).scalars().all()
        assert {nation.id for nation in nations} == {"agrarian", "merchant", "military", "balanced"}
        for nation in nations:
            _assert_nation_invariants(nation)
            assert nation.leader_name
            assert nation.memory_summary
            assert isinstance(nation.known_intel, dict)
            assert nation.army_location["status"] == "HOME"

        ledgers = (await session.execute(select(ResourceFlowLedger))).scalars().all()
        assert ledgers
        assert {ledger.resource_type for ledger in ledgers} <= {"IRON", "STONE", "TIMBER"}
        assert all(ledger.source_id and ledger.source_type for ledger in ledgers)
        assert any(ledger.inflow > 0 or ledger.outflow > 0 for ledger in ledgers)


@pytest.mark.asyncio
async def test_trade_transfers_fifo_source_metadata():
    await init_db()
    async with async_session() as session:
        await initialize_world(session)
        agrarian = await session.get(Nation, "agrarian")
        merchant = await session.get(Nation, "merchant")
        assert agrarian and merchant
        agrarian.stock_iron = 1000
        merchant.stock_iron = 0
        agrarian.stock_iron_sources = [{"amount": 1000, "remaining": 1000, "source_type": "initial", "source_id": "initial_agrarian_iron", "acquired_tick": 0}]
        merchant.stock_iron_sources = []

        await resolve_trades(1, session)

        assert agrarian.stock_iron < 1000
        assert merchant.stock_iron > 0
        assert merchant.stock_iron_sources
        assert merchant.stock_iron_sources[0]["source_id"] == "initial_agrarian_iron"
        assert merchant.stock_iron_sources[0]["acquired_tick"] == 0


@pytest.mark.asyncio
async def test_develop_resource_policy_moves_workers_and_produces_deposit_ledger():
    await init_db()
    async with async_session() as session:
        await initialize_world(session)
        record = await intervene(session, "IRON", "20_20")
        agrarian = await session.get(Nation, "agrarian")
        assert agrarian is not None
        farmers_before = agrarian.pop_farmers
        extractors_before = agrarian.pop_extractors
        iron_before = agrarian.stock_iron

        await execute_policy(session, agrarian, "develop_resource_deposit", 1)
        deposit = (await session.execute(select(ResourceDeposit).where(ResourceDeposit.source_intervention_id == record.id))).scalars().one()
        assert deposit.developed_by == agrarian.id
        assert deposit.development_level == 1
        assert agrarian.pop_farmers == farmers_before - 100
        assert agrarian.pop_extractors == extractors_before + 100

        await run_tick(session)
        assert agrarian.stock_iron > iron_before
        ledgers = (await session.execute(select(ResourceFlowLedger).where(ResourceFlowLedger.deposit_id == deposit.id))).scalars().all()
        assert ledgers
        assert any(ledger.inflow > 0 and ledger.source_id == deposit.id for ledger in ledgers)


@pytest.mark.asyncio
async def test_world_will_iron_deposit_develops_and_extends_chain():
    await init_db()
    async with async_session() as session:
        await initialize_world(session)
        record = await intervene(session, "IRON", "20_20")
        assert record.stage == 1
        assert record.intervention_type == "IRON"
        assert record.hex_ids == ["20_20"]
        assert record.triggered_event_ids
        initial_chain = await get_chain(session, record.id)
        assert any(link.target_type == "ResourceDeposit" for link in initial_chain)
        deposit = (await session.execute(select(ResourceDeposit).where(ResourceDeposit.source_intervention_id == record.id))).scalars().one()
        assert deposit.placed_tick == record.tick_number
        assert deposit.placed_year == record.year
        assert deposit.discovered_by

        for _ in range(2):
            await run_tick(session)

        chain = await get_chain(session, record.id)
        assert len(chain) > len(initial_chain)
        assert any(link.target_type == "ResourceFlowLedger" for link in chain)

        events = (await session.execute(select(WorldEvent).where(WorldEvent.source_id == record.id))).scalars().all()
        assert events

        causal_links = (await session.execute(select(CausalLink).where(CausalLink.intervention_id == record.id))).scalars().all()
        assert causal_links
        assert all(link.source_intervention_id == record.id for link in causal_links if link.link_type == "created")

        stored_record = await session.get(InterventionRecord, record.id)
        assert stored_record is not None
        assert stored_record.causal_summary


def teardown_module():
    Path("test_worldsim.db").unlink(missing_ok=True)

@pytest.mark.asyncio
async def test_m1_api_surface_for_p3_endpoints():
    import httpx
    from worldsim.backend.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        init_response = await client.post("/api/world/init")
        assert init_response.status_code == 200

        tick_response = await client.post("/api/world/tick")
        assert tick_response.status_code == 200
        tick_payload = tick_response.json()
        assert tick_payload["tick_number"] == 1

        nation_response = await client.get("/api/world/nation/agrarian")
        assert nation_response.status_code == 200
        assert nation_response.json()["id"] == "agrarian"

        routes_response = await client.get("/api/world/trade-routes")
        assert routes_response.status_code == 200
        assert routes_response.json()

        decisions_response = await client.get("/api/nation/agrarian/decisions/1/1")
        assert decisions_response.status_code == 200
        assert isinstance(decisions_response.json(), list)

        replay_response = await client.get("/api/world/replay/1")
        assert replay_response.status_code == 200
        assert replay_response.json()["tick_number"] == 1

        events_response = await client.get("/api/world/events?page=1&limit=5")
        assert events_response.status_code == 200
        assert len(events_response.json()) <= 5

        reset_response = await client.post("/api/world/reset")
        assert reset_response.status_code == 200
        assert reset_response.json()["tick_number"] == 0
