import fitz
import os
from datetime import datetime

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

def analyze_text_quality(text):
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
    confidence -= min(metrics['cid_codes'] * 2, 50)  # Penalty for (cid:XX) codes
    confidence -= min(metrics['gibberish_ratio'] * 100, 40)  # Penalty for gibberish
    
    # Bonus for readable words
    if metrics['readable_words'] > 50:
        confidence += 10
    elif metrics['readable_words'] < 20:
        confidence -= 30
    
    metrics['confidence_score'] = max(confidence, 0)
    
    return metrics

def classify_page_quality(text):
    """Classify page quality based on text analysis"""
    metrics = analyze_text_quality(text)
    
    # Clean page criteria (expanded to include low gibberish pages)
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
    
    # Borderline - needs manual review
    else:
        return "BORDERLINE"

def process_all_pages(pdf_file, total_pages=None):
    """Process all pages and classify them"""
    # Auto-detect total pages if not specified
    if total_pages is None:
        doc = fitz.open(pdf_file)
        total_pages = doc.page_count
        doc.close()
    
    print("PHASE 1: PYMUPDF SCREENING")
    print("=" * 80)
    print(f"Processing {total_pages} pages from: {pdf_file}")
    print(f"Auto-detected {total_pages} pages in PDF")
    print("=" * 80)
    
    results = {
        'clean_pages': [],
        'problem_pages': [],
        'borderline_pages': [],
        'all_metrics': {}
    }
    
    for page_num in range(1, total_pages + 1):
        print(f"\nProcessing Page {page_num}...")
        
        # Extract text
        text = extract_with_pymupdf(pdf_file, page_num)
        
        # Analyze quality
        metrics = analyze_text_quality(text)
        quality = classify_page_quality(text)
        
        # Store results
        page_result = {
            'page_num': page_num,
            'text': text,
            'metrics': metrics,
            'quality': quality
        }
        
        results['all_metrics'][page_num] = metrics
        
        if quality == "CLEAN":
            results['clean_pages'].append(page_result)
            gibberish_pct = metrics['gibberish_ratio'] * 100
            print(f"  [CLEAN] - {metrics['readable_words']} words, {metrics['confidence_score']:.1f}% confidence, {gibberish_pct:.1f}% gibberish")
        elif quality == "PROBLEM":
            results['problem_pages'].append(page_result)
            print(f"  [PROBLEM] - {metrics['cid_codes']} (cid:XX) codes, {metrics['confidence_score']:.1f}% confidence")
        else:
            results['borderline_pages'].append(page_result)
            print(f"  [BORDERLINE] - {metrics['readable_words']} words, {metrics['confidence_score']:.1f}% confidence")
    
    return results

