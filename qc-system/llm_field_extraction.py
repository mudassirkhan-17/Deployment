"""
LLM Pipeline for Extracting Structured Fields from Extracted Policy Content

This script reads the extracted content from qc_heading_extraction.py
and uses GPT-5 nano to extract structured certificate fields.
Follows the same structure as backend/phase3_llm.py
"""

import json
import os
import openai
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables!")
    print("LLM extraction will fail without OpenAI API key")


@dataclass
class ExtractedFields:
    """Structure for extracted certificate fields"""
    coverage: str
    policy_number: Optional[str] = None
    named_insured: Optional[str] = None
    dba: Optional[str] = None
    mailing_address: Optional[str] = None
    policy_period: Optional[str] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    issue_date: Optional[str] = None
    
    # Insurer Information
    insurer_name: Optional[str] = None
    insurer_naic: Optional[str] = None
    
    # Producer/Agency Information
    producer_name: Optional[str] = None
    producer_address: Optional[str] = None
    producer_phone: Optional[str] = None
    producer_email: Optional[str] = None
    
    # Certificate Holder
    certificate_holder: Optional[str] = None
    additional_insured: Optional[str] = None
    loss_payee: Optional[str] = None
    mortgagee: Optional[str] = None
    
    # Coverage Limits (varies by coverage type)
    limits: Dict = None
    
    # Deductibles
    deductibles: Dict = None
    
    # Premiums
    premiums: Dict = None
    
    # Locations/Operations
    locations: List[str] = None
    description_of_operations: Optional[str] = None
    
    # Coverage Details
    occurrence_or_claims_made: Optional[str] = None
    aggregate_applies_per: Optional[str] = None
    
    # Property Certificate Specific
    perils_insured: Dict = None
    loan_number: Optional[str] = None
    
    # GL Certificate Specific
    certificate_number: Optional[str] = None
    revision_number: Optional[str] = None
    
    # Other
    forms_endorsements: List[str] = None
    remarks: Optional[str] = None
    
    def __post_init__(self):
        if self.limits is None:
            self.limits = {}
        if self.deductibles is None:
            self.deductibles = {}
        if self.premiums is None:
            self.premiums = {}
        if self.locations is None:
            self.locations = []
        if self.perils_insured is None:
            self.perils_insured = {}
        if self.forms_endorsements is None:
            self.forms_endorsements = []


def get_llm_client():
    """Initialize and return OpenAI client using GPT-5 nano (same as backend)"""
    if not openai.api_key:
        raise ValueError(
            "No API key found. Please set OPENAI_API_KEY environment variable.\n"
            "Example: export OPENAI_API_KEY='your-key-here'"
        )
    
    # Initialize OpenAI client (same structure as backend)
    client = openai.OpenAI(api_key=openai.api_key)
    return client


