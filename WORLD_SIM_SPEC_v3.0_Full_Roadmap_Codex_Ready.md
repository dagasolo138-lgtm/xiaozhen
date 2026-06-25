# WORLD SIM — Codex 开发规范 v3.0（分阶段完整路线版）

> 古代四国世界模拟器。4个AI控制的国家，每月手动推进一次Tick，
> 每国每月自主决策2–6件政策，涌现行为驱动历史进程。
>
> v2.0 新增：贸易路线系统、战争解算、文化扩散与叛乱、
> 人口生命周期、外交关系公式、内部派系政治。
>
> v2.1 修复：HexCulture独立表、LLM Fallback规则、PendingProposal表、
> Canvas Viewport规范、faction_merchants bug、军事国粮食储备。
>
> v2.2 修复：并行LLM宣战时序冲突、派系震荡阻尼、记忆压缩定量信息保留。
>
> v2.3 修复（GPT审查）：粮食单位统一定义、职业人口与成年人口对齐、
> 文化代码改为HexCulture批量SQL、army_budget_ratio公式修正、
> USER_PROMPT补充memory_summary、政策效果状态归属表、新增MVP开工策略。
> v2.4 新增：世界意志系统完整设计（Section 22）。
>
> v2.5 修复（GPT第三轮）：Phase1工具去煤铜金、立即可见执行路径、ResourceFlowLedger因果账本、
> WorldEvent溯源字段、conscript改用pop_farmers、移除society双扣战争伤亡、
> 性能验收拆两条、Nation补culture_spread_bonus/elder_tech_bonus/road_level、
> Section21/22命名统一为开发里程碑/权限层级。
>
> v2.9 最终交付修复：统一异步SQLite约定与主键、明确本次仅实施“里程碑一 + 世界意志权限一”、
> 新增矿工人口闭环、资源批次FIFO溯源、资源开发执行链、政策/随机事件语义执行器、
> 清除冻结系统的Tick调用、修正人口再平衡和世界意志章节冲突。
> v3.0 补全：世界意志权限2–5的完整开发规范、每层解锁条件、工具集、国家感知规则、
> 数据模型与验收门槛；明确权限按后续版本发布开启，不是游戏内等级或年份锁。

> **本次 Codex 实施范围（优先级最高）**：只实现“里程碑一 + 世界意志权限一”。
> 当前可运行 Tick 只包含：地形再生、经济、贸易、规则型国家决策、政策验证/执行、资源发现、因果链、时间推进与快照。
> **第21节与第22.6–22.10节是后续开发的绑定路线，不得在本次提前实现。** LLM、人口生命周期、文化、战争、外交派系、技术、合法性和债务均为后续里程碑内容；本次不得创建调用链、不得从 Tick 调用、不得以空实现替代。

---

## 0. 对 Codex 的绝对约束

- **当前交付范围优先级最高**：仅实现第21节“里程碑一”与第22节“权限层级1”。`worldsim_models.py` 是唯一例外：为保持迁移稳定，可以一次定义第3节列出的全部模型，但本次只创建、读写和测试M1需要的表；后续系统模块不得创建、调用或以空函数占位。
- **只创建当前实施范围中已明确列出的文件**；后续里程碑文件必须等其里程碑开始后再创建。不得凭空创建SPEC未提及的文件。
- **永远不要加版本后缀** — 不得出现 `_v2` `_final` `_new`。
- **文件命名格式** — `worldsim_模块名.py` / `worldsim_模块名.ts`。
- **ORM固定** — 数据模型只用 `SQLModel`；异步引擎和 `AsyncSession` 使用 SQLModel 依赖的 SQLAlchemy async backend 是允许且必需的底层实现。不得引入其他ORM。
- **数据库固定** — SQLite + `aiosqlite`，所有数据库会话必须是 `AsyncSession`；任何数据库读写都必须 `await`。
- **不得自选状态管理** — 前端只用 `Zustand`，禁用 Redux / MobX。
- **LLM调用** — 仅在里程碑二开始后创建 `worldsim_llm.py`；届时只通过该文件统一封装，禁止其他文件直接调用 API。
- **所有LLM输出必须过验证层** — 仅在里程碑二开始后启用 `worldsim_validator.py`。
- **数学计算** — 所有公式用 `float`，禁止引入 numpy / pandas。
- **政策与事件** — 禁止对 `army_size`、职业人口总量、可溯源库存来源批次、文化占比做通用字典直接写入；必须调用第20节的语义执行器。
- **冲突优先级** — 本节 > 第6节当前Tick > 第19节任务清单 > 其他章节。后续系统章节只在对应里程碑启动后生效。

---

## 1. 技术栈（锁定，不得更改）

```
后端语言      Python 3.12
后端框架      FastAPI 0.111 + uvicorn
数据库        SQLite（单文件，worldsim.db）+ aiosqlite
ORM           SQLModel + AsyncSession（SQLAlchemy async backend仅作为SQLModel底层）
LLM           DeepSeek V4（openai-compatible，baseurl可配置）
              接口统一，可切换任何openai-compatible端点
后端流式      SSE（sse-starlette）
地形噪声      noise（pip install noise，提供Perlin/Simplex）

前端框架      React 18 + TypeScript + Vite
状态管理      Zustand
地图渲染      HTML5 Canvas（纯手写，禁止引入 Pixi.js / Phaser / Three.js）
地图坐标      六边形网格（offset坐标，奇数行右移半格）
HTTP客户端    原生 fetch + EventSource（SSE）

依赖管理      后端 uv / pip，前端 pnpm
```

---

## 2. 项目目录结构

> 当前交付只创建标为 **[M1]** 的文件。标为 **[后续]** 的文件是预留名称，必须等对应里程碑开始后创建。

```
worldsim/
├── backend/
│   ├── main.py                    # [M1] FastAPI入口，路由注册
│   ├── worldsim_models.py         # [M1] 全部SQLModel数据模型（唯一数据定义处）
│   ├── worldsim_db.py             # [M1] Async SQLite连接/建表/session管理
│   ├── worldsim_engine.py         # [M1] 当前Tick主循环，系统编排
│   ├── worldsim_economy.py        # [M1] 经济系统：资源采集/消耗/生产/税收
│   ├── worldsim_trade.py          # [M1] 贸易路线：路线生成/撮合/来源批次转移
│   ├── worldsim_terrain.py        # [M1] 地形生成：六边形网格/Perlin噪声/资源分布
│   ├── worldsim_events.py         # [M1] 仅资源发现、经济阈值与事件写入
│   ├── worldsim_policies.py       # [M1] 第一阶段政策、规则AI、语义执行器
│   ├── worldsim_validator.py      # [M1] 规则AI/玩家系统执行前的资源与前置条件验证
│   ├── worldsim_worldwill.py      # [M1] 干预执行/即时发现/传播/因果追踪
│   ├── worldsim_init.py           # [M1] 世界初始化：四国生成/地形种子/贸易路线
│   ├── worldsim_llm.py            # [后续：里程碑二]
│   ├── worldsim_politics.py       # [后续：里程碑三]
│   ├── worldsim_combat.py         # [后续：里程碑三]
│   ├── worldsim_society.py        # [后续：里程碑四]
│   ├── worldsim_culture.py        # [后续：里程碑四]
│   └── worldsim_tech.py           # [后续：技术系统启用后]
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # [M1]
│   │   ├── App.tsx                # [M1]
│   │   ├── store/worldStore.ts    # [M1]
│   │   ├── components/
│   │   │   ├── HexMap.tsx         # [M1]
│   │   │   ├── NationPanel.tsx    # [M1]
│   │   │   ├── EventLog.tsx       # [M1]
│   │   │   ├── TickControl.tsx    # [M1]
│   │   │   ├── PolicyViewer.tsx   # [M1]
│   │   │   ├── WorldWillToolbar.tsx   # [M1]
│   │   │   ├── InterventionPanel.tsx  # [M1]
│   │   │   ├── InterventionTimeline.tsx # [M1]
│   │   │   ├── TradeRouteOverlay.tsx # [后续：里程碑二]
│   │   │   └── WarPanel.tsx       # [后续：里程碑三]
│   │   └── api/client.ts          # [M1]
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── SPEC.md
├── pyproject.toml
└── .env.example
```

---

## 3. 核心数据模型（worldsim_models.py）

> Codex 必须严格遵守以下字段名。v2.9新增字段已经列在本节；不得在代码中自行发明额外数据字段。
> 所有模型定义集中在此文件，其他文件只做 import。
> 每个 `table=True` 模型必须有主键。字符串ID统一写作 `id: str = Field(primary_key=True)`。

### 3.1 HexCell — 地形格子

```python
class HexCell(SQLModel, table=True):
    id: str = Field(primary_key=True)  # f"{q}_{r}"
    q: int
    r: int
    terrain: str                     # PLAIN / FOREST / MOUNTAIN / RIVER / COAST / DESERT
    elevation: float                 # 0.0–1.0
    fertility: float                 # 0.0–1.0，影响农业产出
    resource_food: float             # 基础月产量
    resource_wood: float
    resource_stone: float
    resource_iron: float
    passable: bool                   # False = 山脉/深水，不可穿越
    fog: str                         # UNKNOWN / KNOWN / ACTIVE
    nation_id: Optional[str]         # 控制方，None = 无主地
    settlement_id: Optional[str]     # 是否有聚落

    # 防御加成（建造城墙/要塞后累积）
    fortification: float = 0.0      # 0.0–1.0

    # ⚠️ 文化成分不存在本表。
    # 独立存储在 HexCulture 表（见3.2节）。
    # 禁止在此表添加 cultural_composition JSON 字段。
```

### 3.2 HexCulture — 格子文化成分（独立表）

> **架构原因**：文化成分若存为JSON字段，每Tick需对9600格逐行
> 反序列化→修改→序列化→写回，SQLite单线程写入下性能不可接受。
> 独立表后可用批量SQL UPDATE，单次Tick文化扩散降至毫秒级。

```python
class HexCulture(SQLModel, table=True):
    # 联合主键 (hex_id, nation_id)
    hex_id: str    = Field(primary_key=True)   # FK → HexCell.id
    nation_id: str = Field(primary_key=True)   # "agrarian"/"merchant"/"military"/"balanced"/"barbarian"
    percentage: float                           # 0.0–100.0，该格内此文化占比

# 约束：同一 hex_id 下所有行的 percentage 之和 = 100.0
# 初始化：控制区内格 → (hex_id, owner_nation_id, 100.0)
# 边境格 → (hex_id, owner, 70.0) + (hex_id, neighbor, 30.0)

# 文化扩散的批量SQL模式（worldsim_culture.py使用）：
# UPDATE hex_culture SET percentage = percentage + delta
# WHERE hex_id IN (SELECT id FROM hex_cell WHERE nation_id = ?)
# 再做归一化：percentage = percentage / SUM(percentage) * 100
# 索引：CREATE INDEX idx_hexculture_hex ON hex_culture(hex_id)
#        CREATE INDEX idx_hexculture_nation ON hex_culture(nation_id)
```

### 3.3 Nation — 国家

```python
class Nation(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "agrarian" / "merchant" / "military" / "balanced"
    name: str
    archetype: str                   # 同id，冗余便于查询
    color: str                       # 地图色 hex值

    # 人口分层——职业（整数）
    # ⚠️ v2.9闭环规则：以下六项之和 = pop_adults（始终成立）
    # pop_farmers + pop_craftsmen + pop_warriors + pop_nobles + pop_conscripts + pop_extractors = pop_adults
    pop_farmers: int      # 农民（主要劳动力，征兵来源）
    pop_craftsmen: int    # 工匠
    pop_warriors: int     # 职业军人阶层（常备军/武士贵族，社会身份，不因一次征兵改变）
    pop_nobles: int       # 贵族
    pop_conscripts: int = 0  # 临时征召兵（从pop_farmers转来，裁军后归还为pop_farmers）
    pop_extractors: int = 0  # 矿工/伐木工/采石工；从pop_farmers转来，资源点关闭后归还

    # v2新增：人口分层——年龄
    pop_children: int                # 0–14岁，不参与生产，消耗食物×0.6
    pop_adults: int                  # 15–50岁，主力劳动与军事
    pop_elders: int                  # 50+岁，产出×0.4，传承技术加成

    pop_total: int                   # 计算字段 = children+adults+elders

    # 资源库存（浮点，负值=告急/欠债）
    stock_food: float
    stock_wood: float
    stock_stone: float
    stock_iron: float
    stock_gold: float

    # v2.8新增：资源来源批次追踪（支持因果链跨月溯源）
    # JSON格式：[{"source_id":"natural","source_type":"NATURAL","acquired_tick":0,"remaining":850.0}]
    # 每种资源单独维护有序批次列表；消耗与贸易转出必须按FIFO逐批扣减。
    # 贸易转出时转移原批次元数据，接收方保留原source_id与acquired_tick。
    # 只追踪iron/stone/wood三种可溯源资源；food/gold来源当前不追踪。
    stock_iron_sources:  str = '[]'  # JSON FIFO batch list; init中写入natural初始批次
    stock_stone_sources: str = '[]'
    stock_wood_sources:  str = '[]'

    # 核心指标（0.0–1.0）
    morale: float
    stability: float
    prestige: float

    # 军事（v2.5完整闭环）
    # army_size = pop_warriors + pop_conscripts（pop_extractors不属于军队）（计算关系，每次人口操作后重算）
    # 征兵：pop_farmers -= N, pop_conscripts += N → army_size自动+N
    # 裁军：pop_conscripts -= N, pop_farmers += N → army_size自动-N
    # 战死（combat统一执行）：
    #   优先减 pop_conscripts，其次减 pop_warriors
    #   同步减 pop_adults（= pop_conscripts减少量 + pop_warriors减少量）
    #   army_size重算 = pop_warriors + pop_conscripts
    army_size: int                   # 计算字段 = pop_warriors + pop_conscripts，不得手动设置
    army_quality: float              # 0.0–1.0
    army_location: str               # JSON: {"hex_id": "60_40", "status": "HOME/CAMPAIGN/SIEGE"}
    at_war_with: str                 # JSON列表，当前交战国ID列表

    # 经济
    gdp_monthly: float
    tax_rate: float
    trade_balance: float             # 本月贸易顺差/逆差
    debt: float = 0.0                # v2.7新增：负债总量（来自借款政策）
    debt_creditor: Optional[str]     # v2.7新增：主要债权国ID（null=无债）
    debt_interest_rate: float = 0.0  # v2.7新增：月息率（谈判结果，通常0.01-0.05）

    # v2.5新增：Section 20政策效果表中引用的国家级修正字段
    culture_spread_bonus: float = 0.0
    elder_tech_bonus: float = 0.0
    road_level: int = 0

    # v2新增：内部派系支持度（0.0–1.0）
    faction_nobles: float
    faction_military: float
    faction_commoners: float

    # v2新增：历史记录（影响暴力传染）
    succession_type: str             # "PEACEFUL" / "VIOLENT"
    coup_multiplier: float = 1.0

    # v2.7新增：合法性（与stability分离的第二政治维度）
    # stability = 三派系加权平均（民心支持）
    # legitimacy = 统治者的继承合法性与神圣授权感知
    # 两者独立：暴君可以高stability低legitimacy，仁君可以高legitimacy低stability
    legitimacy: float = 0.75         # 初始值0.75（开国之君）
    # 影响规则见Section 12.5

    # v2.7新增：战争疲惫（与当前战争状态绑定）
    war_exhaustion: float = 0.0      # 0.0–1.0，每参战月+0.02
    # 影响规则见Section 11.3

    # v2.7新增：技术积累
    tech_points: float = 0.0         # 每月积累，受学堂/工匠比例影响
    tech_unlocked: str = '[]'        # JSON列表，已解锁的技术键名
    # 解锁阈值见Section 12.6（后续系统）

    # AI状态
    leader_name: str
    leader_personality: str
    leader_goal: str
    memory_summary: str
    known_intel: str

    # 时间
    founded_year: int
    current_year: int
    current_month: int
```

### 3.4 Settlement — 聚落

```python
class Settlement(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    nation_id: str
    hex_id: str
    size: str                        # VILLAGE / TOWN / CITY / CAPITAL
    population: int
    buildings: str                   # JSON列表，见第13节建筑定义
    specialization: str              # FARMING / TRADE / MILITARY / CRAFT / MIXED
    storage_cap: float               # 该聚落仓储上限（建粮仓后增加）
```

### 3.5 TradeRoute — 贸易路线（v2新增）

```python
class TradeRoute(SQLModel, table=True):
    id: str = Field(primary_key=True)  # f"{nation_a}_{nation_b}_{established_tick}"
    nation_a: str
    nation_b: str
    route_hex_path: str              # JSON列表，途经hex_id
    goods_a_to_b: str                # JSON: {"food":100,"iron":0,"gold":50}
    goods_b_to_a: str                # JSON
    monthly_volume: float            # 贸易总量（用于计算关系加成）
    established_year: int
    established_month: int
    status: str                      # ACTIVE / BLOCKED / SEVERED
    block_reason: Optional[str]      # 封锁原因（战争/政策）
```

