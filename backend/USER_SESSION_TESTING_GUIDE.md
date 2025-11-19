# User Session & Sheet Routing Testing Guide

## Overview
This guide walks you through testing the new user session-based sheet routing feature. When users log in and upload insurance quotes, their data will automatically be routed to their own sheet tab.

---

## Architecture Flow

```
User Login (mudassir@gmail.com)
    ↓
Session created: user_id = "mudassir"
    ↓
Upload PDFs
    ↓
Frontend sends: Header "X-User-ID: mudassir"
    ↓
Backend extracts user_id from header
    ↓
Data stored in metadata with userId: "mudassir"
    ↓
Phase 3 LLM processing
    ↓
Check metadata for userId
    ↓
Select sheet tab: spreadsheet.worksheet("mudassir")
    ↓
Data filled to "mudassir" tab (NOT "MAIN SHEET")
```

---

## Testing Steps

### Step 1: Deploy Changes
```bash
cd ~/deployment2
git add .
git commit -m "feat: add user session-based sheet routing"
git push

# On EC2 instance:
cd ~/deployment2
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 2: Verify Backend is Running
```bash
# Check Docker containers
docker ps

# Check logs
docker-compose logs backend -f
```

**Expected Output:**
```
backend    | ✅ FastAPI server running on 0.0.0.0:8000
```

### Step 3: Test Login Flow

**Open Frontend:**
- Go to: `https://deployment2-nine.vercel.app/login`
- Or: http://insurance-backend.duckdns.org (if Vercel not working)

**Create Test Users:**
Create 2-3 test accounts:
1. `mudassir@gmail.com` / `password123`
2. `aamir@gmail.com` / `password123`
3. `areesh@gmail.com` / `password123`

**Verify Session:**
After login, check browser console:
```javascript
// Open DevTools (F12) → Console → type:
localStorage.getItem('user')
// Should output: {"user_id": "mudassir", "email": "mudassir@gmail.com"}
```

### Step 4: Upload PDFs as User 1 (mudassir)

1. **Click "Generate Summary"** on dashboard
2. **Add Carrier:** "State Farm" (or any carrier)
3. **Upload Files:** 
   - Property PDF: `/path/to/property.pdf`
   - Liability PDF: `/path/to/liability.pdf`
4. **Click "Execute"**
5. **Note Upload ID:** e.g., `upload_20240115_143022`

**Check Logs for User Routing:**
```bash
docker-compose logs backend | grep "user_id"
```

**Expected Output:**
```
backend    | 📝 Processing upload for user: mudassir
backend    | ✅ Phase 1 queued for upload: upload_20240115_143022, Task ID: ...
```

### Step 5: Monitor Processing

**Check Phase 3 Processing:**
```bash
docker-compose logs celery_worker -f
```

**Expected Output When All Phases Complete:**
```
celery_worker | 📋 Using user-specific sheet tab: 'mudassir'
celery_worker | ✅ Opened user tab: mudassir
celery_worker | 🎉 ALL CARRIERS COMPLETE! Auto-filling sheets...
```

### Step 6: Verify Data in Google Sheets

1. **Open Google Sheets:**
   - Go to: https://docs.google.com/spreadsheets/d/1o94CsCnk3fvvMYjUQidjKNUjnfSaP89vPwYh4U4hKNY/edit
   
2. **Check Sheet Tabs at Bottom:**
   - Should see: MAIN SHEET | AAMIR | AREESH | mudassir | ... 

3. **Click on "mudassir" Tab:**
   - Should see data populated (Not empty!)
   
4. **Verify Carrier Data:**
   - Company Name: "Mckinney & Co. Insurance"
   - Carrier: State Farm
   - Fields populated with LLM extracted values

### Step 7: Test User 2 (aamir)

**Logout from mudassir:**
- Click "Logout" button

**Login as aamir:**
- Email: `aamir@gmail.com`
- Password: `password123`

**Upload PDFs:**
1. Go to "Generate Summary"
2. Add carrier: "Allstate"
3. Upload files
4. Click "Execute"