def create_extraction_prompt(coverage: str, content: str) -> str:
    """Create prompt for LLM to extract fields"""
    
    field_descriptions = {
        'GL': """
Extract the following General Liability certificate fields:

IMPORTANT CONTEXT HELPERS:
- The text may contain MULTIPLE coverage types mixed together (GL, Property, EPLI, Liquor, WC, etc.)
- Look for SECTION HEADERS like "COMMERCIAL GENERAL LIABILITY", "GL COVERAGE PART DECLARATIONS", "GENERAL LIABILITY COVERAGE" to find GL-specific content
- GL limits appear AFTER these headers and before other coverage sections
- Common patterns for GL limits:
  * "LIMITS OF INSURANCE" heading followed by limit rows
  * "Each Occurrence Limit" with a dollar amount
  * "General Aggregate" with a dollar amount
  * "Personal & Advertising Injury" line
  * Medical Expense amounts

Extract these fields:
- Policy Number
- Named Insured (and DBA if present)
- Mailing Address
- Effective Date, Expiration Date
- Insurer Name, NAIC Number
- Producer/Agency Name, Address, Phone, Email
- Certificate Number, Revision Number (if present)
- Limits (EXTRACT FROM GL SECTION ONLY):
  * Each Occurrence Limit (format: "Each Occurrence Limit $ X,XXX,XXX")
  * General Aggregate Limit (format: "General Aggregate ... $ X,XXX,XXX")
  * Products-Completed Operations Aggregate Limit
  * Personal & Advertising Injury Limit
  * Damage to Premises Rented to You Limit
  * Medical Expense Limit (format: "Medical Expense Limit $ X,XXX" or "Medical Payments Limit")
- Deductibles (if present in GL section)
- Aggregate Applies Per (POLICY/PROJECT/LOC)
- Occurrence or Claims-Made
- Description of Operations/Locations
- Forms and Endorsements
- Remarks/Special Provisions
""",
        'PROPERTY': """
Extract the following Property certificate fields:

IMPORTANT CONTEXT HELPERS:
- The text may contain MULTIPLE coverage types mixed together (GL, Property, EPLI, Liquor, WC, etc.)
- Look for SECTION HEADERS like "COMMERCIAL PROPERTY", "PROPERTY COVERAGE", "BUSINESSOWNERS PROPERTY COVERAGE", "PROPERTY DECLARATIONS" to find Property-specific content
- Property limits appear AFTER these headers and before other coverage sections
- Common patterns for Property coverage:
  * "COVERAGES AND LIMITS OF INSURANCE" section
  * "Building" limit (e.g., "Building $ X,XXX,XXX")
  * "Business Personal Property" limit
  * "Business Income" limit with deductible
  * Deductible lines (e.g., "DEDUCTIBLE AMOUNT: $ X,XXX")

Extract these fields:
- Policy Number
- Named Insured (and DBA if present)
- Mailing Address
- Effective Date, Expiration Date
- Insurer Name, NAIC Number
- Producer/Agency Name, Address, Phone, Email
- Loan Number (if present)
- Perils Insured: Basic, Broad, Special, Replacement Cost
- Coverage Limits with Amounts and Deductibles (FROM PROPERTY SECTION ONLY):
  * Building (e.g., "Building $ X,XXX,XXX")
  * Business Personal Property (e.g., "Business Personal Property $ X,XXX,XXX")
  * Business Income (e.g., "Business Income $ X,XXX,XXX")
  * Equipment Breakdown
  * Employee Dishonesty
  * Money & Securities
  * Pumps & Canopy (if applicable)
  * Outdoor Signs (if applicable)
  * Windstorm or Hail
  * Deductible Amounts (extract deductible values, not limits)
- Location/Description
- Forms and Endorsements
- Remarks/Special Conditions
""",
        'EPLI': """
Extract the following Employment Practices Liability certificate fields:

IMPORTANT CONTEXT HELPERS:
- Look for SECTION HEADERS like "EMPLOYMENT PRACTICES", "EPLI", "EMPLOYMENT LIABILITY COVERAGE", "EMPLOYMENT PRACTICES DECLARATIONS"
- EPLI limits appear AFTER these headers before other coverage sections
- Common patterns:
  * "LIMITS OF INSURANCE" section
  * "Per Employee Limit" or similar EPLI-specific limits
  * "Each Wrongful Act" limit

Extract these fields:
- Policy Number
- Named Insured (and DBA if present)
- Mailing Address
- Effective Date, Expiration Date
- Insurer Name, NAIC Number
- Producer/Agency Name, Address, Phone, Email
- Limits (FROM EPLI SECTION ONLY):
  * Each Wrongful Act Limit
  * Per Employee Limit
  * Aggregate Limit
  * Deductible
- Description of Operations
- Forms and Endorsements
- Remarks
""",
        'LIQUOR': """
Extract the following Liquor Liability certificate fields:

IMPORTANT CONTEXT HELPERS:
- Look for SECTION HEADERS like "LIQUOR LIABILITY", "LIQUOR LIABILITY COVERAGE", "LIQUOR LIABILITY DECLARATIONS"
- Liquor limits appear AFTER these headers before other coverage sections
- Common patterns:
  * "LIMITS OF INSURANCE" section with liquor-specific amounts
  * "Each Occurrence" and "General Aggregate" for liquor coverage

Extract these fields:
- Policy Number
- Named Insured (and DBA if present)
- Mailing Address
- Effective Date, Expiration Date
- Insurer Name, NAIC Number
- Producer/Agency Name, Address, Phone, Email
- Limits (FROM LIQUOR SECTION ONLY):
  * Each Occurrence Limit
  * General Aggregate Limit
  * Per Location Limit (if applicable)
  * Deductible
- Description of Operations
- Forms and Endorsements
- Remarks
""",
        'WC': """
Extract the following Workers Compensation certificate fields:

IMPORTANT CONTEXT HELPERS:
- Look for SECTION HEADERS like "WORKERS COMPENSATION", "WORKERS COMP", "EMPLOYERS LIABILITY", "WC COVERAGE", "WORKERS COMPENSATION DECLARATIONS"
- WC limits/coverage appear AFTER these headers before other coverage sections
- Common patterns:
  * "COVERAGE LIMITS" section
  * State-specific coverage (Employer's Liability, Waiver of Subrogation)
  * Per accident/per employee limits

Extract these fields:
- Policy Number
- Named Insured (and DBA if present)
- Mailing Address
- Effective Date, Expiration Date
- Insurer Name, NAIC Number
- Producer/Agency Name, Address, Phone, Email
- Limits (FROM WC SECTION ONLY):
  * Per Accident Limit
  * Each Employee Limit
  * Policy Limit
  * Deductible
- State Classifications (if present)
- Description of Operations
- Forms and Endorsements
- Remarks
"""
    }
    
    field_desc = field_descriptions.get(coverage, "Extract all relevant policy fields.")
    
    prompt = f"""You are an expert at extracting structured information from insurance policy documents.

TASK: Extract {coverage} coverage fields from text that may contain MULTIPLE coverage types mixed together.

STRATEGY: Use NEIGHBORING SURROUNDING TEXT to identify which section/limits belong to {coverage}:

For EACH piece of data you want to extract:
1. Look at the NEIGHBORING TEXT AROUND IT (before and after)
2. Identify {coverage}-specific keywords in the surrounding context
3. If surrounded by {coverage} identifiers, extract it
4. If surrounded by OTHER coverage keywords, SKIP IT

Examples of neighboring text patterns:
- If you see "COMMERCIAL GENERAL LIABILITY" or "GL COVERAGE PART DECLARATIONS" nearby → the following limits are GL limits
- If you see "COMMERCIAL PROPERTY" or "PROPERTY COVERAGE" nearby → the following limits are Property limits
- If you see "EMPLOYMENT PRACTICES LIABILITY" nearby → following limits are EPLI limits
- If you see "LIQUOR LIABILITY COVERAGE" nearby → following limits are Liquor limits
- If you see "WORKERS COMPENSATION" nearby → following limits are WC limits

For limits specifically:
- Look at what comes BEFORE the limit line (section header? coverage name?)
- Look at what comes AFTER the limit line (next limit? different coverage?)
- If the neighboring lines have {coverage}-specific keywords, extract this limit
- If neighboring lines have OTHER coverage names, SKIP this limit

{field_desc}

EXTRACTION RULES:
- Only extract fields that are actually present in the {coverage} section (confirmed by neighboring text)
- Ignore limits/info from OTHER coverage types by checking neighboring context
- For dates, use the format found in the document (MM/DD/YYYY or similar)
- For monetary amounts, include commas and dollar signs as shown
- For limits, create a nested object with limit names as keys and values as strings
- When in doubt about which coverage a limit belongs to, check the SURROUNDING TEXT for coverage keywords
- Return ONLY valid JSON, no additional text or explanation

Content to extract from:
---
{content}
---

Return the extracted fields as a JSON object with this structure (include ALL fields found, use null for missing):
{{
  "policy_number": "...",
  "named_insured": "...",
  "dba": "...",
  "mailing_address": "...",
  "effective_date": "...",
  "expiration_date": "...",
  "insurer_name": "...",
  "insurer_naic": "...",
  "producer_agency": {{"name": "...", "address": "...", "phone": "...", "email": "..."}},
  "certificate_number": "...",
  "revision_number": "...",
  "limits": {{
    "each_occurrence": "...",
    "general_aggregate": "...",
    "products_completed_operations": "...",
    "personal_advertising_injury": "...",
    "damage_to_premises_rented": "...",
    "medical_expense": "..."
  }},
  "deductibles": {{}},
  "premiums": {{}},
  "locations": ["..."],
  "description_of_operations": "...",
  "occurrence_or_claims_made": "...",
  "forms_and_endorsements": ["..."],
  "remarks": "..."
}}

IMPORTANT: For LIMITS, extract the actual dollar amounts shown next to each limit type. For example:
- If you see "Each Occurrence Limit $ 1,000,000", extract "1,000,000" or "$1,000,000"
- If you see "General Aggregate ... $ 2,000,000", extract "2,000,000" or "$2,000,000"

JSON:"""
    
    return prompt


