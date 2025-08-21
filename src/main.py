import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# PostgreSQL connection URL - uses environment variable with fallback
# CHANGE TO be the database (postgres) created locally , use compose is better.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@host.docker.internal:5432/mydb")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Pydantic schema
class UserCreate(BaseModel):
    name: str
    email: str

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API route to write data into PostgreSQL
@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = User(name=user.name, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")

# Health check endpoint for Kubernetes
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fastapi-postgres-app"}

# Readiness probe endpoint for Kubernetes
@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        # Simple database connectivity check - just test the connection
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not ready", "database": "disconnected", "error": str(e)}