### 3.6 War — 战争状态（v2新增）

```python
class War(SQLModel, table=True):
    id: str = Field(primary_key=True)  # f"{attacker}_{defender}_{start_tick}"
    attacker_id: str
    defender_id: str
    start_year: int
    start_month: int
    end_year: Optional[int]
    end_month: Optional[int]
    status: str                      # ACTIVE / PEACE / ATTACKER_WON / DEFENDER_WON
    current_front_hex: Optional[str] # 当前主战场格子id
    attacker_casualties: int
    defender_casualties: int
    war_score: float                 # -1.0（防守方优势）到 1.0（进攻方优势）
    peace_terms: Optional[str]       # JSON，和平条款
```

### 3.7 DiplomaticRelation — 外交关系（v2新增）

```python
class DiplomaticRelation(SQLModel, table=True):
    id: str = Field(primary_key=True)  # f"{nation_a}_{nation_b}"（字典序排列）
    nation_a: str
    nation_b: str
    score: float                     # -1.0 到 1.0，实时计算结果
    has_alliance: bool = False
    has_trade_deal: bool = False
    has_marriage: bool = False
    has_defense_pact: bool = False
    is_at_war: bool = False
    historical_events: str           # JSON列表，近期影响关系的事件（含freshness）
    last_updated_tick: int
```

### 3.8 PendingProposal — 待处理外交提案（v2.1新增）

> **架构原因**：宗主关系、联盟、联姻等提案需要跨Tick持久化等待对方回应。
> 若只依赖 memory_summary，每5月压缩一次会导致提案丢失。
> 独立表保证提案不会在记忆压缩中消失。

```python
class PendingProposal(SQLModel, table=True):
    id: str = Field(primary_key=True)  # f"{from_nation}_{to_nation}_{tick_number}"
    from_nation: str
    to_nation: str
    proposal_type: str               # ALLIANCE / MARRIAGE / SUZERAINTY / CEASEFIRE / TRADE_DEAL
    terms: str                       # JSON，提案具体条款（如割地、赔款金额）
    created_tick: int
    expires_tick: int                # 超过此Tick自动变为EXPIRED（默认创建后3个Tick）
    status: str                      # PENDING / ACCEPTED / REJECTED / EXPIRED
    response_reasoning: Optional[str]  # 接受/拒绝方的LLM推理

# 提案流程：
# Tick N：nation_a执行 form_alliance 政策，创建 PendingProposal（status=PENDING）
# Tick N+1：nation_b的LLM在USER_PROMPT中收到【待回应提案】字段
#            nation_b可选择 accept_proposal / reject_proposal（新增隐式政策）
#            验证通过后 status→ACCEPTED，同时更新 DiplomaticRelation
# Tick N+3：若仍PENDING，status自动→EXPIRED，提案作废

# USER_PROMPT中需新增字段：
# 【待回应提案】
# {pending_proposals_json}  # 仅展示 to_nation == 本国 且 status=PENDING 的提案
```

### 3.9 PolicyAction — 决策记录

```python
class PolicyAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nation_id: str
    year: int
    month: int
    action_type: str
    action_key: str
    target_id: Optional[str]
    intensity: float
    reasoning: str                   # LLM推理，内部用，不展示
    status: str                      # PENDING / APPROVED / REJECTED
    reject_reason: Optional[str]
    effects_applied: str             # JSON
```

### 3.10 WorldEvent — 事件日志

```python
class WorldEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    year: int
    month: int
    tick_number: int
    event_type: str                  # NATURAL / POLITICAL / ECONOMIC / MILITARY / DIPLOMATIC / CULTURAL
    severity: str                    # INFO / WARNING / CRITICAL
    nation_ids: str                  # JSON列表
    title: str
    description: str
    cascade_effects: str             # JSON，次级效果
    # v2.5新增：因果链溯源字段（支持持久来源追踪机制）
    source_deposit_ids: str = '[]'       # JSON，与此事件相关的ResourceDeposit ID列表
    source_intervention_ids: str = '[]'  # JSON，可上溯到的玩家干预ID列表
    # 每次创建WorldEvent时，从触发方的ResourceFlowLedger继承上游来源
    # 这样第1月铁矿→第13月战争的链条可以完整追溯
```

### 3.11 WorldState — 全局快照

```python
class WorldState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    year: int
    month: int
    tick_number: int
    global_tension: float            # 0.0–1.0
    active_wars: str                 # JSON列表
    active_treaties: str             # JSON列表
    snapshot: str                    # JSON，完整世界状态，用于回放

# ⚠️ 快照保留策略（防止数据库膨胀）：
# 每次 save_world_snapshot() 执行后，自动清理旧快照：
#   DELETE FROM worldstate WHERE tick_number < (current_tick - 100)
# 始终保留最近100个Tick的回放能力，超出部分自动删除。
# 100Tick约占用 ~50MB，可接受。
```

---

## 3.12 全局资源单位定义（worldsim_models.py顶部常量）

> ⚠️ v2.3核心修复：粮食单位之前未定义，导致stock_food数值与文字描述月数完全矛盾。
> 所有资源单位必须在此统一定义，整个代码库按此换算，不得各自为政。

```python
# ════════════════════════════════════════════════════════
# 全局资源单位换算表（WORLD SIM Resource Unit Standard）
# ════════════════════════════════════════════════════════

# 粮食（food）
# 1 food单位 = 100人一个月的基础口粮
# 月消耗公式：MONTHLY_FOOD = pop_total // 100
# 军队出征额外消耗（campaign）：army_size // 50 per month（是驻扎的2倍）
# 验证：农业国 pop_total=60000 → MONTHLY_FOOD=600；stock_food=9600 → 16个月 ✓

# 黄金（gold）
# 1 gold单位 = 一支百人队一个月的标准军费
# 军队月维护：SOLDIER_MONTHLY_COST = 0.02 gold/soldier
# 军费比例：army_budget_ratio = (army_size × 0.02) / gdp_monthly
# 验证：军事国 25000×0.02/2000 = 0.25，恰在高阈值 ✓

# 铁（iron）
# 1 iron单位 = 100件基础铁器（农具、武器）的原料
# 军备消耗：army_quality提升1档消耗约100 iron

# 木材（wood）
# 1 wood单位 = 一栋标准建筑所需木料

# 石料（stone）
# 1 stone单位 = 十米城墙或一栋石质建筑所需石料

# ────────────────────────────────────────────────────────
# 便捷计算函数（定义在此，全局引用）
def monthly_food_consumption(pop_total: int) -> int:
    return max(1, pop_total // 100)

def army_maintenance_gold(army_size: int) -> float:
    SOLDIER_MONTHLY_COST = 0.02
    return army_size * SOLDIER_MONTHLY_COST

def army_budget_ratio(army_size: int, gdp_monthly: float) -> float:
    return army_maintenance_gold(army_size) / max(gdp_monthly, 1.0)
# ════════════════════════════════════════════════════════
```

---

## 4. 四国初始配置（worldsim_init.py）

> 严格按此参数初始化，不得自行调整比例。

### 农业国（Agrarian）— 稷原王国

```python
NATION_AGRARIAN = {
    "id": "agrarian",
    "name": "稷原王国",
    "color": "#4CAF50",
    # 职业人口（v2.9：六类职业总和=pop_adults=38000）
    # army_size = pop_warriors + pop_conscripts（pop_extractors不属于军队） = 3000+2000 = 5000 ✓
    "pop_farmers": 27000,    # 71%（2000人转为征召兵）
    "pop_craftsmen": 5000,   # 13%
    "pop_warriors": 3000,    # 8%，职业常备军
    "pop_nobles": 1000,      # 3%
    "pop_conscripts": 2000,  # 临时征召兵（合计38000=pop_adults ✓）
    "pop_extractors": 0,    # 初始无矿工/伐木工/采石工
    # 年龄人口（pop_total = 60000）
    "pop_children": 18000,
    "pop_adults": 38000,
    "pop_elders": 4000,
    # 资源（v2.3修正：按新粮食单位换算）
    # monthly_food_consumption = 60000//100 = 600
    # 16个月储备 = 600×16 = 9600
    "stock_food": 9600.0,
    "stock_wood": 1200.0,
    "stock_stone": 800.0,
    "stock_iron": 400.0,
    "stock_gold": 600.0,
    # 指标
    "morale": 0.72,
    "stability": 0.75,
    "prestige": 0.55,
    # 军事（弱）
    "army_size": 5000,
    "army_quality": 0.45,
    # 经济
    "gdp_monthly": 1800.0,
    "tax_rate": 0.18,
    # 派系（平民支持高，贵族和军事一般）
    "faction_nobles": 0.65,
    "faction_military": 0.50,
    "faction_commoners": 0.80,
    "legitimacy": 0.80,          # 老牌农业王国，继承稳定
    "war_exhaustion": 0.0,
    "tech_points": 30.0,         # 轻微领先（农业技术积累）
    "debt": 0.0,
    # AI
    "leader_personality": '["保守","重农","和平主义","多疑","恋土"]',
    "leader_goal": "维持粮食霸权，以粮食供给换取军事保护",
    # 地图：控制四国中约50%的高肥力平原格
}
```

### 商业城邦（Merchant）— 澜港联盟

```python
NATION_MERCHANT = {
    "id": "merchant",
    "name": "澜港联盟",
    "color": "#FFD700",
    # 职业人口（v2.9：六类职业总和=pop_adults=31000）
    # army_size = pop_warriors + pop_conscripts（pop_extractors不属于军队） = 2000+1000 = 3000 ✓
    "pop_farmers": 3000,     # 10%（1000人转为征召兵）
    "pop_craftsmen": 20000,  # 65%
    "pop_warriors": 2000,    # 6%
    "pop_nobles": 5000,      # 16%
    "pop_conscripts": 1000,  # 临时征召兵（合计31000=pop_adults ✓）
    "pop_extractors": 0,    # 初始无矿工/伐木工/采石工
    "pop_children": 10000,
    "pop_adults": 31000,
    "pop_elders": 4000,
    # 资源（v2.3修正）
    # monthly_food_consumption = 45000//100 = 450
    # ~2个月储备 = 450×2 = 900（依赖进口，储备极少）
    "stock_food": 900.0,
    "stock_wood": 2000.0,
    "stock_stone": 1500.0,
    "stock_iron": 1800.0,
    "stock_gold": 3500.0,
    "morale": 0.78,
    "stability": 0.82,
    "prestige": 0.80,              # 外交声望最高
    "army_size": 3000,
    "army_quality": 0.40,
    "gdp_monthly": 2400.0,         # GDP最高
    "tax_rate": 0.12,              # 低税吸引商业
    "faction_nobles": 0.75,
    "faction_military": 0.45,
    "faction_commoners": 0.78,
    "legitimacy": 0.72,          # 联盟体制，合法性来自商业协议而非王权
    "war_exhaustion": 0.0,
    "tech_points": 45.0,         # 商业贸易带来技术见闻，最高起点
    "debt": 0.0,
    "leader_personality": '["精明","中立","重商","善谈判","短视","逐利"]',
    "leader_goal": "保持中立，成为各国不可或缺的贸易枢纽，以金融制衡武力",
    # 地图：控制中部河流三角洲，主要渡口，贸易路线交汇
}
```

### 军事帝国（Military）— 铁鹰帝国

```python
NATION_MILITARY = {
    "id": "military",
    "name": "铁鹰帝国",
    "color": "#DC143C",
    # 职业人口（v2.9：六类职业总和=pop_adults=52000）
    # pop_warriors + pop_conscripts = army_size = 25000
    "pop_farmers": 13000,    # 35%→25%（5000人初始征召为conscripts）
    "pop_craftsmen": 10000,  # 19%
    "pop_warriors": 20000,   # 38%，职业常备军
    "pop_nobles": 4000,      # 8%
    "pop_conscripts": 5000,  # 初始已征召（合计52000=pop_adults ✓）
    "pop_extractors": 0,    # 初始无矿工/伐木工/采石工
    # army_size = pop_warriors + pop_conscripts（pop_extractors不属于军队） = 20000+5000 = 25000 ✓
    "pop_children": 20000,
    "pop_adults": 52000,
    "pop_elders": 6000,
    # 资源（v2.3修正）
    # monthly_food_consumption = 78000//100 = 780
    # ~4个月储备 = 780×4 = 3120
    "stock_food": 3120.0,
    "stock_wood": 1800.0,
    "stock_stone": 2000.0,
    "stock_iron": 3000.0,          # 铁矿最多
    "stock_gold": 800.0,
    "morale": 0.65,
    "stability": 0.68,
    "prestige": 0.62,
    "army_size": 25000,            # 军队规模四国之最
    "army_quality": 0.75,          # 战斗力最强
    "gdp_monthly": 2000.0,
    "tax_rate": 0.28,              # 重税养军
    # GDP的约15%投入军费维护：army_maintenance = gdp_monthly × 0.15
    "faction_nobles": 0.60,
    "faction_military": 0.88,
    "faction_commoners": 0.52,
    "legitimacy": 0.65,          # 军事政权，合法性依赖持续胜利
    "war_exhaustion": 0.0,
    "tech_points": 20.0,         # 重军轻文，技术积累最少
    "debt": 0.0,
    "leader_personality": '["扩张主义","强硬","荣誉至上","冲动","短于外交","嗜战"]',
    "leader_goal": "建立军事霸权，迫使他国称臣纳贡，统一四国",
    # 地图：控制北部山地，铁矿丰富，有天然防御优势
}
```

### 全产业国（Balanced）— 中衡郡国

```python
NATION_BALANCED = {
    "id": "balanced",
    "name": "中衡郡国",
    "color": "#9370DB",
    # 职业人口（v2.9：六类职业总和=pop_adults=42000）
    # army_size = pop_warriors + pop_conscripts（pop_extractors不属于军队） = 8000+4000 = 12000 ✓
    "pop_farmers": 15000,    # 36%（4000人转为征召兵）
    "pop_craftsmen": 12000,  # 29%
    "pop_warriors": 8000,    # 19%
    "pop_nobles": 3000,      # 7%
    "pop_conscripts": 4000,  # 临时征召兵（合计42000=pop_adults ✓）
    "pop_extractors": 0,    # 初始无矿工/伐木工/采石工
    "pop_children": 16000,
    "pop_adults": 42000,
    "pop_elders": 4000,
    # 资源（v2.3修正）
    # monthly_food_consumption = 62000//100 = 620
    # ~8个月储备（自给自足）= 620×8 = 4960
    "stock_food": 4960.0,
    "stock_wood": 1600.0,
    "stock_stone": 1400.0,
    "stock_iron": 1200.0,
    "stock_gold": 1400.0,
    "morale": 0.68,
    "stability": 0.70,
    "prestige": 0.65,
    "army_size": 12000,
    "army_quality": 0.55,
    "gdp_monthly": 1900.0,
    "tax_rate": 0.20,
    "faction_nobles": 0.65,
    "faction_military": 0.62,
    "faction_commoners": 0.68,
    "legitimacy": 0.75,          # 均衡体制，合法性中等稳定
    "war_exhaustion": 0.0,
    "tech_points": 35.0,         # 均衡发展，技术中等
    "debt": 0.0,
    "leader_personality": '["稳健","全局观","内向","重内政","善周旋","务实"]',
    "leader_goal": "构建全产业内循环，不依赖任何单一国家，韬光养晦",
    # 每项能力约为专项国的60-70%，但无明显短板
    # 地图：东部混合地形，各类地形均有
}
```

---

## 5. 政策系统（worldsim_policies.py）

### 5.1 政策选项池