def extract_fields_with_llm(client, coverage: str, content: str) -> Dict:
    """Extract fields using GPT-5 nano (following backend structure)"""
    
    prompt = create_extraction_prompt(coverage, content)
    
    try:
        # Use OpenAI API (GPT-5 Responses API format) - same as backend
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
            return {}
        
        # Clean up markdown code blocks if present
        if result_text.startswith('```json'):
            result_text = result_text[7:]  # Remove ```json
        if result_text.startswith('```'):
            result_text = result_text[3:]   # Remove ```
        if result_text.endswith('```'):
            result_text = result_text[:-3]  # Remove trailing ```
        result_text = result_text.strip()
        
        # Parse JSON response
        try:
            extracted = json.loads(result_text)
            return extracted
        except json.JSONDecodeError as e:
            print(f"  [ERROR] Failed to parse JSON response: {e}")
            print(f"  Raw response: {result_text[:500]}...")
            return {}
            
    except Exception as e:
        print(f"  [ERROR] LLM processing failed: {e}")
        return {}


def process_extraction_results(json_file: str = "qc_extraction_results.json", 
                               single_policy: Optional[str] = None) -> Dict:
    """
    Process extraction results and extract fields using LLM
    
    Args:
        json_file: Path to qc_extraction_results.json (contains heading-extracted content)
        single_policy: If provided, process only this policy filename (e.g., "package2_ocr_output.txt")
    
    Note: This extracts from HEADING-EXTRACTED content (filtered pages from qc_heading_extraction.py),
          NOT directly from OCR. The heading extraction already filtered to relevant pages.
    """
    
    print("\n" + "="*80)
    print("LLM FIELD EXTRACTION PIPELINE".center(80))
    print("="*80 + "\n")
    print("[INFO] Extracting from HEADING-EXTRACTED content (filtered pages)")
    print("[INFO] Source: qc_extraction_results.json (from qc_heading_extraction.py)")
    print("[INFO] Note: JSON keys use OCR input filenames, but content is extracted/filtered\n")
    
    # Load extraction results
    results_path = Path(json_file)
    if not results_path.exists():
        raise FileNotFoundError(f"Extraction results file not found: {json_file}")
    
    with open(results_path, 'r') as f:
        extraction_data = json.load(f)
    
    # Initialize LLM client
    print("[INFO] Initializing LLM client (GPT-5 nano)...")
    try:
        client = get_llm_client()
        print(f"[OK] Using GPT-5 nano client\n")
    except Exception as e:
        print(f"[ERROR] Failed to initialize LLM client: {e}")
        return {}
    
    # Filter to single policy if requested
    results_to_process = extraction_data.get('results', {})
    if single_policy:
        if single_policy not in results_to_process:
            available = list(results_to_process.keys())
            raise ValueError(
                f"Policy '{single_policy}' not found in results.\n"
                f"Available policies: {available}"
            )
        results_to_process = {single_policy: results_to_process[single_policy]}
        print(f"[INFO] Processing single policy: {single_policy}\n")
    
    # Process each file's results
    all_extracted_fields = {
        'timestamp': datetime.now().isoformat(),
        'llm_model': 'gpt-5-nano',
        'source': 'heading-extracted_content',  # Clarify source
        'results': {}
    }
    
    for filename, file_data in results_to_process.items():
        print(f"\n{'='*80}")
        print(f"Processing: {filename}")
        print(f"{'='*80}")
        
        file_extracted_fields = {}
        
        # Process each coverage section
        # Note: filename is the OCR input filename, but sections contain extracted/filtered content
        sections = file_data.get('sections', {})
        for coverage in ['GL', 'PROPERTY', 'EPLI', 'LIQUOR', 'WC']:
            section_data = sections.get(coverage)
            
            if not section_data or not section_data.get('content'):
                print(f"  [{coverage}] Skipped (no content)")
                continue
            
            # This content is already extracted/filtered by qc_heading_extraction.py
            # It's NOT raw OCR - it's the filtered pages around each heading
            content = section_data['content']
            print(f"  [{coverage}] Extracting fields from {len(content):,} chars (extracted pages)...")
            
            try:
                extracted = extract_fields_with_llm(client, coverage, content)
                file_extracted_fields[coverage] = extracted
                print(f"  [{coverage}] ✓ Extracted {len(extracted)} fields")
            except Exception as e:
                print(f"  [{coverage}] ✗ Error: {e}")
                file_extracted_fields[coverage] = {}
        
        all_extracted_fields['results'][filename] = file_extracted_fields
    
    return all_extracted_fields


