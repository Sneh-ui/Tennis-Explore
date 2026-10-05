# Tennis Explore — Production Runbook

> How to run **PostgreSQL + Backend (FastAPI) + Frontend (Vite/React)** the production way on **macOS / Linux / Windows**.

---

## 0. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.9+ | `python3 --version` / `py --version` (Windows) |
| Node.js | 18+ | `node -v && npm -v` |
| PostgreSQL | 16 | `psql --version` |
| Git | any | `git --version` |

Clone:

```bash
git clone <repo-url>
cd 735-Tennis-Explore
```

Project layout:

```
735-Tennis-Explore/
├── backend/
│   ├── structured_data/api.py      # FastAPI app
│   ├── structured_data/sql/*.sql
│   ├── auth/sql/01_create_users.sql
│   ├── requirements.txt
│   └── .env                        # not committed, create from .env.example
├── frontend/
│   ├── vite.config.js
│   ├── .env                        # VITE_API_URL
│   └── src/
└── SETUP.md
```

---

## 1. Database — PostgreSQL 16

### 1.1 Install

**macOS (Homebrew)**

```bash
brew install postgresql@16
brew services start postgresql@16
# or manual
pg_ctl -D $(brew --prefix)/var/postgresql@16 -l /tmp/pg.log start
```

**Linux (Ubuntu/Debian)**

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
# or
sudo service postgresql start
```

**Linux (Fedora/RHEL)**

```bash
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
```

**Windows**

- Installer: https://www.postgresql.org/download/windows/ (EnterpriseDB)
- Or Chocolatey: `choco install postgresql16`
- Or Docker (see below)

**Docker (any OS, prod-like)**

```bash
docker run -d --name tennis-pg \
  -e POSTGRES_USER=tennis_user \
  -e POSTGRES_PASSWORD=tennis_pass \
  -e POSTGRES_DB=tennis_rankings_v2 \
  -p 5432:5432 postgres:16

# logs
docker logs -f tennis-pg
```

### 1.2 Create database & migrate

Replace `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT` with your values.

```bash
# create db (if not created by docker)
createdb -h localhost -p 5432 -U <DB_USER> tennis_rankings_v2
# e.g. createdb -h localhost -p 5432 -U postgres tennis_rankings_v2

# if createdb not in PATH on Windows, use psql:
psql -h localhost -p 5432 -U <DB_USER> -c "CREATE DATABASE tennis_rankings_v2;"

# run migrations from project root
psql -h localhost -p 5432 -U <DB_USER> -d tennis_rankings_v2 -f backend/structured_data/sql/01_create_schema.sql
psql -h localhost -p 5432 -U <DB_USER> -d tennis_rankings_v2 -f backend/auth/sql/01_create_users.sql

# verify (idempotent seed, no python seeder needed)
psql -h localhost -p 5432 -U <DB_USER> -d tennis_rankings_v2 -c "SELECT id, name, email, role FROM auth.users;"
#  analyst@tennisexplore.au / ace123   -> Lead Analyst
#  admin@tennisexplore.au   / admin123 -> Admin

psql -h localhost -p 5432 -U <DB_USER> -d tennis_rankings_v2 -c "\dt *.*"
psql -h localhost -p 5432 -U <DB_USER> -d tennis_rankings_v2 -c "SELECT version();"
```

### 1.3 Start / Stop / Check

```bash
# macOS brew
brew services start postgresql@16
brew services stop postgresql@16
pg_isready -h localhost -p 5432

# Linux systemd
sudo systemctl status postgresql
sudo systemctl restart postgresql
pg_isready -h localhost -p 5432

# Windows services
# Services app -> postgresql-x64-16 -> Start/Stop
pg_isready -h localhost -p 5432

# Docker
docker start tennis-pg
docker stop tennis-pg
```

---

## 2. Backend — FastAPI (Python)

> Always run from **project root**, not from `backend/`. Module import is `backend.structured_data.api`.

### 2.1 Env

Create `backend/.env` from `backend/.env.example`:

```ini
STRUCTURED_DB_HOST=localhost
STRUCTURED_DB_PORT=5432
STRUCTURED_DB_NAME=tennis_rankings_v2
STRUCTURED_DB_USER=<DB_USER>
STRUCTURED_DB_PASSWORD=<DB_PASS>
JWT_SECRET=change-me-to-a-very-long-random-string-for-hs256-32bytes
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
```

- `STRUCTURED_DB_USER/PASSWORD` must match the postgres user you created.
- `JWT_SECRET` must be >=32 chars random in production.
- Loaded via `python-dotenv` in `backend/auth/utils.py` and `backend/structured_data/database.py`.

### 2.2 Install & Run

```bash
# from project root
cd 735-Tennis-Explore