```python
POLICIES = {

    # ═══ 经济类 ═══
    "raise_farm_tax": {
        "cat": "经济", "label": "提高农业税率",
        "cost": {},
        "effect": {"tax_rate": +0.03, "morale": -0.04,
                   "faction_commoners": -0.06},
    },
    "lower_trade_tax": {
        "cat": "经济", "label": "降低商业税",
        "cost": {"gold": 200},
        "effect": {"tax_rate": -0.02, "gdp_monthly": +0.06, "prestige": +0.02,
                   "faction_nobles": +0.03},
    },
    "conscript_labor": {
        "cat": "经济", "label": "征发劳役修建水利",
        "cost": {},
        "effect": {"morale": -0.06, "owned_plain_fertility_delta": +0.04, "stability": -0.03,
                   "faction_commoners": -0.08},
    },
    "open_market": {
        "cat": "经济", "label": "开放集市",
        "cost": {"gold": 100},
        # ⚠️ v2.1修正：原有 faction_merchants 字段不存在，已移除
        # Nation模型只有 faction_nobles / faction_military / faction_commoners
        "effect": {"gdp_monthly": +0.08, "stock_gold": +0.05,
                   "faction_nobles": +0.03},  # 贵族商人从集市获益
    },
    "monopolize_iron_trade": {
        "cat": "经济", "label": "国家垄断铁器贸易",
        "cost": {},
        "prereq": {"stock_iron": 500},
        "effect": {"stock_gold": +0.10, "prestige": -0.05, "trade_balance": +0.08},
    },
    "ban_food_export": {
        "cat": "经济", "label": "禁止粮食出口",
        "cost": {},
        "effect": {"stock_food": +0.12, "prestige": -0.08, "trade_balance": -0.05},
        "side_effect": "封锁所有粮食类贸易路线",
    },
    "encourage_farming": {
        "cat": "经济", "label": "鼓励开荒",
        "cost": {"gold": 150},
        "effect": {"workforce_transfer_to_farmers_ratio": +0.03, "owned_plain_food_yield_modifier": +0.06, "morale": +0.02},
    },
    "build_granary": {
        "cat": "经济", "label": "建立国家粮仓",
        "cost": {"gold": 300, "stone": 200},
        "effect": {"storage_cap_food": +2000, "stability": +0.04},
        "one_time": False,  # 可重复建，每次增加上限
    },
    "mint_currency": {
        "cat": "经济", "label": "铸造货币",
        "cost": {"iron": 100},
        "prereq_building": "mint",
        "effect": {"gdp_monthly": +0.05, "trade_balance": +0.04},
    },
    "land_reform": {
        "cat": "经济", "label": "推行土地改革",
        "cost": {},
        "effect": {"morale": +0.08, "stability": -0.05, "workforce_transfer_to_farmers_ratio": +0.04,
                   "faction_nobles": -0.15, "faction_commoners": +0.12},
    },
    "seize_noble_land": {
        "cat": "经济", "label": "没收贵族土地",
        "cost": {},
        "effect": {"stock_gold": +0.12, "stability": -0.10, "prestige": -0.05,
                   "faction_nobles": -0.20},
    },
    "grant_land_to_nobles": {
        "cat": "经济", "label": "赐地封赏功臣",
        "cost": {"gold": 200},
        "effect": {"army_quality": +0.03, "stability": +0.05,
                   "faction_nobles": +0.10, "faction_military": +0.05},
    },

    # ═══ 政治类 ═══
    "centralize_power": {
        "cat": "政治", "label": "加强中央集权",
        "cost": {"gold": 200},
        "effect": {"stability": +0.06, "tax_rate": +0.02, "prestige": +0.03,
                   "faction_nobles": -0.08, "faction_commoners": -0.02},
    },
    "decentralize": {
        "cat": "政治", "label": "分权给地方长官",
        "cost": {},
        "effect": {"morale": +0.05, "stability": -0.03, "gdp_monthly": +0.03,
                   "faction_nobles": +0.06},
    },
    "purge_opposition": {
        "cat": "政治", "label": "清洗反对派贵族",
        "cost": {"gold": 100},
        "effect": {"stability": +0.08, "prestige": -0.06, "morale": -0.04,
                   "faction_nobles": -0.12, "coup_multiplier": +0.3},
    },
    "establish_bureaucracy": {
        "cat": "政治", "label": "建立官僚制度",
        "cost": {"gold": 400},
        "one_time": True,
        "effect": {"stability": +0.10, "tax_rate": +0.03, "gdp_monthly": +0.05},
    },
    "promulgate_law_code": {
        "cat": "政治", "label": "颁布成文法典",
        "cost": {"gold": 200},
        "one_time": True,
        "effect": {"stability": +0.08, "prestige": +0.05, "morale": +0.04},
    },
    "hold_grand_ceremony": {
        "cat": "政治", "label": "举办国家祭祀",
        "cost": {"gold": 300},
        "effect": {"morale": +0.10, "stability": +0.04, "prestige": +0.06,
                   "legitimacy": +0.05,              # v2.7：祭祀强化神授合法性
                   "faction_commoners": +0.08},
    },
    # ── v2.7新增：债务与信贷政策 ──
    "request_loan": {
        "cat": "外交", "label": "向他国申请借款",
        "cost": {},
        "effect": {"stock_gold": +500, "debt": +500,
                   "target_relation": +0.05},        # 债权国获得影响力
        "requires_target": True,
        "note": "目标国LLM收到借款请求，下月决策接受/拒绝/附加条件。接受后设定debt_interest_rate。",
        "major_action": True,
    },
    "offer_loan": {
        "cat": "外交", "label": "主动向他国提供借款",
        "prereq": {"stock_gold": 500},
        "cost": {"gold": 500},
        "effect": {"target_stock_gold": +500, "target_debt": +500,
                   "target_relation": +0.10,         # 债务国关系改善
                   "prestige": +0.04},               # 展示财力
        "requires_target": True,
        "note": "商业国的核心战略工具。debt_interest_rate在0.01-0.03之间由提案方设定。",
        "major_action": True,
    },
    "repay_debt": {
        "cat": "经济", "label": "偿还债务",
        "cost": {},                                  # 消耗gold在effect中
        "effect": {"stock_gold": -200, "debt": -200,
                   "target_relation": +0.03,
                   "legitimacy": +0.02},             # 守信用提升合法性
        "prereq": {"debt": "> 0", "stock_gold": ">= 200"},
        "requires_target": True,
        "note": "每次偿还200单位，可多次选择。debt清零后debt_creditor和debt_interest_rate重置。",
    },
    "elevate_new_nobles": {
        "cat": "政治", "label": "扶持新贵制衡旧贵",
        "cost": {"gold": 250},
        "effect": {"stability": +0.05, "army_quality": +0.02,
                   "faction_nobles": -0.05},  # 旧贵族不满
    },
    "public_execution": {
        "cat": "政治", "label": "公开处决叛乱者",
        "cost": {},
        "effect": {"stability": +0.10, "morale": -0.08, "prestige": -0.04,
                   "coup_multiplier": +0.5},  # 暴力传染
    },
    "general_amnesty": {
        "cat": "政治", "label": "大赦天下",
        "cost": {"gold": 100},
        "effect": {"morale": +0.12, "stability": +0.06, "prestige": +0.04,
                   "faction_commoners": +0.10, "coup_multiplier": -0.2},
    },

    # ═══ 军事类 ═══
    "conscript_troops": {
        "cat": "军事", "label": "大规模征兵",
        "cost": {"food": 300},
        # v2.5闭环：征兵 = 农民转为征召兵，army_size随之增加
        # pop_farmers -= 2000, pop_conscripts += 2000
        # army_size重算 = pop_warriors + pop_conscripts（不手动设置army_size）
        "effect": {"pop_farmers": -2000, "pop_conscripts": +2000,
                   "morale": -0.05, "faction_military": +0.05,
                   "faction_commoners": -0.06},
        "major_action": False,
    },
    "disband_troops": {
        "cat": "军事", "label": "裁军减轻负担",
        "cost": {},
        # v2.5闭环：裁军 = 征召兵归还为农民
        # pop_conscripts -= 1500, pop_farmers += 1500
        # army_size重算（只能裁征召兵，不裁职业武士）
        "effect": {"pop_conscripts": -1500, "pop_farmers": +1500,
                   "stock_gold": +0.06, "morale": +0.03,
                   "faction_military": -0.08},
        "prereq": "pop_conscripts >= 1500",  # 无征召兵时不能裁军
    },
    "train_elite_units": {
        "cat": "军事", "label": "训练精锐部队",
        "cost": {"gold": 400, "iron": 150},
        # v2.8修正：原 army_size: -500 违反"army_size=warriors+conscripts"规则
        # 精锐化 = 将征召兵中500人转为职业军人（提升quality，减少conscripts）
        # 若conscripts不足，则直接提升现有warriors的quality
        "effect": {"army_quality": +0.08,
                   "pop_conscripts": -500, "pop_warriors": +500},
        # army_size不变（warriors+conscripts总和不变），但quality提升
        "prereq": "pop_conscripts >= 500",
        "alt_effect_if_no_conscripts": {"army_quality": +0.05},  # 无征召兵时只能小幅提升
    },
    "build_fortifications": {
        "cat": "军事", "label": "修建边境防御工事",
        "cost": {"gold": 500, "stone": 400},
        "effect": {"border_fortification_delta": +0.15, "stability": +0.03},
        "side_effect": "在边境hex_cells上增加fortification值",
    },
    "stockpile_weapons": {
        "cat": "军事", "label": "囤积战略武器",
        "cost": {"gold": 300, "iron": 200},
        "effect": {"army_quality": +0.04},
    },
    "send_scouts": {
        "cat": "军事", "label": "派遣侦察队",
        "cost": {"gold": 50},
        "effect": {"intel_freshness_target": +0.40},  # 大幅刷新对目标国情报
        "requires_target": True,
    },
    "border_garrison": {
        "cat": "军事", "label": "边境大规模驻军",
        "cost": {"gold": 200, "food": 200},
        "effect": {"border_fortification_delta": +0.10, "neighbor_tension": +0.08},
    },
    "launch_raid": {
        "cat": "军事", "label": "对邻国发动袭扰",
        "cost": {"food": 100},
        "effect": {"target_morale": -0.08, "global_tension": +0.15,
                   "target_stock_food": -200},
        "requires_target": True,
        "major_action": False,
    },
    "declare_war": {
        "cat": "军事", "label": "正式宣战",
        "cost": {},
        "effect": {"global_tension": +0.30, "prestige": +0.05,
                   "faction_military": +0.10},
        "requires_target": True,
        "major_action": True,  # 每月最多1个major_action
        "side_effect": "创建War记录，封锁与目标国贸易路线",
    },
    "request_ceasefire": {
        "cat": "军事", "label": "请求停火议和",
        "cost": {},
        "effect": {"global_tension": -0.10, "prestige": -0.05,
                   "faction_military": -0.06},
        "requires_war": True,
        "requires_target": True,
        "major_action": True,
    },

    # ═══ 外交类 ═══
    "send_envoy": {
        "cat": "外交", "label": "派遣使者修好",
        "cost": {"gold": 100},
        "effect": {"target_relation": +0.10, "prestige": +0.02},
        "requires_target": True,
    },
    "propose_trade_deal": {
        "cat": "外交", "label": "提出贸易协议",
        "cost": {"gold": 50},
        "effect": {"trade_balance": +0.05, "target_relation": +0.06,
                   "has_trade_deal": True},
        "requires_target": True,
    },
    "propose_marriage": {
        "cat": "外交", "label": "提出王室联姻",
        "cost": {"gold": 200},
        "effect": {"target_relation": +0.20, "stability": +0.03,
                   "has_marriage": True},
        "requires_target": True,
    },
    "form_alliance": {
        "cat": "外交", "label": "缔结军事同盟",
        "cost": {"gold": 100},
        "effect": {"target_relation": +0.25, "has_alliance": True},
        "requires_target": True,
        "major_action": True,
    },
    "expel_envoy": {
        "cat": "外交", "label": "驱逐他国使者",
        "cost": {},
        "effect": {"target_relation": -0.20, "global_tension": +0.10},
        "requires_target": True,
    },
    "demand_tribute": {
        "cat": "外交", "label": "索要战争赔款",
        "cost": {},
        "effect": {"target_relation": -0.15, "stock_gold": +0.10,
                   "prestige": +0.08},
        "requires_target": True,
        "requires_winning_war": True,
        "major_action": True,
    },
    "cede_territory": {
        "cat": "外交", "label": "割地换取和平",
        "cost": {},
        "effect": {"target_relation": +0.15, "prestige": -0.10,
                   "stability": -0.05, "faction_military": -0.10},
        "requires_target": True,
        "requires_war": True,
        "major_action": True,
    },
    "fund_rebellion": {
        "cat": "外交", "label": "秘密资助他国叛乱",
        "cost": {"gold": 300},
        "effect": {"target_stability": -0.12, "global_tension": +0.08,
                   "target_faction_commoners": -0.08},
        "requires_target": True,
        "if_discovered": {"prestige": -0.20, "target_relation": -0.40},
        "discovery_chance": 0.25,   # 每月25%概率被发现
    },
    "propose_suzerainty": {
        "cat": "外交", "label": "提出宗主-藩属关系",
        "cost": {},
        "effect": {"prestige": +0.10},
        "requires_target": True,
        "major_action": True,
        "note": "目标国LLM下月会收到此提案并决策接受/拒绝",
    },
    "break_alliance": {
        "cat": "外交", "label": "单方面废除同盟",
        "cost": {},
        "effect": {"target_relation": -0.30, "prestige": -0.08,
                   "has_alliance": False},
        "requires_target": True,
        "prereq": "has_alliance == True",
    },

    # ═══ 社会类 ═══
    "promote_new_tools": {
        "cat": "社会", "label": "推广新式农具",
        "cost": {"gold": 200},
        "effect": {"resource_food_monthly": +0.08, "morale": +0.04,
                   "faction_commoners": +0.05},
    },
    "establish_schools": {
        "cat": "社会", "label": "建立学堂",
        "cost": {"gold": 350, "wood": 100},
        "effect": {"gdp_monthly": +0.04, "stability": +0.03, "prestige": +0.04,
                   "pop_elders_bonus": +0.05},  # 老人技术传承加强
    },
    "promote_state_religion": {
        "cat": "社会", "label": "强化官方宗教",
        "cost": {"gold": 150},
        "effect": {"morale": +0.08, "stability": +0.05, "prestige": +0.03,
                   "faction_commoners": +0.06},
        "note": "据历史数据：宗教制度化与王朝寿命负相关，长期或产生反效果",
    },
    "open_immigration": {
        "cat": "社会", "label": "开放移民政策",
        "cost": {},
        "effect": {"immigration_adults": 800, "gdp_monthly": +0.03, "morale": -0.02,
                   "foreign_culture_pressure": +0.02},  # 后续文化系统处理
    },
    "expel_foreigners": {
        "cat": "社会", "label": "驱逐外来人口",
        "cost": {},
        "effect": {"morale": +0.04, "prestige": -0.06, "trade_balance": -0.04,
                   "foreign_culture_pressure": -0.05},
    },
    "restrict_movement": {
        "cat": "社会", "label": "限制人口流动",
        "cost": {},
        "effect": {"stability": +0.03, "morale": -0.05,
                   "faction_commoners": -0.04},
    },
    "standardize_script": {
        "cat": "社会", "label": "推行统一文字",
        "cost": {"gold": 200},
        "one_time": True,
        "effect": {"stability": +0.04, "prestige": +0.06, "gdp_monthly": +0.02,
                   "culture_spread_bonus": +0.03},  # 后续文化系统读取
    },

    # ═══ 建设类 ═══
    "build_roads": {
        "cat": "建设", "label": "修建道路网络",
        "cost": {"gold": 400, "stone": 300},
        "effect": {"trade_balance": +0.06, "road_project": True,
                   "gdp_monthly": +0.04, "culture_spread_bonus": +0.02},
        "side_effect": "降低途经hex的军队移动消耗",
    },
    "build_port": {
        "cat": "建设", "label": "建造港口",
        "cost": {"gold": 500, "wood": 400},
        "prereq_terrain": "COAST or RIVER",
        "effect": {"trade_balance": +0.10, "gdp_monthly": +0.06},
    },
    "repair_walls": {
        "cat": "建设", "label": "修缮城墙",
        "cost": {"gold": 300, "stone": 200},
        "effect": {"fortification": +0.08, "stability": +0.03},
        "side_effect": "在首都hex增加fortification值",
    },
    "build_temple": {
        "cat": "建设", "label": "建造神殿",
        "cost": {"gold": 400, "stone": 300},
        "effect": {"morale": +0.10, "prestige": +0.08, "stability": +0.04,
                   "faction_commoners": +0.08},
    },
    "dig_canal": {
        "cat": "建设", "label": "开凿运河",
        "cost": {"gold": 600, "stone": 200},
        "one_time": True,
        "effect": {"owned_plain_fertility_delta": +0.06, "trade_balance": +0.08,
                   "gdp_monthly": +0.05},
    },
    "build_armory": {
        "cat": "建设", "label": "建造兵工厂",
        "cost": {"gold": 450, "iron": 300},
        "effect": {"army_quality": +0.05, "gdp_monthly": +0.03,
                   "faction_military": +0.05},
    },
    "build_mint": {
        "cat": "建设", "label": "建立铸币厂",
        "cost": {"gold": 350, "stone": 150},
        "one_time": True,
        "effect": {"gdp_monthly": +0.03, "prestige": +0.04},
        "side_effect": "解锁mint_currency政策",
    },
    "develop_resource_deposit": {
        "cat": "建设", "label": "开发资源矿脉",
        "cost": {"gold": 200, "wood": 100},
        # 触发条件（全部满足）：
        #   1. 本国已发现目标ResourceDeposit
        #   2. 距最近聚落 <= 5格
        #   3. pop_farmers >= 150（留足最低农业人口）
        #   4. stock_gold >= 200, stock_wood >= 100
        # 执行效果（v2.8：包含劳动力分配）：
        #   workers = 100（默认）
        #   deposit.workers_assigned = workers
        #   pop_farmers -= workers（农民转为矿工，不再参与农业生产）
        #   deposit.developed_by = nation_id
        #   deposit.development_level = 1
        #   deposit.monthly_yield = 重算（基于workers/quality/difficulty/road_level）
        # 矿场关闭时（depleted或主动放弃）：
        #   pop_farmers += deposit.workers_assigned
        "requires_deposit": True,
        "requires_target": False,
        "effect_description": "开发指定矿脉，分配100名农民为矿工，每月产出写入ResourceFlowLedger",
    },
```

