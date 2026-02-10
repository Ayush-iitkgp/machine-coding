# Odin AI

A chat application with a React frontend and FastAPI backend.

## Project Structure

```
odin-ai/
├── backend/          # FastAPI Python backend
│   ├── main.py       # Chat API
│   ├── database.py   # PostgreSQL connection
│   ├── models.py     # SQLAlchemy models
│   ├── alembic/      # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # React + Vite frontend
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Dependencies

### Backend (Python)

| Package   | Version   | Purpose                    |
|-----------|-----------|----------------------------|
| fastapi   | ≥0.115.0  | Web framework              |
| uvicorn   | ≥0.32.0   | ASGI server                |
| sqlalchemy| ≥2.0.0    | ORM & database toolkit     |
| asyncpg   | ≥0.29.0   | Async PostgreSQL driver    |
| alembic   | ≥1.13.0   | Database migrations        |
| psycopg2-binary | ≥2.9.9 | Sync PostgreSQL (for migrations) |

### Frontend (Node.js)

| Package   | Version   | Purpose                    |
|-----------|-----------|----------------------------|
| react     | ^19.2.0   | UI framework               |
| react-dom | ^19.2.0   | React DOM renderer         |
| vite      | ^7.3.1    | Build tool & dev server    |

## Prerequisites

**Option A: Local development**

- Python 3.10+
- Node.js 20+ (recommend using [nvm](https://github.com/nvm-sh/nvm))
- pip

**Option B: Docker**

- Docker (or [Colima](https://github.com/abiosoft/colima) on Mac)
- Docker Compose

> **Colima users:** Set `DOCKER_HOST=unix://$HOME/.colima/default/docker.sock`. If builds fail with "no such host" pulling images, see [docs/DOCKER_TROUBLESHOOTING.md](docs/DOCKER_TROUBLESHOOTING.md).

---

## Setup & Run

### Option 1: Docker (recommended)

1. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

2. From the project root:
   ```bash
   docker compose up --build
   ```

   Migrations run automatically when the backend starts. To run manually:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

3. Open:
   - **Chat app**: http://localhost:5173
   - **API docs**: http://localhost:8000/docs
   - **Health** (incl. DB status): http://localhost:8000/health

Services: PostgreSQL (port 5432), backend (8000), frontend (5173). All support hot reload.

---

### Option 2: Local development

**PostgreSQL** must be running. Either:

- Start only the database with Docker: `docker compose up -d db`
- Or use a local PostgreSQL instance (create database `odin_ai`, user `odin`, password `odin`)

#### Backend

1. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set the database URL (if not using defaults):
   ```bash
   export DATABASE_URL=postgresql+asyncpg://odin:odin@localhost:5432/odin_ai
   ```

4. Run migrations:
   ```bash
   alembic upgrade head
   ```

5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

   - API: http://127.0.0.1:8000  
   - API docs: http://127.0.0.1:8000/docs  
   - Health: http://127.0.0.1:8000/health  

#### Frontend

1. Ensure Node.js 20+ is active (e.g. `nvm use` if using nvm).

2. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

3. Run the dev server:
   ```bash
   npm run dev
   ```

   - App: http://localhost:5173  

#### Run both

Terminal 1 (backend):

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload
```

Terminal 2 (frontend):

```bash
cd frontend && npm run dev
```

---

## API

| Endpoint   | Method | Description                |
|------------|--------|----------------------------|
| `/chat`    | POST   | Send a message and get a response (stored in PostgreSQL) |
| `/health`  | GET    | Health check and database connectivity |
| `/docs`    | GET    | Interactive API documentation     |

**Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

---

## Database migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/).

**Apply migrations:**
```bash
cd backend
alembic upgrade head
```

**Create a new migration (after changing models):**
```bash
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

**Rollback one revision:**
```bash
alembic downgrade -1
```

Uses `DATABASE_URL` (async URL is converted to sync for migrations).
