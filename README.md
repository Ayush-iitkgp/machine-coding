# Odin AI

A chat application with a React frontend and FastAPI backend.

## Project Structure

```
odin-ai/
├── backend/          # FastAPI Python backend
│   ├── main.py       # Chat API
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

- Docker
- Docker Compose

---

## Setup & Run

### Option 1: Docker (recommended)

1. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

2. From the project root:
   ```bash
   docker compose up --build
   ```

3. Open:
   - **Chat app**: http://localhost:5173
   - **API docs**: http://localhost:8000/docs

Both services support hot reload—edit files and changes apply without restarting.

---

### Option 2: Local development

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

3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

   - API: http://127.0.0.1:8000  
   - API docs: http://127.0.0.1:8000/docs  

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
| `/chat`    | POST   | Send a message and get a response |
| `/docs`    | GET    | Interactive API documentation     |

**Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```
