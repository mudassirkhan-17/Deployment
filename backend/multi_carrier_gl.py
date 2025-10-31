#!/usr/bin/env python3
"""
SIMPLE MULTI-CARRIER SETUP
===============================================================================
Ask user for number of carriers and their names.
For each carrier, let them select a PDF and get the path.

Usage: python multi_carrier.py
"""

import os
import glob
import re
import json
from datetime import datetime

# Import functions from pdf_input_selector
from pdf_input_selector import get_available_pdfs, display_pdf_selection, get_user_selection

# Import Phase 1 functions
from A_phase1_Pymupdf import process_all_pages, save_results

# Import Phase 2 functions
from A_phase2_ocr import process_all_pages_with_ocr, save_ocr_results, get_all_pages_from_phase1

# Import Phase 2C functions
from A_phase2c_smart_selection import process_all_pages_selection, save_selection_results
from A_phase2c_smart_selection import read_pymupdf_clean_pages, read_ocr_all_pages

# Import Phase 2D functions
from A_phase2d_intelligent_combining import create_intelligent_combined_file

# Import Phase 3 functions (GENERAL LIABILITY VERSION)
from A_phase3_llm_GeneralLiability import read_combined_file, create_chunks, extract_with_llm, merge_extraction_results, save_extraction_results, create_final_validated_fields

# Import Phase 4 functions
from A_phase5_simple_sheets import push_to_sheets

def get_user_pdf_selection(pdf_files):
    """Get user's PDF selection and return both filename and path"""
    selected_pdf = get_user_selection(pdf_files)
    pdf_path = f"pdf/{selected_pdf}"  # Will be correct when we change to property/ directory
    print(f"Path: {pdf_path}")
    return selected_pdf, pdf_path

def get_carrier_setup():
    """Get carrier setup from user"""
    print("=" * 60)
    print("CARRIER SETUP")
    print("=" * 60)
    
    # Ask number of carriers
    while True:
        try:
            num_carriers = int(input("How many carriers do you want to process? (1, 2, 3, etc.): "))
            if num_carriers >= 1:
                break
            print("Please enter 1 or more carriers")
        except ValueError:
            print("Please enter a valid number")
    
    # Get available PDFs
    pdf_files = get_available_pdfs()
    if not pdf_files:
        print("No PDF files available!")
        return []
    
    # Get carrier names and PDF selections
    carriers = []
    for i in range(num_carriers):
        print(f"\n{'='*60}")
        print(f"CARRIER {i+1} SETUP")
        print(f"{'='*60}")
        
        # Get carrier name
        while True:
            carrier_name = input(f"Enter name for Carrier {i+1}: ").strip()
            if carrier_name:
                break
            print("Please enter a valid carrier name")
        
        # Get PDF selection for this carrier
        print(f"\nPDF Selection for {carrier_name}:")
        display_pdf_selection(pdf_files)
        selected_pdf, pdf_path = get_user_pdf_selection(pdf_files)
        
        carriers.append({
            'name': carrier_name,
            'pdf_file': selected_pdf,
            'pdf_path': pdf_path
        })
    
    print(f"\nCarriers setup complete!")
    return carriers