### 5.2 互斥规则

```python
MUTEX_GROUPS = [
    {"raise_farm_tax", "lower_trade_tax"},
    {"open_immigration", "expel_foreigners"},
    {"conscript_troops", "disband_troops"},
    {"centralize_power", "decentralize"},
    {"declare_war", "send_envoy"},           # 对同一目标
    {"form_alliance", "fund_rebellion"},      # 对同一目标
    {"land_reform", "seize_noble_land"},     # 同月不能两步打击贵族
    {"build_fortifications", "conscript_troops"},  # 资源冲突
]
```

### 5.3 政策数量规则

> 当前里程碑的规则AI只能从第20.3的 `PHASE_1_POLICY_KEYS` 中选择。
> 后续政策即使保留在字典中，也必须被Validator拒绝，直到对应里程碑启用。

```python
MIN_ACTIONS = 2
MAX_ACTIONS = 6
MAX_MAJOR_ACTIONS = 1       # 宣战/结盟/割地等每月最多1个
MAX_BUILD_ACTIONS = 2       # 建设类每月最多2个
MAX_DIPLOMATIC_ACTIONS = 3  # 外交类每月最多3个（对不同目标）
```

---

## 6. 当前交付 Tick 主循环（worldsim_engine.py，里程碑一）

> **本节是当前可执行Tick的唯一权威来源。** 只调用里程碑一已实现模块。
> 第8–14节的未来系统不得在本次交付中导入、调用或以空函数替代。
> `current_tick/current_month/current_year` 必须在函数开头读取一次，之后只传递变量，不得重复查询。

```python
async def run_tick(db_session) -> TickResult:
    """执行一个月的里程碑一世界推进。"""
    current_state = await get_current_world_state(db_session)
    current_tick = current_state.tick_number
    current_month = current_state.month
    current_year = current_state.year

    # Step 1：季节与地图基础资源再生
    await terrain_system.monthly_regen(db_session, month=current_month)

    # Step 2：经济结算。consume_resources()是食物扣除的唯一入口。
    nations = await get_all_nations(db_session)
    for nation in nations:
        await economy_system.extract_resources(
            nation=nation,
            current_tick=current_tick,
            db_session=db_session,
        )
        await economy_system.consume_resources(nation, db_session)
        await economy_system.produce_goods(nation, db_session)
        await economy_system.collect_tax(nation, db_session)
        await economy_system.pay_army_maintenance(nation, db_session)

    # Step 3：贸易撮合。可溯源资源的批次必须随贸易转移。
    trade_events = await trade_system.resolve_trades(
        current_tick=current_tick,
        db_session=db_session,
    )

    # Step 4：资源节点远方发现。即时发现发生在POST /intervene内，不在此重跑。
    discovery_events = []
    for deposit in await world_will_system.get_undiscovered_deposits(db_session):
        discovery_events.extend(
            await world_will_system.propagate_resource_discovery(
                deposit=deposit,
                current_tick=current_tick,
                db_session=db_session,
            )
        )

    # Step 5：仅使用规则型AI选择“已验证可用”的第一阶段政策。
    decisions = []
    for nation in await get_all_nations(db_session):
        decisions.append(
            policy_system.choose_rule_based_actions(
                nation=nation,
                current_tick=current_tick,
                db_session=db_session,
            )
        )

    # Step 6：验证并执行。任何资源、人口、库存来源变化只能经语义执行器。
    policy_events = []
    for nation, decision_list in zip(await get_all_nations(db_session), decisions):
        for decision in decision_list:
            result = await validator.validate(
                decision=decision,
                nation=nation,
                current_tick=current_tick,
                db_session=db_session,
            )
            if result.approved:
                policy_events.extend(
                    await policy_executor.execute(
                        decision=decision,
                        nation=nation,
                        current_tick=current_tick,
                        db_session=db_session,
                    )
                )
            await save_policy_action(decision, result, db_session)

    # Step 7：经济阈值与资源相关随机事件。事件一律由语义处理器执行。
    random_events = await event_system.generate_m1_events(
        current_tick=current_tick,
        current_month=current_month,
        db_session=db_session,
    )
    threshold_events = await event_system.scan_m1_thresholds(
        current_tick=current_tick,
        db_session=db_session,
    )
    all_events = trade_events + discovery_events + policy_events + random_events + threshold_events

    # Step 8：本Tick结束后建立因果链接；绝不依赖“最近N Tick”的时间窗。
    for event in all_events:
        await world_will_system.trace_links(
            event=event,
            current_tick=current_tick,
            db_session=db_session,
        )

    # Step 9：推进时间与持久化
    await advance_month(db_session)
    snapshot = await save_world_snapshot(db_session)
    return TickResult(events=all_events, snapshot=snapshot)
```

### 6.1 后续完整 Tick 的启用顺序

文化、人口、政治、外交、战争、LLM、技术、合法性、债务只可在对应里程碑完成后，按以下顺序插入当前Tick：

```text
人口生命周期 → 文化扩散 → 派系/稳定度 → 外交 → 战争 → LLM决策 → 记忆压缩 → 合法性/技术/债务。
```

启用任一系统前，先补齐其测试与语义执行器；不可先把函数塞进Tick再补实现。

---

## 7. 贸易路线系统（worldsim_trade.py）

> 参考来源：`void-reckoning-engine` trade route handling + `Nova1390/ai-civ-sandbox` road system

### 7.1 贸易路线生成

```python
def find_trade_route_path(nation_a_capital, nation_b_capital, hex_map) -> list[str]:
    """
    A*寻路：在hexcell网格上找最短路径。
    路径成本：PLAIN=1, FOREST=2, MOUNTAIN=5（不可翻越则inf）,
              RIVER=1（沿河），COAST=1（海岸）
    道路建设（build_roads政策）将途经格成本×0.5
    """

def check_route_status(route: TradeRoute, active_wars: list[War]) -> str:
    """
    检查贸易路线状态：
    - 路径上任一hex被交战方控制 → BLOCKED
    - ban_food_export政策生效 → 粮食路线BLOCKED
    - 双方无外交关系恶化到-0.6以下 → SEVERED
    """

async def resolve_trades(db_session):
    """
    每月贸易撮合逻辑（gravity model，借鉴void-reckoning）：
    1. 识别surplus：stock > 6个月消耗量的资源
    2. 识别deficit：stock < 2个月消耗量的资源
    3. 撮合：surplus方→deficit方，优先距离近+关系好的路线
    4. 自动定价：surplus方price×0.8，deficit方price×1.2
    5. 执行转移：更新双方库存和trade_balance。
       IRON/STONE/TIMBER必须调用 transfer_resource_batches_fifo()：
       从发送方最早来源批次逐个扣减，将同一source_id/source_type/acquired_tick
       写入接收方库存批次，并为每个被转移批次各写一条ResourceFlowLedger。
    6. 活跃贸易路线关系加成：+0.03/条/月
    """
```

### 7.2 贸易对四国的结构性依赖

```
初始设计的依赖链（必须涌现出来，不要硬编码）：

军事国  ──粮食需求──→  农业国（军事国stock_food只有2.5个月储备）
军事国  ──经济需求──→  商业国（军事国gold储备最少）
农业国  ──铁器需求──→  军事国（农业国iron不足）
商业国  ──粮食需求──→  农业国（商业国food只有2个月储备）
平衡国  ──金融需求──→  商业国（平衡国gold中等，希望融资）

这个依赖链不应硬编码，而是通过资源不均+贸易撮合自然形成。
```

---

## 8. 人口生命周期（worldsim_society.py，后续里程碑四）

> 本节不属于当前交付实现范围。开始里程碑四前，按本节实现；不可从里程碑一 Tick 调用。

```python
WORKFORCE_FIELDS = [
    "pop_farmers", "pop_craftsmen", "pop_warriors",
    "pop_nobles", "pop_conscripts", "pop_extractors",
]

async def update_population_cohorts(nation, db_session):
    """人口年龄变化只在这里调整；战争伤亡由combat.apply_casualties()单独处理。"""
    new_adults = int(nation.pop_children * 0.006)
    new_elders = int(nation.pop_adults * 0.004)
    natural_deaths = int(nation.pop_elders * 0.015)

    nation.pop_children = max(0, nation.pop_children - new_adults)
    nation.pop_adults = max(0, nation.pop_adults + new_adults - new_elders)
    nation.pop_elders = max(0, nation.pop_elders + new_elders - natural_deaths)

    food_months = nation.stock_food / max(monthly_food_consumption(nation.pop_total), 1)
    morale_birth_modifier = 0.5 + nation.morale
    food_birth_modifier = min(1.2, max(0.1, food_months / 6.0))
    births = int(nation.pop_adults * 0.008 * morale_birth_modifier * food_birth_modifier)
    nation.pop_children += births

    famine_adult_deaths = 0
    if nation.stock_food < 0:
        severity = abs(nation.stock_food) / max(monthly_food_consumption(nation.pop_total), 1)
        famine_deaths = int(nation.pop_total * min(severity, 1.0) * 0.05)
        child_deaths = min(nation.pop_children, int(famine_deaths * 0.40))
        elder_deaths = min(nation.pop_elders, int(famine_deaths * 0.35))
        famine_adult_deaths = min(nation.pop_adults, famine_deaths - child_deaths - elder_deaths)
        nation.pop_children -= child_deaths
        nation.pop_elders -= elder_deaths
        nation.pop_adults -= famine_adult_deaths
        await emit_event("FAMINE", severity=severity, nation=nation, db_session=db_session)

    # 此函数实际改变成年人口的唯一净值；不引用未定义的delta_adults。
    adult_delta = new_adults - new_elders - famine_adult_deaths
    await rebalance_workforce(nation, adult_delta, db_session)

    nation.pop_total = max(0, nation.pop_children + nation.pop_adults + nation.pop_elders)
    nation.army_size = nation.pop_warriors + nation.pop_conscripts


async def rebalance_workforce(nation, adult_delta: int, db_session):
    """非战争成年人口变化的唯一再平衡入口。"""
    if adult_delta > 0:
        # 新成年人口默认进入农业劳动力；后续政策可经transfer_workforce改变职业。
        nation.pop_farmers += adult_delta
    elif adult_delta < 0:
        # 非战争损失按当前六类职业比例扣减，含矿工，保证总和随成年人口同步缩小。
        loss = min(-adult_delta, sum(getattr(nation, f) for f in WORKFORCE_FIELDS))
        remaining_loss = loss
        initial_total = max(sum(getattr(nation, f) for f in WORKFORCE_FIELDS), 1)
        for field in WORKFORCE_FIELDS:
            cut = min(getattr(nation, field), int(loss * getattr(nation, field) / initial_total))
            setattr(nation, field, getattr(nation, field) - cut)
            remaining_loss -= cut
        # 处理整数除法余数，优先从非关键劳动力扣除。
        for field in ["pop_farmers", "pop_craftsmen", "pop_extractors", "pop_conscripts", "pop_warriors", "pop_nobles"]:
            if remaining_loss <= 0:
                break
            cut = min(getattr(nation, field), remaining_loss)
            setattr(nation, field, getattr(nation, field) - cut)
            remaining_loss -= cut

    await normalize_workforce(nation, db_session)


async def normalize_workforce(nation, db_session):
    """最后一道不变量校验：六类职业总和必须精确等于pop_adults。"""
    for field in WORKFORCE_FIELDS:
        setattr(nation, field, max(0, int(getattr(nation, field))))
    workforce_total = sum(getattr(nation, f) for f in WORKFORCE_FIELDS)
    difference = nation.pop_adults - workforce_total
    if difference >= 0:
        nation.pop_farmers += difference
    else:
        to_remove = -difference
        for field in ["pop_farmers", "pop_craftsmen", "pop_extractors", "pop_conscripts", "pop_warriors", "pop_nobles"]:
            if to_remove <= 0:
                break
            cut = min(getattr(nation, field), to_remove)
            setattr(nation, field, getattr(nation, field) - cut)
            to_remove -= cut
    assert sum(getattr(nation, f) for f in WORKFORCE_FIELDS) == nation.pop_adults
    nation.army_size = nation.pop_warriors + nation.pop_conscripts
```

### 8.1 人口与军队的语义入口

```text
transfer_workforce(nation, from_field, to_field, amount)
  只改变职业分布；不改变pop_adults。

apply_immigration(nation, adults)
  pop_adults += adults；随后rebalance_workforce(+adults)，默认进入pop_farmers。

apply_noncombat_adult_loss(nation, adults)
  pop_adults -= adults；随后rebalance_workforce(-adults)。

apply_casualties(nation, casualties)
  仅战争使用：优先pop_conscripts，再pop_warriors；同步减少pop_adults；
  不再调用rebalance_workforce()，最后重算army_size。
```

---

## 9. 文化扩散与叛乱（worldsim_culture.py）

> 参考来源：`Greal-dev/unciv-warfare-economics-evolution` 文化成分系统

### 9.1 每月文化扩散（批量SQL版本）

> ⚠️ v2.3完整重写：原代码引用 `hex_cell.cultural_composition` JSON字段，
> 与Section 3.2禁令直接冲突。此节全部改为操作 HexCulture 独立表，
> 禁止任何 `json.loads(hex_cell.cultural_composition)` 调用。

```python
async def diffuse_all(db_session):
    """
    每月文化扩散主入口。
    每个Tick调用一次（不是每国调用一次），对所有ACTIVE格批量处理。
    全程使用批量SQL，禁止逐格Python循环。
    """

    # ══ Step A：自然同化 ════════════════════════════════════════════
    # 控制方文化在自己的格子里每月自然增长 0.5 个百分点
    # 使用单条SQL批量完成，无需Python循环
    await db_session.execute("""
        UPDATE hex_culture
        SET percentage = percentage + 0.5
        WHERE nation_id = (
            SELECT nation_id FROM hex_cell
            WHERE hex_cell.id = hex_culture.hex_id
            AND hex_cell.nation_id IS NOT NULL
        )
        AND hex_id IN (
            SELECT id FROM hex_cell WHERE fog = 'ACTIVE'
        )
    """)

    # ══ Step B：驻军文化强化 ════════════════════════════════════════
    # 驻军的格子，控制方文化额外增长
    # garrison_influence = garrison_size / 1000 * 0.5（百分点/月）
    # 驻军数据从 WorldState.snapshot 的 army_location 字段读取
    garrison_hexes = await get_garrison_hex_map(db_session)
    # garrison_hexes: {hex_id: {nation_id: garrison_size}}
    if garrison_hexes:
        # 构建批量UPDATE的VALUES列表
        values = [
            (hex_id, nation_id, size / 1000 * 0.5)
            for hex_id, armies in garrison_hexes.items()
            for nation_id, size in armies.items()
        ]
        await db_session.execute("""
            UPDATE hex_culture
            SET percentage = percentage + :delta
            WHERE hex_id = :hex_id AND nation_id = :nation_id
        """, values)

    # ══ Step C：贸易路线文化渗透 ════════════════════════════════════
    # 每条ACTIVE贸易路线，对途经格注入0.2%/月的对方文化
    active_routes = await get_active_trade_routes(db_session)
    route_values = []
    for route in active_routes:
        for hex_id in json.loads(route.route_hex_path):
            # 双向渗透
            route_values.append((hex_id, route.nation_b, 0.2))
            route_values.append((hex_id, route.nation_a, 0.2))
    if route_values:
        # INSERT OR IGNORE先确保行存在，再UPDATE
        await db_session.execute("""
            INSERT OR IGNORE INTO hex_culture (hex_id, nation_id, percentage)
            VALUES (:hex_id, :nation_id, 0)
        """, route_values)
        await db_session.execute("""
            UPDATE hex_culture SET percentage = percentage + :delta
            WHERE hex_id = :hex_id AND nation_id = :nation_id
        """, route_values)

    # ══ Step D：归一化 ══════════════════════════════════════════════
    # 每个hex_id下所有行的percentage之和归一化到100
    # 使用窗口函数或子查询批量处理
    await db_session.execute("""
        UPDATE hex_culture
        SET percentage = percentage * 100.0 / (
            SELECT SUM(h2.percentage)
            FROM hex_culture h2
            WHERE h2.hex_id = hex_culture.hex_id
        )
        WHERE hex_id IN (SELECT id FROM hex_cell WHERE fog = 'ACTIVE')
    """)

    await db_session.commit()


async def check_rebellions(db_session) -> list:
    """
    叛乱检测：读取HexCulture表，找出外来文化占比高的格子。
    ⚠️ 禁止读取 hex_cell.cultural_composition 字段。
    """
    events = []

    # 单条SQL找出所有外来文化占比高的格子
    # owner_pct = hex_culture行中 nation_id = hex_cell.nation_id 的那行
    # foreign_pct = 100 - owner_pct
    rebellion_hexes = await db_session.execute("""
        SELECT
            hc_owner.hex_id,
            hc.nation_id AS hex_owner,
            (100 - hc_owner.percentage) AS foreign_pct,
            hc_dominant.nation_id AS dominant_foreign
        FROM hex_cell hc
        JOIN hex_culture hc_owner
            ON hc_owner.hex_id = hc.id
            AND hc_owner.nation_id = hc.nation_id
        JOIN hex_culture hc_dominant
            ON hc_dominant.hex_id = hc.id
            AND hc_dominant.nation_id != hc.nation_id
        WHERE hc.fog = 'ACTIVE'
          AND hc.nation_id IS NOT NULL
          AND (100 - hc_owner.percentage) > 65
        GROUP BY hc.id
        HAVING hc_dominant.percentage = MAX(hc_dominant.percentage)
    """)

    for row in rebellion_hexes:
        if row.foreign_pct > 85:
            # 自动领土转移（无需LLM）
            await db_session.execute("""
                UPDATE hex_cell SET nation_id = :new_owner WHERE id = :hex_id
            """, {"new_owner": row.dominant_foreign, "hex_id": row.hex_id})
            events.append(create_event(
                "CULTURAL", "CRITICAL",
                f"格{row.hex_id}文化融合完成，归入{row.dominant_foreign}",
                [row.hex_owner, row.dominant_foreign]
            ))
        else:
            # 65–85%：叛乱苗头，通知LLM下月处理
            events.append(create_event(
                "CULTURAL", "WARNING",
                f"格{row.hex_id}出现叛乱苗头（外来文化{row.foreign_pct:.0f}%）",
                [row.hex_owner]
            ))

    return events
```

