"""
Phase 3: LLM Information Extraction
Extracts 34 specific property coverage fields from insurance documents using GPT.
Works with Google Cloud Storage.
Uses Joblib for parallel chunk processing.
"""
import json
import openai
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import storage
from dotenv import load_dotenv
from joblib import Parallel, delayed

load_dotenv()

BUCKET_NAME = 'deployment'

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables!")
    print("Phase 3 LLM extraction will fail without OpenAI API key")


def _get_bucket() -> storage.bucket.Bucket:
    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def _download_text_from_gcs(bucket: storage.bucket.Bucket, blob_path: str) -> str:
    """Download text file from GCS"""
    blob = bucket.blob(blob_path)
    if not blob.exists():
        return ""
    return blob.download_as_string().decode('utf-8')


def _upload_json_to_gcs(bucket: storage.bucket.Bucket, blob_path: str, data: Dict[str, Any]) -> None:
    """Upload JSON file to GCS"""
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    print(f"✅ Uploaded to: gs://{BUCKET_NAME}/{blob_path}")


def read_combined_file_from_gcs(bucket: storage.bucket.Bucket, file_path: str) -> List[Dict[str, Any]]:
    """Read the intelligent combined file from Phase 2D"""
    try:
        content = _download_text_from_gcs(bucket, file_path)
        if not content:
            print(f"Warning: Combined file not found at {file_path}")
            return []
        
        print(f"Reading intelligent combined file from: {file_path}")
        
        # Extract all pages
        all_pages = []
        page_sections = re.findall(
            r'PAGE (\d+) \((PyMuPDF|OCR) \(.*?\)\):.*?TEXT CONTENT:.*?------------------------------\n(.*?)\n={80}',
            content,
            re.DOTALL
        )
        
        for page_num, source, page_text in page_sections:
            all_pages.append({
                'page_num': int(page_num),
                'source': source,
                'text': page_text.strip()
            })
        
        # Sort by page number
        all_pages.sort(key=lambda x: x['page_num'])
        
        print(f"Extracted {len(all_pages)} pages from combined file")
        for page in all_pages:
            print(f"  Page {page['page_num']:2d} ({page['source']:8s}): {len(page['text']):5,} chars")
        
        return all_pages
        
    except Exception as e:
        print(f"Error reading combined file: {e}")
        return []


