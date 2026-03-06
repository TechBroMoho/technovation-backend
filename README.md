# Technovation Backend

FastAPI + PostgreSQL backend for the Technovation coach scheduling system.

## Project Structure

```
technovation-backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── db/
│   │   └── database.py      # DB connection + session
│   ├── models/
│   │   └── models.py        # SQLAlchemy table definitions
│   └── routes/
│       ├── auth.py          # Google OAuth login + callback
│       └── calendar.py      # Test Google Calendar API call
├── .env.example             # Template for secrets
├── requirements.txt
└── README.md
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up your `.env` file
```bash
cp .env.example .env
# Fill in your values in .env
```

You'll need:
- A **PostgreSQL database** (local or via [Neon.tech](https://neon.tech) / [Supabase](https://supabase.com) — both free)
- A **Google Cloud project** with OAuth 2.0 credentials ([instructions here](https://console.cloud.google.com/))
  - Set the redirect URI to: `http://localhost:8000/auth/callback`
  - Enable the **Google Calendar API** and **Google OAuth2 API**

### 3. Run the server
```bash
uvicorn app.main:app --reload
```

The server will be at `http://localhost:8000`

## Testing the Demo Flow

1. Go to `http://localhost:8000/auth/login` in your browser
2. Log in with Google
3. You'll be redirected back and see a success message
4. Test the calendar call: `http://localhost:8000/calendar/test/your@email.com`

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Health check |
| GET | `/auth/login` | Redirects to Google OAuth |
| GET | `/auth/callback` | Google redirects here after login |
| GET | `/calendar/test/{email}` | Lists stored user's calendars |

## Database Tables

- **users** — Google ID, email, name
- **oauth_tokens** — access token, refresh token, expiry, linked to user
- **bookings** — placeholder for Cal.com integration