---

## 10. 外交关系公式（worldsim_politics.py）

> 参考来源：`JaySpiffy/void-reckoning-engine` Relationship Factors

```python
def calculate_relation_score(nation_a: Nation, nation_b: Nation,
                              relations: DiplomaticRelation,
                              world_state: WorldState) -> float:
    """
    计算两国关系分（-1.0 到 1.0）。
    每月调用，结果写入 DiplomaticRelation.score。
    """
    score = 0.0

    # ── 结构性因素（每月自动） ──
    # 共享边境产生竞争压力
    shared_border_count = count_shared_border_hexes(nation_a, nation_b)
    score -= shared_border_count * 0.005   # 每共享1格-0.005，上限-0.10

    # 实力差距（弱者恐惧强者）
    power_ratio = get_power_score(nation_b) / max(get_power_score(nation_a), 1)
    if power_ratio > 2.0:
        score -= 0.05  # 对方明显更强，产生恐惧

    # ── 协议加成 ──
    if relations.has_alliance:       score += 0.30
    if relations.has_trade_deal:     score += 0.08
    if relations.has_marriage:       score += 0.20
    if relations.has_defense_pact:   score += 0.15
    if relations.is_at_war:          score -= 0.80

    # ── 活跃贸易路线加成 ──
    active_routes = count_active_routes(nation_a.id, nation_b.id)
    score += active_routes * 0.03   # 每条路线+0.03/月

    # ── 历史事件（衰减记忆，借鉴void-reckoning）──
    events = json.loads(relations.historical_events)
    for event in events:
        # freshness每月×0.90，低于0.1后从列表移除
        event["freshness"] *= 0.90
        score += event["relation_impact"] * event["freshness"]
    relations.historical_events = json.dumps(
        [e for e in events if e["freshness"] > 0.1]
    )

    # ── 性格匹配（借鉴void-reckoning personality match）──
    score += personality_compatibility(
        json.loads(nation_a.leader_personality),
        json.loads(nation_b.leader_personality)
    )
    # 例：两个"扩张主义"性格互相排斥-0.05；"和平主义"和"重商"相容+0.03

    # ── 阈值行为触发（写入WorldEvent供LLM参考）──
    # > 0.60 → LLM倾向提出同盟 / 联姻
    # 0.20–0.60 → 中立，贸易优先
    # -0.20–0.20 → 紧张观望，派遣侦察
    # < -0.40 → LLM倾向宣战 / 资助叛乱

    relations.score = max(-1.0, min(1.0, score))
    return relations.score


def personality_compatibility(pa: list, pb: list) -> float:
    """性格相容性表（部分示例）"""
    COMPAT = {
        ("扩张主义", "扩张主义"): -0.06,
        ("和平主义", "和平主义"): +0.04,
        ("重商",     "重商"):     +0.05,
        ("扩张主义", "和平主义"): -0.04,
        ("保守",     "稳健"):     +0.03,
        ("嗜战",     "和平主义"): -0.08,
        ("善谈判",   "重商"):     +0.04,
    }
    total = 0.0
    for trait_a in pa:
        for trait_b in pb:
            key = tuple(sorted([trait_a, trait_b]))
            total += COMPAT.get(key, 0.0)
    return max(-0.15, min(0.15, total))
```

---

## 11. 战争解算（worldsim_combat.py）

> 参考来源：`RomanTsisyk/multi-agent-simulation-engine` combat formula
> + `xe-nvdk/ai-war-games` terrain modifiers
> + `ben9583/civilization-simulator` stability collapse

### 11.1 战斗公式

```python
async def resolve_monthly_combat(war: War, is_winter: bool, db_session) -> CombatResult:
    """每个Tick对每场进行中的战争执行一次月度结算"""

    attacker = await get_nation(war.attacker_id, db_session)
    defender = await get_nation(war.defender_id, db_session)

    # is_winter由完整Tick局部上下文传入；冬季行军修正不写入WorldState。
    # ── 基础战斗力 ──
    atk_power = (attacker.army_size
                 * attacker.army_quality
                 * morale_modifier(attacker.morale))

    def_power = (defender.army_size
                 * defender.army_quality
                 * morale_modifier(defender.morale)
                 * home_terrain_bonus(war.current_front_hex, defender.id))

    # ── 地形修正（借鉴ai-war-games）──
    TERRAIN_MODIFIERS = {
        "MOUNTAIN": {"defense": 1.5, "attack": 0.7},
        "FOREST":   {"defense": 1.2, "attack": 0.9},
        "PLAIN":    {"defense": 1.0, "attack": 1.0},
        "RIVER":    {"defense": 1.3, "attack": 0.8},  # 守河易攻河难
        "COAST":    {"defense": 1.0, "attack": 1.1},
    }

    # ── 补给线修正 ──
    distance_to_capital = hex_distance(
        war.current_front_hex,
        get_capital_hex(attacker.id, db_session)
    )
    supply_modifier = max(0.4, 1.0 - distance_to_capital * 0.04)
    atk_power *= supply_modifier

    # ── 工事加成 ──
    front_hex = get_hex(war.current_front_hex, db_session)
    def_power *= (1 + front_hex.fortification * 0.5)

    # ── 月度伤亡（v2.5闭环：战死同步减少职业/征召分层和pop_adults）──
    exchange_ratio = atk_power / max(def_power, 1)
    atk_casualties = int(defender.army_size * 0.02 * (1 / exchange_ratio))
    def_casualties = int(attacker.army_size * 0.02 * exchange_ratio)

    atk_casualties = min(atk_casualties, attacker.army_size // 10)
    def_casualties = min(def_casualties, defender.army_size // 10)

    def apply_casualties(nation, casualties):
        """优先减pop_conscripts，再减pop_warriors，同步减pop_adults"""
        conscript_dead = min(casualties, nation.pop_conscripts)
        warrior_dead   = min(casualties - conscript_dead, nation.pop_warriors)
        total_dead     = conscript_dead + warrior_dead
        nation.pop_conscripts -= conscript_dead
        nation.pop_warriors   -= warrior_dead
        nation.pop_adults     -= total_dead       # 同步减成年人口
        nation.army_size       = nation.pop_warriors + nation.pop_conscripts  # 重算

    apply_casualties(attacker, atk_casualties)
    apply_casualties(defender, def_casualties)
    war.attacker_casualties += atk_casualties
    war.defender_casualties += def_casualties

    # ── 士气损耗 ──
    attacker.morale -= atk_casualties / attacker.pop_total * 0.5
    defender.morale -= def_casualties / defender.pop_total * 0.5

    # ── war_score更新 ──
    war.war_score += (def_casualties - atk_casualties) / 5000
    war.war_score = max(-1.0, min(1.0, war.war_score))

    # ── 胜利条件检测 ──
    winner = check_victory(war, attacker, defender, db_session)

    # ── 粮食消耗（军队出征每月消耗额外粮食）──
    attacker.stock_food -= attacker.army_size // 50
    defender.stock_food -= defender.army_size // 100  # 守方消耗少一半

    return CombatResult(
        war=war,
        atk_casualties=atk_casualties,
        def_casualties=def_casualties,
        winner=winner,
        events=build_combat_events(war, atk_casualties, def_casualties)
    )

def check_victory(war, attacker, defender, db_session) -> Optional[str]:
    """
    胜利条件（任一满足）：
    1. 对方首都被攻占（capital hex.nation_id被改变）
    2. 对方army_size < 500
    3. 对方stability < 0.10（内部崩溃，参考ben9583/civilization-simulator）
    4. 对方stock_food < 0 连续3个月（断粮）
    5. 主动求和（request_ceasefire政策）
    """
```

### 11.2 战争对内政的反馈

```python
# 战争持续时间→国内稳定度惩罚
# 每月战争：stability -= 0.01（进攻方） / 0.005（防守方）
# 战败：stability -= 0.15（单次）, prestige -= 0.20
# 战胜：morale += 0.10, prestige += 0.15
# 割地和平：后续文化系统启用后，通过HexCulture批量SQL重置/混合文化成分；禁止访问不存在的cultural_composition字段。
```

### 11.3 战争疲惫（v2.7新增，worldsim_combat.py）

```python
def update_war_exhaustion(nation, db_session):
    """
    每个参战月 war_exhaustion += 0.02（Step 8执行）。
    war_score偏向己方时疲惫增速慢；逆境时疲惫增速快。
    和平后每月自然恢复：war_exhaustion -= 0.03（比积累快）。
    """

    # 非战争状态：自然恢复
    if not nation.at_war_with:
        nation.war_exhaustion = max(0.0, nation.war_exhaustion - 0.03)
        return

    # 战争疲惫的下游效果（在update_faction_approvals中读取）：
    # war_exhaustion > 0.3 → faction_commoners -= 0.02/月（平民厌战）
    # war_exhaustion > 0.5 → faction_military -= 0.01/月（军队也厌战）
    # war_exhaustion > 0.7 → LLM prompt注入"[战争疲惫极度严重]"警告
    #                         LLM倾向主动提出停火/割地

    # 冬季效果（is_winter=True）：
    # 进攻方 war_exhaustion += 0.04（冬季行军额外疲惫）
    # 防守方 war_exhaustion += 0.01（守城相对轻松）

    # 战争疲惫注入LLM USER_PROMPT的字段：
    # 【当前战争疲惫】{war_exhaustion:.0%}（{疲惫描述}）
    # 描述映射：<30%="军队士气尚可" 30-60%="厌战情绪蔓延" 60-85%="民心动摇" >85%="国家难以为继"
```

---

## 12. 内部派系政治（worldsim_politics.py）

> 参考来源：`ShiJbey/minerva` 效用驱动决策
> + `ianlintner/forum` 关系网络衰减
> + `TheApexWu/psychohistoryML` 历史规律（暴力传染、精英过度生产）

```python
async def update_faction_approvals(nation, db_session):
    """
    每月更新三大派系支持度。
    这些值直接影响stability，并作为LLM prompt的输入。
    """

    # ── 贵族派系（faction_nobles）──
    # 受：税率（高税损贵族）、土地政策、中央集权程度
    tax_noble_penalty = max(0, nation.tax_rate - 0.15) * 0.5
    nation.faction_nobles -= tax_noble_penalty

    # 精英过度生产警告（历史规律：贵族人口>8%触发内耗）
    noble_ratio = nation.pop_nobles / max(nation.pop_total, 1)
    if noble_ratio > 0.08:
        nation.faction_nobles -= 0.01  # 贵族争权内耗
        emit_event("POLITICAL", "WARNING",
                   f"{nation.name}贵族阶层过度膨胀，内部权力争夺加剧", [nation.id])

    # ── 军事派系（faction_military）──
    # 受：军费比例、战争胜败、军队规模
    # v2.3修正：原 army_size × 50 / gdp_monthly 单位不一致
    # 正确公式使用Section 3.5定义的函数
    ratio = army_budget_ratio(nation.army_size, nation.gdp_monthly)
    # 验算：军事国 25000×0.02/2000=0.25（高线），农业国 5000×0.02/1800=0.056（低线）
    if ratio < 0.10:
        nation.faction_military -= 0.02   # 军费不足，军方不满
    if ratio > 0.25:
        nation.faction_military += 0.01   # 军费充足，军方满意

    # ── 平民派系（faction_commoners）──
    # 受：粮食储备月数、税率
    # v2.3修正：原 pop_total × 0.5 与粮食单位定义矛盾
    food_months = nation.stock_food / max(monthly_food_consumption(nation.pop_total), 1)
    if food_months < 1.0:
        nation.faction_commoners -= 0.05  # 食物不足，民心大失
    elif food_months > 6.0:
        nation.faction_commoners += 0.01  # 粮食充裕，民心稳定
    nation.faction_commoners -= max(0, nation.tax_rate - 0.20) * 0.3

    # ── 暴力传染（psychohistoryML历史规律）──
    # 暴力清洗/处决后coup_multiplier增加，稳定度长期承压
    nation.coup_multiplier = max(1.0, nation.coup_multiplier * 0.95)  # 每月自然衰减5%

    # ── 派系震荡阻尼（v2.1 Gemini建议）────────────────────────────
    # 问题：land_reform等政策单月可导致faction_nobles -0.15，LLM连续两月
    #       选择打击贵族政策会直接触发noble_revolt，涌现变成死循环。
    # 修复：无论本月政策如何叠加，每个派系单月净变化绝对值不超过 FACTION_CHANGE_CAP
    FACTION_CHANGE_CAP = 0.12  # 单月任意派系支持度最大变动幅度

    for attr in ["faction_nobles", "faction_military", "faction_commoners"]:
        prev = getattr(nation, f"_prev_{attr}", getattr(nation, attr))
        curr = getattr(nation, attr)
        delta = curr - prev
        if abs(delta) > FACTION_CHANGE_CAP:
            clamped = prev + (FACTION_CHANGE_CAP if delta > 0 else -FACTION_CHANGE_CAP)
            setattr(nation, attr, clamped)
    # 注意：worldsim_engine在Step 6开始时需保存各派系初始值到 _prev_faction_* 临时变量
    # ───────────────────────────────────────────────────────────────

    # ── 稳定度计算 ──
    raw_stability = (nation.faction_nobles   * 0.35
                   + nation.faction_military * 0.35
                   + nation.faction_commoners * 0.30)

    # 暴力传染系数压低稳定度上限
    stability_cap = 1.0 / nation.coup_multiplier
    nation.stability = min(raw_stability, stability_cap)

    # ── 三派系硬边界约束（阻尼之后再做范围裁剪）──
    for attr in ["faction_nobles", "faction_military", "faction_commoners"]:
        val = getattr(nation, attr)
        setattr(nation, attr, max(0.05, min(1.0, val)))
```

### 12.5 合法性系统（v2.7新增，⚠️ Phase 2冻结）

> **v2.8冻结说明**：字段已加入Nation模型（legitimacy字段），第一阶段初始值固定不变。
> update_legitimacy()函数**不在第一阶段实现**，等里程碑三完成后接入。
> 冻结原因：合法性、技术和债务需要独立验收；本文件已将合法性月度衰减改为合法Python表达式。

