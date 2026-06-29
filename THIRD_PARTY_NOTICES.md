# Third-party notices

WorldSim includes adapted ideas and small reference snapshots from the following permissively licensed projects. License texts and selected source snapshots are stored under `third_party/open_source/`.

## stephanh42/hexutil

- URL: https://github.com/stephanh42/hexutil
- License: MIT
- Copyright: Copyright (c) 2017 Stephan Houben
- Usage: Hex-grid neighbor and distance concepts adapted to WorldSim's odd-row offset coordinate system in `worldsim/backend/worldsim_terrain.py`.

## chad-autry/hex-grid-map

- URL: https://github.com/chad-autry/hex-grid-map
- License: MIT
- Copyright: Copyright (c) 2015 Chad Autry
- Usage: Canvas hex-grid rendering concepts adapted in `worldsim/frontend/src/components/HexMap.tsx`; no Paper.js dependency or runtime import is used.

## seapagan/fastapi_async_sqlalchemy2_example

- URL: https://github.com/seapagan/fastapi_async_sqlalchemy2_example
- License: MIT
- Copyright: Copyright (c) 2023-2025 Grant Ramsay
- Usage: Async FastAPI/SQLAlchemy structure reviewed for compatibility; no runtime source is imported.
