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

bash "$ROOT/tool/sync_brand.sh" || true
flutter pub get
dart run flutter_launcher_icons

echo
echo "OK — applicationId attendu : com.nicee.larosace"
echo "Vérif :"
grep -R "applicationId" android/app/build.gradle android/app/build.gradle.kts 2>/dev/null || true