```python
def update_legitimacy(nation, db_session):
    """
    合法性（legitimacy）与稳定度（stability）分离的第二政治维度。
    stability = 民心（三派系是否支持）
    legitimacy = 统治者继承的神圣授权感知

    两者完全独立：
    - 暴君可以高stability低legitimacy（民众被压制但统治者不被认为合法）
    - 仁君可以高legitimacy低stability（大家认为他有权统治，但内政很乱）
    """

    # ── 合法性自然衰减（统治时间越长，合法性需要周期性刷新）──
    nation.legitimacy -= 0.003  # 每月-0.003，约28年衰减到0

    # ── 合法性来源（加法项）──
    # 军事胜利（每次）：       +0.08
    # 大型祭祀/宗教仪式：      +0.05（hold_grand_ceremony政策）
    # 还清债务：               +0.02（守信用）
    # 颁布法典（one-time）：   +0.10
    # 联姻（每次成功）：       +0.06

    # ── 合法性损耗（减法项）──
    # 暴力继承（政变/刺杀）：  → 立即设为0.35
    # 战败割地：               -0.10
    # 饥荒连续2月：            -0.05/月
    # 贵族叛乱平定（镇压胜）： -0.03（强硬但有效）
    # 贵族叛乱平定（失败）：   -0.15

    # ── 合法性效果 ──
    if nation.legitimacy < 0.40:
        # 低合法性：所有稳定度政策效果×0.5
        # 征税容易触发叛乱（阈值降低30%）
        # LLM prompt注入"[统治合法性动摇]"警告
        nation._legitimacy_penalty = True

    if nation.legitimacy > 0.80:
        # 高合法性：解锁特殊政策选项
        # - 宣布神圣战争（declare_holy_war，比普通宣战prestige损耗更低）
        # - 强制人口迁移（不触发正常的morale惩罚）
        # - 超高税率（tax_rate可超过0.35而不立即引发事件）
        nation._high_legitimacy_bonus = True

    # ── 军事政权的legitimacy依赖 ──
    # 军事国leader_personality含"荣誉至上"时：
    # 每月未发生战争或重大军事行动：legitimacy -= 0.01（和平让强人失去存在感）
    if "荣誉至上" in json.loads(nation.leader_personality):
        if not nation.at_war_with and nation.war_exhaustion == 0:
            nation.legitimacy -= 0.01

    nation.legitimacy = max(0.05, min(1.0, nation.legitimacy))
```

### 12.6 技术积累系统（v2.7新增，⚠️ Phase 2冻结，新建 worldsim_tech.py）

> **v2.8冻结说明**：tech_points/tech_unlocked字段已加入Nation模型，初始值固定。
> accumulate()函数和TECH_THRESHOLDS效果执行**不在第一阶段实现**。
> 等里程碑二完成后接入，届时技术解锁效果需逐一对应Section 20状态归属表。

```python
TECH_THRESHOLDS = {
    # (解锁阈值, 技术键, 显示名, 效果描述)
    50:  ("iron_tools",      "铁制农具",   "所有农业格fertility+0.08，resource_food+10%"),
    100: ("written_law",     "成文法典",   "颁布法典政策稳定度效果×2，legitimacy+0.10"),
    180: ("iron_smelting",   "铸铁技术",   "铁矿monthly_yield+40%，army_quality上限提升至0.90"),
    280: ("irrigation",      "系统灌溉",   "解锁大规模水利工程建设（dig_canal效果×1.5）"),
    400: ("currency_system", "货币经济",   "贸易路线效率+25%，stock_gold月产+20"),
    550: ("military_drill",  "军事操典",   "army_quality每月自然提升+0.002，征兵后combat_ready更快"),
    720: ("bureaucracy",     "官僚制度v2", "已有官僚制度国家：税收效率+15%，stability上限提升至0.95"),
}

async def accumulate(nation, db_session):
    """后续完整Tick启用后执行"""

    # ── 技术点积累 ──
    # 工匠比例越高积累越快（工艺进步的历史驱动力）
    craftsman_ratio = nation.pop_craftsmen / max(nation.pop_adults, 1)
    base_gain = 0.5 + craftsman_ratio * 2.0   # 0.5–2.5点/月

    # 贸易加成（沿贸易路线接触他国技术）
    active_routes = count_active_routes(nation.id, db_session)
    trade_bonus = active_routes * 0.15

    # 学堂加成
    school_bonus = 0.3 if "学堂" in get_buildings(nation.id, db_session) else 0.0

    # 老人传承
    elder_bonus = nation.elder_tech_bonus

    nation.tech_points += base_gain + trade_bonus + school_bonus + elder_bonus

    # ── 技术解锁检测 ──
    unlocked = json.loads(nation.tech_unlocked)
    for threshold, (key, name, effect_desc) in TECH_THRESHOLDS.items():
        if nation.tech_points >= threshold and key not in unlocked:
            unlocked.append(key)
            nation.tech_unlocked = json.dumps(unlocked)
            # 触发WorldEvent
            create_world_event(
                "ECONOMIC", "INFO",
                f"{nation.name}掌握了{name}",
                f"效果：{effect_desc}",
                [nation.id]
            )
            # 技术沿贸易路线向接触国家扩散（每月10%概率传给相连国家）
            await propagate_tech(nation.id, key, db_session)
```

### 12.7 债务与信贷处理（v2.7新增，⚠️ Phase 2冻结，worldsim_economy.py）

> **v2.8冻结说明**：debt/debt_interest_rate/debt_creditor字段已加入Nation模型。
> process_debt()函数和request_loan/offer_loan政策**第一阶段不实现**。
> 冻结原因：需要PendingProposal新增LOAN类型和接受/拒绝执行链，等里程碑二后实现。

```python
async def process_debt(nation, db_session):
    """后续完整Tick启用后：扣除债务利息，检测违约"""

    if nation.debt <= 0:
        return

    # 月度利息扣除
    interest = nation.debt * nation.debt_interest_rate
    nation.stock_gold -= interest

    # 利息流向债权国
    creditor = get_nation(nation.debt_creditor, db_session)
    if creditor:
        creditor.stock_gold += interest
        # 写入ResourceFlowLedger（gold来源追踪）

    # 违约检测
    if nation.stock_gold < -500:
        # 无力偿还：触发违约事件
        create_world_event(
            "ECONOMIC", "CRITICAL",
            f"{nation.name}发生债务违约",
            f"国库严重亏空，债权国{creditor.name if creditor else '未知'}提出强制索赔",
            [nation.id, nation.debt_creditor]
        )
        # 债权国LLM下月收到违约通知，可选择：
        # - 宽限（target_relation+0.10，但prestige-0.05）
        # - 索要割地/赔款（major_action）
        # - 宣战（declare_war）
```

---

## 13. LLM 调用规范（worldsim_llm.py）

### 13.1 System Prompt 模板

```python
SYSTEM_PROMPT = """
你是{nation_name}的最高统治者{leader_name}。
这是一个古代世界模拟，时间约公元前{year}年{month}月。
你的性格特征：{personality}
你的长期执政目标：{leader_goal}

当前内部局势：
- 贵族派系支持度：{faction_nobles:.0%}
- 军方支持度：{faction_military:.0%}
- 平民支持度：{faction_commoners:.0%}

你必须以JSON格式返回本月决策，不得输出任何其他内容。
选择2到6项政策，严格遵守：
1. 不能选超出当前资源承受范围的政策
2. 同一互斥组内不能同时选择
3. major_action每月最多1个
4. 决策须符合你的性格、长期目标，并考虑派系稳定

返回格式：
{
  "decisions": [
    {
      "action_key": "policy键名（必须是POLICIES字典中存在的键）",
      "target_nation_id": "目标国ID或null",
      "intensity": 0.0到1.0之间的浮点数,
      "reasoning": "一句话内部推理"
    }
  ]
}
"""

USER_PROMPT = """
═══ 当前状态（第{year}年{month}月）═══

【执政记忆摘要】
{memory_summary}

【本国状况】
{nation_status_json}

【合法性与疲惫】
统治合法性：{legitimacy:.0%}（{legitimacy_desc}）
战争疲惫：{war_exhaustion:.0%}（{exhaustion_desc}）
当前债务：{debt:.0f}金（利息：每月{debt_interest:.0f}金）

【已解锁技术】{tech_unlocked_names}

【已知情报】（freshness<0.5表示情报陈旧）
{intel_json}

【本月事件】
{events_json}

【当前战争】
{wars_json}

【贸易路线】
{trade_routes_json}

【外交关系评分】（-1.0极度敌对 → 1.0极度友好）
{relations_json}

【待回应提案】
{pending_proposals_json}

【可选政策】
{available_policies_json}

请选择本月政策。
"""
```

### 13.2 调用参数与 Fallback 规则

```python
LLM_CONFIG = {
    "model": "deepseek-chat",
    "max_tokens": 1000,
    "temperature": 0.75,            # 保留随机性，产生涌现
    "response_format": {"type": "json_object"},
    "timeout": 25,                  # v2.1：从30秒收紧至25秒
}

# ── Fallback 规则（v2.1新增）──────────────────────────────────
# 单次Tick的LLM调用失败不得阻塞整个Tick推进。
# 执行策略：

MAX_RETRIES = 2                     # 超时或非法JSON时最多重试2次
RETRY_DELAY = 2                     # 重试间隔秒数

FALLBACK_DECISION = {
    # 所有重试均失败后，该国本月执行此默认决策（不阻塞Tick）
    "decisions": [
        {
            "action_key": "hold_court",      # 空决策：休养生息
            "target_nation_id": None,
            "intensity": 0.5,
            "reasoning": "[LLM_FALLBACK] 本月无决策，休养生息"
        }
    ]
}

# hold_court 是隐式内置政策（不在POLICIES字典中，无需验证）：
# effect: {} — 什么都不做，仅记录日志
# status: "FALLBACK"（区别于APPROVED/REJECTED）

# 并发失败处理：
# asyncio.gather 使用 return_exceptions=True
# 对每个结果单独检查是否为 Exception，失败则用 FALLBACK_DECISION 替代
# Tick继续正常推进，失败国仅本月无决策

# 费用控制：
# 每Tick最多 4次主调用 + 4×2次重试 = 最多12次LLM调用
# DeepSeek V4约 $0.001/次，单Tick最多 ~$0.012，可接受
```

### 13.3 记忆压缩（每5Tick执行一次）

```python
async def compress_memory(nation, db_session):
    """
    每5个月对每国执行一次记忆压缩，防止prompt过长。
    调用LLM将过去5月的事件日志压缩为memory_summary。
    """

    # ⚠️ v2.1 Gemini建议修复：压缩prompt必须强制保留定量信息
    # 原问题：LLM压缩后"割让了hex 60_40"变成"曾割地求和"，
    #         下次决策时LLM无法知道具体丢失了哪块领土。

    COMPRESS_PROMPT = """
    以下是{nation_name}过去5个月的执政记录：
    {recent_events_json}

    请用150字以内做执政摘要，必须严格保留以下定量信息（如有发生）：
    1. 涉及的其他国家名称（不得用代称）
    2. 具体数字条约（例："向铁鹰帝国赔款500金"，不能写"赔偿了一笔钱"）
    3. 割让或获得的具体格子ID（例："割让hex 60_40、61_40"，不能写"割地"）
    4. 战争胜败结果及伤亡数字
    5. 缔结或废除的协议类型（同盟/联姻/贸易协定）

    输出格式：纯文本，不要JSON，不要标题，不要换行符。
    """

    # 压缩结果写入 nation.memory_summary（覆盖上次摘要）
    # 下次压缩时，将 memory_summary + 新5月事件 一起作为输入
    # 这样摘要具有累积性，不会完全遗忘5个月前的关键事件
```

### 13.4 情报时效衰减

```python
# known_intel 结构（每条情报含freshness字段）
{
  "merchant": {
    "army_size": 3000,
    "stability": 0.82,
    "freshness": 0.64,       # 每月×0.80，<0.3时prompt中注明"[情报陈旧]"
    "last_updated_month": 3
  }
}
# send_scouts政策触发 → 目标国freshness重置为1.0，数据刷新为当前真实值
```

---

## 14. 事件系统（worldsim_events.py）

> 当前里程碑只实现 M1 事件。所有事件通过 `event_handlers` 调用语义执行器，禁止直接写入职业人口、`army_size` 或可溯源资源库存。

```python
M1_RANDOM_EVENTS = [
    {
        "key": "bumper_harvest",
        "prob": 0.05,
        "season": "AUTUMN",
        "handler": "apply_harvest_bonus",
        "parameters": {"food": 500, "morale": 0.05},
        "label": "丰年大收",
    },
    {
        "key": "bandit_raid",
        "prob": 0.03,
        "handler": "apply_bandit_raid",
        "parameters": {"gold": 200, "food": 150, "morale": -0.03},
        "label": "山贼劫掠",
    },
    {
        "key": "natural_iron_vein",
        "prob": 0.01,
        "handler": "create_natural_resource_deposit",
        "parameters": {"resource_type": "IRON", "placed_by_player": False},
        "label": "发现天然铁矿",
    },
]

M1_THRESHOLD_EVENTS = [
    {
        "key": "famine_crisis",
        "condition": "stock_food < 0",
        "handler": "emit_famine_warning",
        "label": "粮食告急",
    },
    {
        "key": "gold_bankruptcy",
        "condition": "stock_gold < 0 and pop_conscripts > 0",
        "handler": "disband_conscripts_for_budget",
        "parameters": {"max_count": 1000},
        "label": "国库告罄，被迫裁军",
    },
]

# 里程碑三以后才可启用：瘟疫、贵族叛乱、政变、刺杀、难民、战争阈值。
# 启用时必须分别调用：apply_noncombat_adult_loss()、transfer_workforce()、
# apply_casualties()或外交/政治专用执行器，禁止把effect字典直接setattr到Nation。
```

---

## 15. API 端点（main.py）

```
# 世界状态
GET  /api/world/state                          # 完整世界状态快照
GET  /api/world/nations                        # 四国摘要
GET  /api/world/nation/{id}                    # 单国详情（含派系/人口/情报）
GET  /api/world/map                            # 全量hex数据（fog过滤）
GET  /api/world/map/culture                    # 文化成分叠加层数据

# 事件与历史
GET  /api/world/events?page=1&limit=50         # 历史事件流（分页）
GET  /api/world/events/stream                  # SSE：实时事件推送
GET  /api/world/replay/{tick_number}           # 回放某Tick快照

# 贸易与外交
GET  /api/world/trade-routes                   # 所有贸易路线（含status）
GET  /api/world/relations                      # 6对双边关系评分矩阵
GET  /api/world/wars                           # 当前战争列表

# 决策记录
GET  /api/nation/{id}/decisions/{year}/{month} # 某国某月决策+验证结果
GET  /api/nation/{id}/memory                   # 某国记忆摘要

# Tick控制
POST /api/world/tick                           # 手动推进一个月（核心端点）
POST /api/world/reset                          # 重置世界（开发用）
POST /api/world/pause                          # 暂停/恢复（未来自动tick用）
```

---

## 16. 地图规格（worldsim_terrain.py）

```python
MAP_CONFIG = {
    "cols": 120,
    "rows": 80,
    "total_cells": 9600,       # 每格≈10km²，总面积约韩国量级

    # 初期激活区域
    "initial_active_radius": 25,   # 地图中心半径25格为ACTIVE
    # 其余UNKNOWN，随领土扩张解锁（控制的hex周围2格变KNOWN）

    # 地形生成（Perlin噪声分层）
    "noise_layers": {
        "elevation": {"scale": 0.03, "octaves": 4},
        "moisture":  {"scale": 0.05, "octaves": 2},
        "iron_ore":  {"scale": 0.08, "octaves": 1},
    },

    # 地形判定规则
    "terrain_rules": {
        # elevation > 0.75 → MOUNTAIN
        # elevation > 0.55 and moisture > 0.6 → FOREST
        # elevation < 0.15 → COAST
        # moisture > 0.75 and elevation 0.2-0.5 → RIVER
        # else → PLAIN
        # elevation < 0.05 → 不可穿越（深水）
    },

    # 四国初始领土（地图分区，各有自然边界）
    "nation_zones": {
        "agrarian": {"region": "west",   "desc": "西部平原，高肥力，50%以上PLAIN"},
        "merchant": {"region": "center", "desc": "中部河流三角洲，RIVER格最多"},
        "military": {"region": "north",  "desc": "北部山地，MOUNTAIN多，铁矿集中"},
        "balanced": {"region": "east",   "desc": "东部混合地形"},
    },

    # 初始文化成分：各国领土内格子默认100%本国文化
    # 边境格设为70%本国/30%邻国（写入HexCulture表，非HexCell字段）
}
```

### 16.1 Canvas 渲染规范（HexMap.tsx）

> **架构原因**：9600格若全量渲染，Chrome单帧绘制时间超过16ms（60fps上限），
> 导致交互卡顿。必须实现视口裁剪，只渲染屏幕可见区域。

```typescript
// HexMap.tsx 渲染约束（v2.1新增，必须遵守）

// ── 视口状态 ──
interface Viewport {
  offsetX: number      // 地图平移量（像素）
  offsetY: number      // 地图平移量（像素）
  scale: number        // 缩放比例，范围 0.3–3.0
}

// ── 六边形尺寸 ──
const HEX_BASE_SIZE = 24   // px，100%缩放时的hex半径

// ── 渲染裁剪规则 ──
// 每帧只渲染满足以下条件的hex：
//   hex屏幕坐标X ∈ [-HEX_BASE_SIZE, canvasWidth + HEX_BASE_SIZE]
//   hex屏幕坐标Y ∈ [-HEX_BASE_SIZE, canvasHeight + HEX_BASE_SIZE]
// 边缘缓冲1格，防止移动时出现边缘空白

// ── LOD（细节层级）规则 ──
// scale >= 1.0：完整渲染（边框+地形色+文化叠加色+图标）
// scale 0.5–1.0：省略图标，保留地形色+文化叠加色
// scale < 0.5：仅渲染色块（不绘制hex边框线，大幅提升性能）
// fog=UNKNOWN：只渲染纯黑色块，跳过所有计算

// ── 交互事件 ──
// onWheel → scale变化（deltaY × -0.001，clamp到0.3–3.0）
// onMouseDown + onMouseMove → offsetX/Y平移
// onClick → 选中hex，右侧面板显示详情

// ── 文化叠加色 ──
// 每个hex颜色 = lerp(地形基础色, 控制国颜色, 0.4)
// 文化成分从 HexCulture 表批量获取，不要逐格请求API
// GET /api/world/map/culture 一次性返回所有ACTIVE格的文化数据

// ── 性能目标 ──
// 视口内格子通常约 300–600 个（取决于缩放级别）
// 目标：每帧渲染时间 < 8ms（在普通笔记本上）
```

