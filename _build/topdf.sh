#!/usr/bin/env bash
# Render an HTML source file to PDF with headless Chrome.
# usage: topdf.sh <input.html> <output.pdf>
#
# Chrome sometimes does not exit after --print-to-pdf, so this runs it in the
# background and kills it once the PDF has been written and stopped growing.
set -uo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
IN="$1"
OUT="$2"

[ -f "$IN" ] || { echo "missing input: $IN" >&2; exit 1; }

PROFILE="$(mktemp -d)"
rm -f "$OUT"

URL="file://$(python3 -c 'import sys,urllib.parse,os;print(urllib.parse.quote(os.path.abspath(sys.argv[1])))' "$IN")"

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --user-data-dir="$PROFILE" \
  --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw \
  --virtual-time-budget=6000 \
  --print-to-pdf="$OUT" \
  "$URL" >/dev/null 2>&1 &
CHROME_PID=$!

# Wait for the PDF to appear and settle (size stable across two polls).
prev=-1
for _ in $(seq 1 60); do
  sleep 0.5
  if [ -s "$OUT" ]; then
    cur=$(wc -c < "$OUT")
    [ "$cur" = "$prev" ] && break
    prev=$cur
  fi
done

kill "$CHROME_PID" 2>/dev/null
wait "$CHROME_PID" 2>/dev/null
rm -rf "$PROFILE"

[ -s "$OUT" ] || { echo "PDF not produced: $OUT" >&2; exit 1; }
echo "wrote $(basename "$OUT") ($(du -h "$OUT" | cut -f1))"
