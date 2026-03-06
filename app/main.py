from fastapi import FastAPI
from app.db.database import Base, engine
from app.routes import auth, calendar

# Create all tables in the database on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Technovation Scheduling Backend",
    description="Backend API for the Technovation coach scheduling system",
    version="0.1.0",
)

# Register route groups
app.include_router(auth.router)
app.include_router(calendar.router)


@app.get("/")
def root():
    return {"message": "Technovation backend is running!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