---

## 17. 开源代码参考表（Codex 使用）

> 所有参考代码只用于理解算法和架构；不得整体复制。每次引用前确认许可证与具体实现一致。

| 来源 | 参考内容 | 本项目的适配要求 |
|---|---|---|
| `CodeByBryant/Sovereign` | Perlin 地形、资源分布 | 用 Python 重写；只保留生成思想。 |
| `Greal-dev/unciv-warfare-economics-evolution` | 文化成分与叛乱 | 改为 HexCulture 独立表与批量 SQL。 |
| `rofergon/Theron-hex-lands` | 饥荒、出生率、生命周期 | 改为人口 cohort，不创建个体 agent。 |
| `ShiJbey/minerva` | 派系效用与叛乱 | 改为 faction 数值，不复制实现。 |
| `ianlintner/forum` | 关系衰减与事件记忆 | 适配为 DiplomaticRelation.historical_events。 |
| `VSAnimator/catan_test` | 引擎/API 分层 | 只参考模块边界。 |
| `TheApexWu/psychohistoryML` | 参数化历史规律 | 仅作为可调参数来源。 |

---

## 18. 环境变量（.env.example）

```env
# LLM配置
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./worldsim.db

# 模拟参数
TICK_AUTO=false                  # 手动推进
INITIAL_YEAR=500                 # 公元前500年开始
WORLD_SEED=42                    # 地形随机种子（固定可复现）

# 开发
DEBUG=true
CORS_ORIGINS=http://localhost:5173
LOG_LLM_PROMPTS=false            # true时记录完整LLM输入输出到文件
SNAPSHOT_RETAIN_TICKS=100        # 保留最近N个Tick的快照，超出自动清理
```

---

## 19. Codex 任务清单（本次只执行里程碑一 + 权限层级1）

```text
Step 1:  建立第2节标为[M1]的目录与文件；不得创建[后续]文件。

Step 2:  worldsim_models.py
         在唯一模型文件中定义第3节全部模型；本次只迁移、读写和测试M1需要的
         HexCell、Nation、Settlement、TradeRoute、PolicyAction、WorldEvent、WorldState、
         ResourceDeposit、ResourceFlowLedger、InterventionRecord、CausalLink。
         每个table模型必须有主键；Nation六类职业之和必须等于pop_adults。
         初始化 stock_iron_sources/stock_stone_sources/stock_wood_sources 为FIFO批次列表。

Step 3:  worldsim_db.py
         使用 SQLModel + AsyncSession + sqlite+aiosqlite；建表、session依赖、事务边界、索引。
         必建索引：HexCulture（后续保留）、ResourceFlowLedger(nation_id,tick_number)、
         ResourceDeposit(hex_id,developed_by)。

Step 4:  worldsim_terrain.py 与 worldsim_init.py
         生成120×80六边形地图、初始化四国、首都、资源、初始FIFO来源批次与贸易候选路径。
         初始化后断言：army_size == pop_warriors + pop_conscripts；
         六类职业总和 == pop_adults。

Step 5:  worldsim_economy.py
         实现基础资源采集、唯一食物消耗入口、税收、军费；实现
         add_resource_batch() / consume_resource_fifo() / transfer_resource_batches_fifo()。
         实现开发资源点：farmers → extractors；月产出、储量、木材按max_reserves再生、
         资源枯竭/放弃时extractors → farmers；每次流入/流出写ResourceFlowLedger。

Step 6:  worldsim_trade.py
         实现无硬编码的盈余/短缺撮合。IRON/STONE/TIMBER贸易必须逐批转移FIFO来源。

Step 7:  worldsim_policies.py 与 worldsim_validator.py
         仅启用 PHASE_1_POLICY_KEYS；规则AI只从该集合选择。
         实现第20节语义执行器；任何验证失败均不改变世界状态。

Step 8:  worldsim_events.py
         只实现第14节M1事件与阈值事件；禁止直接setattr职业人口或army_size。

Step 9:  worldsim_worldwill.py
         实现权限层级1：铁矿、石材、木材、肥沃土地、水源。
         POST /intervene 同步执行即时可见；远方发现由Tick处理。
         只有IRON/STONE/TIMBER生成ResourceDeposit；肥沃土地和水源直接修改HexCell并写InterventionRecord。
         实现因果链：来源批次 → 账本 → WorldEvent → CausalLink。

Step 10: worldsim_engine.py
         严格实现第6节当前Tick；不得导入LLM、society、culture、politics、combat、tech模块。

Step 11: main.py 与前端M1组件
         完成第15节M1端点、地图、国家面板、事件流、Tick控制、世界意志工具栏、配置面板、因果时间轴。

Step 12: 联调测试A（Tick × 3）
         ✓ 贸易在资源差异下自然产生
         ✓ 每笔IRON/STONE/TIMBER流入、消耗、转出均有FIFO来源与账本
         ✓ 四国职业与军队不变量始终成立

Step 13: 联调测试B（放置铁矿）
         ✓ 控制该格国家在POST /intervene返回前收到自然事件
         ✓ 规则AI可选择develop_resource_deposit；farmers减少100，extractors增加100
         ✓ 下月起铁库存增长、来源批次与账本保留deposit_id
         ✓ GET /api/world/intervention/{id}/chain可返回可验证链条

Step 14: 性能测试
         ✓ 本地Tick（无LLM）<1秒
         ✓ 视口内地图绘制<8ms

停止条件：完成Step 14后停止，不得提前实现里程碑二至五。
```

---

## 20. 政策与事件的语义执行契约（v2.9）

> `POLICIES.effect` 只用于描述效果，不能被通用 `setattr` 直接应用。
> 所有会破坏不变量、需要批量地图更新或需要来源追踪的变化，必须映射到以下语义执行器。

```text
语义执行器                         允许改变的状态
──────────────────────────────────────────────────────────────────────────
add_resource_batch()               stock_iron/stone/wood + 对应FIFO来源批次 + ResourceFlowLedger
consume_resource_fifo()            对应库存与FIFO来源批次 + ResourceFlowLedger outflow
transfer_resource_batches_fifo()   双方库存批次 + 双方账本；保持原source_id/source_type/acquired_tick
transfer_workforce()               六类职业之间的内部转移；pop_adults不变
assign_extractors_to_deposit()     farmers → extractors；workers_assigned增加
release_deposit_workers()          extractors → farmers；workers_assigned归零
apply_immigration()                pop_adults变化后调用rebalance_workforce()
apply_noncombat_adult_loss()       pop_adults变化后调用rebalance_workforce()
apply_casualties()                 conscripts/warriors与pop_adults同步减少；重算army_size
apply_owned_plain_fertility()      批量更新本国PLAIN HexCell.fertility
apply_owned_food_yield_modifier()  批量更新本国PLAIN HexCell.resource_food
apply_border_fortification()       批量更新边境HexCell.fortification
apply_capital_fortification()      更新首都HexCell.fortification
apply_road_project()               更新Nation.road_level与指定路径效果
create_resource_deposit()          仅IRON/STONE/TIMBER；写InterventionRecord与发现事件
create_natural_resource_deposit()  自然事件专用；placed_by_player=False
```

### 20.0 成本扣除规则

```text
政策或建设成本中的IRON / STONE / TIMBER必须使用consume_resource_fifo()，
并在ResourceFlowLedger写出purpose=对应政策键名。FOOD与GOLD可直接扣库存，
但必须在PolicyAction.effects_applied记录数额。
```

### 20.1 明确禁止的通用直接写入

```text
army_size
pop_farmers / pop_craftsmen / pop_warriors / pop_nobles / pop_conscripts / pop_extractors
pop_adults（除apply_immigration/apply_noncombat_adult_loss/apply_casualties）
stock_iron / stock_stone / stock_wood（除add/consume/transfer资源批次函数）
HexCulture百分比
```

### 20.2 第5节中旧效果键的映射

```text
stock_food_monthly          → apply_owned_food_yield_modifier()
fertility_avg               → apply_owned_plain_fertility()
storage_cap_food            → 指定Settlement.storage_cap
fortification_border        → apply_border_fortification()
fortification（首都）        → apply_capital_fortification()
army_speed                  → apply_road_project()
cultural_spread_rate        → 后续文化系统的Nation.culture_spread_bonus
resource_food_monthly       → apply_owned_food_yield_modifier()
pop_elders_bonus            → Nation.elder_tech_bonus（后续系统）
intel_freshness_target      → 后续情报JSON更新
neighbor_tension            → 后续DiplomaticRelation.historical_events
cultural_composition_foreign→ 后续文化系统专用；当前不得执行
```

### 20.3 当前可启用政策集合

```python
PHASE_1_POLICY_KEYS = {
    "raise_farm_tax",
    "lower_trade_tax",
    "open_market",
    "monopolize_iron_trade",
    "ban_food_export",
    "build_granary",
    "conscript_troops",
    "disband_troops",
    "train_elite_units",
    "build_fortifications",
    "stockpile_weapons",
    "build_roads",
    "repair_walls",
    "build_armory",
    "develop_resource_deposit",
}
```

其余政策保留为后续设计，不得在当前规则AI、Validator或前端可选列表出现。

---

## 21. 开发里程碑与世界意志权限（完整路线）

> 世界意志权限按**系统能力与验收结果**开放，不按游戏年份、玩家行为、神力值、冷却或任务解锁。\
> 本次 Codex 只实现里程碑一与权限层级1。后续四层已经在本规范中定义，等对应里程碑另行交付给 Codex 时实施。\
> 每次新层开放后，世界中所有存档立即可使用该层工具；国家只感知到自然、社会或政治事件，从不感知玩家。

### 21.1 权限开放的唯一机制

```text
WorldState.world_will_max_stage: int = 1

初始新世界 = 1。
当前后端只接受 tool.stage <= world_will_max_stage 的干预请求；前端只显示对应工具。

后续版本发布顺序：
1. 实现该层所需系统、数据迁移、事件处理器、AI/LLM输入与验收测试；
2. 对既有存档执行无损迁移与默认值初始化；
3. 运行该层的确定性模拟验收；
4. 将 world_will_max_stage 提升到对应层级；
5. 在世界事件流写入一条“世界意志权限层级已开放”的系统记录。

这只是开发版本开关，不是游戏内科技树。玩家不需要完成目标，不会失去已开放权限。
```

### 21.2 权限层级总表

| 权限层级 | 主题 | 必须完成的系统能力 | 开放版本 | 当前状态 |
|---|---|---|---|---|
| 1 | 物质资源 | 经济、资源点、工人、来源批次、因果链 | 里程碑一 | 本次实现 |
| 2 | 环境与生产 | 季节、区域状态、农业产出、路线通行、环境事件 | 里程碑二 | 仅定义 |
| 3 | 人口与生命 | 人口生命周期、迁徙、疾病、医疗、劳动力再平衡 | 里程碑三 | 仅定义 |
| 4 | 信息与文化 | 情报可信度、调查、文化扩散、宗教/思想实体 | 里程碑四 | 仅定义 |
| 5 | 政治与权力 | 派系、领袖、继承、合法性、叛乱、完整外交 | 里程碑五 | 仅定义 |

### 21.3 里程碑一：核心经济引擎 + 权限1（本次交付）

```text
包含：四国初始化、地形、资源采集/消耗、贸易、规则AI、政策验证、事件流、
      世界意志五种工具、资源开发、FIFO来源批次、因果链、地图与基础前端。
不包含：LLM、人口年龄层、文化、外交派系、战争、技术、合法性、债务。
验收：第19节Step 12–14全部通过。
```

### 21.4 里程碑二：环境与生产 + LLM/基础外交 + 权限2

```text
启用：worldsim_llm.py、季节/天气/区域状态系统、基础外交与路线通行状态。
LLM只在已验证合法的政策集合中选择；不得负责状态合法性。
权限2在第22.6全部验收通过后开放。
```

### 21.5 里程碑三：人口与生命 + 战争/外交完整系统 + 权限3

```text
启用：worldsim_society.py、worldsim_combat.py、迁徙、疾病、医疗、战争疲惫、和谈。
权限3在第22.7全部验收通过后开放。
```

### 21.6 里程碑四：信息与文化深层系统 + 权限4

```text
启用：worldsim_culture.py、HexCulture批量SQL、情报报告、调查与辟谣、宗教/思想实体、文化叛乱。
权限4在第22.8全部验收通过后开放。
```

### 21.7 里程碑五：政治与权力 + 技术/合法性/债务 + 权限5

```text
启用：worldsim_politics.py、领袖与继承、派系、合法性、叛乱/政变、技术、债务、完整外交。
权限5在第22.9全部验收通过后开放。
每个子系统必须独立验收后才接入完整Tick；不得同时无测试地批量启用。
```

## 22. 世界意志系统（v3.0，五层完整定义；本次只实施权限1）

> **设计纲领：玩家放下历史条件，国家自己写出后果。**
> 国家只感知自然事件，不感知玩家。没有冷却、神力、目标或胜负；玩家得到的是可核验的因果链。

### 22.1 权限层级1的严格边界

```text
当前可用工具：铁矿、石材、原始林、肥沃土地、水源。

IRON / STONE / TIMBER：创建ResourceDeposit，国家可发现、分配矿工开发、持续产出。
FERTILE_SOIL / SPRING：不创建ResourceDeposit，不进入develop_resource_deposit；
它们直接修改HexCell并写InterventionRecord与WorldEvent。

煤、铜、金及权限2–5工具仅为后续设计；当前不得显示、调用或创建相关库存字段。
```

### 22.2 当前数据模型（新增至 worldsim_models.py）

```python
class ResourceDeposit(SQLModel, table=True):
    """可被国家开发的实体资源点；当前只允许IRON/STONE/TIMBER。"""
    id: str = Field(primary_key=True)              # f"deposit_{tick}_{hex_id}"
    hex_id: str
    resource_type: str                             # IRON / STONE / TIMBER
    reserves: float
    max_reserves: float                            # 初始时等于reserves；TIMBER再生上限
    quality: float                                 # 0.0–1.0
    extraction_difficulty: float                   # 0.0–1.0，高值降低单位劳动力产出
    regen_rate: float = 0.0                        # TIMBER：每月恢复max_reserves的比例；矿物为0
    discovered_by: str = '[]'                      # JSON nation id列表
    developed_by: Optional[str] = None
    development_level: int = 0                     # 0未开发 / 1初级；M1只允许0或1
    depleted: bool = False
    placed_by_player: bool = True
    placed_tick: int
    placed_year: int
    placed_month: int
    workers_assigned: int = 0                      # 同步等于Nation.pop_extractors中分配至该点的份额
    monthly_yield: float = 0.0                     # 由recalculate_deposit_yield()写入
    source_intervention_id: Optional[str] = None

# 产量：
# required_workers = 100 * (1 + extraction_difficulty)
# labor_modifier = min(1.0, workers_assigned / required_workers)
# base = {IRON: 0.5, STONE: 0.8, TIMBER: 1.2}[resource_type]
# monthly_yield = workers_assigned * base / (1 + extraction_difficulty) * quality
#                 * labor_modifier * (1 + nation.road_level * 0.15)
# TIMBER再生：reserves = min(max_reserves, reserves + max_reserves * regen_rate)
# reserves<=0时：depleted=True，release_deposit_workers()将对应矿工归还为农民。


class ResourceFlowLedger(SQLModel, table=True):
    """每个资源来源批次的流入或流出记录。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    tick_number: int
    nation_id: str
    resource_type: str                             # IRON / STONE / TIMBER
    source_id: str                                 # deposit_xxx / natural / 其他原始来源标识
    source_type: str                               # DEPOSIT / NATURAL；贸易不改写原始来源类型
    acquired_tick: int                             # 原批次首次取得时间；贸易后保持不变
    deposit_id: Optional[str] = None
    trade_route_id: Optional[str] = None
    inflow: float = 0.0
    outflow: float = 0.0
    purpose: str = ""                             # extraction / trade / build_armory / training等
    linked_event_id: Optional[int] = None


class InterventionRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)              # f"intervention_{tick}_{seq}"
    tick_number: int
    year: int
    month: int
    stage: int
    intervention_type: str
    hex_ids: str
    parameters: str
    immediately_visible_to: str
    discovered_by: str = '[]'
    triggered_event_ids: str = '[]'
    downstream_event_ids: str = '[]'
    causal_summary: str = ''


class CausalLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_intervention_id: Optional[str] = None
    source_event_id: Optional[int] = None
    caused_event_id: int
    causal_type: str                               # DIRECT / INDIRECT / PROBABILISTIC
    lag_ticks: int
    causal_note: str
```

