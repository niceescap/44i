#!/usr/bin/env bash
# Prépare le socle Android : applicationId com.nicee.larosace, icône logocarre.
# Usage (depuis flutter_app/) : bash tool/prepare_android.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if grep -Rqs "com.nicee.interpretes44" android 2>/dev/null; then
  echo "Ancien package com.nicee.interpretes44 détecté — régénération de android/"
  rm -rf android
fi

if [ ! -f android/app/build.gradle ] && [ ! -f android/app/build.gradle.kts ]; then
  flutter create --org com.nicee --project-name la_rosace --platforms android .
fi

patch_id() {
  local file="$1"
  [ -f "$file" ] || return 0
  sed -i \
    -e 's/applicationId = "com.nicee.la_rosace"/applicationId = "com.nicee.larosace"/' \
    -e 's/namespace = "com.nicee.la_rosace"/namespace = "com.nicee.larosace"/' \
    -e 's/applicationId "com.nicee.la_rosace"/applicationId "com.nicee.larosace"/' \
    -e 's/namespace "com.nicee.la_rosace"/namespace "com.nicee.larosace"/' \
    "$file"
}

patch_id android/app/build.gradle
patch_id android/app/build.gradle.kts

# Si flutter create a posé MainActivity sous com.nicee.la_rosace, on le déplace.
OLD_KT="android/app/src/main/kotlin/com/nicee/la_rosace/MainActivity.kt"
NEW_DIR="android/app/src/main/kotlin/com/nicee/larosace"
if [ -f "$OLD_KT" ]; then
  mkdir -p "$NEW_DIR"
  sed 's/package com.nicee.la_rosace/package com.nicee.larosace/' "$OLD_KT" > "$NEW_DIR/MainActivity.kt"
  rm -rf android/app/src/main/kotlin/com/nicee/la_rosace
fi

# flutter create ne pose INTERNET que dans debug/profile.
# Un AAB release sans ça = Failed host lookup: 44i.webredirect.org
MAIN_MANIFEST="android/app/src/main/AndroidManifest.xml"
if [ -f "$MAIN_MANIFEST" ] && ! grep -q 'android.permission.INTERNET' "$MAIN_MANIFEST"; then
  echo "Patch INTERNET manquant dans $MAIN_MANIFEST"
  python3 - <<'PY'
from pathlib import Path
p = Path("android/app/src/main/AndroidManifest.xml")
text = p.read_text()
needle = "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">"
insert = needle + """
    <!-- OBLIGATOIRE en release. flutter create ne le met que dans debug/profile. -->
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>"""
if needle not in text:
    raise SystemExit("manifest inattendu, INTERNET non injecté")
p.write_text(text.replace(needle, insert, 1))
PY
fi
if [ -f "$MAIN_MANIFEST" ]; then
  sed -i 's/android:label="la_rosace"/android:label="La Rosace"/' "$MAIN_MANIFEST"
fi

bash "$ROOT/tool/sync_brand.sh" || true
flutter pub get
if [ -f "$ROOT/assets/brand/logocarre.jpg" ]; then
  dart run flutter_launcher_icons
else
  echo "SKIP flutter_launcher_icons — logocarre.jpg absent (icône par défaut, l'éditeur la fournira)"
fi

echo
echo "OK — applicationId attendu : com.nicee.larosace"
echo "Vérif :"
grep -R "applicationId" android/app/build.gradle android/app/build.gradle.kts 2>/dev/null || true
echo "INTERNET main manifest :"
grep -n "android.permission.INTERNET" "$MAIN_MANIFEST" || echo "MANQUANT — AAB release cassé"
