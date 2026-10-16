#!/bin/sh
# Smoke test: export a material at 256x256 with --hotspot, convert it again through the MCP server,
# and check map sizes.
set -eu
cd "$(dirname "$0")"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT

./mm-material list >/dev/null
./mm-material generate metal-scratched --output "$out/gen" --size 256 --param seed=1 --hotspot >/dev/null
# convert-hotspot through the MCP server.
call='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"convert_hotspot","arguments":'
call="$call"'{"albedo":"'"$out"'/gen/albedo.png","normal":"'"$out"'/gen/normal.png","orm":"'"$out"'/gen/orm.png","output":"'"$out"'/mcp"}}}'
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' "$call" |
  ./mm-material-mcp | grep -q '"structuredContent"' || { echo "FAIL MCP convert_hotspot"; exit 1; }

for f in "$out"/gen/albedo.png "$out"/gen/normal.png "$out"/gen/orm.png \
         "$out"/gen/hotspot/albedo.png "$out"/gen/hotspot/normal.png "$out"/gen/hotspot/orm.png \
         "$out"/mcp/albedo.png "$out"/mcp/normal.png "$out"/mcp/orm.png; do
  size=$(sips -g pixelWidth -g pixelHeight "$f" | awk '/pixel/ {print $2}' | paste -sd x -)
  [ "$size" = 256x256 ] || { echo "FAIL $f is $size"; exit 1; }
done

if ./mm-material generate metal-noise --output "$out/bad" --param nope=1 2>/dev/null; then
  echo "FAIL unknown parameter accepted"; exit 1
fi
echo OK
