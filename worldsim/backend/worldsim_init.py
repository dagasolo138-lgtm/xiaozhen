import os
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select
from .worldsim_models import *
from .worldsim_terrain import generate_map, offset_distance
from .worldsim_economy import assert_nation_invariants

NATIONS = [
 ("agrarian","稷原王国","#66bb6a",4200,700,300,120,1000,5320,1200,9000,600,350,180,800),
 ("merchant","澜港联盟","#42a5f5",2600,1400,220,180,900,4400,900,5200,1600,450,120,2600),
 ("military","铁鹰帝国","#ef5350",2500,800,900,220,850,4420,800,4200,700,500,900,1000),
 ("balanced","中衡郡国","#ab47bc",3300,1000,420,180,900,4900,1000,6500,900,700,320,1400),
]

def batch(resource, amount, nation, tick=0):
    return [{"amount": amount, "source_type":"initial", "source_id":f"initial_{nation}_{resource.lower()}", "acquired_tick":tick}]

async def initialize_world(session: AsyncSession) -> WorldState:
    for model in [CausalLink, InterventionRecord, ResourceFlowLedger, ResourceDeposit, WorldEvent, PolicyAction, TradeRoute, Settlement, HexCulture, HexCell, Nation, WorldState]:
        await session.execute(delete(model))
    cells = generate_map(int(os.getenv("WORLDSIM_SEED", "42")))
    starts = {"agrarian":(20,20),"merchant":(90,20),"military":(25,60),"balanced":(85,58)}
    for cell in cells:
        for nid,(cq,cr) in starts.items():
            if offset_distance(cell.q, cell.r, cq, cr) <= 12:
                cell.nation_id = nid
        session.add(cell)
    for nid,name,color,farm,craft,war,nob,child,adult,elder,food,wood,stone,iron,gold in NATIONS:
        n = Nation(id=nid,name=name,archetype=nid,color=color,pop_farmers=farm,pop_craftsmen=craft,pop_warriors=war,pop_nobles=nob,pop_children=child,pop_adults=adult,pop_elders=elder,pop_total=child+adult+elder,stock_food=food,stock_wood=wood,stock_stone=stone,stock_iron=iron,stock_gold=gold,stock_wood_sources=batch("TIMBER",wood,nid),stock_stone_sources=batch("STONE",stone,nid),stock_iron_sources=batch("IRON",iron,nid),army_size=war,army_location={"hex_id": f"{starts[nid][0]}_{starts[nid][1]}", "status": "HOME"},gdp_monthly=adult*0.02,leader_name=f"{name}执政者",leader_personality="谨慎",leader_goal="维持国家生存并扩大资源基础",memory_summary="新世界初始化。",known_intel={"known_nations": [item[0] for item in NATIONS if item[0] != nid]})
        assert_nation_invariants(n); session.add(n)
        cq,cr = starts[nid]; sid=f"capital_{nid}"; session.add(Settlement(id=sid,nation_id=nid,hex_id=f"{cq}_{cr}",name=f"{name}都城",kind="CAPITAL",population=adult+child+elder))
    ids=[n[0] for n in NATIONS]
    for a in ids:
        for b in ids:
            if a < b:
                for res in ("IRON","STONE","TIMBER"):
                    session.add(TradeRoute(id=f"route_{a}_{b}_{res}",from_nation_id=a,to_nation_id=b,resource_type=res))
    state = WorldState(id="world", initialized=True, year=1, month=1, tick_number=0, world_will_max_stage=1, snapshot={"tick_number": 0, "year": 1, "month": 1, "nation_ids": ids})
    session.add(state); await session.commit(); return state
