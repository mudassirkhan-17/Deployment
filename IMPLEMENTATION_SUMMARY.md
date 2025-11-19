# User Session-Based Sheet Routing - Implementation Summary

## What Was Changed

### 1. **Frontend Changes**
**File:** `frontend/app/summary/page.tsx`

Added user ID to API request headers:
```javascript
headers: {
  'ngrok-skip-browser-warning': 'true',
  'X-User-ID': user?.user_id || '',  // NEW: Send user ID to backend
}
```

### 2. **Backend API Changes**
**File:** `backend/app.py`

Extract user ID from request headers:
```python
user_id = request.headers.get('X-User-ID', 'default')
print(f"📝 Processing upload for user: {user_id}")
```

Pass user ID to upload handler:
```python
result = process_carrier_uploads(carriers_data, user_id)
```

### 3. **Upload Handler Changes**
**File:** `backend/upload_handler.py` (Already had support!)

The `process_carrier_uploads` function already had `user_id` parameter:
```python
def process_carrier_uploads(carriers_data: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    # Stores user_id in metadata:
    upload_record = {
        "uploadId": upload_id,
        "userId": user_id,  # NEW: Stores user with upload
        "uploadedAt": datetime.now().isoformat(),
        ...
    }
```

### 4. **Phase 3 (LLM Extraction) Changes**
**File:** `backend/phase3_llm.py`

Extract user from metadata and route to user-specific sheet tab:
```python
# Get user_id from metadata
user_id = record.get('userId', 'default')
print(f"📋 Using user-specific sheet tab: '{user_id}'")

# Select sheet tab based on user_id
spreadsheet = client.open("Insurance Fields Data")
try:
    sheet = spreadsheet.worksheet(user_id)
    print(f"✅ Opened user tab: {user_id}")
except gspread.exceptions.WorksheetNotFound:
    print(f"⚠️  User tab '{user_id}' not found. Falling back to MAIN SHEET")
    sheet = spreadsheet.sheet1
```

### 5. **Phase 5 (Google Sheets Finalization) Changes**
**File:** `backend/phase5_googlesheet.py`

Similar logic to Phase 3:
```python
# Get user_id from metadata for user-specific tab
user_id = upload_record.get('userId', 'default')
print(f"📋 Using user-specific sheet tab: '{user_id}'")

# Try to open user-specific tab
try:
    sheet = spreadsheet.worksheet(user_id)
    print(f"✅ Opened user tab: {user_id}")
except gspread.exceptions.WorksheetNotFound:
    print(f"⚠️  User tab '{user_id}' not found. Falling back to MAIN SHEET")
    sheet = spreadsheet.sheet1
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER LOGS IN: mudassir@gmail.com                               │
├─────────────────────────────────────────────────────────────────┤
│ Session Created: user_id = "mudassir"                           │
│ localStorage: {"user_id": "mudassir", "email": "mudassir@..."}  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER UPLOADS PDFs FROM FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│ Frontend reads: user_id from localStorage                       │
│ Sends Header: X-User-ID: mudassir                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND: /upload-quotes/ ENDPOINT                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. Extracts header: user_id = request.headers.get('X-User-ID') │
│ 2. Passes to upload_handler: process_carrier_uploads(data, uid) │
│ 3. Stores in metadata: "userId": "mudassir"                    │
│ 4. Returns: uploadId + stores userId association               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ CELERY BACKGROUND TASKS (Phases 1-3)                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. OCR Processing                                               │
│ 2. Smart Selection                                              │
│ 3. Intelligent Combination                                      │
│ 4. LLM Extraction (Phase 3)                                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: SHEET ROUTING (NEW!)                                  │
├─────────────────────────────────────────────────────────────────┤
│ 1. Read metadata: user_id = record.get('userId')               │
│ 2. Connect to Google Sheets                                     │
│ 3. SELECT TAB: spreadsheet.worksheet(user_id)                  │
│    └─ If "mudassir": Opens "mudassir" tab                      │
│    └─ If not found: Falls back to "MAIN SHEET"                 │
│ 4. Fill data to selected tab                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ GOOGLE SHEETS: USER-SPECIFIC TABS                              │
├─────────────────────────────────────────────────────────────────┤
│ [MAIN SHEET] [AAMIR] [AREESH] [mudassir] [Other users...]    │
│              ↑                  ↑
│         Aamir's data      Mudassir's data
│         (isolated)          (isolated)
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### ✅ User Isolation
- Each user's uploads → their own tab
- No data mixing between users
- Clean separation of concerns

### ✅ Fallback Safety
- If user tab doesn't exist → falls back to MAIN SHEET
- No errors if tabs not pre-created
- Graceful degradation

### ✅ Session Integration
- Uses existing AuthContext from login
- No new auth system needed
- Works with current database structure

### ✅ Backward Compatible
- Old uploads (no userId) default to "default" user
- Existing MAIN SHEET still works
- No breaking changes

### ✅ Logging & Debugging
Clear logs for troubleshooting:
```
📝 Processing upload for user: mudassir
📋 Using user-specific sheet tab: 'mudassir'
✅ Opened user tab: mudassir
```

---

## Testing Scenarios

### Scenario 1: Single User
```
User: mudassir
├─ Upload 1 → mudassir tab (data populated)
├─ Upload 2 → mudassir tab (data updated/cleared then refilled)
└─ Result: Only latest upload visible in mudassir tab ✓
```

### Scenario 2: Multiple Users
```
User: mudassir
├─ Upload → mudassir tab ✓

