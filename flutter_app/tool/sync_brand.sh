#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/../backend/static/brand"
DST="$ROOT/assets/brand"
mkdir -p "$DST"
cp -f "$SRC/bandeau.jpg" "$DST/bandeau.jpg"
cp -f "$SRC/rosace.png" "$DST/rosace.png"
if [ -f "$SRC/logocarre.jpg" ]; then
  cp -f "$SRC/logocarre.jpg" "$DST/logocarre.jpg"
  echo "OK brand → $DST (bandeau, rosace, logocarre)"
else
  echo "OK brand → $DST (bandeau, rosace) — logocarre.jpg absent, icône launcher inchangée"
fi