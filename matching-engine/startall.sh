#!/usr/bin/env bash
# Start exchange engine, client, and admin. Logs and PIDs go to ./.run/
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

start_service() {
  local name="$1" dir="$2" cmd="$3"
  local pid_file="$RUN_DIR/$name.pid"
  local log_file="$RUN_DIR/$name.log"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$name] already running (pid $(cat "$pid_file"))"
    return 0
  fi

  echo "[$name] starting..."
  (
    cd "$dir"
    nohup bash -c "$cmd" </dev/null >"$log_file" 2>&1 &
    echo $! >"$pid_file"
    disown
  )
  sleep 2
  if kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$name] pid $(cat "$pid_file"), log: $log_file"
  else
    echo "[$name] FAILED to start — see $log_file"
    return 1
  fi
}

start_service engine "$ROOT/exchange/engine" "uv run python -m engine.main"
start_service admin  "$ROOT/exchange/admin"  "npm run dev"
start_service client "$ROOT/client"          "npm run dev"

echo
echo "URLs:"
echo "  Admin UI:         http://localhost:3001"
echo "  Client UI:        http://localhost:5173"
echo "  Engine API:       http://localhost:8000"
echo "  Engine client WS: ws://localhost:8765"
echo "  Engine admin WS:  ws://localhost:8000/ws/admin"
echo
echo "Tail logs:  tail -f $RUN_DIR/{engine,admin,client}.log"
echo "Stop all:   ./stopall.sh"
