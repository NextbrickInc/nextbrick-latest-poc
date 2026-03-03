#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Keysight Agentic AI POC unified dev launcher
#
# Usage:   ./start.sh
# Stops:   Ctrl-C  (kills both servers gracefully)
#
# Requirements:  Python venv at backend/venv  +  node_modules present
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/keysight-ai-assistant-main"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[keysight]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
log "Keysight Agentic AI POC — starting all services..."

if [ ! -f "$BACKEND_DIR/venv/bin/uvicorn" ]; then
  warn "Backend venv not found. Creating and installing deps..."
  python3 -m venv "$BACKEND_DIR/venv"
  "$BACKEND_DIR/venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
  ok "Backend venv ready"
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  warn "node_modules not found. Installing..."
  cd "$FRONTEND_DIR" && npm install --prefer-offline
  ok "node_modules ready"
fi

# ── Start backend ─────────────────────────────────────────────────────────────
log "Starting FastAPI backend on http://localhost:8000..."
cd "$BACKEND_DIR"
"$BACKEND_DIR/venv/bin/uvicorn" app.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info &
BACKEND_PID=$!
ok "Backend started (PID $BACKEND_PID)"

# ── Wait for backend health ───────────────────────────────────────────────────
log "Waiting for backend to be healthy..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    ok "Backend healthy ✓"
    break
  fi
  sleep 1
  if [ "$i" -eq 20 ]; then
    err "Backend did not start in 20s. Check logs above."
    kill "$BACKEND_PID" 2>/dev/null || true
    exit 1
  fi
done

# ── Start frontend ────────────────────────────────────────────────────────────
log "Starting Vite dev server on http://localhost:8080..."
cd "$FRONTEND_DIR"
if [ -n "${NGROK:-}" ]; then
  npm run dev:ngrok &
else
  npm run dev &
fi
FRONTEND_PID=$!
ok "Frontend started (PID $FRONTEND_PID)"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Keysight Agentic AI POC is running                 ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend  →  http://localhost:8080                  ║${NC}"
echo -e "${GREEN}║  Backend   →  http://localhost:8000                  ║${NC}"
echo -e "${GREEN}║  Swagger   →  http://localhost:8000/api/docs         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Press ${RED}Ctrl-C${NC} to stop all services."

# ── Graceful shutdown ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  log "Shutting down..."
  kill "$BACKEND_PID"  2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  ok "All services stopped."
}
trap cleanup INT TERM

wait
