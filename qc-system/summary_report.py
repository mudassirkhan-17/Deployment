import json
from pathlib import Path

with open('qc_extraction_results.json') as f:
    data = json.load(f)

print('='*80)
print('EXTRACTION RESULTS - ALL 10 CARRIERS/PDFs'.center(80))
print('='*80)
print()

total_files = len(data.get('results', {}))
print(f'Total Files Processed: {total_files}')
print()

for filename, result in data.get('results', {}).items():
    print(f'{filename}')
    print('-' * 80)
    
    log = result.get('log', {})
    sections = result.get('sections', {})
    
    print(f'  Total Pages: {log.get("total_pages", "N/A")}')
    print(f'  Headings Found:')
    for coverage, count in log.get('headings_found', {}).items():
        print(f'    {coverage}: {count}')
    
    print(f'  Sections Extracted:')
    for coverage, section_data in sections.items():
        if section_data:
            pages = section_data.get('start_page', 'N/A')
            end_page = section_data.get('end_page', 'N/A')
            content_len = section_data.get('page_count', 'N/A')
            print(f'    {coverage}: Pages {pages}-{end_page} ({content_len} pages)')
    
    print()

print('='*80)
print('[DONE] All carriers processed successfully!')
print('='*80)

