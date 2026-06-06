from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import models, schemas, auth
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

import os
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "112345092693-pupt6aflejpc70esti0en7gcrg2cmp0h.apps.googleusercontent.com")
app = FastAPI(title="Full Auth System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.post("/auth/register", response_model=schemas.UserResponse)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        name     = body.name,
        email    = body.email,
        password = auth.hash_password(body.password),
        source   = "email"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login")
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth.verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_token({"user_id": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email
        }
    }


@app.post("/auth/google")
def google_login(body: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        id_info = id_token.verify_oauth2_token(
            body.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    email   = id_info.get("email")
    name    = id_info.get("name")
    picture = id_info.get("picture")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            name    = name,
            email   = email,
            source  = "google",
            picture = picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = auth.create_token({"user_id": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":      user.id,
            "name":    user.name,
            "email":   user.email,
            "picture": user.picture
        }
    }


@app.get("/auth/me")
def get_me(token: str, db: Session = Depends(get_db)):
    payload = auth.verify_token(token)
    user = db.query(models.User).filter(models.User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
