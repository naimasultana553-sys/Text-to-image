from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

import models, schemas, database, auth, image_service

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="ImagiText AI API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email Configuration (Should use environment variables in production)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("EMAIL_USER", "your-email@gmail.com")
SENDER_PASSWORD = os.getenv("EMAIL_PASS", "your-app-password")

def send_reset_email(target_email: str, code: str):
    if SENDER_EMAIL == "your-email@gmail.com" or SENDER_PASSWORD == "your-app-password":
        logging.warning("Email credentials not configured in .env")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = target_email
        msg['Subject'] = "ImagiText AI - Password Reset Code"
        
        body = f"Your verification code is: {code}\n\nThis code will expire in 15 minutes."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@app.post("/forgot-password")
def forgot_password(req: schemas.ForgotPassword, db: Session = Depends(database.get_db)):
    from datetime import datetime, timezone, timedelta
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        # Security: Don't reveal if user exists, but here we can be helpful for dev
        return {"message": "If this email is registered, you will receive a code."}
    
    import random
    reset_code = f"{random.randint(100000, 999999)}"
    user.reset_code = reset_code
    # Use timezone-aware UTC for robustness
    user.reset_code_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
    db.commit()
    
    logging.info(f"Generated reset code for {req.email}")
    
    # Send real email
    success = send_reset_email(req.email, reset_code)
    
    if success:
        return {"message": "Verification code sent to your email address."}
    else:
        # Fallback for demo if credentials aren't set
        logging.error(f"\n[DEMO FALLBACK] Code for {req.email}: {reset_code}\n")
        return {"message": f"Real email failed (check credentials). For testing, use code: {reset_code}"}

@app.post("/reset-password")
def reset_password(req: schemas.ResetPassword, db: Session = Depends(database.get_db)):
    from datetime import datetime, timezone
    user = db.query(models.User).filter(models.User.email == req.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.reset_code or user.reset_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
        
    # Compare naive UTC times
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.reset_code_expires and user.reset_code_expires < current_time:
        raise HTTPException(status_code=400, detail="Verification code has expired")
    
    user.hashed_password = auth.get_password_hash(req.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()
    return {"message": "Password updated successfully"}

@app.post("/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.User)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

from fastapi import BackgroundTasks

def background_save_image(db_image_id: int, image_url: str):
    from sqlalchemy.orm import Session
    from database import SessionLocal
    import image_service
    
    db = SessionLocal()
    try:
        local_path = image_service.save_image_locally(image_url)
        if local_path:
            db_image = db.query(models.Image).filter(models.Image.id == db_image_id).first()
            if db_image:
                db_image.url = local_path
                db.commit()
    finally:
        db.close()

@app.post("/generate", response_model=schemas.Image)
def generate_image(
    image_req: schemas.ImageCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Generate URL instantly (no waiting for download)
    image_url = image_service.generate_image_ai(image_req.prompt, current_user.id)
    
    # Save to DB with external URL first
    db_image = models.Image(
        user_id=current_user.id,
        prompt=image_req.prompt,
        url=image_url,
        style=image_req.style
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    
    # Start background task to save a local copy if not on Vercel
    if not os.getenv("VERCEL"):
        background_tasks.add_task(background_save_image, db_image.id, image_url)
    
    return db_image

@app.get("/history", response_model=list[schemas.Image])
def get_history(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Image).filter(models.Image.user_id == current_user.id).order_by(models.Image.created_at.desc()).all()

# Serve static files at the end if not on Vercel
if not os.getenv("VERCEL"):
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# On Vercel, the frontend is served via vercel.json rewrites
# But for local fallback, we keep this:
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
