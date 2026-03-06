import os
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import OAuthToken, User

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar.readonly",
])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
def login():
    """Step 1: Redirect the user to Google's OAuth consent screen."""
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query_string}")


@router.get("/callback")
def oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    Step 2: Google redirects here after the user logs in.
    Exchange the code for tokens and store them in Postgres.
    """
    # Exchange authorization code for tokens
    token_response = httpx.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    })

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_response.text}")

    tokens = token_response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    # Get user info from Google
    userinfo_response = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    user_info = userinfo_response.json()
    google_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name")

    # Upsert user
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Calculate token expiry
    expiry = None
    if expires_in:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Upsert tokens
    token_record = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    if token_record:
        token_record.access_token = access_token
        token_record.refresh_token = refresh_token or token_record.refresh_token
        token_record.token_expiry = expiry
    else:
        token_record = OAuthToken(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=expiry,
        )
        db.add(token_record)

    db.commit()

    return {
        "message": "Login successful! Tokens stored in database.",
        "user": {"email": email, "name": name},
    }
