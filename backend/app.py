from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
import os
from tasks import celery_app
import tempfile
from auth import register, login
from database import get_all_users, user_exists_by_email, create_user, get_user
from dotenv import load_dotenv
import os

load_dotenv()

google_cloud_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if google_cloud_credentials:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_cloud_credentials

app = FastAPI()

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for ngrok + Vercel)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = storage.Client()
bucket_name = 'deployment'
bucket = client.get_bucket(bucket_name)

@app.get("/")
def read_root():
    return {"message": "Hello, World! Insurance PDF Analysis API"}

@app.post("/register/")
def register_endpoint(email: str = Form(...), password: str = Form(...)):
    """Register new user"""
    result = register(email, password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/login/")
def login_endpoint(email: str = Form(...), password: str = Form(...)):
    """Login user"""
    result = login(email, password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.get("/health")
def health_check():
    return {"status": "healthy"}