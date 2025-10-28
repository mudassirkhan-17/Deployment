from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import FileResponse
from google.cloud import storage
import os
# from tasks import celery_app, analyze_pdf_task
import tempfile
# from auth import register, login, verify_token
from dotenv import load_dotenv
import os

load_dotenv()

google_cloud_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if google_cloud_credentials:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_cloud_credentials

app = FastAPI()

client = storage.Client()
bucket_name = 'deployment'
bucket = client.get_bucket(bucket_name)

@app.get("/")
def read_root():
    return {"message": "Hello, World! Insurance PDF Analysis API"}

