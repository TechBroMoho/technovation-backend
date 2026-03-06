from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db.database import get_db
from app.models.models import User, OAuthToken

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/test/{user_email}")
def test_calendar(user_email: str, db: Session = Depends(get_db)):
    """
    Test endpoint: look up a user's stored tokens and list their Google Calendars.
    This proves the full pipeline works: DB → tokens → Google API call.
    """
    # Find user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found with email: {user_email}")

    # Find their tokens
    token_record = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    if not token_record:
        raise HTTPException(status_code=404, detail="No tokens found for this user. Have they logged in?")

    # Reconstruct Google credentials from stored tokens
    credentials = Credentials(
        token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
    )

    # Call the Google Calendar API
    service = build("calendar", "v3", credentials=credentials)
    calendar_list = service.calendarList().list().execute()
    calendars = [
        {"id": c["id"], "summary": c.get("summary", "Unnamed")}
        for c in calendar_list.get("items", [])
    ]

    return {
        "user": user.email,
        "calendars_found": len(calendars),
        "calendars": calendars,
    }