def process_carrier_pdf(carrier):
    """Process Phase 1 and Phase 2 for a single carrier"""
    print(f"\n{'='*60}")
    print(f"PROCESSING {carrier['name'].upper()}")
    print(f"{'='*60}")
    
    # Store original directory
    original_dir = os.getcwd()
    
    try:
        # Change to property directory (one level up from src/)
        property_dir = os.path.join(original_dir, "..")
        os.chdir(property_dir)
        print(f"Changed to directory: {os.getcwd()}")
        
        # PHASE 1: Process all pages using existing function
        print(f"\nPhase 1: PyMuPDF Extraction for {carrier['name']}")
        phase1_results = process_all_pages(carrier['pdf_path'])
        save_results(phase1_results)
        rename_files_with_carrier_prefix(carrier['name'], "phase1")
        
        # PHASE 2: OCR processing
        print(f"\nPhase 2: OCR Processing for {carrier['name']}")
        # Get pages from the carrier-specific report
        all_pages = get_all_pages_from_carrier_report(carrier['name'])
        if all_pages:
            phase2_results = process_all_pages_with_ocr(carrier['pdf_path'], all_pages)
            save_ocr_results(phase2_results)
            rename_files_with_carrier_prefix(carrier['name'], "phase2")
        else:
            print(f"No pages found from Phase 1 for {carrier['name']}")
            phase2_results = None
        
        # PHASE 2C: Smart LLM selection
        print(f"\nPhase 2C: Smart LLM Selection for {carrier['name']}")
        if phase2_results:
            # Read carrier-specific files
            pymupdf_pages = read_carrier_pymupdf_pages(carrier['name'])
            ocr_pages = read_carrier_ocr_pages(carrier['name'])
            
            if pymupdf_pages and ocr_pages:
                phase2c_results = process_all_pages_selection(pymupdf_pages, ocr_pages)
                save_selection_results(phase2c_results)
                rename_files_with_carrier_prefix(carrier['name'], "phase2c")
            else:
                print(f"Could not read PyMuPDF or OCR pages for {carrier['name']}")
                phase2c_results = None
        else:
            print(f"No OCR results for Phase 2C for {carrier['name']}")
            phase2c_results = None
        
        # PHASE 2D: Intelligent combining
        print(f"\nPhase 2D: Intelligent Combining for {carrier['name']}")
        if phase2c_results:
            # Read carrier-specific files for combining
            pymupdf_pages_2d = read_carrier_pymupdf_pages(carrier['name'])
            ocr_pages_2d = read_carrier_ocr_pages(carrier['name'])
            
            if pymupdf_pages_2d and ocr_pages_2d:
                # Convert carrier-specific dictionaries to text-only dictionaries for Phase 2D
                pymupdf_text_only = {k: v['text'] for k, v in pymupdf_pages_2d.items()}
                ocr_text_only = {k: v['text'] for k, v in ocr_pages_2d.items()}
                
                # Create carrier-specific combined file directly
                carrier_combined_file = create_carrier_combined_file(carrier['name'], phase2c_results, pymupdf_text_only, ocr_text_only)
                phase2d_results = carrier_combined_file
            else:
                print(f"Could not read PyMuPDF or OCR pages for Phase 2D for {carrier['name']}")
                phase2d_results = None
        else:
            print(f"No Phase 2C results for Phase 2D for {carrier['name']}")
            phase2d_results = None
        
        # PHASE 3: LLM Field Extraction
        print(f"\nPhase 3: LLM Field Extraction for {carrier['name']}")
        if phase2d_results:
            # Read carrier-specific combined file
            carrier_combined_file = f"{carrier['name']}_intelligent_combined_all_pages.txt"
            all_pages = read_carrier_combined_file(carrier_combined_file)
            
            if all_pages:
                # Convert carrier data format to match Phase 3 expectations
                pages_list = []
                for page_num, page_text in all_pages.items():
                    pages_list.append({
                        'page_num': page_num,
                        'text': page_text,
                        'source': 'Combined'  # Since it's from intelligent combining
                    })
                
                chunks = create_chunks(pages_list, chunk_size=4)
                all_results = []
                
                for chunk in chunks:
                    print(f"Processing Chunk {chunk['chunk_num']}/{len(chunks)} for {carrier['name']}...")
                    result = extract_with_llm(chunk, chunk['chunk_num'], len(chunks))
                    all_results.append(result)
                
                merged_result = merge_extraction_results(all_results)
                save_carrier_extraction_results(carrier['name'], merged_result, all_results)
                create_carrier_final_validated_fields(carrier['name'], merged_result)
                phase3_results = merged_result
            else:
                print(f"Could not read combined file for {carrier['name']}")
                phase3_results = None
        else:
            print(f"No Phase 2D results for Phase 3 for {carrier['name']}")
            phase3_results = None
        
        print(f"\n{carrier['name']} processing completed!")
        return {
            'phase1': phase1_results,
            'phase2': phase2_results,
            'phase2c': phase2c_results,
            'phase2d': phase2d_results,
            'phase3': phase3_results
        }
        
    except Exception as e:
        print(f"Processing failed for {carrier['name']}: {e}")
        return None
    finally:
        # Always return to original directory
        os.chdir(original_dir)

