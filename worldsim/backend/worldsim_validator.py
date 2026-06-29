from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .worldsim_models import Nation, ResourceDeposit

async def validate_policy(session: AsyncSession, nation: Nation, policy_key: str) -> tuple[bool, str]:
    if policy_key == "build_granary" and nation.stock_wood < 80: return False, "insufficient timber"
    if policy_key == "stockpile_weapons" and nation.stock_iron < 40: return False, "insufficient iron"
    if policy_key == "build_fortifications" and nation.stock_stone < 100: return False, "insufficient stone"
    if policy_key == "repair_walls" and nation.stock_stone < 50: return False, "insufficient stone"
    if policy_key == "build_armory" and (nation.stock_stone < 80 or nation.stock_wood < 60): return False, "insufficient stone or timber"
    if policy_key == "train_elite_units" and (nation.stock_iron < 30 or nation.stock_gold < 50): return False, "insufficient iron or gold"
    if policy_key == "conscript_troops" and nation.pop_farmers < 100: return False, "insufficient farmers"
    if policy_key == "disband_troops" and nation.pop_conscripts < 50: return False, "no conscripts"
    if policy_key == "develop_resource_deposit":
        dep = (await session.execute(select(ResourceDeposit).where(ResourceDeposit.discovered == True, ResourceDeposit.developed_by == None))).scalars().first()
        if not dep: return False, "no discovered deposit"
        if nation.pop_farmers < 100: return False, "insufficient farmers"
    return True, "ok"
