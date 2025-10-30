import fitz
import os
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import storage
import io

BUCKET_NAME = 'deployment'
PDF_FOLDER = 'pdf'
METADATA_FILE = f'{PDF_FOLDER}/uploads_metadata.json'


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


def _download_bytes(bucket: storage.bucket.Bucket, blob_path: str) -> bytes:
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()


def _analyze_text_quality(text: str) -> Dict[str, Any]:
    """Analyze text quality and return metrics"""
    metrics = {
        'total_chars': len(text),
        'cid_codes': text.count('(cid:'),
        'readable_words': len([word for word in text.split() if len(word) > 2 and word.isalpha()]),
        'special_chars': len([char for char in text if not char.isalnum() and char not in ' .,!?()-']),
        'gibberish_ratio': 0,
        'confidence_score': 0
    }
    
    # Calculate gibberish ratio
    if metrics['total_chars'] > 0:
        metrics['gibberish_ratio'] = metrics['special_chars'] / metrics['total_chars']
    
    # Calculate confidence score (0-100)
    confidence = 100
    confidence -= min(metrics['cid_codes'] * 2, 50)
    confidence -= min(metrics['gibberish_ratio'] * 100, 40)
    
    # Bonus for readable words
    if metrics['readable_words'] > 50:
        confidence += 10
    elif metrics['readable_words'] < 20:
        confidence -= 30
    
    metrics['confidence_score'] = max(confidence, 0)
    
    return metrics


def _classify_page_quality(metrics: Dict[str, Any]) -> str:
    """Classify page quality based on text analysis"""
    
    # Clean page criteria
    if ((metrics['cid_codes'] < 8 and 
         metrics['readable_words'] > 60 and 
         metrics['gibberish_ratio'] < 0.2 and
         metrics['confidence_score'] > 70) or
        (metrics['gibberish_ratio'] < 0.4 and 
         metrics['readable_words'] > 40 and
         metrics['confidence_score'] > 50)):
        return "CLEAN"
    
    # Problem page criteria  
    elif (metrics['cid_codes'] > 10 or 
          metrics['readable_words'] < 20 or 
          metrics['gibberish_ratio'] > 0.5 or
          metrics['confidence_score'] < 30):
        return "PROBLEM"
    
    # Borderline
    else:
        return "BORDERLINE"


def _extract_and_analyze_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract text from PDF bytes and analyze quality"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = doc.page_count
        
        results = {
            'clean_pages': [],
            'problem_pages': [],
            'borderline_pages': [],
            'all_metrics': {},
            'total_pages': total_pages
        }
        
        for page_num in range(1, total_pages + 1):
            page = doc[page_num - 1]
            text = page.get_text()
            
            metrics = _analyze_text_quality(text)
            quality = _classify_page_quality(metrics)
            
            page_result = {
                'page_num': page_num,
                'quality': quality,
                'metrics': metrics
            }
            
            results['all_metrics'][page_num] = metrics
            
            if quality == "CLEAN":
                results['clean_pages'].append(page_result)
            elif quality == "PROBLEM":
                results['problem_pages'].append(page_result)
            else:
                results['borderline_pages'].append(page_result)
        
        doc.close()
        return results
        
    except Exception as e:
        return {
            'error': str(e),
            'total_pages': 0,
            'clean_pages': [],
            'problem_pages': [],
            'borderline_pages': []
        }


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
                length_bytes = len(_download_bytes(bucket, blob_path))
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


def _save_quality_results_to_gcs(bucket: storage.bucket.Bucket, upload_id: str, results: Dict[str, Any], analysis_data: Dict[str, Any]) -> None:
    """Save quality analysis results to GCS phase1/results folder"""
    import json as _json
    
    # Create phase1/results folder structure at root level
    results_path = f'phase1/results/{upload_id}_quality_analysis.json'
    
    # Save JSON to GCS
    blob = bucket.blob(results_path)
    blob.upload_from_string(
        _json.dumps(results, indent=2),
        content_type='application/json'
    )
    
    print(f"✅ Saved quality analysis to: gs://{BUCKET_NAME}/{results_path}")
    
    # Save phase1_report.txt to GCS
    try:
        _save_report_txt(bucket, upload_id, analysis_data)
    except Exception as e:
        print(f"Warning: Failed to save report.txt: {e}")
    
    # Save pymupdf_clean_pages_only.txt to GCS
    try:
        _save_clean_pages_txt(bucket, upload_id, analysis_data)
    except Exception as e:
        print(f"Warning: Failed to save clean_pages.txt: {e}")