User: aamir
├─ Upload → aamir tab ✓
├─ mudassir tab unchanged ✓
└─ Result: Data isolation verified ✓
```

### Scenario 3: Tab Not Pre-Created
```
User: areesh (tab "areesh" doesn't exist in sheet)
├─ Upload
├─ Phase 3: "⚠️  User tab 'areesh' not found"
├─ Falls back to: MAIN SHEET
└─ Result: Graceful fallback ✓
```

---

## Files Modified

1. `frontend/app/summary/page.tsx` - Add X-User-ID header
2. `backend/app.py` - Extract user from headers
3. `backend/phase3_llm.py` - Route to user-specific tab
4. `backend/phase5_googlesheet.py` - Route to user-specific tab

## Files Created

1. `backend/USER_SESSION_TESTING_GUIDE.md` - Comprehensive testing guide
2. `IMPLEMENTATION_SUMMARY.md` - This file

---

## Deployment Steps

### 1. Code Deployment
```bash
cd ~/deployment2
git add .
git commit -m "feat: add user session-based sheet routing"
git push
```

### 2. EC2 Deployment
```bash
ssh ec2-instance
cd ~/deployment2
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3. Verification
```bash
docker ps  # Verify all containers running
docker-compose logs backend -f  # Verify no errors
```

### 4. Test with Guide
- See `backend/USER_SESSION_TESTING_GUIDE.md`

---

## Future Enhancements

1. **Auto-Create User Tabs**: Create tabs automatically on first upload
2. **Sheet Templates**: Apply pre-formatted templates to new user tabs
3. **Permission Management**: Set read-only/edit permissions per user
4. **Data Export**: Export user-specific data to CSV/PDF
5. **Multi-Organization**: Support different sheets per organization
6. **Quota Tracking**: Monitor usage per user/organization

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Data going to MAIN SHEET | Check X-User-ID header in Network tab |
| WorksheetNotFound error | Pre-create user tabs in Google Sheets (optional) |
| Session not persisting | Check localStorage: `localStorage.getItem('user')` |
| Wrong user_id | Log out, clear localStorage, log in again |
| Multiple uploads overwrite | This is expected (sheet cleared before each fill) |

---

## Questions & Support

For issues or questions:
1. Check logs: `docker-compose logs backend -f`
2. Check Network tab in browser DevTools (F12)
3. Verify localStorage: `localStorage.getItem('user')` in console
4. Review testing guide: `backend/USER_SESSION_TESTING_GUIDE.md`

