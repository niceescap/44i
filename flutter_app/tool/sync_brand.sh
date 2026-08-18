#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/../backend/static/brand"
DST="$ROOT/assets/brand"
mkdir -p "$DST"
cp -f "$SRC/bandeau.jpg" "$DST/bandeau.jpg"
cp -f "$SRC/rosace.png" "$DST/rosace.png"
echo "OK brand → $DST"
