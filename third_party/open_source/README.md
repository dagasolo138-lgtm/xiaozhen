# Open-source references used for WorldSim M1 adaptation

This directory contains small, unmodified reference snapshots from permissively licensed GitHub projects that were reviewed before adapting ideas into the WorldSim M1 codebase. The runtime application does not import these files directly; they are kept to satisfy license notice requirements and to make the adaptation trail auditable.

## Included references

| Project | Source | License | How it was used |
|---|---|---|---|
| `stephanh42/hexutil` | https://github.com/stephanh42/hexutil | MIT | Adapted hex-grid neighbor/distance concepts into `worldsim_terrain.py` for SPEC-compatible odd-row offset coordinates. |
| `chad-autry/hex-grid-map` | https://github.com/chad-autry/hex-grid-map | MIT | Adapted Canvas/grid rendering concepts into `HexMap.tsx` without importing Paper.js or adding forbidden render engines. |
| `seapagan/fastapi_async_sqlalchemy2_example` | https://github.com/seapagan/fastapi_async_sqlalchemy2_example | MIT | Reviewed async SQLAlchemy/FastAPI structure; no runtime source is imported. |

GPL/AGPL projects were not imported. All adapted runtime code remains constrained to SPEC.md M1 and world-will permission level 1.
