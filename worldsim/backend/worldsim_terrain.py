"""M1 terrain and odd-row offset hex helpers.

Hex helper concepts are adapted from the MIT-licensed `stephanh42/hexutil`
reference kept under `third_party/open_source/hexutil`, but converted to the
SPEC.md odd-row offset coordinate system: rows with odd `r` are shifted right by
half a hex.
"""

import random
from collections.abc import Iterable
from .worldsim_models import HexCell

WIDTH, HEIGHT = 120, 80

_EVEN_ROW_DELTAS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1))
_ODD_ROW_DELTAS = ((1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1))


def offset_neighbors(q: int, r: int) -> list[tuple[int, int]]:
    """Return six neighboring coordinates for odd-row offset hexes."""
    deltas = _ODD_ROW_DELTAS if r % 2 else _EVEN_ROW_DELTAS
    return [(q + dq, r + dr) for dq, dr in deltas]


def offset_to_cube(q: int, r: int) -> tuple[int, int, int]:
    """Convert odd-row offset coordinates to cube coordinates for distance."""
    x = q - (r - (r & 1)) // 2
    z = r
    y = -x - z
    return x, y, z


def offset_distance(aq: int, ar: int, bq: int, br: int) -> int:
    """Hex distance between two odd-row offset cells."""
    ax, ay, az = offset_to_cube(aq, ar)
    bx, by, bz = offset_to_cube(bq, br)
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


def iter_cells_in_radius(center_q: int, center_r: int, radius: int, width: int = WIDTH, height: int = HEIGHT) -> Iterable[tuple[int, int]]:
    """Yield bounded odd-row offset cells within `radius` of a center."""
    for r in range(max(0, center_r - radius * 2), min(height, center_r + radius * 2 + 1)):
        for q in range(max(0, center_q - radius * 2), min(width, center_q + radius * 2 + 1)):
            if offset_distance(center_q, center_r, q, r) <= radius:
                yield q, r


def make_cell(q: int, r: int, rng: random.Random) -> HexCell:
    elevation = rng.random()
    fertility = rng.random()
    terrain = "PLAIN"
    if elevation > .82:
        terrain = "MOUNTAIN"
    elif fertility > .78:
        terrain = "FOREST"
    elif fertility < .12:
        terrain = "DESERT"
    elif r in (20, 45) and q % 7 in (0, 1):
        terrain = "RIVER"
    elif q in (0, WIDTH - 1) or r in (0, HEIGHT - 1):
        terrain = "COAST"
    return HexCell(
        id=f"{q}_{r}",
        q=q,
        r=r,
        terrain=terrain,
        elevation=elevation,
        fertility=fertility,
        resource_food=max(0.2, fertility * 6),
        resource_wood=5 if terrain == "FOREST" else 0.8,
        resource_stone=5 if terrain == "MOUNTAIN" else 0.4,
        resource_iron=3 if terrain == "MOUNTAIN" and elevation > .9 else 0.1,
        passable=terrain != "MOUNTAIN",
    )


def generate_map(seed: int = 42) -> list[HexCell]:
    rng = random.Random(seed)
    return [make_cell(q, r, rng) for r in range(HEIGHT) for q in range(WIDTH)]

async def monthly_regen(session, month: int) -> list:
    """Regenerate M1 terrain resources without enabling later season/weather systems."""
    from sqlmodel import select

    cells = (await session.execute(select(HexCell).where(HexCell.terrain == "FOREST"))).scalars().all()
    for cell in cells:
        cell.resource_wood = min(6.0, cell.resource_wood + 0.05)
    return []
