from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
import os
from tasks import celery_app
import tempfile
from auth import register, login
from database import get_all_users, user_exists_by_email, create_user, get_user
from upload_handler import process_carrier_uploads, get_upload_history
from dotenv import load_dotenv
import os
from phase1 import process_upload_lengths, process_upload_quality_analysis
# from phase2_ocr import process_upload_ocr_analysis
from phase2_ocr_nano import process_upload_ocr_analysis

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
def register_endpoint(username: str = Form(...), password: str = Form(...)):
    """Register new user with username"""
    result = register(username, password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/login/")
def login_endpoint(username: str = Form(...), password: str = Form(...)):
    """Login user with username"""
    result = login(username, password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload-quotes/")
async def upload_quotes(
    request: Request,
    carriers_json: str = Form(...),
    files: list = File(...)
):
    """
    Upload multiple carrier quotes
    
    Form data:
    - carriers_json: JSON string with carrier names
    - files: List of PDF files (property1, liability1, property2, liability2, ...)
    
    Headers:
    - X-User-ID: User ID for routing to user-specific sheet tab
    
    Example:
    {
      "carriers": [
        {"name": "State Farm"},
        {"name": "Allstate"}
      ]
    }
    """
    try:
        import json
        
        # Extract username from headers or use default
        username = request.headers.get('X-User-ID', 'default')
        print(f"📝 Processing upload for user: {username}")
        
        # Parse carriers data
        carriers_info = json.loads(carriers_json)
        carriers = carriers_info.get("carriers", [])
        
        if not carriers:
            raise HTTPException(status_code=400, detail="No carriers provided")
        
        # Files can be 0 to 4 per carrier (property, liability, liquor, workersComp) - completely optional
        min_files = 0
        max_files = len(carriers) * 4
        
        if len(files) < min_files or len(files) > max_files:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 0-{max_files} files for {len(carriers)} carriers, got {len(files)}"
            )
        
        # Process files for each carrier
        carriers_data = []
        
        # Initialize all carriers with None
        for carrier in carriers:
            carriers_data.append({
                "carrierName": carrier.get("name", f"Carrier_{len(carriers_data)+1}"),
                "propertyPDF": None,
                "liabilityPDF": None,
                "liquorPDF": None,
                "workersCompPDF": None
            })
        
        # Get file metadata list
        form_data = await request.form()
        file_metadata_list = form_data.getlist('file_metadata')
        
        # Process each file with its metadata
        for idx, file in enumerate(files):
            if idx < len(file_metadata_list):
                try:
                    metadata = json.loads(file_metadata_list[idx])
                    carrier_index = metadata.get('carrierIndex')
                    file_type = metadata.get('type')
                    
                    # Read file
                    file_content = await file.read()
                    
                    # Assign to correct carrier and type
                    if 0 <= carrier_index < len(carriers_data):
                        if file_type == 'property':
                            carriers_data[carrier_index]['propertyPDF'] = file_content
                        elif file_type == 'liability':
                            carriers_data[carrier_index]['liabilityPDF'] = file_content
                        elif file_type == 'liquor':
                            carriers_data[carrier_index]['liquorPDF'] = file_content
                        elif file_type == 'workersComp':
                            carriers_data[carrier_index]['workersCompPDF'] = file_content
                except Exception as e:
                    print(f"Error processing file metadata: {e}")
                    raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
        
        # Process uploads (username already extracted from headers above)
        result = process_carrier_uploads(carriers_data, username)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("message"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in upload_quotes: {str(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/upload-history/")
def get_history(user_id: str = None):
    """
    Get upload history for a user or all uploads
    """
    try:
        result = get_upload_history(user_id)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confirm-upload/")
def confirm_upload(
    uploadId: str = Form(...)
):
    """
    Confirm upload execution
    
    This endpoint is called after the user reviews the uploaded files
    and confirms they want to proceed.
    """
    try:
        return {
            "success": True,
            "message": f"Upload confirmed",
            "uploadId": uploadId
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/phase1/process")
def process_phase1(uploadId: str):
    try:
        result = process_upload_lengths(uploadId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in process_phase1: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/phase1/quality-analysis")
def analyze_quality(uploadId: str):
    """
    Queue Phase 1 quality analysis task.
    Files are already uploaded to GCS - this just queues the processing.
    Returns immediately so users don't wait.
    Processing happens in background queue (one at a time).
    """
    try:
        from tasks import process_phase1_task
        # Queue the task - files are already in GCS from upload step
        # User ID is stored in metadata and will be retrieved during processing
        task = process_phase1_task.delay(uploadId)
        print(f"✅ Phase 1 queued for upload: {uploadId}, Task ID: {task.id}")
        return {
            "success": True,
            "message": f"Processing queued. Your upload will be processed shortly.",
            "uploadId": uploadId,
            "taskId": task.id,
            "status": "queued"
        }
    except Exception as e:
        print(f"ERROR in analyze_quality: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/phase2/ocr-analysis")
def analyze_ocr(uploadId: str):
    """
    Run OCR on all PDF pages using Tesseract.
    Can be called manually or automatically triggered after Phase 1.
    """
    try:
        result = process_upload_ocr_analysis(uploadId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in analyze_ocr: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/phase2d/intelligent-combination")
def intelligent_combination(uploadId: str):
    """
    Create intelligent combined file from Phase 2C smart selection results.
    Automatically triggered after Phase 2C completes.
    """
    try:
        from phase2d_intelligent_combination import process_upload_intelligent_combination
        result = process_upload_intelligent_combination(uploadId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in intelligent_combination: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/phase3/llm-extraction")
def llm_extraction(uploadId: str):
    """
    Extract insurance fields using GPT from Phase 2D intelligent combined file.
    Automatically triggered after Phase 2D completes.
    """
    try:
        from phase3_llm import process_upload_llm_extraction
        result = process_upload_llm_extraction(uploadId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in llm_extraction: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/phase5/googlesheets-push")
def googlesheets_push(uploadId: str, sheetName: str = "Insurance Fields Data"):
    """
    DEPRECATED: Use /finalize-upload instead.
    This endpoint pushes individual carriers (causes overwriting).
    """
    try:
        from phase5_googlesheet import process_upload_googlesheets_push
        result = process_upload_googlesheets_push(uploadId, sheetName)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in googlesheets_push: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/finalize-upload")
def finalize_upload(uploadId: str, sheetName: str = "Insurance Fields Data"):
    """
    Finalize upload: Push ALL carriers to Google Sheets in side-by-side format.
    Should be called AFTER all carriers complete Phase 3.
    This prevents individual carriers from overwriting each other.
    """
    try:
        from phase5_googlesheet import finalize_upload_to_sheets
        result = finalize_upload_to_sheets(uploadId, sheetName)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in finalize_upload: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


# ============================================================
# QC System Endpoints
# ============================================================

@app.post("/upload-qc/")
async def upload_qc(
    request: Request,
    policy_pdf: UploadFile = File(...),
    property_cert_pdf: UploadFile = File(None),
    gl_cert_pdf: UploadFile = File(None),
    username: str = Form(...)
):
    """
    Upload policy PDF and certificate PDFs for QC processing
    
    Form data:
    - policy_pdf: Policy PDF file
    - property_cert_pdf: Property certificate PDF
    - gl_cert_pdf: GL certificate PDF
    - username: Username for tracking
    
    Returns:
        upload_id and task_id for tracking
    """
    try:
        import json
        import uuid
        from datetime import datetime
        
        print(f"📝 QC upload received from user: {username}")
        
        # Generate unique upload ID
        upload_id = f"qc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        print(f"   Upload ID: {upload_id}")
        
        # Read file contents
        policy_content = await policy_pdf.read()
        print(f"   Policy PDF size: {len(policy_content)} bytes")
        
        # Upload policy PDF to GCS
        policy_blob_path = f"qc/uploads/{upload_id}/policy.pdf"
        blob = bucket.blob(policy_blob_path)
        blob.upload_from_string(policy_content, content_type='application/pdf')
        policy_gcs_path = f"gs://{bucket_name}/{policy_blob_path}"
        print(f"   ✓ Uploaded policy PDF: {policy_blob_path}")
        
        # Upload property certificate if provided
        if property_cert_pdf:
            property_cert_content = await property_cert_pdf.read()
            print(f"   Property Certificate size: {len(property_cert_content)} bytes")
            property_cert_blob_path = f"qc/uploads/{upload_id}/property_cert.pdf"
            blob = bucket.blob(property_cert_blob_path)
            blob.upload_from_string(property_cert_content, content_type='application/pdf')
            print(f"   ✓ Uploaded property certificate: {property_cert_blob_path}")
        else:
            print(f"   ⊘ Property certificate not provided")
        
        # Upload GL certificate if provided
        if gl_cert_pdf:
            gl_cert_content = await gl_cert_pdf.read()
            print(f"   GL Certificate size: {len(gl_cert_content)} bytes")
            gl_cert_blob_path = f"qc/uploads/{upload_id}/gl_cert.pdf"
            blob = bucket.blob(gl_cert_blob_path)
            blob.upload_from_string(gl_cert_content, content_type='application/pdf')
            print(f"   ✓ Uploaded GL certificate: {gl_cert_blob_path}")
        else:
            print(f"   ⊘ GL certificate not provided")
        
        # Queue QC processing task
        from tasks import process_qc_task
        task = process_qc_task.delay(upload_id, policy_gcs_path, username)
        print(f"   ✓ Queued QC task: {task.id}")
        
        return {
            "success": True,
            "upload_id": upload_id,
            "task_id": task.id,
            "status": "queued",
            "message": "QC processing started"
        }
    
    except Exception as e:
        print(f"❌ QC upload failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/qc-results/{upload_id}")
def get_qc_results(upload_id: str):
    """
    Retrieve QC results for a given upload_id
    
    Returns:
        - llm_results: Extracted policy fields for Property and GL
        - flagged_results: Color-coded comparison results
        - certificates: Proxy URLs for property and GL certificate PDFs
    """
    try:
        from qc_integration import get_qc_results
        
        print(f"📥 Retrieving QC results for: {upload_id}")
        
        results = get_qc_results(upload_id)
        
        if "error" in results:
            raise HTTPException(status_code=404, detail=results["error"])
        
        # Debug: Print what we got
        print(f"📊 Results keys: {list(results.keys())}")
        print(f"   - flagged_results: {results.get('flagged_results') is not None}")
        print(f"   - llm_results: {results.get('llm_results') is not None}")
        
        # Generate proxy URLs instead of signed URLs to avoid CORS
        certificates = {
            "property": None,
            "gl": None
        }
        
        # Check if certificates exist and generate proxy URLs
        try:
            property_cert_path = f"qc/uploads/{upload_id}/property_cert.pdf"
            blob = bucket.blob(property_cert_path)
            if blob.exists():
                certificates["property"] = f"/qc-cert/{upload_id}/property"
                print(f"✓ Property certificate available")
        except Exception as e:
            print(f"⚠️  Property cert check failed: {e}")
        
        try:
            gl_cert_path = f"qc/uploads/{upload_id}/gl_cert.pdf"
            blob = bucket.blob(gl_cert_path)
            if blob.exists():
                certificates["gl"] = f"/qc-cert/{upload_id}/gl"
                print(f"✓ GL certificate available")
        except Exception as e:
            print(f"⚠️  GL cert check failed: {e}")
        
        results["certificates"] = certificates
        
        print(f"✅ Returning results with flagged_results: {results.get('flagged_results') is not None}")
        
        return {
            "success": True,
            "upload_id": upload_id,
            "data": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get QC results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/qc-cert/{upload_id}/{cert_type}")
def get_qc_certificate(upload_id: str, cert_type: str):
    """
    Proxy endpoint to serve certificate PDFs (avoids CORS issues)
    """
    try:
        if cert_type not in ["property", "gl"]:
            raise HTTPException(status_code=400, detail="Invalid certificate type")
        
        cert_path = f"qc/uploads/{upload_id}/{cert_type}_cert.pdf"
        blob = bucket.blob(cert_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        # Download and return the PDF
        pdf_content = blob.download_as_bytes()
        
        from fastapi.responses import Response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={cert_type}_cert.pdf"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to serve certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))