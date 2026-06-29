from __future__ import annotations

from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON

RESOURCE_TYPES = {"FOOD", "TIMBER", "STONE", "IRON", "GOLD"}
TRACEABLE_RESOURCES = {"TIMBER", "STONE", "IRON"}
WORLD_WILL_STAGE_1_TOOLS = {"IRON", "STONE", "TIMBER", "FERTILE_SOIL", "SPRING"}

class HexCell(SQLModel, table=True):
    id: str = Field(primary_key=True)
    q: int
    r: int
    terrain: str
    elevation: float
    fertility: float
    resource_food: float
    resource_wood: float
    resource_stone: float
    resource_iron: float
    passable: bool
    fog: str = "KNOWN"
    nation_id: Optional[str] = None
    settlement_id: Optional[str] = None
    fortification: float = 0.0

class HexCulture(SQLModel, table=True):
    hex_id: str = Field(primary_key=True)
    nation_id: str = Field(primary_key=True)
    percentage: float

class Nation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    archetype: str
    color: str

    # Workforce population. These six fields must sum to pop_adults.
    pop_farmers: int
    pop_craftsmen: int
    pop_warriors: int
    pop_nobles: int
    pop_conscripts: int = 0
    pop_extractors: int = 0

    # Age layers.
    pop_children: int
    pop_adults: int
    pop_elders: int
    pop_total: int

    # Resource stocks.
    stock_food: float
    stock_wood: float
    stock_stone: float
    stock_iron: float
    stock_gold: float
    stock_wood_sources: list = Field(default_factory=list, sa_column=Column(JSON))
    stock_stone_sources: list = Field(default_factory=list, sa_column=Column(JSON))
    stock_iron_sources: list = Field(default_factory=list, sa_column=Column(JSON))

    # Core indicators.
    morale: float = 0.7
    stability: float = 0.7
    prestige: float = 0.5

    # Military.
    army_size: int
    army_quality: float = 0.5
    army_location: dict = Field(default_factory=lambda: {"hex_id": "", "status": "HOME"}, sa_column=Column(JSON))
    at_war_with: list = Field(default_factory=list, sa_column=Column(JSON))
    war_exhaustion: float = 0.0

    # Economy.
    gdp_monthly: float = 0.0
    tax_rate: float = 0.1
    trade_tax_rate: float = 0.05
    trade_balance: float = 0.0
    army_budget_ratio: float = 0.1
    debt: float = 0.0
    debt_creditor: Optional[str] = None
    debt_interest_rate: float = 0.0

    # M1-safe national modifiers referenced by semantic executors.
    culture_spread_bonus: float = 0.0
    elder_tech_bonus: float = 0.0
    road_level: int = 0

    # Internal politics fields are modeled now but not processed until later milestones.
    faction_nobles: float = 0.33
    faction_military: float = 0.33
    faction_commoners: float = 0.34
    succession_type: str = "PEACEFUL"
    coup_multiplier: float = 1.0
    legitimacy: float = 0.75

    # Technology fields are modeled now but not processed until later milestones.
    tech_points: float = 0.0
    tech_unlocked: list = Field(default_factory=list, sa_column=Column(JSON))

    # AI state fields are modeled for persistence; LLM is not enabled in M1.
    leader_name: str = ""
    leader_personality: str = ""
    leader_goal: str = ""
    memory_summary: str = ""
    known_intel: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Calendar values are kept per nation for API/query compatibility.
    founded_year: int = 1
    current_year: int = 1
    current_month: int = 1

class Settlement(SQLModel, table=True):
    id: str = Field(primary_key=True)
    nation_id: str
    hex_id: str
    name: str
    kind: str
    population: int
    storage_cap_food: float = 10000.0

class TradeRoute(SQLModel, table=True):
    id: str = Field(primary_key=True)
    from_nation_id: str
    to_nation_id: str
    resource_type: str
    active: bool = True
    volume: float = 0.0
    status: str = "ACTIVE"

class War(SQLModel, table=True):
    id: str = Field(primary_key=True)
    attacker_id: str
    defender_id: str
    active: bool = True

class DiplomaticRelation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    nation_a_id: str
    nation_b_id: str
    relation_score: float = 0.0
    historical_events: list = Field(default_factory=list, sa_column=Column(JSON))

class PendingProposal(SQLModel, table=True):
    id: str = Field(primary_key=True)
    from_nation_id: str
    to_nation_id: str
    proposal_type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    response_reasoning: Optional[str] = None

class PolicyAction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    nation_id: str
    year: int = 1
    month: int = 1
    tick_number: int
    action_type: str = "POLICY"
    action_key: str = ""
    policy_key: str
    target_id: Optional[str] = None
    intensity: float = 1.0
    reasoning: str = "RULE_AI"
    status: str
    reject_reason: Optional[str] = None
    effects_applied: dict = Field(default_factory=dict, sa_column=Column(JSON))
    reason: str = ""

class WorldEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    year: int = 1
    month: int = 1
    tick_number: int
    event_type: str
    severity: str = "INFO"
    nation_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    title: str
    description: str
    cascade_effects: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_deposit_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    source_intervention_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    nation_id: Optional[str] = None
    hex_id: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None

class WorldState(SQLModel, table=True):
    id: str = Field(primary_key=True, default="world")
    year: int = 1
    month: int = 1
    tick_number: int = 0
    global_tension: float = 0.0
    active_wars: list = Field(default_factory=list, sa_column=Column(JSON))
    active_treaties: list = Field(default_factory=list, sa_column=Column(JSON))
    snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    map_width: int = 120
    map_height: int = 80
    world_will_max_stage: int = 1
    initialized: bool = False

class ResourceDeposit(SQLModel, table=True):
    id: str = Field(primary_key=True)
    hex_id: str
    resource_type: str
    reserves: float
    max_reserves: float
    quality: float
    extraction_difficulty: float
    regen_rate: float = 0.0
    discovered_by: list = Field(default_factory=list, sa_column=Column(JSON))
    discovered: bool = False
    developed_by: Optional[str] = None
    development_level: int = 0
    depleted: bool = False
    workers_assigned: int = 0
    monthly_yield: float = 0.0
    placed_by_player: bool = False
    placed_tick: int = 0
    placed_year: int = 1
    placed_month: int = 1
    created_tick: int = 0
    source_intervention_id: Optional[str] = None

class ResourceFlowLedger(SQLModel, table=True):
    id: str = Field(primary_key=True)
    tick_number: int
    nation_id: str
    resource_type: str
    source_id: str
    source_type: str
    acquired_tick: int
    deposit_id: Optional[str] = None
    trade_route_id: Optional[str] = None
    inflow: float = 0.0
    outflow: float = 0.0
    direction: str
    amount: float
    purpose: str = ""
    linked_event_id: Optional[str] = None

class InterventionRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    tick_number: int
    year: int = 1
    month: int = 1
    stage: int = 1
    intervention_type: str = ""
    tool_type: str
    hex_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    hex_id: str
    parameters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    immediately_visible_to: list = Field(default_factory=list, sa_column=Column(JSON))
    immediate_visible: bool = True
    discovered_by: list = Field(default_factory=list, sa_column=Column(JSON))
    triggered_event_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    downstream_event_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    causal_summary: str = ""
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))

class CausalLink(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source_intervention_id: Optional[str] = None
    source_event_id: Optional[str] = None
    caused_event_id: Optional[str] = None
    causal_type: str = "DIRECT"
    lag_ticks: int = 0
    causal_note: str = ""
    intervention_id: str
    sequence: int
    link_type: str
    target_type: str
    target_id: str
    description: str
