#!/usr/bin/env bash
set -euo pipefail

# Phase 1 Wave 4 smoke test — closes 01-VALIDATION.md row `1-04-streamlit-app-smoke` (UI-01 + UI-02 + TRUST-01).
# Boots Streamlit in the background, curls home + /methodology, asserts first-meaningful-paint copy
# appears in the rendered HTML. Tears down cleanly on success or failure.
#
# Usage:
#   bash scripts/smoke.sh
#   SMOKE_PORT=8502 bash scripts/smoke.sh   # run on alternate port
#
# Documented limitation: Streamlit serves content via WebSocket-driven component tree.
# The initial HTTP response for / is the Streamlit boot shell HTML which contains the
# <title>DRHPLens · Ask about Swiggy</title> (from st.set_page_config) but NOT the
# rendered hero heading text. We assert 'DRHPLens' (present in the page title) as the
# closest signal from a single curl call. A deeper check (Playwright headless Chrome)
# is a Phase 6 polish item. The manual test script (tests/manual/CITATION_INTERACTION.md)
# covers deeper interactive verifications.

PORT="${SMOKE_PORT:-8501}"
LOGFILE="${SMOKE_LOG:-/tmp/drhplens_smoke.log}"
PID_FILE="/tmp/drhplens_smoke.pid"

cleanup() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      # Give Streamlit a moment to terminate gracefully
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.2
      done
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
}
trap cleanup EXIT INT TERM

echo "Booting Streamlit on port $PORT..."
streamlit run app.py \
  --server.port "$PORT" \
  --server.headless true \
  --server.address 127.0.0.1 \
  --browser.gatherUsageStats false \
  > "$LOGFILE" 2>&1 &
echo $! > "$PID_FILE"

# Wait up to 30s for first response (cold-start tolerance per UI-SPEC §Loading "Warming up" 30-60s allowance)
READY=0
for attempt in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:$PORT/" -o /dev/null 2>/dev/null; then
    READY=1
    break
  fi
  sleep 0.5
done

if [[ "$READY" -ne 1 ]]; then
  echo "FAIL: Streamlit did not become ready within 30s."
  echo "--- Streamlit log ---"
  tail -50 "$LOGFILE"
  exit 1
fi

echo "Streamlit is up. Checking home page..."
HOME_BODY=$(curl -sf "http://127.0.0.1:$PORT/")
# The Streamlit boot shell HTML contains the <title> set via st.set_page_config.
# Asserting 'DRHPLens' (present in the page title "DRHPLens · Ask about Swiggy")
# is the closest signal available from a single curl call without driving the WebSocket.
if ! echo "$HOME_BODY" | grep -q 'DRHPLens'; then
  echo "FAIL: home page does not contain 'DRHPLens' in rendered HTML."
  echo "--- HTML head ---"
  echo "$HOME_BODY" | head -50
  exit 1
fi

echo "Checking /methodology page..."
METH_BODY=$(curl -sf "http://127.0.0.1:$PORT/methodology")
if ! echo "$METH_BODY" | grep -q 'Methodology'; then
  echo "FAIL: /methodology page does not contain 'Methodology' in rendered HTML."
  echo "--- HTML head ---"
  echo "$METH_BODY" | head -50
  exit 1
fi

echo "PASS: Streamlit boots; home + /methodology both return 200 with expected copy."
exit 0
