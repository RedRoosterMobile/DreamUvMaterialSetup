#!/bin/sh
# Smoke test: export a template at 256x256, convert it to the hotspot layout, and check map sizes.
set -eu
cd "$(dirname "$0")"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT

./mm-material list >/dev/null
./mm-material generate metal-scratched --output "$out/gen" --size 256 --param seed=1 >/dev/null
./mm-material convert-hotspot --albedo "$out/gen/albedo.png" --normal "$out/gen/normal.png" \
  --orm "$out/gen/orm.png" --output "$out/hotspot" >/dev/null

for f in "$out"/gen/albedo.png "$out"/gen/normal.png "$out"/gen/orm.png \
         "$out"/hotspot/albedo.png "$out"/hotspot/normal.png "$out"/hotspot/orm.png; do
  size=$(sips -g pixelWidth -g pixelHeight "$f" | awk '/pixel/ {print $2}' | paste -sd x -)
  [ "$size" = 256x256 ] || { echo "FAIL $f is $size"; exit 1; }
done

if ./mm-material generate metal-noise --output "$out/bad" --param nope=1 2>/dev/null; then
  echo "FAIL unknown parameter accepted"; exit 1
fi
echo OK