# create venv (recommended)
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
# Windows CMD
# .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r backend/requirements.txt
# includes: fastapi, uvicorn, PyJWT, passlib[bcrypt]==4.0.1, email-validator, psycopg2-binary, python-dotenv
```

**Development (auto-reload)**

```bash
# from project root
python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 --reload
```

**Production**

```bash
python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 --workers 2
# or with gunicorn
# pip install gunicorn
# gunicorn -k uvicorn.workers.UvicornWorker backend.structured_data.api:app --bind 0.0.0.0:8000 --workers 2
```

**Background (Linux/macOS)**

```bash
nohup python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
tail -f /tmp/uvicorn.log
```

**Windows background**

```powershell
Start-Process -NoNewWindow python -ArgumentList "-m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000" -RedirectStandardOutput uvicorn.log
```

### 2.3 Verify

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"analyst@tennisexplore.au","password":"ace123"}'
# {"access_token":"eyJ...","token_type":"bearer","user":{"id":1,"name":"Alex Rivera",...}}

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"analyst@tennisexplore.au","password":"wrong"}'
# {"detail":"Invalid email or password"}

# use token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"analyst@tennisexplore.au","password":"ace123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
# {"id":1,"name":"Alex Rivera","email":"analyst@tennisexplore.au","role":"Lead Analyst",...}

curl "http://localhost:8000/players/search?name=Alex"
```

PowerShell equivalent for `TOKEN` test uses `Invoke-RestMethod`.

---

## 3. Frontend — Vite + React

### 3.1 Env

Create `frontend/.env`:

```ini
VITE_API_URL=http://localhost:8000
```

For production set to your deployed backend URL, e.g. `https://api.tennisexplore.au`.

Vite also proxies `/auth` to `http://localhost:8000` via `frontend/vite.config.js` (dev only).

### 3.2 Install & Run

```bash
cd frontend

npm install

# development
npm run dev -- --host 0.0.0.0 --port 5173
# open http://localhost:5173 -> login analyst@tennisexplore.au / ace123 -> /ai-chatbot

# production build + preview
npm run build
npm run preview -- --host 0.0.0.0 --port 4173
# open http://localhost:4173

# or serve dist/ via nginx / static host
# npx serve -s dist -l 4173
```

### 3.3 Verify

```bash
curl http://localhost:5173/ | head -20
# <!DOCTYPE html> <title>Tennis Explore</title>
```

---

## 4. Common Pitfalls

- **Run backend from project root**, not `backend/`: `backend.structured_data.api` import fails otherwise. Always `cd 735-Tennis-Explore && python -m uvicorn backend.structured_data.api:app ...`
- **Port mismatch**: `backend/structured_data/database.py` defaults to `5433`, but postgres default is `5432`. Override via `backend/.env` `STRUCTURED_DB_PORT=5432`.
- **CORS**: backend allows `allow_origins=["*"]` in `backend/structured_data/api.py`. For credentialed prod, set explicit frontend origin.
- **JWT secret**: change `JWT_SECRET` in production, keep >=32 chars.
- **Windows psql**: add `C:\Program Files\PostgreSQL\16\bin` to `PATH` or use full path.

---

## 5. One-liner startup (after initial setup)

**macOS / Linux**

```bash
pg_isready -h localhost -p 5432 || pg_ctl -D $(brew --prefix)/var/postgresql@16 -l /tmp/pg.log start  # or sudo systemctl start postgresql
cd 735-Tennis-Explore && nohup python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
cd frontend && npm run dev -- --host 0.0.0.0 --port 5173
```

**Windows (PowerShell)**

```powershell
pg_isready -h localhost -p 5432; if ($LASTEXITCODE -ne 0) { pg_ctl -D "$env:PGDATA" -l pg.log start }
cd 735-Tennis-Explore; python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 --reload
# new terminal
cd frontend; npm run dev -- --host 0.0.0.0 --port 5173
```

**Docker quick prod**

```bash
docker run -d --name tennis-pg -e POSTGRES_USER=tennis_user -e POSTGRES_PASSWORD=tennis_pass -e POSTGRES_DB=tennis_rankings_v2 -p 5432:5432 postgres:16
psql -h localhost -p 5432 -U tennis_user -d tennis_rankings_v2 -f backend/structured_data/sql/01_create_schema.sql
psql -h localhost -p 5432 -U tennis_user -d tennis_rankings_v2 -f backend/auth/sql/01_create_users.sql
cd 735-Tennis-Explore && docker build -t tennis-backend -f backend/Dockerfile .  # if Dockerfile added
```
