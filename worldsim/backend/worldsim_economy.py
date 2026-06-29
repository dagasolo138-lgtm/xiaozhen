from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import CausalLink, Nation, ResourceDeposit, ResourceFlowLedger

SOURCE_FIELDS = {"IRON":"stock_iron_sources","STONE":"stock_stone_sources","TIMBER":"stock_wood_sources"}
STOCK_FIELDS = {"IRON":"stock_iron","STONE":"stock_stone","TIMBER":"stock_wood"}


def assert_nation_invariants(n: Nation) -> None:
    jobs = n.pop_farmers+n.pop_craftsmen+n.pop_warriors+n.pop_nobles+n.pop_conscripts+n.pop_extractors
    if jobs != n.pop_adults:
        raise ValueError(f"{n.id} workforce mismatch")
    if n.army_size != n.pop_warriors+n.pop_conscripts:
        raise ValueError(f"{n.id} army mismatch")


async def add_resource_batch(session: AsyncSession, nation: Nation, resource_type: str, amount: float, source_type: str, source_id: str, tick: int, purpose: str) -> list[ResourceFlowLedger]:
    if amount <= 0: return []
    setattr(nation, STOCK_FIELDS[resource_type], getattr(nation, STOCK_FIELDS[resource_type])+amount)
    batches = list(getattr(nation, SOURCE_FIELDS[resource_type]) or [])
    batches.append({"amount": amount, "remaining": amount, "source_type": source_type, "source_id": source_id, "acquired_tick": tick})
    setattr(nation, SOURCE_FIELDS[resource_type], batches)
    ledger = ResourceFlowLedger(id=f"ledger_{uuid4().hex}", tick_number=tick, nation_id=nation.id, resource_type=resource_type, direction="in", amount=amount, inflow=amount, outflow=0.0, source_type=source_type, source_id=source_id, acquired_tick=tick, deposit_id=source_id if source_type == "deposit" else None, purpose=purpose)
    session.add(ledger)
    return [ledger]


async def consume_resource_fifo(session: AsyncSession, nation: Nation, resource_type: str, amount: float, tick: int, purpose: str) -> bool:
    if amount <= 0: return True
    if getattr(nation, STOCK_FIELDS[resource_type]) < amount: return False
    remain = amount; out = []
    batches = list(getattr(nation, SOURCE_FIELDS[resource_type]) or [])
    while remain > 1e-9 and batches:
        batch = dict(batches.pop(0)); available = float(batch.get("remaining", batch.get("amount", 0.0))); take = min(available, remain)
        available -= take; remain -= take; batch["remaining"] = available; batch["amount"] = available
        out.append((batch, take))
        if available > 1e-9: batches.insert(0, batch)
    if remain > 1e-9: return False
    setattr(nation, STOCK_FIELDS[resource_type], getattr(nation, STOCK_FIELDS[resource_type])-amount)
    setattr(nation, SOURCE_FIELDS[resource_type], batches)
    for batch, take in out:
        session.add(ResourceFlowLedger(id=f"ledger_{uuid4().hex}", tick_number=tick, nation_id=nation.id, resource_type=resource_type, direction="out", amount=take, inflow=0.0, outflow=take, source_type=batch["source_type"], source_id=batch["source_id"], acquired_tick=batch["acquired_tick"], deposit_id=batch["source_id"] if batch["source_type"] == "deposit" else None, purpose=purpose))
    return True


async def transfer_resource_batches_fifo(session: AsyncSession, src: Nation, dst: Nation, resource_type: str, amount: float, tick: int, purpose: str) -> bool:
    if getattr(src, STOCK_FIELDS[resource_type]) < amount: return False
    remain = amount; moved = []; batches = list(getattr(src, SOURCE_FIELDS[resource_type]) or [])
    while remain > 1e-9 and batches:
        batch = dict(batches.pop(0)); available = float(batch.get("remaining", batch.get("amount", 0.0))); take = min(available, remain)
        available -= take; remain -= take; batch["remaining"] = available; batch["amount"] = available
        moved.append((batch, take))
        if available > 1e-9: batches.insert(0, batch)
    if remain > 1e-9: return False
    setattr(src, STOCK_FIELDS[resource_type], getattr(src, STOCK_FIELDS[resource_type])-amount); setattr(src, SOURCE_FIELDS[resource_type], batches)
    dst_batches = list(getattr(dst, SOURCE_FIELDS[resource_type]) or [])
    for batch, take in moved:
        dst_batches.append({**batch, "amount": take, "remaining": take})
        for nation, direction in ((src,"out"),(dst,"in")):
            session.add(ResourceFlowLedger(id=f"ledger_{uuid4().hex}", tick_number=tick, nation_id=nation.id, resource_type=resource_type, direction=direction, amount=take, inflow=take if direction == "in" else 0.0, outflow=take if direction == "out" else 0.0, source_type=batch["source_type"], source_id=batch["source_id"], acquired_tick=batch["acquired_tick"], deposit_id=batch["source_id"] if batch["source_type"] == "deposit" else None, purpose=purpose))
    setattr(dst, STOCK_FIELDS[resource_type], getattr(dst, STOCK_FIELDS[resource_type])+amount); setattr(dst, SOURCE_FIELDS[resource_type], dst_batches)
    return True


