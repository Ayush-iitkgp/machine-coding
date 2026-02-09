# Staff Engineer Interview - Development Environment Setup

This document provides setup instructions and verification steps for the pre-interview technical requirements.

## Installed Tools & Versions

| Tool | Version | Status |
|------|---------|--------|
| **FastAPI** | 0.128.5 | ✅ Installed |
| **Uvicorn** | 0.40.0 | ✅ Installed |
| **Vite** | 7.3.1 | ✅ Installed |
| **Cursor IDE** | Free version | ✅ In use |
| **Node.js** | 20.19.6 (via nvm) | Required for Vite |

---

## 1. FastAPI (Python Framework)

### Location
- Backend: `backend/`
- Virtual environment: `backend/venv/`

### Verify Installation
```bash
cd backend
source venv/bin/activate
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
uvicorn --version
```

### Run the API
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```
- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

### Screenshot for Verification
1. Run `uvicorn main:app --reload` in terminal
2. Open http://127.0.0.1:8000/docs in browser
3. Screenshot showing the FastAPI Swagger UI with version visible

---

## 2. Cursor IDE

### Verification
- You're already using Cursor IDE (this project is open in it)
- Free version: https://cursor.sh

### Screenshot for Verification
1. Open Cursor IDE with this project
2. Screenshot showing the project structure in the file explorer
3. Ensure Cursor version is visible (Help → About or status bar)

---

## 3. Vite Development Environment

### Prerequisite: Node.js 20+
This project uses `.nvmrc` to specify Node 20. If you use nvm:
```bash
nvm use
# or: nvm use 20
```

### Verify Installation
```bash
cd frontend
npm list vite
npm run dev
```

### Run the Dev Server
```bash
cd frontend
npm install   # if not already done
npm run dev
```
- App: http://localhost:5173

### Screenshot for Verification
1. Run `npm run dev` in terminal
2. Screenshot showing "VITE v7.3.1 ready" and the Local URL
3. Optional: Screenshot of the app in browser at http://localhost:5173

---

## Quick Start (Both Servers)

**Terminal 1 - Backend:**
```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm run dev
```

---

## Screenshots Checklist for Interview Submission

- [ ] **FastAPI**: Terminal showing `uvicorn` running + browser showing `/docs` (Swagger UI)
- [ ] **Cursor IDE**: Project open in Cursor with file explorer visible
- [ ] **Vite**: Terminal showing `VITE v7.3.1 ready` with dev server URL

Ensure version numbers are clearly visible in each screenshot.
