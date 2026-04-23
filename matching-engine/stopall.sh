#!/usr/bin/env bash
# Stop engine, client, and admin started by startall.sh.
# Uses PID files in ./.run/, falls back to killing by port.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"

stop_by_pidfile() {
  local name="$1"
  local pid_file="$RUN_DIR/$name.pid"
  [[ -f "$pid_file" ]] || return 1

  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "[$name] stopping pid $pid (+ children)"
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill -TERM "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "[$name] forcing kill"
      pkill -KILL -P "$pid" 2>/dev/null || true
      kill -KILL "$pid" 2>/dev/null || true
    fi
  else
    echo "[$name] not running (stale pid file)"
  fi
  rm -f "$pid_file"
  return 0
}

stop_by_port() {
  local name="$1" port="$2"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "[$name] port $port: killing $(echo "$pids" | tr '\n' ' ')"
    kill -TERM $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then kill -KILL $pids 2>/dev/null || true; fi
  fi
}

for svc in engine admin client; do
  stop_by_pidfile "$svc" || true
done

# Fallback cleanup in case services were started without the script.
stop_by_port engine-api 8000
stop_by_port engine-ws  8765
stop_by_port admin      3001
stop_by_port client     5173

echo "done."
