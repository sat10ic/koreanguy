#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

echo ""[1/8] fetch""      ; python scripts/fetch.py
echo ""[2/8] indicators"" ; python scripts/indicators.py
echo ""[3/8] regime""     ; python scripts/regime.py
echo ""[4/8] screen""     ; python scripts/screen.py
echo ""[5/8] verify""     ; python scripts/verify.py
echo ""[6/8] track""      ; python scripts/track.py
echo ""[7/8] render""     ; python scripts/render.py
echo ""[8/8] notify""     ; python scripts/notify.py
echo ""done.""