def create_chunks(all_pages: List[Dict[str, Any]], chunk_size: int = 4) -> List[Dict[str, Any]]:
    """Split pages into chunks of 4 pages each"""
    chunks = []
    
    for i in range(0, len(all_pages), chunk_size):
        chunk_pages = all_pages[i:i+chunk_size]
        
        # Combine text from all pages in this chunk
        chunk_text = ""
        page_nums = []
        sources = []
        
        for page in chunk_pages:
            chunk_text += f"=== PAGE {page['page_num']} ({page['source']}) ===\n"
            chunk_text += page['text'] + "\n\n"
            page_nums.append(page['page_num'])
            sources.append(page['source'])
        
        chunks.append({
            'chunk_num': len(chunks) + 1,
            'pages': chunk_pages,
            'page_nums': page_nums,
            'sources': sources,
            'text': chunk_text.strip(),
            'char_count': len(chunk_text)
        })
    
    print(f"\nCreated {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"  Chunk {chunk['chunk_num']}: Pages {chunk['page_nums']} ({chunk['char_count']:,} chars)")
    
    return chunks


def extract_with_llm(chunk: Dict[str, Any], chunk_num: int, total_chunks: int) -> Dict[str, Any]:
    """Extract information using LLM"""
    
    prompt = f"""
    Analyze the following insurance document text and extract ONLY the 34 specific property coverage fields listed below.
    
    CRITICAL: Extract ONLY these 34 fields. Do NOT create new field names or extract any other information.
    
    THE 34 SPECIFIC FIELDS TO EXTRACT (with examples):
    1. Construction Type - Look for: "FRAME", "Frame", "Joisted Masonry", "Masonry Non-Combustible"
    2. Valuation and Coinsurance - Look for: "Replacement Cost, 80%", "RC, 90%", "Actual Cash Value"
       CRITICAL: Valuation and Coinsurance are often in SEPARATE columns/fields in tables:
       - Column 1: "Valuation: RC" or "Valuation: Replacement Cost" or just "RC"
       - Column 2: "Coins %: 90%" or "Coinsurance: 80%" or just "90%"
       You MUST find BOTH parts and COMBINE them as "RC, 90%" or "Replacement Cost, 90%"
       Common abbreviations: RC = Replacement Cost, ACV = Actual Cash Value
    3. Cosmetic Damage - Look for: "Excluded", "Included", "Cosmetic Damage is Excluded"
    4. Building - Look for: "$500,000", "$648,000 (RC, 90%)", "Coverage not required"
       CRITICAL: If in a table with Valuation and Coins % columns, include them: "$648,000 (RC, 90%)"
    5. Pumps - Look for: "$10,000.00", "$160,000 (RC, 90%)"
       CRITICAL: If in a table with Valuation and Coins % columns, include them: "$160,000 (RC, 90%)"
    6. Canopy - Look for: "$40,000", "$160,000 (RC, 90%)"
       CRITICAL: If in a table with Valuation and Coins % columns, include them: "$160,000 (RC, 90%)"
    7. ROOF EXCLUSION - Look for: "Included", "Excluded", "Cosmetic Damage is Excluded"
    8. Roof Surfacing - Look for: "ACV only applies to roofs that are more than 15 years old", "CP 10 36", "CP 10 36 applies"
       CRITICAL: Often appears in "Subject to:" sections as "CP 10 36 – Limitations on Coverage for Roof Surfacing applies"
       ALSO check endorsement/form lists for "CP 10 36 10 12" or similar codes
       Extract as: "CP 10 36 applies" or "Limitations on Coverage for Roof Surfacing applies" or the full text found
       Form codes like "CP 10 36" are VALID VALUES - DO NOT leave empty if you find them
    9. Roof Surfacing -Limitation - Look for: "ACV on Roof", "Cosmetic Damage is Excluded", "CP 10 36"
       CRITICAL: If "CP 10 36" is mentioned anywhere in Subject to/endorsements, extract it here too
       Extract as: "CP 10 36 applies" or "Limitations on Coverage for Roof Surfacing applies"
       This field and "Roof Surfacing" often have the SAME value when referencing form codes
    10. Business Personal Property - Look for: "$50,000.00", "$50,000 (RC, 90%)", "$200,000"
        If in a table with Valuation and Coins % columns, include them: "$50,000 (RC, 90%)"
    11. Business Income - Look for: "$100,000", "$120,000 (RC, 1/6)", "$100,000 (RC, 1/3)", "$100,000"
        NOTE: Business Income often has coinsurance 1/6 or 1/3 (different from 90%)
        If in a table with Valuation and Coins % columns, include them: "$100,000 (RC, 1/3)"
        Extract dollar amount even if valuation/coinsurance not shown
    12. Business Income with Extra Expense - Look for: "$100,000", "$100,000 (RC, 1/6)", "$100,000 (RC, 1/3)"
        If in a table with Valuation and Coins % columns, include them
    13. Equipment Breakdown - Look for: "Included", "$225,000"
    14. Outdoor Signs - Look for: "$10,000", "$5,000", "Included", "Deductible $250"
    15. Signs Within 1,000 Feet to Premises - Look for: any signs within 1,000 feet coverage
    16. Employee Dishonesty - Look for: "$5,000", "Included", "Not Offered"
    17. Money & Securities - Look for: "$10,000", "$5,000", "On Premises $2,500 / Off Premises $2,500"
    18. Money and Securities (Inside; Outside) - Look for: separate inside/outside limits
    19. Spoilage - Look for: "$5,000", "$10,000", "Deductible $250"
    20. Theft - Look for: "Sublimit: $5,000", "Ded: $2,500", "Sublimit $10,000"
    21. Theft Sublimit - Look for: "$5,000", "$15,000", "$10,000", "Theft Sublimit: $10,000"
        May appear in endorsement sections or main tables
    22. Theft Deductible - Look for: "$2,500", "$1,000", "$250", "Theft Deductible: $1,000"
        May appear in endorsement sections or main tables
    23. Windstorm or Hail - Look for: "$2,500", "2%", "1%", "Min Per Building", "Excluded", "$2,500 Min"
        Often in coverage tables under "Wind/Hail Ded" column
        Can be dollar amount, percentage, or "Excluded"
    24. Named Storm Deductible - Look for: any named storm deductible
    25. Wind and Hail and Named Storm exclusion - Look for: any wind/hail/named storm exclusion
    26. All Other Perils Deductible - Look for: "$2,500", "$1,000", "$5,000", "$5000"
        Often in coverage tables under "AOP Ded" column - extract the dollar amount shown
        Extract ANY dollar amount found near "AOP" or "All Other Perils"
    27. Fire Station Alarm - Look for: "$2,500.00", "Local", "Central"
    28. Burglar Alarm - Look for: "Local", "Central", "Active Central Station"
    29. Terrorism - Look for: "APPLIES", "Excluded", "Included", "Can be added"
        Also look for: "TRIA", "Subject to TRIA", "Terrorism Risk Insurance Act"
    30. Protective Safeguards Requirements - Look for: any protective safeguards requirements
    31. Minimum Earned Premium (MEP) - Look for: "25%", "MEP: 25%", "35%"
    32. Property Premium - Look for: "TOTAL CHARGES W/O TRIA $7,176.09", "W/O TRIA $7,176.09, WITH TRIA $7,441.13"
        CRITICAL: Look for "TOTAL CHARGES" or "Total Premium (With/Without Terrorism)" - NOT "Property Premium"
        "Property Premium" is base only; we need TOTAL which includes endorsements
        DO NOT extract from "Summary of Cost" section (that combines all policies - property, GL, liquor)
        Extract from property coverage section as: "W/O TRIA $7,176.09, WITH TRIA $7,441.13" or single value
    33. Total Premium (With/Without Terrorism) - Look for: "W/O TRIA $7,176.09, WITH TRIA $7,441.13"
        Same as Property Premium - look for TOTAL CHARGES, not base property premium
        DO NOT extract from "Summary of Cost" section
    34. Policy Premium - Look for: "$2,500.00", "Policy Premium", "Base Premium"
    
    EXTRACTION RULES:
    - Extract EXACTLY as written in the document
    - Look for SIMILAR PATTERNS even if exact examples don't match
    - For Dollar Amounts: Look for any dollar amounts ($X,XXX, $X,XXX.XX)
    - For Percentages: Look for any percentages (X%, X.X%)
    - For Deductibles: Look for "Deductible", "Ded", "Min", "Per" with amounts
      * Check coverage tables for columns like "Wind/Hail Ded", "AOP Ded", etc.
      * Can be: dollar amounts ($5,000), percentages (2%), or status (Excluded)
    - For Sublimits: Look for "Sublimit", "Limit", "Max" with amounts
    - For Coverage Status: Look for "Included", "Excluded", "Not Offered", "Coverage not required"
    - For "Valuation and Coinsurance": MUST extract TWO pieces and combine them:
      * Part 1 (Valuation): RC, Replacement Cost, ACV, Actual Cash Value
      * Part 2 (Coinsurance %): Look for "Coins %", "Coinsurance", or percentage (80%, 90%, 100%)
      * COMBINE as: "RC, 90%" or "Replacement Cost, 80%" - DO NOT extract just "RC" alone
      * If in a table, these may be in separate columns - find both and combine them
    - For COVERAGE AMOUNTS (Building, Pumps, Canopy, BPP, Business Income):
      * If in a TABLE with Valuation and Coins % columns, include them: "$648,000 (RC, 90%)"
      * Example: "Building #01 $648,000 RC 90%" should extract as "$648,000 (RC, 90%)"
      * Business Income often has 1/6 or 1/3 coinsurance instead of 90%
      * If valuation columns not present, extract just the dollar amount
    - For FORM CODES (Roof Surfacing, Terrorism, Windstorm):
      * Form codes like "CP 10 36", "TRIA" are VALID VALUES
      * Often appear in "Subject to:" sections at the end of quotes
      * Extract as "CP 10 36 applies" or "TRIA" - these are complete values
    - For ENDORSEMENT SECTIONS (Theft Sublimit/Deductible, Outdoor Signs, etc.):
      * Check "Additional Endorsements" or "Additional Coverages" sections
      * Format: "Field Name: $value" (e.g., "Theft Sublimit: $10,000")
    - For PREMIUM EXTRACTION (Property Premium, Total Premium):
      * Extract ONLY "TOTAL CHARGES" or "Total Premium" from property coverage section
      * If document shows BOTH "Property Premium" ($6,303) and "Total Premium" ($7,176), extract the TOTAL
      * "Property Premium" = base coverage only; "Total Premium" = base + endorsements (we want TOTAL)
      * CRITICAL: DO NOT extract from "Summary of Cost" section at the end
      * "Summary of Cost" combines property + GL + liquor + fees = wrong value
      * Look for "TOTAL CHARGES W/O TRIA" or "Total Premium (With/Without Terrorism)" in property section
    - If field is not found, set to null
    - Do NOT hallucinate or make up values
    - Do NOT combine or modify existing values (EXCEPT for Valuation/Coinsurance and Coverage Amounts as noted above)
    - Do NOT extract administrative, financial, or policy information
    
    IMPORTANT: This is chunk {chunk_num} of {total_chunks}. This chunk contains pages {chunk['page_nums']}.
    
    CRITICAL PAGE NUMBER EXTRACTION:
    - The document text below has clear page markers: "=== PAGE X (OCR) ===" or "=== PAGE X (PyMuPDF) ==="
    - For each field you extract, find which "=== PAGE X ===" section it appears in
    - Extract the EXACT page number X from that section marker
    - Look BACKWARDS from the field to find the most recent "=== PAGE X ===" marker
    - DO NOT guess or estimate page numbers - use the exact number from the marker
    - Multiple fields can be on the same page
    
    Example: If you see:
    === PAGE 7 (OCR) ===
    Commercial Property
    Building #01: $648,000
    Construction: MNC
    
    Then "Construction Type" should have page: 7 (because it's under "=== PAGE 7 ===" marker)
    
    CRITICAL: Return ONLY valid JSON with this exact format:
    {{
        "Construction Type": {{"value": "MNC", "page": 7}},
        "Building": {{"value": "$648,000 (RC, 90%)", "page": 7}},
        "Business Income": {{"value": "$120,000 (RC, 1/6)", "page": 7}},
        "Roof Surfacing": {{"value": "CP 10 36 applies", "page": 9}},
        "Roof Surfacing -Limitation": {{"value": "Limitations on Coverage for Roof Surfacing applies", "page": 9}},
        "Windstorm or Hail": {{"value": "Excluded", "page": 7}},
        "All Other Perils Deductible": {{"value": "$5,000", "page": 7}},
        "Theft Sublimit": {{"value": "$10,000", "page": 8}},
        "Theft Deductible": {{"value": "$1,000", "page": 8}},
        "Terrorism": {{"value": "TRIA", "page": 9}},
        "Property Premium": {{"value": "W/O TRIA $7,176.09, WITH TRIA $7,441.13", "page": 9}}
    }}
    
    If a field is not found, use: {{"value": null, "page": null}}
    
    IMPORTANT: 
    - Check entire document: main tables, endorsement sections, and "Subject to:" sections
    - For Premium: Extract "TOTAL CHARGES" from property section, NOT "Summary of Cost" at end
    - If both "Property Premium" and "Total Premium" exist, extract the TOTAL (includes endorsements)
    - "Summary of Cost" section combines all policies (property + GL + liquor) - DO NOT use it
    
    Do not provide explanations, context, or any text outside the JSON object.
    
    Document text:
    {chunk['text']}
    """
    
    try:
        print(f"  Processing chunk {chunk_num} with LLM (Pages {chunk['page_nums']})...")
        
        # Use OpenAI API (correct format)
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.responses.create(
            model="gpt-5-nano",
            input=prompt,
            reasoning={
                "effort": "low"
            },
            text={
                "verbosity": "low"
            }
        )
        
        result_text = response.output_text.strip()
        
        # Check if response is empty
        if not result_text:
            print(f"  [ERROR] Empty response from LLM")
            return {'_metadata': {'chunk_num': chunk_num, 'page_nums': chunk['page_nums'], 'error': 'Empty LLM response'}}
        
        # Clean up markdown code blocks if present
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        # Try to parse JSON
        try:
            result_json = json.loads(result_text)
            
            # Convert to compatible format
            converted_json = {}
            individual_page_fields = {}
            
            for field, data in result_json.items():
                if isinstance(data, dict) and 'value' in data and 'page' in data:
                    converted_json[field] = data['value']
                    if data['value'] is not None and data['page'] is not None:
                        individual_page_fields[field] = [data['page']]
                        print(f"    Found {field} on Page {data['page']}")
                else:
                    converted_json[field] = data
            
            # Add metadata
            converted_json['_metadata'] = {
                'chunk_num': chunk_num,
                'page_nums': chunk['page_nums'],
                'sources': chunk['sources'],
                'char_count': chunk['char_count'],
                'individual_page_fields': individual_page_fields
            }
            
            found_fields = len([k for k, v in converted_json.items() if v is not None and k != '_metadata'])
            print(f"  [SUCCESS] Extracted {found_fields} fields from pages {chunk['page_nums']}")
            return converted_json
            
        except json.JSONDecodeError as e:
            print(f"  [ERROR] Failed to parse JSON response")
            print(f"  Raw LLM response: {result_text[:200]}...")
            return {'_metadata': {'chunk_num': chunk_num, 'page_nums': chunk['page_nums'], 'error': f'JSON parse failed: {str(e)}'}}
            
    except Exception as e:
        print(f"  [ERROR] LLM processing failed: {e}")
        return {'_metadata': {'chunk_num': chunk_num, 'page_nums': chunk['page_nums'], 'error': str(e)}}


def merge_extraction_results(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge results from all chunks, prioritizing non-null values"""
    
    # Define the expected fields
    expected_fields = [
        "Construction Type", "Valuation and Coinsurance", "Cosmetic Damage", "Building",
        "Pumps", "Canopy", "ROOF EXCLUSION", "Roof Surfacing", "Roof Surfacing -Limitation",
        "Business Personal Property", "Business Income", "Business Income with Extra Expense",
        "Equipment Breakdown", "Outdoor Signs", "Signs Within 1,000 Feet to Premises",
        "Employee Dishonesty", "Money & Securities", "Money and Securities (Inside; Outside)",
        "Spoilage", "Theft", "Theft Sublimit", "Theft Deductible", "Windstorm or Hail",
        "Named Storm Deductible", "Wind and Hail and Named Storm exclusion",
        "All Other Perils Deductible", "Fire Station Alarm", "Burglar Alarm", "Terrorism",
        "Protective Safeguards Requirements", "Minimum Earned Premium (MEP)", "Property Premium",
        "Total Premium (With/Without Terrorism)", "Policy Premium"
    ]
    
    merged_result = {}
    
    # Initialize all expected fields as null
    for field in expected_fields:
        merged_result[field] = None
    
    # Collect all unique fields found by LLM
    all_found_fields = set()
    for chunk_result in all_results:
        if '_metadata' in chunk_result and 'error' not in chunk_result['_metadata']:
            for field in chunk_result.keys():
                if field != '_metadata':
                    all_found_fields.add(field)
    
    # Add any new fields found by LLM
    for field in all_found_fields:
        if field not in merged_result:
            merged_result[field] = None
    
    # Track which specific page each field was found on
    field_sources = {}
    
    # Merge results from all chunks
    for chunk_result in all_results:
        if '_metadata' in chunk_result and 'error' in chunk_result['_metadata']:
            continue  # Skip failed chunks
            
        chunk_pages = chunk_result['_metadata']['page_nums']
        
        for field, value in chunk_result.items():
            if field == '_metadata':
                continue
                
            if value is not None and value != "" and value != "null":
                if merged_result[field] is None:
                    merged_result[field] = value
                    field_sources[field] = [chunk_pages[0]] if chunk_pages else []
                else:
                    if merged_result[field] != value:
                        print(f"  Multiple values found for {field}: '{merged_result[field]}' (pages {field_sources[field]}) and '{value}' (pages {chunk_pages})")
    
    # Add source information to merged result
    merged_result['_extraction_summary'] = {
        'total_chunks_processed': len(all_results),
        'successful_chunks': len([r for r in all_results if '_metadata' in r and 'error' not in r['_metadata']]),
        'field_sources': field_sources
    }
    
    return merged_result


def save_extraction_results_to_gcs(
    bucket: storage.bucket.Bucket,
    merged_result: Dict[str, Any],
    carrier_name: str,
    safe_carrier_name: str,
    file_type: str,
    timestamp: str
) -> str:
    """Save extraction results to GCS"""
    type_short = file_type.replace('PDF', '').lower()
    final_file_path = f'phase3/results/{safe_carrier_name}_{type_short}_final_validated_fields_{timestamp}.json'
    
    # Get page sources from extraction summary
    field_sources = merged_result.get('_extraction_summary', {}).get('field_sources', {})
    
    # Create final validated fields structure
    final_fields = {}
    for field_name, llm_value in merged_result.items():
        if not field_name.startswith('_'):  # Skip metadata fields
            source_pages = field_sources.get(field_name, [])
            page_info = f"Page {source_pages[0]}" if source_pages else ""
            
            final_fields[field_name] = {
                "llm_value": llm_value,
                "vlm_value": None,  # No VLM validation
                "final_value": llm_value,  # Use LLM value as final
                "confidence": "llm_only",
                "source_page": page_info
            }
    
    _upload_json_to_gcs(bucket, final_file_path, final_fields)
    print(f"✅ Saved final validated fields to: gs://{BUCKET_NAME}/{final_file_path}")
    
    return final_file_path


def _check_if_all_carriers_complete(bucket: storage.bucket.Bucket, upload_id: str) -> bool:
    """
    Check if all carriers in this upload have completed Phase 3.
    Returns True if this is the last carrier to finish.
    """
    try:
        # Read metadata to get total carriers
        from phase1 import _read_metadata
        full_metadata = _read_metadata(bucket)
        uploads = full_metadata.get('uploads', [])
        upload_record = next((u for u in uploads if u.get('uploadId') == upload_id), None)
        
        if not upload_record:
            print(f"⚠️  Upload {upload_id} not found in metadata")
            return False
        
        carriers = upload_record.get('carriers', [])
        total_carriers = len(carriers)
        
        if total_carriers == 0:
            print(f"⚠️  No carriers found for upload {upload_id}")
            return False
        
        # Count how many carriers have completed Phase 3
        completed_count = 0
        for carrier in carriers:
            carrier_name = carrier.get('carrierName', 'Unknown')
            safe_name = carrier_name.lower().replace(" ", "_").replace("&", "and")
            
            # Check for property, liability, and liquor final validated fields
            for file_type in ['propertyPDF', 'liabilityPDF', 'liquorPDF']:
                pdf_info = carrier.get(file_type)
                if not pdf_info or not pdf_info.get('path'):
                    continue
                
                # Extract timestamp from PDF path
                pdf_path = pdf_info['path']
                timestamp_match = re.search(r'_(\d{8}_\d{6})\.pdf$', pdf_path)
                if not timestamp_match:
                    continue
                
                timestamp = timestamp_match.group(1)
                type_short = file_type.replace('PDF', '').lower()
                
                # Check if Phase 3 result exists
                final_file_path = f"phase3/results/{safe_name}_{type_short}_final_validated_fields_{timestamp}.json"
                blob = bucket.blob(final_file_path)
                if blob.exists():
                    completed_count += 1
        
        # Calculate total expected files (property + liability + liquor for each carrier)
        expected_files = 0
        for carrier in carriers:
            if carrier.get('propertyPDF') and carrier.get('propertyPDF').get('path'):
                expected_files += 1
            if carrier.get('liabilityPDF') and carrier.get('liabilityPDF').get('path'):
                expected_files += 1
            if carrier.get('liquorPDF') and carrier.get('liquorPDF').get('path'):
                expected_files += 1
        
        print(f"📊 Upload {upload_id}: {completed_count}/{expected_files} files completed")
        
        return completed_count == expected_files and expected_files > 0
        
    except Exception as e:
        print(f"❌ Error checking completion status: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_upload_llm_extraction(upload_id: str) -> Dict[str, Any]:
    """
    Given an upload_id, read Phase 2D results from GCS,
    extract insurance fields using LLM, and save results.
    """
    if not openai.api_key:
        return {"success": False, "error": "OpenAI API key not configured. Cannot run Phase 3."}
    
    bucket = _get_bucket()
    
    # Read metadata
    from phase1 import _read_metadata
    metadata = _read_metadata(bucket)
    
    uploads: List[Dict[str, Any]] = metadata.get('uploads', [])
    record = next((u for u in uploads if u.get('uploadId') == upload_id), None)
    if record is None:
        return {"success": False, "error": f"uploadId {upload_id} not found"}
    
    all_results: List[Dict[str, Any]] = []
    
    for carrier in record.get('carriers', []):
        carrier_name = carrier.get('carrierName')
        safe_carrier_name = carrier_name.lower().replace(" ", "_").replace("&", "and")
        
        for file_type in ['propertyPDF', 'liabilityPDF', 'liquorPDF']:
            pdf_info = carrier.get(file_type)
            if not pdf_info:
                continue
            
            gs_path = pdf_info.get('path')
            if not gs_path:
                continue
            
            try:
                # Extract timestamp from PDF path
                original_pdf_path = pdf_info.get('path')
                timestamp_match = re.search(r'_(\d{8}_\d{6})\.pdf$', original_pdf_path)
                if not timestamp_match:
                    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                else:
                    report_timestamp = timestamp_match.group(1)
                
                type_short = file_type.replace('PDF', '').lower()
                
                # Find latest intelligent combined file
                combined_files = list(bucket.list_blobs(prefix=f'phase2d/results/{safe_carrier_name}_{type_short}_intelligent_combined_'))
                if not combined_files:
                    print(f"Warning: No combined file found for {carrier_name} {file_type}")
                    continue
                
                # Get latest file
                combined_file = sorted(combined_files, key=lambda x: x.time_created)[-1].name
                
                # Read combined file
                all_pages = read_combined_file_from_gcs(bucket, combined_file)
                if not all_pages:
                    print(f"Warning: No pages extracted from {combined_file}")
                    continue
                
                # Create chunks (4 pages each)
                chunks = create_chunks(all_pages, chunk_size=4)
                
                # Process each chunk with LLM - PARALLELIZED for faster processing
                # Route to correct extractor based on file type
                print(f"\nProcessing {len(chunks)} chunks in parallel...")
                
                def process_single_chunk(chunk):
                    """Process one chunk - called in parallel"""
                    print(f"  Processing Chunk {chunk['chunk_num']}/{len(chunks)}...")
                    if file_type == 'liabilityPDF':
                        # Import GL-specific extractor for liability
                        from phase3_gl import extract_with_llm as extract_with_llm_gl
                        return extract_with_llm_gl(chunk, chunk['chunk_num'], len(chunks))
                    elif file_type == 'liquorPDF':
                        # Import Liquor-specific extractor for liquor
                        from phase3_liqour import extract_with_llm as extract_with_llm_liquor
                        return extract_with_llm_liquor(chunk, chunk['chunk_num'], len(chunks))
                    else:
                        # Use property extraction for property PDFs
                        return extract_with_llm(chunk, chunk['chunk_num'], len(chunks))
                
                # Process all chunks in parallel (n_jobs=-1 uses all available cores)
                # backend='threading' is perfect for I/O-bound LLM API calls
                chunk_results = Parallel(
                    n_jobs=-1,
                    backend='threading',
                    verbose=5
                )(
                    delayed(process_single_chunk)(chunk)
                    for chunk in chunks
                )
                
                # Merge all results - route to correct merge function based on file type
                print(f"\nMerging results from {len(chunk_results)} chunks...")
                if file_type == 'liabilityPDF':
                    # Import GL-specific merge for liability extraction
                    from phase3_gl import merge_extraction_results as merge_extraction_results_gl
                    merged_result = merge_extraction_results_gl(chunk_results)
                elif file_type == 'liquorPDF':
                    # Import Liquor-specific merge for liquor extraction
                    from phase3_liqour import merge_extraction_results as merge_extraction_results_liquor
                    merged_result = merge_extraction_results_liquor(chunk_results)
                else:
                    # Use property merge for property PDFs
                    merged_result = merge_extraction_results(chunk_results)
                
                # Save results to GCS
                final_path = save_extraction_results_to_gcs(bucket, merged_result, carrier_name, safe_carrier_name, file_type, report_timestamp)
                
                all_results.append({
                    'carrierName': carrier_name,
                    'fileType': file_type,
                    'finalFields': f'gs://{BUCKET_NAME}/{final_path}',
                    'totalFields': len([k for k in merged_result.keys() if not k.startswith('_')]),
                    'fieldsFound': len([k for k, v in merged_result.items() if v is not None and not k.startswith('_')])
                })
                
            except Exception as e:
                print(f"Error processing {carrier_name} {file_type}: {e}")
                all_results.append({
                    'carrierName': carrier_name,
                    'fileType': file_type,
                    'error': str(e)
                })
    
    result = {
        "success": True,
        "uploadId": upload_id,
        "results": all_results
    }
    
    # Check if all carriers in this upload have completed Phase 3
    print("\n✅ Phase 3 LLM extraction complete!")
    print("🔍 Checking if all carriers are complete...")
    
    if _check_if_all_carriers_complete(bucket, upload_id):
        print("🎉 ALL CARRIERS COMPLETE! Auto-triggering Google Sheets finalization...")
        try:
            from phase5_googlesheet import finalize_upload_to_sheets
            sheets_result = finalize_upload_to_sheets(upload_id)
            if sheets_result.get('success'):
                print("✅ Google Sheets finalization complete!")
                result['sheets_push'] = sheets_result
            else:
                print(f"⚠️  Google Sheets finalization had issues: {sheets_result.get('error')}")
                result['sheets_push_error'] = sheets_result.get('error')
        except Exception as e:
            print(f"❌ Google Sheets finalization failed: {e}")
            import traceback
            traceback.print_exc()
            result['sheets_push_error'] = str(e)
    else:
        print("⏳ Other carriers still processing. Waiting for all to complete...")
        print("💡 Or manually run: /finalize-upload/{uploadId}")
    
    return result
