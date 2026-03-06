import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import OAuthToken, User

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def get_flow():
    """Build the Google OAuth flow from environment variables."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
    )


@router.get("/login")
def login():
    """Step 1: Redirect the user to Google's OAuth consent screen."""
    flow = get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",   # Ensures we get a refresh token
        prompt="consent",        # Forces Google to always return a refresh token
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
def oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    Step 2: Google redirects here after the user logs in.
    We exchange the code for tokens and store them in Postgres.
    """
    flow = get_flow()

    # Exchange the authorization code for access + refresh tokens
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Use the access token to get the user's Google profile info
    user_info_service = build("oauth2", "v2", credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()

    google_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name")

    # Upsert the user (create if new, update if existing)
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Parse token expiry if available
    expiry = None
    if credentials.expiry:
        expiry = credentials.expiry.replace(tzinfo=timezone.utc)

    # Upsert the OAuth tokens for this user
    token_record = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    if token_record:
        token_record.access_token = credentials.token
        token_record.refresh_token = credentials.refresh_token or token_record.refresh_token
        token_record.token_expiry = expiry
        token_record.scopes = " ".join(credentials.scopes or [])
    else:
        token_record = OAuthToken(
            user_id=user.id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=expiry,
            scopes=" ".join(credentials.scopes or []),
        )
        db.add(token_record)

    db.commit()

    return {
        "message": "Login successful! Tokens stored in database.",
        "user": {"email": email, "name": name},
    }