def _save_report_txt(bucket: storage.bucket.Bucket, upload_id: str, analysis_data: Dict[str, Any]) -> None:
    """Save phase1_report.txt to GCS"""
    report_path = f'phase1/results/{upload_id}_phase1_report.txt'
    
    report_lines = []
    report_lines.append("PHASE 1 SCREENING REPORT - PYMUPDF ANALYSIS")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for carrier in analysis_data.get('carriers', []):
        carrier_name = carrier.get('carrierName', 'Unknown')
        report_lines.append(f"\nCarrier: {carrier_name}")
        report_lines.append("-" * 80)
        
        for file_data in carrier.get('files', []):
            file_type = file_data.get('type', 'unknown')
            total_pages = file_data.get('total_pages', 0)
            clean_count = file_data.get('clean_pages', 0)
            problem_count = file_data.get('problem_pages', 0)
            borderline_count = file_data.get('borderline_pages', 0)
            
            report_lines.append(f"\n{file_type.upper()}:")
            report_lines.append(f"Total Pages: {total_pages}")
            report_lines.append(f"Clean Pages: {clean_count}")
            report_lines.append(f"Problem Pages: {problem_count}")
            report_lines.append(f"Borderline Pages: {borderline_count}")
            
            # Detailed metrics by page
            page_details = file_data.get('page_details', {})
            if page_details:
                report_lines.append("\nDETAILED METRICS BY PAGE:")
                report_lines.append("-" * 50)
                for page_num, metrics in page_details.items():
                    clean_pages = file_data.get('clean_page_numbers', [])
                    problem_pages = file_data.get('problem_page_numbers', [])
                    
                    if page_num in clean_pages:
                        quality = "CLEAN"
                    elif page_num in problem_pages:
                        quality = "PROBLEM"
                    else:
                        quality = "BORDERLINE"
                    
                    report_lines.append(
                        f"Page {page_num:2d}: {quality:12s} | "
                        f"{metrics['readable_words']:3d} words | "
                        f"{metrics['cid_codes']:3d} (cid:XX) | "
                        f"{metrics['confidence_score']:5.1f}% confidence | "
                        f"{metrics['gibberish_ratio']:5.1%} gibberish"
                    )
    
    report_content = "\n".join(report_lines)
    
    blob = bucket.blob(report_path)
    blob.upload_from_string(report_content, content_type='text/plain')
    
    print(f"✅ Saved report to: gs://{BUCKET_NAME}/{report_path}")


