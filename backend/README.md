# Vendor Financial Assessment (VFA) - Backend

FastAPI backend for vendor financial assessment with AI-powered document extraction and risk analysis.

## Features

- JWT Authentication
- PDF financial statement extraction using OpenAI GPT-4
- Altman Z-Score calculation and risk assessment
- AI-powered vendor recommendations
- SQLite database (zero configuration)

## Prerequisites

- Python 3.9+
- OpenAI API key

## Quick Start

### 1. Navigate to backend

```bash
cd backend
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
# Required - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional - Change for production
SECRET_KEY=your-super-secret-key-min-32-characters
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

### 6. Open in browser

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**That's it!** Database is created automatically on first run (`vfa.db`).

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── auth.py          # Authentication endpoints
│   │   └── assessments.py   # Assessment endpoints
│   ├── agents/
│   │   ├── extraction_agent.py     # PDF data extraction
│   │   ├── validation_agent.py     # Data validation
│   │   └── recommendation_agent.py # AI recommendations
│   ├── core/
│   │   ├── config.py        # App settings
│   │   ├── database.py      # Database connection
│   │   └── security.py      # JWT & password utils
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
├── uploads/                 # Uploaded PDF files
├── vfa.db                   # SQLite database (auto-created)
├── .env                     # Environment variables
└── requirements.txt
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user info |

### Assessments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/assessments` | Create new assessment |
| GET | `/api/assessments` | List all assessments |
| GET | `/api/assessments/{id}` | Get assessment details |
| POST | `/api/assessments/{id}/statements` | Upload financial statement PDF |
| POST | `/api/assessments/{id}/process` | Process uploaded documents |
| GET | `/api/assessments/{id}/results` | Get analysis results |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./vfa.db` |
| `SECRET_KEY` | JWT signing key | Required for production |
| `OPENAI_API_KEY` | OpenAI API key | **Required** |
| `OPENAI_MODEL` | GPT model for extraction | `gpt-4-turbo-preview` |
| `DEBUG` | Enable debug mode | `false` |
| `UPLOAD_DIR` | Directory for uploaded files | `uploads` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:5173"]` |

## Common Issues

### OpenAI API errors
- Verify your API key is correct in `.env`
- Check you have API credits: https://platform.openai.com/usage
- Ensure the model name is valid

### Module not found
```bash
# Make sure venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Reset database
```bash
rm vfa.db
# Restart server - database recreates automatically
```

## Development

### Generate new secret key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Run with custom port
```bash
uvicorn app.main:app --reload --port 8080
```

### View database (optional)
```bash
# Install sqlite viewer
pip install sqlite-web

# Open browser UI
sqlite_web vfa.db
```
