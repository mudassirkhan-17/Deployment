import json
import openai
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../config/.env')

def read_combined_file():
    """Read the intelligent combined file from Phase 2D"""
    # DYNAMIC PATH DETECTION
    combined_paths = [
        'results/intelligent_combined_all_pages.txt',  # When run from property/ (via mine.py)
        '../results/intelligent_combined_all_pages.txt'  # When run from property/src/ (alone)
    ]
    
    combined_file = None
    for path in combined_paths:
        if os.path.exists(path):
            combined_file = path
            break
    
    if not combined_file:
        print("Error: Intelligent combined file not found!")
        print("Please run Phase 2D first to generate intelligent_combined_all_pages.txt")
        return []
    
    print(f"Reading intelligent combined file: {combined_file}")
    
    with open(combined_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all pages
    all_pages = []
    page_sections = re.findall(r'PAGE (\d+) \((PyMuPDF|OCR) \(.*?\)\):.*?TEXT CONTENT:.*?------------------------------\n(.*?)\n={80}', content, re.DOTALL)
    
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

def create_chunks(all_pages, chunk_size=4):
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

def extract_with_llm(chunk, chunk_num, total_chunks):
    """Extract information using LLM with your exact prompt"""
    
    prompt = f"""
    Analyze the following workers compensation insurance document text and extract ONLY the 5 specific workers compensation coverage fields listed below.
    
    CRITICAL: Extract ONLY these 5 fields. Do NOT create new field names or extract any other information.
    
    THE 5 SPECIFIC FIELDS TO EXTRACT (with examples of what to look for):
    1. Limits - Look for: "$1,000,000 Each Accident", "$1,000,000 Policy Limit", "$1,000,000 Each Employee", "$500,000 / $500,000 / $500,000", "$1,000,000 / $1,000,000 / $1,000,000", any workers compensation limits with dollar amounts
    2. FEIN # - Look for: "47-4792684", "39-4013959", "33-4251695", any Federal Employer Identification Numbers (FEIN)
    3. Payroll - Subject to Audit - Look for: "$36,000", "$45,000", "$30,000", any payroll amounts subject to audit
    4. Excluded Officer - Look for: "Parvez Jiwani", "Provide Details", "Details Required", "Officer decision on Inclusion / Exclusion required", any excluded officer information
    5. If Opting out from Workers Compensation Coverage - Look for: "By State Law in GA you are liable --- by not opting any injuries to the employees during work hours will not be covered", any opt-out information or liability statements
    6. Workers Compensation Premium - Look for: "$1,500.00", "WC Premium", "Workers Comp Premium", "TOTAL excl Terrorism", "TOTAL CHARGES W/O TRIA", any workers compensation premium amount (PRIORITY: Look for "TOTAL excl Terrorism" or "TOTAL CHARGES W/O TRIA" first)
    7. Total Premium - Look for: "$3,500.00", "TOTAL incl Terrorism", "TOTAL CHARGES WITH TRIA", "Total Premium", "Annual Premium", any total premium amount
    8. Policy Premium - Look for: "$2,500.00", "Policy Premium", "Base Premium", "Workers Compensation" base amount, any policy premium amount
    
    EXTRACTION RULES:
    - Extract EXACTLY as written in the document
    - Look for SIMILAR PATTERNS even if exact examples don't match
    - For Limits: Look for dollar amounts with "/" separator (e.g., "$X,XXX,XXX / $X,XXX,XXX")
    - For FEIN #: Look for numeric patterns like "XX-XXXXXXX" (Federal Employer Identification Numbers)
    - For Dollar Amounts: Look for any dollar amounts ($X,XXX, $X,XXX.XX, $XXX,XXX)
    - For Officer Information: Extract complete officer details, names, and exclusion/inclusion status
    - For Opt-out Information: Extract complete liability statements and opt-out conditions
    - For Multi-line Values: Extract everything related to that field, preserve line breaks
    - For Complex Values: Extract the complete text block for that field
    - If field is not found, set to null
    - Do NOT hallucinate or make up values
    - Do NOT combine or modify existing values
    - If you see variations not in examples, still extract them exactly as written
    - Do NOT extract administrative, financial, or policy information
    - Do NOT create new field names
    - Do NOT extract policy numbers or legal disclosures
    - Note: Some quotes may have multiple columns (2-3 carriers), extract values for EACH column as separate entries when applicable
    
    IMPORTANT: This is chunk {chunk_num} of {total_chunks}. This chunk contains pages {chunk['page_nums']}. 
    
    For each field you find, look for the nearest page number in the text above it (e.g., "Page 3", "Page 5"). 
    Use the actual page number from the text. Multiple fields can be on the same page.
    
    CRITICAL: Return ONLY valid JSON with this exact format:
    {{
        "Limits": {{"value": "$1,000,000 Each Accident, $1,000,000 Policy Limit, $1,000,000 Each Employee", "page": 5}},
        "FEIN #": {{"value": "47-4792684", "page": 5}},
        "Payroll - Subject to Audit": {{"value": "$36,000", "page": 5}},
        "Excluded Officer": {{"value": "Parvez Jiwani", "page": 5}},
        "If Opting out from Workers Compensation Coverage": {{"value": "By State Law in GA you are liable --- by not opting any injuries to the employees during work hours will not be covered", "page": 3}},
        "Workers Compensation Premium": {{"value": "$1,500.00", "page": 3}},
        "Total Premium": {{"value": "$3,500.00", "page": 3}},
        "Policy Premium": {{"value": "$2,500.00", "page": 3}}
    }}
    
    PAGE DETECTION RULES:
    - Look for "Page X" markers in the text above each field
    - Use the nearest page number found above the field
    - If no page number found, use null for page
    - Multiple fields can share the same page number
    - Extract the actual page number from the text (e.g., "Page 3" = page 3)
    
    If a field is not found, use: {{"value": null, "page": null}}
    Do not provide explanations, context, or any text outside the JSON object.
    
    Document text:
    {chunk['text']}
    """
    
    try:
        print(f"  Processing chunk {chunk_num} with LLM (Pages {chunk['page_nums']})...")
        
        # Use OpenAI API (GPT-5 Responses API format)
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.responses.create(
            model="gpt-5",
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
            result_text = result_text[7:]  # Remove ```json
        if result_text.startswith('```'):
            result_text = result_text[3:]   # Remove ```
        if result_text.endswith('```'):
            result_text = result_text[:-3]  # Remove trailing ```
        result_text = result_text.strip()
        
        # Try to parse JSON
        try:
            result_json = json.loads(result_text)
            
            # Convert new format to old format for compatibility
            converted_json = {}
            individual_page_fields = {}
            
            for field, data in result_json.items():
                if isinstance(data, dict) and 'value' in data and 'page' in data:
                    # New format: {"value": "FRAME", "page": 5}
                    converted_json[field] = data['value']
                    if data['value'] is not None and data['page'] is not None:
                        individual_page_fields[field] = [data['page']]
                        print(f"    Found {field} on Page {data['page']}")
                else:
                    # Old format: direct value
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

def merge_extraction_results(all_results):
    """Merge results from all chunks, prioritizing non-null values"""
    
    # Define the expected fields for WORKERS COMPENSATION INSURANCE
    expected_fields = [
        "Limits",
        "FEIN #",
        "Payroll - Subject to Audit",
        "Excluded Officer",
        "If Opting out from Workers Compensation Coverage",
        "Workers Compensation Premium",
        "Total Premium",
        "Policy Premium"
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
                # If field already has a value, keep the first non-null one
                if merged_result[field] is None:
                    merged_result[field] = value
                    # Store the specific page where this field was found
                    # For now, use the first page of the chunk, but this should be more precise
                    field_sources[field] = [chunk_pages[0]] if chunk_pages else []
                else:
                    # If we have multiple values, note the conflict
                    if merged_result[field] != value:
                        print(f"  Multiple values found for {field}: '{merged_result[field]}' (pages {field_sources[field]}) and '{value}' (pages {chunk_pages})")
    
    # Add source information to merged result
    merged_result['_extraction_summary'] = {
        'total_chunks_processed': len(all_results),
        'successful_chunks': len([r for r in all_results if '_metadata' in r and 'error' not in r['_metadata']]),
        'field_sources': field_sources
    }
    
    return merged_result

def save_extraction_results(merged_result, all_chunk_results):
    """Save extraction results to files"""
    # DYNAMIC PATH DETECTION
    results_paths = [
        'results',  # When run from property/ (via mine.py)
        '../results'  # When run from property/src/ (alone)
    ]
    
    results_dir = None
    for path in results_paths:
        if os.path.exists(path) or os.path.exists(os.path.dirname(path) if os.path.dirname(path) else '.'):
            results_dir = path
            break
    
    if not results_dir:
        results_dir = 'results'  # Default fallback
    
    # Save final merged results (overwrite existing)
    final_file = f"{results_dir}/extracted_insurance_fields.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(merged_result, f, indent=2, ensure_ascii=False)
    
    # Save detailed chunk results (overwrite existing)
    detailed_file = f"{results_dir}/extraction_chunks.json"
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunk_results, f, indent=2, ensure_ascii=False)
    
    # Save summary report (overwrite existing)
    report_file = f"{results_dir}/extraction_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("INSURANCE FIELD EXTRACTION REPORT - STEP 2\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Chunks Processed: {len(all_chunk_results)}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("EXTRACTED FIELDS:\n")
        f.write("-" * 30 + "\n")
        found_fields = 0
        for field, value in merged_result.items():
            if field.startswith('_'):
                continue
            if value is not None:
                found_fields += 1
                source_pages = merged_result['_extraction_summary']['field_sources'].get(field, [])
                f.write(f"{field}: {value} (Pages: {source_pages})\n")
        
        f.write(f"\nSUMMARY:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Fields Found: {found_fields}/{len([f for f in merged_result.keys() if not f.startswith('_')])}\n")
        f.write(f"Success Rate: {found_fields/len([f for f in merged_result.keys() if not f.startswith('_')])*100:.1f}%\n")
    
    return final_file, detailed_file, report_file

def generate_summary(merged_result):
    """Generate console summary"""
    print(f"\n{'='*80}")
    print("STEP 2 SUMMARY - LLM EXTRACTION")
    print(f"{'='*80}")
    
    found_fields = [k for k, v in merged_result.items() if v is not None and not k.startswith('_')]
    total_fields = len([k for k in merged_result.keys() if not k.startswith('_')])
    
    print(f"Total Fields: {total_fields}")
    print(f"Fields Found: {len(found_fields)}")
    print(f"Success Rate: {len(found_fields)/total_fields*100:.1f}%")
    
    if found_fields:
        print(f"\n[SUCCESS] Fields Successfully Extracted:")
        for field in found_fields:
            source_pages = merged_result['_extraction_summary']['field_sources'].get(field, [])
            print(f"  - {field}: {merged_result[field]} (Pages: {source_pages})")
    
    missing_fields = [k for k, v in merged_result.items() if v is None and not k.startswith('_')]
    if missing_fields:
        print(f"\n[MISSING] Fields Not Found:")
        for field in missing_fields:
            print(f"  - {field}")

def create_final_validated_fields(merged_result):
    """Create final_validated_fields.json without VLM validation"""
    # DYNAMIC PATH DETECTION
    results_paths = [
        'results',  # When run from property/ (via mine.py)
        '../results'  # When run from property/src/ (alone)
    ]
    
    results_dir = None
    for path in results_paths:
        if os.path.exists(path) or os.path.exists(os.path.dirname(path) if os.path.dirname(path) else '.'):
            results_dir = path
            break
    
    if not results_dir:
        results_dir = 'results'  # Default fallback
    
    final_fields = {}
    
    # Get page sources from extraction summary
    field_sources = merged_result.get('_extraction_summary', {}).get('field_sources', {})
    
    # Manual corrections for known page locations
    page_corrections = {
        "If Opting out from Workers Compensation Coverage": "Page 3"
    }
    
    for field_name, llm_value in merged_result.items():
        if not field_name.startswith('_'):  # Skip metadata fields
            # Get page numbers where this field was found
            source_pages = field_sources.get(field_name, [])
            
            # Use manual correction if available, otherwise use extracted page
            if field_name in page_corrections:
                page_info = page_corrections[field_name]
            else:
                page_info = f"Page {source_pages[0]}" if source_pages else ""
            
            final_fields[field_name] = {
                "llm_value": llm_value,
                "vlm_value": None,  # No VLM validation
                "final_value": llm_value,  # Use LLM value as final
                "confidence": "llm_only",  # Only LLM confidence
                "source_page": page_info  # Add page information
            }
    
    # Save to file
    final_file = f"{results_dir}/final_validated_fields.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(final_fields, f, indent=2, ensure_ascii=False)
    
    # Also save PDF-specific results
    pdf_file = "pdf/PROPERTY QUOTE1.pdf"  # Default, will be updated by master workflow
    pdf_name = os.path.basename(pdf_file).replace('.pdf', '')
    pdf_specific_file = f'{results_dir}/{pdf_name}_extracted_insurance_fields.json'
    
    with open(pdf_specific_file, 'w', encoding='utf-8') as f:
        json.dump(final_fields, f, indent=2, ensure_ascii=False)
    
    print(f"\n[INFO] Created final_validated_fields.json with LLM-only results")
    print(f"[INFO] Created {pdf_specific_file} for individual PDF results")
    print(f"[INFO] VLM validation skipped to save costs")
    print(f"[INFO] Page information included for each field")
    print(f"[INFO] Applied manual page corrections for known fields")

if __name__ == "__main__":
    # Load API key from environment
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai.api_key:
        print("Error: OPENAI_API_KEY not found in environment variables!")
        print("Please set your API key in the .env file")
        exit(1)
    
    print("STEP 2: WORKERS COMPENSATION LLM INFORMATION EXTRACTION")
    print("=" * 80)
    
    # Read combined file
    all_pages = read_combined_file()
    if not all_pages:
        exit(1)
    
    # Create chunks (4 pages each)
    chunks = create_chunks(all_pages, chunk_size=4)
    
    # Process each chunk with LLM
    all_results = []
    for chunk in chunks:
        print(f"\nProcessing Chunk {chunk['chunk_num']}/{len(chunks)}...")
        result = extract_with_llm(chunk, chunk['chunk_num'], len(chunks))
        all_results.append(result)
    
    # Merge all results
    print(f"\nMerging results from {len(all_results)} chunks...")
    merged_result = merge_extraction_results(all_results)
    
    # Save results
    final_file, detailed_file, report_file = save_extraction_results(merged_result, all_results)
    
    # Generate summary
    generate_summary(merged_result)
    
    # Create final_validated_fields.json (without VLM validation)
    create_final_validated_fields(merged_result)
    
    print(f"\n{'='*80}")
    print("FILES GENERATED:")
    print(f"{'='*80}")
    print(f"Final extraction: {final_file}")
    print(f"Detailed chunks: {detailed_file}")
    print(f"Extraction report: {report_file}")
    print(f"Final validated fields: final_validated_fields.json")
    print(f"\nStep 2 complete! Workers Compensation field extraction finished.")
