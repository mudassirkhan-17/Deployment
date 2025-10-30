import fitz
import os
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import storage

BUCKET_NAME = 'deployment'
PDF_FOLDER = 'pdf'
METADATA_FILE = f'{PDF_FOLDER}/uploads_metadata.json'


def extract_with_pymupdf(pdf_file, page_num):
    """Extract text using PyMuPDF"""
    try:
        doc = fitz.open(pdf_file)
        page = doc[page_num - 1]  # PyMuPDF uses 0-based indexing
        page_text = page.get_text()
        doc.close()
        return page_text
    except Exception as e:
        return f"Error extracting page {page_num}: {e}"


def _get_bucket() -> storage.bucket.Bucket:
    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def _read_metadata(bucket: storage.bucket.Bucket) -> Dict[str, Any]:
    blob = bucket.blob(METADATA_FILE)
    if not blob.exists():
        raise FileNotFoundError(f"{METADATA_FILE} not found in bucket {BUCKET_NAME}")
    content = blob.download_as_string().decode('utf-8')
    import json as _json
    return _json.loads(content)


def _blob_path_from_gs_uri(gs_uri: str) -> str:
    # gs://deployment/pdf/filename.pdf -> pdf/filename.pdf
    prefix = f"gs://{BUCKET_NAME}/"
    if gs_uri.startswith(prefix):
        return gs_uri[len(prefix):]
    return gs_uri  # assume already relative


def _download_length(bucket: storage.bucket.Bucket, blob_path: str) -> int:
    blob = bucket.blob(blob_path)
    content = blob.download_as_bytes()
    return len(content)


def process_upload_lengths(upload_id: str) -> Dict[str, Any]:
    """
    Given an upload_id, read metadata and compute byte lengths for any PDFs present
    per carrier. Returns a structured dict suitable for JSON response.
    """
    bucket = _get_bucket()
    metadata = _read_metadata(bucket)

    uploads: List[Dict[str, Any]] = metadata.get('uploads', [])
    record = next((u for u in uploads if u.get('uploadId') == upload_id), None)
    if record is None:
        return {"success": False, "error": f"uploadId {upload_id} not found"}

    results: List[Dict[str, Any]] = []
    for carrier in record.get('carriers', []):
        carrier_name = carrier.get('carrierName')
        files_info: List[Dict[str, Any]] = []
        for file_type in ['propertyPDF', 'liabilityPDF']:
            pdf_info = carrier.get(file_type)
            if not pdf_info:
                continue
            gs_path = pdf_info.get('path')
            if not gs_path:
                continue
            blob_path = _blob_path_from_gs_uri(gs_path)
            try:
                length_bytes = _download_length(bucket, blob_path)
                files_info.append({
                    'type': file_type,
                    'path': gs_path,
                    'length': length_bytes,
                })
            except Exception as e:
                files_info.append({
                    'type': file_type,
                    'path': gs_path,
                    'error': str(e),
                })
        results.append({
            'carrierName': carrier_name,
            'files': files_info,
        })

    return {
        'success': True,
        'uploadId': upload_id,
        'carriers': results,
    }




if __name__ == "__main__":
    pdf_file = ""
    
    