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

@celery_app.task
def process_ocr_task(upload_id: str):
    """
    Background task to process OCR on all PDFs for an upload.
    Returns immediately to caller, OCR runs in background.
    """
    try:
        from phase2_ocr import process_upload_ocr_analysis
        # from phase2_ocr_nano import process_upload_ocr_analysis
        print(f"📦 Starting OCR task for upload: {upload_id}")
        result = process_upload_ocr_analysis(upload_id)
        
        if result.get('success'):
            print(f"✅ OCR task completed for upload: {upload_id}")
        else:
            print(f"❌ OCR task failed for upload: {upload_id}: {result.get('error')}")
        
        return result
    except Exception as e:
        print(f"❌ OCR task error for upload: {upload_id}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

