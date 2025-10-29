from celery import Celery
from dotenv import load_dotenv
import os
from google.cloud import storage
from pathlib import Path

load_dotenv()

# Set Google credentials from .env file
google_cloud_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if google_cloud_credentials:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_cloud_credentials

# Create Celery app
celery_app = Celery(__name__)
celery_app.config_from_object('celery_config')

# Initialize Google Cloud Storage
client = storage.Client()
bucket_name = os.getenv('BUCKET_NAME', 'deployment')
bucket = client.get_bucket(bucket_name)

@celery_app.task
def example_task(message):
    """Example task that can be called from your FastAPI app"""
    print(f"Processing: {message}")
    return f"Task completed: {message}"

