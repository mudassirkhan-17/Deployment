import gspread
from google.oauth2.service_account import Credentials
import os
from pathlib import Path

def _get_credentials_path():
    """Get Google Sheets credentials path"""
    possible_paths = [
        'credentials/insurance-sheets-474717-7fc3fd9736bc.json',
        '../credentials/insurance-sheets-474717-7fc3fd9736bc.json',
        '../insurance-sheets-474717-7fc3fd9736bc.json',
        'insurance-sheets-474717-7fc3fd9736bc.json'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return str(Path(path).resolve())
    
    creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    if creds_path and os.path.exists(creds_path):
        return creds_path
    
    raise Exception("Google Sheets credentials not found!")

# Connect to Google Sheets
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds_path = _get_credentials_path()
creds = Credentials.from_service_account_file(creds_path, scopes=scope)
client = gspread.authorize(creds)

# Open the sheet
sheet_name = "Insurance Fields Data"
sheet = client.open(sheet_name).sheet1

# Batch update - single API call
updates = [
    {'range': 'B8', 'values': [['50']]},
    {'range': 'B9', 'values': [['25']]}
]

sheet.batch_update(updates)

print("✅ Mapped GL data to sheet (single API call)")