def save_results(results):
    """Save results to files - SIMPLIFIED VERSION (Only 2 files)"""
    
    # Find results directory
    results_dir = None
    for path in ['results', '../results']:
        if os.path.exists(path) or os.path.exists(os.path.dirname(path) if os.path.dirname(path) else '.'):
            results_dir = path
            break
    
    if not results_dir:
        results_dir = 'results'
    
    # FILE 1: Quick summary report (for Phase 2)
    report_file = f"{results_dir}/phase1_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("PHASE 1 SCREENING REPORT - PYMUPDF ANALYSIS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Pages Processed: {len(results['all_metrics'])}\n")
        f.write(f"Clean Pages: {len(results['clean_pages'])}\n")
        f.write(f"Problem Pages: {len(results['problem_pages'])}\n")
        f.write(f"Borderline Pages: {len(results['borderline_pages'])}\n")
        f.write("=" * 80 + "\n\n")
        
        # List each page with metrics
        f.write("DETAILED METRICS BY PAGE:\n")
        f.write("-" * 50 + "\n")
        for page_num, metrics in results['all_metrics'].items():
            # Find quality for this page
            quality = None
            for pr in results['clean_pages']:
                if pr['page_num'] == page_num:
                    quality = "CLEAN"
                    break
            if not quality:
                for pr in results['problem_pages']:
                    if pr['page_num'] == page_num:
                        quality = "PROBLEM"
                        break
            if not quality:
                quality = "BORDERLINE"
            
            f.write(f"Page {page_num:2d}: {quality:12s} | "
                   f"{metrics['readable_words']:3d} words | "
                   f"{metrics['cid_codes']:3d} (cid:XX) | "
                   f"{metrics['confidence_score']:5.1f}% confidence | "
                   f"{metrics['gibberish_ratio']:5.1%} gibberish\n")
        
        # Summary
        f.write("\nSUMMARY:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Clean pages ready for use: {len(results['clean_pages'])}\n")
        f.write(f"Pages requiring OCR: {len(results['problem_pages'])}\n")
        f.write(f"Pages needing manual review: {len(results['borderline_pages'])}\n")
        
        if results['clean_pages']:
            f.write(f"\nClean page numbers: {[p['page_num'] for p in results['clean_pages']]}\n")
        if results['problem_pages']:
            f.write(f"Problem page numbers: {[p['page_num'] for p in results['problem_pages']]}\n")
    
    # FILE 2: All extracted text in ONE place (for Phase 2C)
    clean_only_file = f"{results_dir}/pymupdf_clean_pages_only.txt"
    with open(clean_only_file, 'w', encoding='utf-8') as f:
        f.write("PYMUPDF CLEAN PAGES ONLY - FOR SMART SELECTION\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Clean Pages: {len(results['clean_pages'])}\n")
        f.write(f"Total Pages in PDF: {len(results['all_metrics'])}\n")
        f.write("=" * 80 + "\n\n")
        
        # Save all clean pages
        for page_result in results['clean_pages']:
            f.write(f"PAGE {page_result['page_num']}:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Quality: {page_result['quality']}\n")
            f.write(f"Confidence: {page_result['metrics']['confidence_score']:.1f}%\n")
            f.write(f"Readable Words: {page_result['metrics']['readable_words']}\n")
            f.write(f"Total Characters: {page_result['metrics']['total_chars']}\n")
            f.write(f"(cid:XX) Codes: {page_result['metrics']['cid_codes']}\n")
            f.write(f"Gibberish Ratio: {page_result['metrics']['gibberish_ratio']:.2%}\n")
            f.write("\nTEXT CONTENT:\n")
            f.write(page_result['text'])
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"✅ Saved: {report_file}")
    print(f"✅ Saved: {clean_only_file}")
    
    return report_file, clean_only_file

def generate_summary(results):
    """Generate console summary"""
    print(f"\n{'='*80}")
    print("PHASE 1 SUMMARY")
    print(f"{'='*80}")
    print(f"Total Pages Processed: {len(results['all_metrics'])}")
    print(f"Clean Pages: {len(results['clean_pages'])}")
    print(f"Problem Pages: {len(results['problem_pages'])}")
    print(f"Borderline Pages: {len(results['borderline_pages'])}")
    
    if results['clean_pages']:
        clean_nums = [p['page_num'] for p in results['clean_pages']]
        print(f"\n[CLEAN] Clean pages ready: {clean_nums}")
    
    if results['problem_pages']:
        problem_nums = [p['page_num'] for p in results['problem_pages']]
        print(f"[PROBLEM] Problem pages (need OCR): {problem_nums}")
    
    if results['borderline_pages']:
        borderline_nums = [p['page_num'] for p in results['borderline_pages']]
        print(f"[BORDERLINE] Borderline pages (manual review): {borderline_nums}")
    
    print(f"\nNext step: Process problem pages with OCR + LLM")

if __name__ == "__main__":
    pdf_file = "../pdf/PROPERTY QUOTE1.pdf"
    
    # Check if PDF exists
    if not os.path.exists(pdf_file):
        print(f"Error: PDF file '{pdf_file}' not found!")
        print("Please ensure the PDF file is in the pdf/ subdirectory.")
        exit(1)
    
    # Process all pages (auto-detect total pages)
    results = process_all_pages(pdf_file)
    
    # Save results
    report_file, clean_only_file = save_results(results)
    
    # Generate summary
    generate_summary(results)
    
    print(f"\n{'='*80}")
    print("FILES GENERATED:")
    print(f"{'='*80}")
    print(f"Summary report: {report_file}")
    print(f"Clean pages text: {clean_only_file}")
    print(f"\nPhase 1 complete! Ready for Phase 2 (OCR all pages).")