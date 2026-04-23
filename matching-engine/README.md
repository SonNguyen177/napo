# Exchange

A simplified stock exchange with three services:

| Service | Path              | Stack               | Dev port |
| ------- | ----------------- | ------------------- | -------- |
| Engine  | `exchange/engine` | Python 3.14 + uv    | 8000 (HTTP/admin WS), 8765 (client WS) |
| Admin   | `exchange/admin`  | React + Vite        | 3001     |
| Client  | `client`          | React + Vite        | 5173     |

---

## 1. Prerequisites

Install these once, on either OS:

| Tool      | Version              | Check          |
| --------- | -------------------- | -------------- |
| Python    | 3.14 or newer        | `python --version` |
| uv        | 0.9.15 or newer      | `uv --version` |
| Node.js   | 20 LTS or newer      | `node --version` |
| npm       | ships with Node      | `npm --version` |
| Git       | any recent           | `git --version` |

### macOS

```bash
# Homebrew (skip if already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.14 node
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

Use PowerShell (run as your normal user, not admin unless noted):

```powershell
# Option A: winget (built into Windows 11 / modern Windows 10)
winget install --id Python.Python.3.14 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id astral-sh.uv -e

# Option B: manual installers
#   Python: https://www.python.org/downloads/
#   Node:   https://nodejs.org/
#   uv:     irm https://astral.sh/uv/install.ps1 | iex
```

After installing, **close and reopen your terminal** so the new `PATH` is picked up.

PowerShell script execution is restricted by default. Allow local scripts for your user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 2. First-time setup

Run these once per clone. They install dependencies; nothing is started yet.

### 2.1 Engine (Python)

macOS / Linux:

```bash
cd exchange/engine
uv sync
cd ../..
```

Windows (PowerShell):

```powershell
cd exchange\engine
uv sync
cd ..\..
```

`uv sync` creates `.venv/` inside `exchange/engine` and installs dependencies from `pyproject.toml` / `uv.lock`.

### 2.2 Admin UI (Node)

macOS / Linux:

```bash
cd exchange/admin
npm install
cd ../..
```

Windows:

```powershell
cd exchange\admin
npm install
cd ..\..
```

### 2.3 Client UI (Node)

macOS / Linux:

```bash
cd client
npm install
cd ..
```

Windows:

```powershell
cd client
npm install
cd ..
```

---

## 3. Running the system

You can start everything at once with the provided scripts, or run each service manually in its own terminal.

### 3.1 Scripted — macOS / Linux

From the repo root:

```bash
./startall.sh
```

This launches engine, admin, and client in the background. Logs and PID files are written to `.run/`.

Open in your browser:

- Admin:  http://localhost:3001
- Client: http://localhost:5173

To stop everything:

```bash
./stopall.sh
```

### 3.2 Scripted — Windows (PowerShell)

From the repo root:

```powershell
.\startall.ps1
```

If execution is blocked (and you have not set the policy above), use:

```powershell
powershell -ExecutionPolicy Bypass -File .\startall.ps1
```

Open:

- Admin:  http://localhost:3001
- Client: http://localhost:5173

To stop:

```powershell
.\stopall.ps1
```

### 3.3 Manual — run each service in its own terminal

Useful when you want to see logs live or restart just one service.

**Terminal 1 — Engine**

macOS:
```bash
cd exchange/engine
uv run python -m engine.main
```

Windows:
```powershell
cd exchange\engine
uv run python -m engine.main
```

**Terminal 2 — Admin**

macOS:
```bash
cd exchange/admin
npm run dev
```

Windows:
```powershell
cd exchange\admin
npm run dev
```

**Terminal 3 — Client**

macOS:
```bash
cd client
npm run dev
```

Windows:
```powershell
cd client
npm run dev
```

Stop with `Ctrl+C` in each terminal.

---

## 4. Endpoints

| URL                                 | Purpose                 |
| ----------------------------------- | ----------------------- |
| http://localhost:3001               | Admin UI                |
| http://localhost:5173               | Client UI               |
| http://localhost:8000               | Engine HTTP API         |
| ws://localhost:8765                 | Engine → client market data (WebSocket) |
| ws://localhost:8000/ws/admin        | Engine → admin control / telemetry      |

---

## 5. Logs

When started via the scripts, logs land in `.run/` at the repo root:

- `.run/engine.log`
- `.run/admin.log`
- `.run/client.log`

Tail them live:

macOS:
```bash
tail -f .run/engine.log
```

Windows:
```powershell
Get-Content .run\engine.log -Wait
```

---

## 6. Troubleshooting

**"Port already in use"** — another process is holding 8000 / 8765 / 3001 / 5173. Run the stop script, or:

macOS:
```bash
lsof -ti tcp:8000 | xargs kill -9
```

Windows:
```powershell
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**"Stale PID file"** — the stop script deletes `.run/*.pid` when it can't find the process. Just re-run `startall`.

**Windows: `.ps1` won't run** — either set the execution policy once (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`) or invoke with `powershell -ExecutionPolicy Bypass -File .\startall.ps1`.

**`uv: command not found`** after install — reopen the terminal. The installer appends to your shell profile / `PATH` and the current session won't have it.

**Engine fails immediately** — check `.run/engine.log`. A common cause is a Python version older than 3.14; `uv sync` will have warned during setup.