def transfer_workforce(n: Nation, from_field: str, to_field: str, amount: int) -> bool:
    if getattr(n, from_field) < amount: return False
    setattr(n, from_field, getattr(n, from_field)-amount); setattr(n, to_field, getattr(n, to_field)+amount)
    n.army_size = n.pop_warriors+n.pop_conscripts; assert_nation_invariants(n); return True


async def assign_extractors_to_deposit(n: Nation, deposit: ResourceDeposit, workers: int = 100) -> bool:
    if deposit.developed_by and deposit.developed_by != n.id: return False
    if not transfer_workforce(n, "pop_farmers", "pop_extractors", workers): return False
    deposit.developed_by = n.id; deposit.development_level = max(deposit.development_level, 1); deposit.workers_assigned += workers; return True


async def append_causal_links_for_target(session: AsyncSession, target_type: str, target_id: str, linked_type: str, linked_ids: list[str], description: str) -> None:
    origins = (await session.execute(select(CausalLink).where(CausalLink.target_type == target_type, CausalLink.target_id == target_id))).scalars().all()
    for origin in origins:
        existing = (await session.execute(select(CausalLink).where(CausalLink.intervention_id == origin.intervention_id))).scalars().all()
        seq = max((link.sequence for link in existing), default=0)
        for linked_id in linked_ids:
            seq += 1
            session.add(CausalLink(id=f"cause_{uuid4().hex}", source_intervention_id=origin.intervention_id, caused_event_id=origin.caused_event_id, causal_type="INDIRECT", lag_ticks=0, causal_note=description, intervention_id=origin.intervention_id, sequence=seq, link_type="derived", target_type=linked_type, target_id=linked_id, description=description))


async def extract_resources(nation: Nation, current_tick: int, session: AsyncSession) -> list:
    deposits = (await session.execute(select(ResourceDeposit).where(ResourceDeposit.developed_by == nation.id, ResourceDeposit.depleted == False))).scalars().all()
    for d in deposits:
        if d.reserves <= 0:
            d.depleted = True
            continue
        if d.resource_type == "TIMBER":
            d.reserves = min(d.max_reserves, d.reserves+d.max_reserves*d.regen_rate)
        required_workers = 100 * (1 + d.extraction_difficulty)
        labor_modifier = min(1.0, d.workers_assigned / required_workers) if required_workers else 0.0
        base = {"IRON": 0.5, "STONE": 0.8, "TIMBER": 1.2}[d.resource_type]
        amount = min(d.reserves, d.workers_assigned * base / (1 + d.extraction_difficulty) * d.quality * labor_modifier * (1 + nation.road_level * 0.15))
        d.monthly_yield = amount
        d.reserves -= amount
        if d.reserves <= 0:
            d.depleted = True
        ledgers = await add_resource_batch(session, nation, d.resource_type, amount, "deposit", d.id, current_tick, "resource_extraction")
        if d.placed_by_player and ledgers:
            await append_causal_links_for_target(session, "ResourceDeposit", d.id, "ResourceFlowLedger", [ledger.id for ledger in ledgers], f"{d.resource_type} extraction entered {nation.id} stockpile")
    return []


async def consume_resources(nation: Nation, session: AsyncSession) -> None:
    nation.stock_food -= nation.pop_children*0.03+nation.pop_adults*0.05+nation.pop_elders*0.02


async def produce_goods(nation: Nation, session: AsyncSession) -> None:
    nation.stock_food += nation.pop_farmers*0.08
    nation.gdp_monthly = nation.pop_adults * 0.02 + nation.pop_craftsmen * 0.03


async def collect_tax(nation: Nation, session: AsyncSession) -> None:
    nation.stock_gold += max(0.0, nation.gdp_monthly * nation.tax_rate)


async def pay_army_maintenance(nation: Nation, session: AsyncSession) -> None:
    nation.stock_gold -= nation.army_size*nation.army_budget_ratio*0.01


async def run_economy(session: AsyncSession, tick: int) -> None:
    nations = (await session.execute(select(Nation))).scalars().all()
    for nation in nations:
        await extract_resources(nation, tick, session)
        await consume_resources(nation, session)
        await produce_goods(nation, session)
        await collect_tax(nation, session)
        await pay_army_maintenance(nation, session)

async def release_deposit_workers(nation: Nation, deposit: ResourceDeposit) -> bool:
    """Return all workers assigned to a deposit back to farmers."""
    workers = deposit.workers_assigned
    if workers <= 0:
        deposit.developed_by = None
        deposit.development_level = 0
        return True
    if nation.pop_extractors < workers:
        return False
    nation.pop_extractors -= workers
    nation.pop_farmers += workers
    deposit.workers_assigned = 0
    deposit.developed_by = None
    deposit.development_level = 0
    assert_nation_invariants(nation)
    return True
