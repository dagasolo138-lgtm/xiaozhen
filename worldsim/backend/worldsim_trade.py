from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import Nation, TradeRoute
from .worldsim_economy import STOCK_FIELDS, transfer_resource_batches_fifo

TARGETS = {"IRON":350,"STONE":500,"TIMBER":650}

async def resolve_trades(current_tick: int, session: AsyncSession) -> list:
    nations = (await session.execute(select(Nation))).scalars().all(); by_id={n.id:n for n in nations}
    routes = (await session.execute(select(TradeRoute).where(TradeRoute.active == True))).scalars().all()
    for route in routes:
        a, b = by_id[route.from_nation_id], by_id[route.to_nation_id]; res=route.resource_type; field=STOCK_FIELDS[res]
        surplus = a if getattr(a, field) > TARGETS[res]*1.25 else b if getattr(b, field) > TARGETS[res]*1.25 else None
        scarce = b if surplus is a and getattr(b, field) < TARGETS[res]*0.8 else a if surplus is b and getattr(a, field) < TARGETS[res]*0.8 else None
        if surplus and scarce:
            amount = min(40.0, getattr(surplus, field)-TARGETS[res], TARGETS[res]-getattr(scarce, field))
            if amount > 0 and await transfer_resource_batches_fifo(session, surplus, scarce, res, amount, current_tick, "trade"):
                route.volume += amount
                surplus.trade_balance += amount
                scarce.trade_balance -= amount
    return []

async def run_trade(session: AsyncSession, tick: int) -> None:
    await resolve_trades(tick, session)