**Verify in Google Sheets:**
- Check logs: Should say `📋 Using user-specific sheet tab: 'aamir'`
- Check Google Sheets > "aamir" tab
- Should see Allstate data ONLY (separate from mudassir's data)

### Step 8: Verify Data Isolation

**In Google Sheets:**
- "mudassir" tab: Should have State Farm data
- "aamir" tab: Should have Allstate data
- "MAIN SHEET": Should be empty (fallback only)

---

## Troubleshooting

### Issue 1: Data Going to MAIN SHEET Instead of User Tab

**Check Logs:**
```bash
docker-compose logs backend | grep "📋 Using user-specific sheet"
```

**If Missing:**
- Frontend not sending `X-User-ID` header
- Check `frontend/app/summary/page.tsx` line 188 has header

**If Shows Wrong user_id:**
- Browser localStorage corrupted
- Clear localStorage: `localStorage.clear()` in console
- Log out and log back in

### Issue 2: "WorksheetNotFound" Error

**Expected Behavior:**
```
⚠️  User tab 'mudassir' not found. Falling back to MAIN SHEET
```

**This is OK** - means the tab doesn't exist yet, falls back to MAIN SHEET as safety measure

**To Create User Tabs in Advance:**
In Google Sheets, create tabs named:
- mudassir
- aamir
- areesh

Then re-upload data.

### Issue 3: Session Not Persisting

**Check LocalStorage:**
```javascript
localStorage.getItem('user')
```

**If Empty After Login:**
- Check browser console for errors (F12)
- Check network tab: did login request succeed?

### Issue 4: Multiple Uploads from Same User

**Expected:**
- Each upload replaces previous data in user's tab (clears sheet)
- Latest upload always visible in user's tab

**Check:**
```bash
# Upload twice from mudassir
# Second upload should overwrite first in "mudassir" tab
```

---

## What to Look For in Logs

### Phase 1 (Upload)
```
✅ Processing upload for user: mudassir
✅ Successfully uploaded 1 carriers with 2 PDF files
```

### Phase 2 (OCR)
```
🔍 Processing OCR for mudassir: State Farm...
```

### Phase 3 (LLM)
```
📋 Using user-specific sheet tab: 'mudassir'
✅ Opened user tab: mudassir
🎉 ALL CARRIERS COMPLETE! Auto-filling sheets...
```

### Error Pattern (If Fallback Triggered)
```
⚠️  User tab 'mudassir' not found. Falling back to MAIN SHEET
```

---

## Test Checklist

- [ ] User 1 (mudassir) logs in successfully
- [ ] User 1 localStorage shows correct user_id
- [ ] Frontend sends X-User-ID header (check Network tab)
- [ ] Backend logs show "📝 Processing upload for user: mudassir"
- [ ] Phase 3 logs show "📋 Using user-specific sheet tab: 'mudassir'"
- [ ] Data appears in "mudassir" tab in Google Sheets
- [ ] User 2 (aamir) logs in and uploads
- [ ] Data appears in separate "aamir" tab
- [ ] User 1 data still in "mudassir" tab (isolation verified)
- [ ] Multiple uploads by same user → data updated in same tab
- [ ] Fallback to MAIN SHEET works if user tab missing

---

## Expected Results

### Successful Test Results:
```
User: mudassir@gmail.com
├─ Logs: "📋 Using user-specific sheet tab: 'mudassir'"
├─ Sheet: Data in "mudassir" tab
└─ Isolation: Separate from other users

User: aamir@gmail.com
├─ Logs: "📋 Using user-specific sheet tab: 'aamir'"
├─ Sheet: Data in "aamir" tab
└─ Isolation: Separate from other users

MAIN SHEET: Empty (or fallback only)
```

---

## Commands Reference

### Deploy on EC2
```bash
cd ~/deployment2
git pull
docker-compose down && docker-compose build --no-cache && docker-compose up -d
docker ps
docker-compose logs backend -f
docker-compose logs celery_worker -f
```

### Check User ID in Metadata
```bash
# On EC2, check what user_id is stored
cat backend/metadata.json | grep -A 5 "userId"
```

### Force Reprocess Upload
```bash
# If you want to reprocess an upload:
# Delete GCS phase3 results and re-trigger from Phase 1
```

---

## Next Steps After Successful Testing

1. **Create user tabs in Google Sheets** (if not auto-created)
2. **Share sheets** with team members
3. **Train users** on login flow
4. **Monitor logs** for any "WorksheetNotFound" errors
5. **Consider** auto-creating tabs on first upload (future enhancement)

---

## Questions?

If issues occur:
1. Check backend logs: `docker-compose logs backend -f`
2. Check Celery logs: `docker-compose logs celery_worker -f`
3. Check browser console: F12 → Console
4. Check Network tab: Verify X-User-ID header in requests