def _save_clean_pages_txt(bucket: storage.bucket.Bucket, upload_id: str, analysis_data: Dict[str, Any]) -> None:
    """Save pymupdf_clean_pages_only.txt to GCS (requires fetching PDFs again)"""
    # Note: We need to fetch PDF bytes again to extract clean page text
    # This is a simplified version without full text extraction
    clean_pages_path = f'phase1/results/{upload_id}_pymupdf_clean_pages_only.txt'
    
    report_lines = []
    report_lines.append("PYMUPDF CLEAN PAGES ONLY - FOR SMART SELECTION")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Summary of clean pages
    for carrier in analysis_data.get('carriers', []):
        carrier_name = carrier.get('carrierName', 'Unknown')
        
        for file_data in carrier.get('files', []):
            file_type = file_data.get('type', 'unknown')
            total_pages = file_data.get('total_pages', 0)
            clean_count = file_data.get('clean_pages', 0)
            clean_pages_nums = file_data.get('clean_page_numbers', [])
            
            report_lines.append(f"Carrier: {carrier_name} - {file_type.upper()}")
            report_lines.append(f"Total Pages: {total_pages}")
            report_lines.append(f"Clean Pages: {clean_count}")
            report_lines.append(f"Clean Page Numbers: {clean_pages_nums}")
            report_lines.append("")
            
            # List clean pages with basic metrics
            page_details = file_data.get('page_details', {})
            for page_num in clean_pages_nums:
                if page_num in page_details:
                    metrics = page_details[page_num]
                    report_lines.append(f"PAGE {page_num}:")
                    report_lines.append("-" * 40)
                    report_lines.append(f"Quality: CLEAN")
                    report_lines.append(f"Confidence: {metrics['confidence_score']:.1f}%")
                    report_lines.append(f"Readable Words: {metrics['readable_words']}")
                    report_lines.append(f"Total Characters: {metrics['total_chars']}")
                    report_lines.append(f"(cid:XX) Codes: {metrics['cid_codes']}")
                    report_lines.append(f"Gibberish Ratio: {metrics['gibberish_ratio']:.2%}")
                    report_lines.append("")
                    report_lines.append("Note: Full text content not included in summary")
                    report_lines.append("=" * 80)
                    report_lines.append("")
    
    report_content = "\n".join(report_lines)
    
    blob = bucket.blob(clean_pages_path)
    blob.upload_from_string(report_content, content_type='text/plain')
    
    print(f"✅ Saved clean pages summary to: gs://{BUCKET_NAME}/{clean_pages_path}")


def process_upload_quality_analysis(upload_id: str) -> Dict[str, Any]:
    """
    Given an upload_id, read metadata, fetch PDFs from GCS, and analyze quality.
    Returns structured JSON with page analysis results.
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
        files_analysis: List[Dict[str, Any]] = []
        
        for file_type in ['propertyPDF', 'liabilityPDF']:
            pdf_info = carrier.get(file_type)
            if not pdf_info:
                continue
            
            gs_path = pdf_info.get('path')
            if not gs_path:
                continue
            
            blob_path = _blob_path_from_gs_uri(gs_path)
            
            try:
                # Download PDF bytes
                pdf_bytes = _download_bytes(bucket, blob_path)
                
                # Analyze quality
                analysis = _extract_and_analyze_pdf(pdf_bytes)
                
                files_analysis.append({
                    'type': file_type,
                    'path': gs_path,
                    'length_bytes': len(pdf_bytes),
                    'total_pages': analysis.get('total_pages', 0),
                    'clean_pages': len(analysis.get('clean_pages', [])),
                    'problem_pages': len(analysis.get('problem_pages', [])),
                    'borderline_pages': len(analysis.get('borderline_pages', [])),
                    'quality_summary': {
                        'total': analysis.get('total_pages', 0),
                        'clean': len(analysis.get('clean_pages', [])),
                        'problem': len(analysis.get('problem_pages', [])),
                        'borderline': len(analysis.get('borderline_pages', []))
                    },
                    'page_details': analysis.get('all_metrics', {}),
                    'clean_page_numbers': [p['page_num'] for p in analysis.get('clean_pages', [])],
                    'problem_page_numbers': [p['page_num'] for p in analysis.get('problem_pages', [])],
                    'borderline_page_numbers': [p['page_num'] for p in analysis.get('borderline_pages', [])]
                })
                
            except Exception as e:
                files_analysis.append({
                    'type': file_type,
                    'path': gs_path,
                    'error': str(e)
                })
        
        results.append({
            'carrierName': carrier_name,
            'files': files_analysis,
        })

    # Prepare result
    result = {
        'success': True,
        'uploadId': upload_id,
        'carriers': results,
    }
    
    # Save to GCS results folder (pass both result and results for analysis)
    try:
        _save_quality_results_to_gcs(bucket, upload_id, result, {'carriers': results})
    except Exception as e:
        print(f"Warning: Failed to save results to GCS: {e}")
    
    return result




if __name__ == "__main__":
    pdf_file = ""
    