def save_extracted_fields(extracted_fields: Dict, output_file: str = "llm_extracted_fields.json"):
    """Save extracted fields to JSON file"""
    
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(extracted_fields, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"[OK] Saved extracted fields to: {output_file}")
    print(f"     File size: {output_path.stat().st_size:,} bytes")
    print(f"{'='*80}\n")


def main():
    """Main execution"""
    import sys
    
    # Check for single policy argument
    single_policy = None
    if len(sys.argv) > 1:
        single_policy = sys.argv[1]
        print(f"[INFO] Processing single policy: {single_policy}\n")
    
    # Process extraction results
    extracted_fields = process_extraction_results(single_policy=single_policy)
    
    if extracted_fields:
        # Save results
        output_file = f"llm_extracted_fields_{single_policy.replace('.txt', '')}.json" if single_policy else "llm_extracted_fields.json"
        save_extracted_fields(extracted_fields, output_file)
        
        # Print summary
        print("\n[SUMMARY]")
        for filename, file_data in extracted_fields.get('results', {}).items():
            print(f"\n{filename}:")
            for coverage, fields in file_data.items():
                if fields:
                    print(f"  {coverage}: {len(fields)} fields extracted")
    else:
        print("\n[ERROR] No fields extracted")


if __name__ == "__main__":
    main()