def get_all_pages_from_carrier_report(carrier_name):
    """Get all pages from carrier-specific Phase 1 report"""
    import re
    
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
    
    report_file = f"{results_dir}/{carrier_name}_phase1_report.txt"
    
    if not os.path.exists(report_file):
        print(f"Error: Carrier Phase 1 report '{report_file}' not found!")
        return []
    
    print(f"Reading total pages from: {report_file}")
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'Total Pages Processed: (\d+)', content)
        if match:
            total_pages = int(match.group(1))
            return list(range(1, total_pages + 1))
        else:
            print("Error: Could not find total pages in carrier Phase 1 report.")
            return []

def read_carrier_pymupdf_pages(carrier_name):
    """Read PyMuPDF clean pages for specific carrier"""
    import re
    
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
    
    clean_file = f"{results_dir}/{carrier_name}_pymupdf_clean_pages_only.txt"
    
    if not os.path.exists(clean_file):
        print(f"Error: Carrier PyMuPDF clean pages '{clean_file}' not found!")
        return {}
    
    print(f"Reading PyMuPDF clean pages from: {clean_file}")
    
    clean_pages = {}
    with open(clean_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Extract clean pages
        page_sections = re.findall(r'PAGE (\d+):.*?TEXT CONTENT:\n(.*?)\n={80}', content, re.DOTALL)
        
        for page_num, page_text in page_sections:
            clean_pages[int(page_num)] = {
                'text': page_text.strip(),
                'source': 'PyMuPDF'
            }
    
    print(f"Found {len(clean_pages)} PyMuPDF clean pages: {list(clean_pages.keys())}")
    return clean_pages

def read_carrier_ocr_pages(carrier_name):
    """Read OCR pages for specific carrier"""
    import re
    
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
    
    ocr_file = f"{results_dir}/{carrier_name}_ocr_all_pages_results.txt"
    
    if not os.path.exists(ocr_file):
        print(f"Error: Carrier OCR results '{ocr_file}' not found!")
        return {}
    
    print(f"Reading OCR pages from: {ocr_file}")
    
    ocr_pages = {}
    with open(ocr_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Extract OCR pages
        page_sections = re.findall(r'PAGE (\d+):.*?OCR EXTRACTED TEXT:.*?----------------------------------------\n(.*?)\n={80}', content, re.DOTALL)
        
        for page_num, page_text in page_sections:
            ocr_pages[int(page_num)] = {
                'text': page_text.strip(),
                'source': 'OCR'
            }
    
    print(f"Found {len(ocr_pages)} OCR pages: {list(ocr_pages.keys())}")
    return ocr_pages

def create_carrier_combined_file(carrier_name, selection_results, pymupdf_pages, ocr_pages):
    """Create carrier-specific intelligent combined file"""
    # DYNAMIC PATH DETECTION
    current_dir = os.getcwd()
    if current_dir.endswith('src'):
        results_dir = '../results'
    else:
        results_dir = 'results'
    
    # Create carrier-specific filename
    combined_file = f"{results_dir}/{carrier_name}_intelligent_combined_all_pages.txt"
    
    print("PHASE 2D: INTELLIGENT COMBINING")
    print("=" * 80)
    print(f"Creating carrier-specific combined file: {combined_file}")
    print("=" * 80)
    
    with open(combined_file, 'w', encoding='utf-8') as f:
        f.write(f"INTELLIGENT COMBINED PDF EXTRACTION RESULTS - {carrier_name.upper()} CARRIER\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Carrier: {carrier_name}\n")
        f.write("=" * 80 + "\n\n")
        
        # Selection summary
        pymupdf_count = len([s for s in selection_results.values() if s['selected_source'] == 'PyMuPDF'])
        ocr_count = len([s for s in selection_results.values() if s['selected_source'] == 'OCR'])
        
        f.write("INTELLIGENT SELECTION SUMMARY:\n")
        f.write("-" * 40 + "\n")
        f.write(f"PyMuPDF Selected: {pymupdf_count} pages\n")
        f.write(f"OCR Selected: {ocr_count} pages\n")
        f.write(f"Total Pages: {len(selection_results)} pages\n")
        f.write("=" * 80 + "\n\n")
        
        # Process each page in order
        for page_num_str in sorted(selection_results.keys(), key=int):
            page_num = int(page_num_str)
            selection = selection_results[page_num_str]
            selected_source = selection['selected_source']
            reason = selection['reason']
            confidence = selection['confidence']
            
            # Get the best text for this page
            if selected_source == 'PyMuPDF':
                page_text = pymupdf_pages.get(page_num, '')
                source_info = f"PyMuPDF (Clean)"
            else:  # OCR
                page_text = ocr_pages.get(page_num, '')
                source_info = f"OCR (All Pages)"
            
            f.write(f"PAGE {page_num} ({source_info}):\n")
            f.write("-" * 50 + "\n")
            f.write(f"Selected Source: {selected_source}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"Confidence: {confidence}\n")
            f.write(f"Characters: {len(page_text):,}\n")
            f.write(f"Lines: {len([line for line in page_text.split(chr(10)) if line.strip()])}\n")
            f.write("\nTEXT CONTENT:\n")
            f.write("-" * 30 + "\n")
            f.write(page_text)
            f.write("\n\n" + "=" * 80 + "\n\n")
    
    print(f"✅ Created carrier-specific combined file: {combined_file}")
    return combined_file

def read_carrier_combined_file(carrier_combined_file):
    """Read carrier-specific combined file for Phase 3"""
    # DYNAMIC PATH DETECTION
    current_dir = os.getcwd()
    if current_dir.endswith('src'):
        results_dir = '../results'
    else:
        results_dir = 'results'
    
    combined_file_path = f"{results_dir}/{carrier_combined_file}"
    
    if not os.path.exists(combined_file_path):
        print(f"Error: Carrier combined file '{combined_file_path}' not found!")
        return {}
    
    print(f"Reading carrier combined file from: {combined_file_path}")
    
    # Read the combined file and extract pages
    all_pages = {}
    with open(combined_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Extract pages using regex
        page_sections = re.findall(r'PAGE (\d+) \(.*?\):\n.*?TEXT CONTENT:\n(.*?)(?=\nPAGE \d+|\n={80}\n\n$)', content, re.DOTALL)
        
        for page_num, page_text in page_sections:
            all_pages[int(page_num)] = page_text.strip()
    
    print(f"Found {len(all_pages)} pages in carrier combined file: {list(all_pages.keys())}")
    return all_pages

def save_carrier_extraction_results(carrier_name, merged_result, all_results):
    """Save carrier-specific extraction results"""
    # DYNAMIC PATH DETECTION
    current_dir = os.getcwd()
    if current_dir.endswith('src'):
        results_dir = '../results'
    else:
        results_dir = 'results'
    
    # Save main extraction results
    extraction_file = f"{results_dir}/{carrier_name}_extracted_insurance_fields.json"
    with open(extraction_file, 'w', encoding='utf-8') as f:
        json.dump(merged_result, f, indent=2, ensure_ascii=False)
    
    # Save chunk results
    chunks_file = f"{results_dir}/{carrier_name}_extraction_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved carrier extraction results: {extraction_file}")

def create_carrier_final_validated_fields(carrier_name, merged_result):
    """Create carrier-specific final validated fields for Google Sheets"""
    # DYNAMIC PATH DETECTION
    current_dir = os.getcwd()
    if current_dir.endswith('src'):
        results_dir = '../results'
    else:
        results_dir = 'results'
    
    final_file = f"{results_dir}/{carrier_name}_final_validated_fields.json"
    
    # Extract field sources from metadata
    field_sources = {}
    if '_extraction_summary' in merged_result and 'field_sources' in merged_result['_extraction_summary']:
        field_sources = merged_result['_extraction_summary']['field_sources']
    
    # Create final validated fields structure
    final_fields = {}
    for field_name, field_value in merged_result.items():
        # Skip metadata fields
        if field_name.startswith('_'):
            continue
        
        # Get source page(s) for this field
        source_pages = field_sources.get(field_name, [])
        if source_pages:
            source_page = f"Page {source_pages[0]}"
        else:
            source_page = ""
            
        final_fields[field_name] = {
            "value": field_value if field_value is not None else "",
            "confidence": "high",
            "source_page": source_page,
            "carrier": carrier_name
        }
    
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(final_fields, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created carrier final validated fields: {final_file}")

def push_multi_carrier_to_sheets(carriers):
    """Push multi-carrier data to Google Sheets with side-by-side comparison"""
    import gspread
    from google.oauth2.service_account import Credentials
    
    print("PHASE 4: MULTI-CARRIER GOOGLE SHEETS INTEGRATION")
    print("=" * 80)
    
    # 1. DYNAMIC PATH DETECTION
    current_dir = os.getcwd()
    if current_dir.endswith('src'):
        results_dir = '../results'
        config_dir = '../config'
    else:
        results_dir = 'results'
        config_dir = 'config'
    
    # 2. LOAD ALL CARRIER DATA
    carrier_data = {}
    for carrier in carriers:
        carrier_name = carrier['name']
        data_file = f"{results_dir}/{carrier_name}_final_validated_fields.json"
        
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                carrier_data[carrier_name] = json.load(f)
            print(f"✅ Loaded data for {carrier_name}: {len(carrier_data[carrier_name])} fields")
        else:
            print(f"❌ No data file found for {carrier_name}: {data_file}")
            return False
    
    if not carrier_data:
        print("❌ No carrier data found!")
        return False
    
    # 3. SETUP GOOGLE SHEETS
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds_file = f"{config_dir}/credentials.json"
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        return False
    
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    
    print("✅ Connected to Google Sheets!")
    
    # 4. OPEN SHEET
    try:
        sheet = client.open("Insurance Fields Data").sheet1
        print("✅ Opened sheet: Insurance Fields Data")
    except:
        # If sheet doesn't exist, try to create it
        try:
            spreadsheet = client.create("Insurance Fields Data")
            sheet = spreadsheet.sheet1
            print("✅ Created new sheet: Insurance Fields Data")
        except Exception as e:
            print(f"❌ Could not open or create sheet: {e}")
            return False
    
    # 5. CLEAR EXISTING DATA
    sheet.clear()
    print("✅ Cleared existing data")
    
    # 6. PREPARE SIDE-BY-SIDE DATA
    all_rows = []
    
    # Add coverage type header
    coverage_type = "General Liability Coverages"  # For general liability insurance
    all_rows.append([coverage_type])
    all_rows.append(["=" * len(coverage_type)])  # Underline
    all_rows.append([])  # Empty row for spacing
    
    # Create field header row
    header = ["Field Name"]
    for carrier in carriers:
        carrier_name = carrier['name']
        header.extend([f"LLM Value ({carrier_name})", f"Source Page ({carrier_name})"])
    all_rows.append(header)
    
    # Get all unique field names from all carriers
    all_fields = set()
    for carrier_name, data in carrier_data.items():
        all_fields.update(data.keys())
    
    # Get fields in original order from first carrier's data
    sorted_fields = []
    for carrier in carriers:
        carrier_name = carrier['name']
        if carrier_name in carrier_data:
            for field_name in carrier_data[carrier_name].keys():
                if field_name not in sorted_fields:
                    sorted_fields.append(field_name)
            break  # Only use first carrier's order
    
    # Create data rows
    for field_name in sorted_fields:
        row = [field_name]
        
        for carrier in carriers:
            carrier_name = carrier['name']
            if carrier_name in carrier_data and field_name in carrier_data[carrier_name]:
                field_data = carrier_data[carrier_name][field_name]
                row.extend([
                    field_data.get('value', ''),
                    field_data.get('source_page', '')
                ])
            else:
                row.extend(['', ''])  # Empty values for missing fields
        
        all_rows.append(row)
    
    # 7. PUSH ALL DATA IN ONE BATCH - FIXED VERSION 2024
    try:
        sheet.update('A1', all_rows)  # Don't store the response!
        print(f"✅ Pushed {len(all_rows)} rows to Google Sheets!")
        print(f"✅ Columns: {len(header)}")
        print(f"✅ Fields: {len(sorted_fields)}")
        
        print("\n" + "=" * 80)
        print("GOOGLE SHEETS INTEGRATION COMPLETE!")
        print("=" * 80)
        print("Check your Google Sheet: Multi-Carrier Insurance Comparison")
        print("Format: Field Name | LLM Value (Carrier1) | Source Page (Carrier1) | LLM Value (Carrier2) | Source Page (Carrier2)")
        
        return True
    except Exception as e:
        print(f"❌ Error pushing to Google Sheets: {e}")
        return False

def rename_files_with_carrier_prefix(carrier_name, phase_type):
    """Rename existing files with carrier prefix"""
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
    
    # List of files to rename based on phase
    if phase_type == "phase1":
        files_to_rename = [
            'clean_pages_results.txt',
            'problem_pages_list.txt', 
            'phase1_report.txt',
            'all_pages_results.txt',
            'pymupdf_clean_pages_only.txt'
        ]
    elif phase_type == "phase2":
        files_to_rename = [
            'ocr_all_pages_results.txt',
            'ocr_processing_log.txt'
        ]
    elif phase_type == "phase2c":
        files_to_rename = [
            'smart_selection_results.txt',
            'phase2c_report.txt'
        ]
    elif phase_type == "phase2d":
        files_to_rename = [
            'intelligent_combined_text.txt',
            'phase2d_report.txt'
        ]
    else:
        files_to_rename = []
    
    for filename in files_to_rename:
        old_path = f"{results_dir}/{filename}"
        new_path = f"{results_dir}/{carrier_name}_{filename}"
        
        if os.path.exists(old_path):
            # Remove target file if it exists
            if os.path.exists(new_path):
                os.remove(new_path)
            # Rename the file
            os.rename(old_path, new_path)
            print(f"  Renamed: {filename} -> {carrier_name}_{filename}")

def main():
    """Main function"""
    print("SIMPLE CARRIER SETUP")
    print("=" * 60)
    
    carriers = get_carrier_setup()
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print(f"Total carriers: {len(carriers)}")
    
    for carrier in carriers:
        print(f"\n{carrier['name']}:")
        print(f"  PDF File: {carrier['pdf_file']}")
        print(f"  PDF Path: {carrier['pdf_path']}")
    
    print("=" * 60)
    
    # Process each carrier's PDF
    print("\n" + "=" * 60)
    print("STARTING PHASE 1, 2, 2C, 2D & 3 PROCESSING")
    print("=" * 60)
    
    all_results = {}
    for carrier in carriers:
        result = process_carrier_pdf(carrier)
        all_results[carrier['name']] = result
    
    # Final summary
    print("\n" + "=" * 60)
    print("ALL CARRIERS PROCESSED!")
    print("=" * 60)
    for carrier_name, result in all_results.items():
        if result:
            phase1_pages = len(result['phase1']['clean_pages']) if result['phase1'] else 0
            phase2_pages = len(result['phase2']['successful_pages']) if result['phase2'] else 0
            phase2c_pages = len(result['phase2c']) if result['phase2c'] else 0
            phase2d_success = "✅" if result['phase2d'] else "❌"
            phase3_fields = len(result['phase3']) if result['phase3'] else 0
            print(f"✅ {carrier_name}: Phase1({phase1_pages} clean), Phase2({phase2_pages} OCR), Phase2C({phase2c_pages} decisions), Phase2D({phase2d_success}), Phase3({phase3_fields} fields)")
        else:
            print(f"❌ {carrier_name}: FAILED")
    print("=" * 60)
    
    # PHASE 4: GOOGLE SHEETS INTEGRATION
    print("\n" + "=" * 60)
    print("STARTING PHASE 4: GOOGLE SHEETS INTEGRATION")
    print("=" * 60)
    
    sheets_success = push_multi_carrier_to_sheets(carriers)
    if sheets_success:
        print("✅ PHASE 4 COMPLETE: Data pushed to Google Sheets!")
        print("📊 Check your Google Sheet: Multi-Carrier Insurance Comparison")
        print("📋 Format: Field Name | LLM Value (Carrier1) | Source Page (Carrier1) | LLM Value (Carrier2) | Source Page (Carrier2)")
    else:
        print("❌ PHASE 4 FAILED: Google Sheets integration failed")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
