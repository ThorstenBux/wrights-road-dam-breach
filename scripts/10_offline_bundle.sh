#!/usr/bin/env bash
# Build the self-contained offline copy of the site (docs/ + START-HERE.html) and, optionally,
# install it for presenting. Everything the viewer needs is already in docs/ (data.js per scenario,
# three.js and fonts in docs/vendor/, explicit index.html links), so this is a packaging step only.
#
#   scripts/10_offline_bundle.sh                      # -> wrights-road-dam-breach-offline.zip in the repo root
#   scripts/10_offline_bundle.sh --install            # ... and refresh ~/Desktop/wrights-road-dam-breach-offline/
#   scripts/10_offline_bundle.sh --install /Volumes/USB/flood --open   # custom folder, then open START-HERE.html
#
# Run it from a checkout that has the docs/ you want to present (usually main, or the branch under review).
# Re-run it after every change to docs/ (new scenario, viewer edit, regenerated data.js).
set -euo pipefail
cd "$(dirname "$0")/.."

ZIP=wrights-road-dam-breach-offline.zip
INSTALL="" ; OPEN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --install) INSTALL="${2:-}"; if [ -n "$INSTALL" ] && [ "${INSTALL#--}" = "$INSTALL" ]; then shift; else INSTALL="$HOME/Desktop/wrights-road-dam-breach-offline"; fi ;;
    --open) OPEN=1 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac; shift
done

for f in docs/index.html docs/vendor/three.min.js docs/vendor/fonts.css; do [ -f "$f" ] || { echo "missing $f" >&2; exit 1; }; done
if grep -lE 'cdnjs|fonts\.googleapis' docs/*/index.html >/dev/null 2>&1; then
  echo "viewer copies still reference a CDN (copy webgl/index.html into every docs/<scenario>/ first):" >&2
  grep -lE 'cdnjs|fonts\.googleapis' docs/*/index.html >&2; exit 1
fi
if grep -qE 'href="[a-z-]+/"' docs/index.html; then
  echo "docs/index.html has directory links (must be explicit index.html for file://)" >&2; exit 1
fi

rm -f "$ZIP"
cp docs/index.html docs/START-HERE.html
trap 'rm -f docs/START-HERE.html' EXIT
zip -qr "$ZIP" docs -x 'docs/*.md' 'docs/.DS_Store' '*/.DS_Store'
echo "wrote $ZIP ($(du -h "$ZIP" | cut -f1))"

if [ -n "$INSTALL" ]; then
  rm -rf "$INSTALL"; mkdir -p "$INSTALL"
  unzip -q "$ZIP" -d "$INSTALL"; mv "$INSTALL"/docs/* "$INSTALL"/; rmdir "$INSTALL/docs"
  cp "$ZIP" "$(dirname "$INSTALL")/"
  echo "installed to $INSTALL (zip copied alongside); open START-HERE.html there"
  [ "$OPEN" = 1 ] && open "$INSTALL/START-HERE.html"
fi