### 22.3 资源批次、账本与因果链

```text
Nation.stock_iron_sources / stock_stone_sources / stock_wood_sources 的JSON必须是有序列表：
[
  {"source_id":"deposit_12_45_30","source_type":"DEPOSIT","acquired_tick":12,"remaining":80.0},
  {"source_id":"natural","source_type":"NATURAL","acquired_tick":0,"remaining":400.0}
]

所有可溯源资源操作都遵循：
1. add_resource_batch()：追加或合并同源批次，写入一条inflow账本。
2. consume_resource_fifo()：按acquired_tick从早到晚扣减；每个被扣批次写一条outflow账本。
3. transfer_resource_batches_fifo()：按FIFO从卖方取批次，将原source_id/source_type/acquired_tick转给买方；双方各写账本。
4. 任何由资源消耗触发的WorldEvent，必须从其outflow账本继承source_id；若source_id是deposit，读取其source_intervention_id。
5. trace_links()只为明确继承来源的事件创建CausalLink：贡献>20%为DIRECT/强显示；5–20%为PROBABILISTIC/折叠；<5%不显示。

因此，库存跨月、贸易转卖、数月后的建设或扩军，仍能追溯到最初矿脉；不可用“最近N Tick”推测因果。
```

### 22.4 信息可见与发现（worldsim_worldwill.py）

```python
async def apply_immediate_visibility(intervention, hex_id: str, db_session) -> list[WorldEvent]:
    """POST /api/world/intervene在返回前调用，事件写入本月。"""
    visible = []
    hex_cell = await get_hex(hex_id, db_session)
    for nation_id in await get_all_nation_ids(db_session):
        if hex_cell.nation_id == nation_id:
            visible.append(nation_id)                 # 控制格：100%
        elif await controls_adjacent_hex(nation_id, hex_id, db_session) and random.random() < 0.85:
            visible.append(nation_id)                 # 相邻控制格：85%
    for nation_id in visible:
        await record_intervention_discovery(intervention, nation_id, db_session)
        await create_natural_discovery_event(intervention, nation_id, db_session)
    return visible


async def propagate_resource_discovery(deposit, current_tick: int, db_session) -> list[WorldEvent]:
    """当前Tick Step 4执行；只处理即时可见范围之外、尚未发现的国家。"""
    events = []
    discovered = set(json.loads(deposit.discovered_by))
    for nation_id in await get_all_nation_ids(db_session):
        if nation_id in discovered:
            continue
        if await controls_adjacent_hex(nation_id, deposit.hex_id, db_session):
            continue
        if await route_passes_through(nation_id, deposit.hex_id, db_session):
            probability = 0.15
        elif await has_recent_scouts(nation_id, current_tick, db_session):
            probability = 0.10
        else:
            probability = 0.02
        if random.random() < probability:
            events.append(await record_resource_discovery(deposit, nation_id, current_tick, db_session))
    return events
```

### 22.5 工具清单

```python
WORLD_WILL_TOOLS = {
    "place_iron_deposit": {
        "stage": 1, "resource_type": "IRON", "reserves": (500, 3000),
        "quality": (0.3, 0.9), "terrain_req": ["MOUNTAIN", "PLAIN"], "regen_rate": 0.0,
    },
    "place_stone_deposit": {
        "stage": 1, "resource_type": "STONE", "reserves": (1000, 8000),
        "quality": (0.3, 0.9), "terrain_req": ["MOUNTAIN", "PLAIN"], "regen_rate": 0.0,
    },
    "place_timber_grove": {
        "stage": 1, "resource_type": "TIMBER", "reserves": (500, 3000),
        "quality": (0.3, 0.9), "terrain_req": ["PLAIN", "FOREST"], "regen_rate": 0.05,
    },
    "place_fertile_soil": {
        "stage": 1, "resource_type": None, "terrain_req": ["PLAIN"],
        "effect": "HexCell.fertility += 0.3，上限1.0",
    },
    "place_spring": {
        "stage": 1, "resource_type": None, "terrain_req": ["PLAIN", "DESERT"],
        "effect": "HexCell.terrain改为RIVER，fertility += 0.2，上限1.0；按地形重算resource_food",
    },
}
```

### 22.6 资源开发政策的精确定义

```text
开发前置条件：
- 目标是本国已发现、未枯竭、development_level=0的IRON/STONE/TIMBER ResourceDeposit。
- 距最近本国Settlement不超过5格。
- pop_farmers >= 150；stock_gold >= 200；stock_wood >= 100。

执行：
- 扣除200 gold与100 wood；木材必须consume_resource_fifo(... purpose="develop_deposit")。
- transfer_workforce(pop_farmers → pop_extractors, 100)。
- deposit.workers_assigned=100；developed_by=nation.id；development_level=1；重算monthly_yield。
- 创建WorldEvent，事件继承deposit.source_intervention_id。

关闭/枯竭/失去控制权：
- release_deposit_workers()将该deposit的workers_assigned从pop_extractors归还至pop_farmers。
- workers_assigned=0，development_level=0；不删除历史账本或因果链接。
```

### 22.7 API与前端

```text
POST /api/world/intervene
GET  /api/world/interventions
GET  /api/world/intervention/{id}/chain
GET  /api/world/deposits
GET  /api/world/causal-links?source_id={id}

InterventionTimeline只显示拥有明确CausalLink的下游事件；不得把时间接近当作因果。
```

---

*SPEC版本：v2.9 — 当前文件是唯一权威来源。所有与本文件冲突的代码均需修改以符合本规范。*


---

### 22.6 权限层级2：环境与生产（里程碑二开放）

**目的**：玩家改变地区的生产条件与通行条件，国家自行决定储粮、贸易、迁徙、修路、停战或扩张。环境干预是区域事件，不是直接增加库存。

#### 22.6.1 前置能力与开锁门槛

```text
必须已实现：
- SeasonState：每Tick明确季节与基础气候；
- RegionalCondition：区域效果，可叠加、可持续、可过期；
- 农业产出读取 fertility、降水、干旱/洪水/虫害修正；
- TradeRoute 有 OPEN / DEGRADED / CLOSED 通行状态；
- AI/LLM上下文含本国受影响区域、持续月数、预估粮食与贸易影响；
- WorldEvent 可记录条件来源 intervention_id。

验收：同一随机种子下，干旱、丰年、山口关闭均产生可复现的产出/贸易变化；
      条件结束后数值回到未受干预时的规则状态，不残留永久错误修正。
```

#### 22.6.2 工具集

| 工具 | 范围 | 引擎效果 | 国家看到的自然事件 |
|---|---|---|---|
| 降雨 | 1–7格，1–3月 | 增加降水与当季农业修正 | “北部迎来持续降雨” |
| 干旱 | 1–12格，1–6月 | 降低降水、粮食产出与河道通行 | “北部旱情持续” |
| 洪涝 | 1–7格，1–2月 | 降低当期农业、破坏道路/库存，后续提升部分冲积地肥力 | “河流决堤，低地受灾” |
| 丰年 | 1–12格，当季 | 提升农业产出，不直接加粮食库存 | “气候温和，作物丰收” |
| 虫害 | 1–7格，1–3月 | 降低农业产出；可被后续政策缓解 | “虫灾蔓延至农田” |
| 野火 | 1–5格，即时 | 降低森林储量、破坏道路/聚落设施风险 | “林地发生大火” |
| 开启山口 | 指定山口 | 将可通行地形/路线状态改为OPEN | “积雪消退，山口可通行” |
| 封闭山口 | 指定山口，1–6月 | 将可通行状态改为CLOSED或DEGRADED | “雪崩/塌方阻断山口” |

#### 22.6.3 可见、溯源与限制

```text
- 受影响格控制国当月100%获得事件；相邻国按边境/贸易路线获得信息；远方国家只通过贸易和外交得知。
- 每个 RegionalCondition 必须有 source_intervention_id、start_tick、end_tick、affected_hex_ids。
- 环境事件导致的粮食、路线与迁徙事件继承 source_intervention_id；禁止把“丰年”直接写为 stock_food += N。
- 同一格同类条件刷新持续时间，不无限叠加倍率；冲突条件按预定义优先级结算（洪涝 > 干旱 > 降雨，野火独立）。
```

---

### 22.7 权限层级3：人口与生命（里程碑三开放）

**目的**：玩家改变生命、劳动力和人口流动的条件。国家能看见病、迁徙、动物资源或公共卫生变化，后果必须通过人口系统结算。

#### 22.7.1 前置能力与开锁门槛

```text
必须已实现：
- 年龄层人口、职业人口与军队人口守恒；
- PopulationEvent：疾病、出生、死亡、迁徙、难民；
- DiseaseOutbreak：传播、潜伏、死亡率、医疗缓解、结束条件；
- MigrationFlow：来源、目的地、人数、职业构成、原因；
- 聚落医疗/卫生与粮食可影响疾病结果；
- 战争与饥荒伤亡通过同一人口语义执行器结算。

验收：
- 100个月模拟中总人口、各年龄层、职业人口与军队人口始终守恒；
- 瘟疫不会把死亡直接写入总人口而遗漏职业/年龄层；
- 迁徙不会凭空复制人口；
- 疾病结束后不会留下永久传播状态。
```

#### 22.7.2 工具集

| 工具 | 范围 | 引擎效果 | 国家看到的事件 |
|---|---|---|---|
| 瘟疫暴发 | 指定聚落或相邻格 | 创建 DiseaseOutbreak；传播、死亡和医疗由规则结算 | “城中出现不明热病” |
| 疫病缓解 | 指定聚落 | 降低现有 DiseaseOutbreak 的传播/死亡率，不直接复活人口 | “泉水改善，病势趋缓” |
| 兽群迁入 | 1–7格，3–12月 | 增加狩猎/畜牧产出与相关劳动力机会 | “大量兽群迁徙至草场” |
| 渔场丰沛 | 沿水域格，3–12月 | 提升食物多样性与渔业产出 | “近海渔汛旺盛” |
| 人口迁徙潮 | 起点区域→目标区域 | 创建 MigrationFlow；国家可接纳、限制、安置或驱逐 | “大量流民抵达边境” |
| 医疗植物发现 | 指定森林/山地格 | 创建可开发的医疗资源与治疗政策机会 | “山民发现可退热的草药” |

#### 22.7.3 安全结算规则

```text
- 瘟疫、迁徙与伤亡只能调用 population_system 语义执行器；禁止直接改 pop_total、pop_adults 或职业字段。
- “疫病缓解”只能影响未来传播和死亡，不补回已经死亡的人口。
- 迁徙潮的总人数先从来源地移除，再按实际到达比例转入目的地；路途死亡、拒绝入境和回流必须有事件记录。
- 人口事件一律携带 source_intervention_id，并写入史书与因果链。
```

---

### 22.8 权限层级4：信息与文化（里程碑四开放）

**目的**：玩家改变国家所相信、传播和认同的东西。假情报不是向 Nation 写入假事实，而是生成一条带来源、可信度与可调查性的报告；国家可以相信、怀疑、调查或利用它。

#### 22.8.1 前置能力与开锁门槛

```text
必须已实现：
- IntelligenceReport：内容、来源、真值、可信度、传播范围、到期时间；
- Investigation：国家可花费资源调查报告，结果可能证实、证伪或保持不确定；
- HexCulture / CultureEntity：文化成分与文化中心，批量SQL扩散；
- BeliefMovement：宗教/思想运动、支持度、聚落锚点、政策偏好；
- 国家决策上下文区分 objective_facts 与 intelligence_reports；LLM不得把未证实情报写成客观事实。

验收：
- 假情报被证伪后不改变地图、库存、军队等客观状态；
- 不同国家可基于不同可信度作出不同决策；
- 文化扩散总和在每格保持1.0±0.001；
- 100Tick文化扩散不产生负数、NaN或重复覆盖。
```

#### 22.8.2 工具集

| 工具 | 范围 | 引擎效果 | 国家看到的事件 |
|---|---|---|---|
| 传播真情报 | 指定国家/区域 | 生成真值为真、可传播的 IntelligenceReport | “商旅带回边境军情” |
| 散布谣言 | 指定国家/区域 | 生成真值为假或部分失真的报告，带初始可信度 | “市集流传敌国将入侵” |
| 文化中心 | 指定聚落 | 创建/加强 CultureEntity 锚点，影响周边文化权重 | “学派在此兴起” |
| 宗教运动 | 指定聚落/区域 | 创建 BeliefMovement，改变派系偏好与社会凝聚 | “新教派开始传讲” |
| 复兴传统 | 指定国家文化区域 | 提升本土文化韧性与文化传播阻力 | “古老仪式重新流行” |
| 跨境译介 | 两个已连通区域 | 提升特定文化/思想沿贸易路线传播 | “外来著作被译介传播” |

#### 22.8.3 信息边界

```text
- AI/LLM收到的情报必须标注可信度、来源和“未证实”状态。
- 国家可基于谣言部署军队或调整外交；引擎不允许谣言直接改变客观变量。
- 调查成功、自然证据出现或事件到期后，报告状态更新为 CONFIRMED / REFUTED / EXPIRED；相关决策与后果仍保留在历史里。
- 宗教/思想并不等于国家文化；它们是独立实体，可跨国家、跨文化传播。
```

---

### 22.9 权限层级5：政治与权力（里程碑五开放）

**目的**：玩家改变统治集团的稳定性与权力继承条件。政治干预必须触发可被国家制度处理的事件，不能直接重写某国全部属性或强制指定结局。

#### 22.9.1 前置能力与开锁门槛

```text
必须已实现：
- Leader：寿命、能力、性格、合法性来源、健康、继承规则；
- Faction：支持度、利益、组织度、军政影响力；
- SuccessionCrisis、CoupAttempt、Rebellion、AssassinationAttempt 等结构化事件；
- 合法性、债务、战争疲惫、文化/宗教支持、外交干预共同影响政治结果；
- 外交系统可处理资助、施压、承认新政权、庇护流亡者。

验收：
- 政治事件不直接删改 Nation，必须经事件→派系/领袖→制度结算；
- 继承危机在同一随机种子下可复现；
- 政变、叛乱和刺杀结局可失败，并产生可解释的后果；
- 不出现无领袖国家、重复领袖或派系支持度越界。
```

#### 22.9.2 工具集

| 工具 | 范围 | 引擎效果 | 国家看到的事件 |
|---|---|---|---|
| 刺杀风波 | 指定领袖/聚落 | 创建 AssassinationAttempt；安保、派系与随机结算决定成败 | “宫廷传出刺杀传闻” |
| 继承危机 | 指定国家 | 创建 SuccessionCrisis；候选人和派系争夺合法性 | “统治者病重，继承未明” |
| 派系崛起 | 指定国家/派系 | 提升组织度与议题可见度，非直接加支持度到胜利 | “军方/商人集团迅速集结” |
| 民变火种 | 指定聚落 | 创建 RebellionPressure；由税负、粮食、文化、镇压共同结算 | “城中出现抗税集会” |
| 外国资助线索 | 资助国→目标国派系 | 创建可被发现的 covert support 记录与外交风险 | “边境截获可疑资助” |
| 领袖际遇 | 指定领袖 | 创建健康、声望、丑闻、婚姻或功绩事件候选，由规则决定性格/合法性变化 | “统治者经历重大变故” |

#### 22.9.3 政治干预的边界

```text
- “改变领袖性格”只能通过 LeaderEvent 影响特定性格维度，幅度有限且需写明事件原因；禁止直接覆盖完整人格。
- 刺杀、政变、叛乱均可失败。玩家注入的是条件，不是结果。
- 对外资助必须能被调查、曝光或否认，并进入外交关系与因果链。
- 政治事件影响的所有合法性、派系、军队、财政变化都必须继承 source_intervention_id。
```

---

### 22.10 后续层级的交付协议（每次交给 Codex）

```text
每次只交付一个里程碑，禁止把两层权限混合实现。

下一次交付 Codex 的标准任务格式：
1. 读取本SPEC、第21节对应里程碑与第22节对应权限层级；
2. 读取已实现代码和 codex.md，以当前仓库为准；
3. 为该层新增的模型、迁移、Tick步骤、事件处理器、前端工具与测试建立清单；
4. 先写确定性规则与测试，再接入LLM；
5. 运行本层验收与至少100个月、10个种子的回归模拟；
6. 通过后将 WorldState.world_will_max_stage 提升一级，并更新 codex.md；
7. 停止。不得提前实现下一层。

建议实施顺序：
M1/权限1 → M2/权限2 → M3/权限3 → M4/权限4 → M5/权限5。
```
