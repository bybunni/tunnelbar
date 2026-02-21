#!/bin/bash
# Generate Tunnelbar.icns from the existing menubar icon PNG.
# Uses sips (macOS built-in) to resize and iconutil to compile.
set -euo pipefail

SRC="tunnelbar/resources/icon_idle@2x.png"
ICONSET="tunnelbar/resources/Tunnelbar.iconset"
ICNS="tunnelbar/resources/Tunnelbar.icns"

mkdir -p "$ICONSET"

for size in 16 32 128 256 512; do
    sips -z $size $size "$SRC" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
    double=$((size * 2))
    sips -z $double $double "$SRC" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
done

iconutil --convert icns --output "$ICNS" "$ICONSET"
rm -rf "$ICONSET"
echo "Created $ICNS"
