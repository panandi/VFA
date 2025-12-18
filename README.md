# VFA Application

A full-stack application with a React frontend and FastAPI backend.

## Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS
- React Router DOM

**Backend:**
- FastAPI
- PostgreSQL + SQLAlchemy
- Alembic (database migrations)
- OpenAI / LangGraph (AI features)

## Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL

## Setup

### 1. Clone and Navigate

```bash
cd VFA
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

Edit `backend/.env` and configure:
- `DATABASE_URL` - Your PostgreSQL connection string
- `SECRET_KEY` - A secure random string for JWT
- `OPENAI_API_KEY` - Your OpenAI API key

### 3. Database Setup

```bash
# Make sure PostgreSQL is running
# Create the database
createdb vfa

# Run migrations
cd backend
alembic upgrade head
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

## Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate  # if not already activated
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000

API docs available at: http://localhost:8000/docs

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend runs at: http://localhost:5173

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key |
| `OPENAI_API_KEY` | OpenAI API key for AI features |
| `OPENAI_MODEL` | OpenAI model (default: gpt-4-turbo-preview) |
| `DEBUG` | Enable debug mode (true/false) |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL (default: http://localhost:8000/api) |

## Scripts

### Frontend

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Backend

- `uvicorn app.main:app --reload` - Start development server
- `alembic upgrade head` - Run database migrations
- `alembic revision --autogenerate -m "message"` - Create new migration
