# Username-Based Authentication & Sheet Routing - Testing Guide

## Overview
Complete rewrite from email-based to username-based authentication. Usernames now directly map to Google Sheets tabs for clean data organization.

---

## What Changed

### ✅ Database
```
Old: email field + auto-generated user_id
New: username field as primary identifier
```

### ✅ Frontend
```
Old: Email input (type="email")
New: Username input (type="text")
```

### ✅ Backend
```
Old: check email → create user_1, user_2, etc
New: check username → create user with username as key
```

### ✅ Sheets
```
Old: user_1 tab, user_2 tab, etc
New: mudassir tab, aamir tab, areesh tab (direct username!)
```

---

## Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND - LOGIN PAGE                                               │
├─────────────────────────────────────────────────────────────────────┤
│ Old: Email input (your@email.com)                                   │
│ New: Username input (mudassir) ← NO email validation!              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND - AUTHCONTEXT.TSX                                          │
├─────────────────────────────────────────────────────────────────────┤
│ Old: user_id + email stored                                         │
│ New: Only username stored                                           │
│ localStorage: {"username": "mudassir"}                              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ API CALL: /login/                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Old: POST { email: "...", password: "..." }                        │
│ New: POST { username: "mudassir", password: "..." }                │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND - AUTH.PY                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Old: user_exists_by_email() → returns user_id                      │
│ New: user_exists_by_username() → returns username                  │
│ Database key: username (not auto-generated ID)                     │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND - UPLOAD PAGE (SUMMARY)                                    │
├─────────────────────────────────────────────────────────────────────┤
│ Header: X-User-ID: mudassir (from localStorage)                    │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND - UPLOAD HANDLER                                            │
├─────────────────────────────────────────────────────────────────────┤
│ Stores in metadata: "username": "mudassir"                         │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3/5 - GOOGLE SHEETS                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Old: Selects spreadsheet.worksheet(user_1)                         │
│ New: Selects spreadsheet.worksheet("mudassir")                     │
│ Data goes to "mudassir" tab DIRECTLY! ✅                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pre-Deployment Checklist

- [ ] Code reviewed in all files
- [ ] No syntax errors
- [ ] Ready to deploy

---

## Deployment Steps

### Step 1: Deploy Code
```bash
cd ~/deployment2
git add .
git commit -m "refactor: switch from email to username-based auth"
git push
```

### Step 2: On EC2
```bash
ssh ec2-instance
cd ~/deployment2
git pull

# Backup old metadata (in case we need to rollback)
gsutil cp gs://deployment/metadata/users.json gs://deployment/metadata/users.json.backup

# Clear old user data (email-based) - IMPORTANT!
# You can either:
# Option A: Keep backup and manually migrate users
# Option B: Fresh start (recommended if not in production)

# For now, let's start fresh:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 3: Verify Deployment
```bash
docker ps
# Should show: api, redis, celery_worker

docker-compose logs backend -f
# Should show: ✅ FastAPI server running
```

---

## Testing Scenarios

### ✅ Scenario 1: Register New User

**Steps:**
1. Open frontend: `https://deployment2-nine.vercel.app/register`
2. Enter:
   - Username: `mudassir`
   - Password: `password123`
   - Confirm: `password123`
3. Click "Register"

**Expected Results:**
```
✅ Redirect to login page
✅ No errors in console
✅ Backend logs show: (none specifically, registration is fast)
```

---

### ✅ Scenario 2: Login with Username

**Steps:**
1. Go to login page
2. Enter:
   - Username: `mudassir`
   - Password: `password123`
3. Click "Login"

**Expected Results:**

**Browser Console (F12):**
```javascript
localStorage.getItem('user')
// Output: {"username":"mudassir"}
// NOT: {"user_id":"user_1","email":"mudassir@gmail.com"}
```

**Backend Logs:**
```
✅ No specific login logs (it's fast)
```

**Redirect:**
```
✅ Redirects to /dashboard
```

---

### ✅ Scenario 3: Upload with Username

**Steps:**
1. After login, click "Generate Summary"
2. Add carrier: "State Farm"
3. Upload Property PDF
4. Click "Execute"

**Network Tab (F12 → Network):**
```
Request to /upload-quotes/
Headers:
  X-User-ID: mudassir  ← Should be username!
```

**Backend Logs:**
```bash
docker-compose logs backend -f
# Expected output:
📝 Processing upload for user: mudassir
✅ Successfully uploaded 1 carriers with 1 PDF files
uploadId: upload_20250118_143022
```

**Browser:**
```
✅ Upload success dialog
✅ uploadId displayed
```

---

### ✅ Scenario 4: Processing & Sheet Population

**Monitoring Phase 1-3:**
```bash
docker-compose logs celery_worker -f
```

**Expected Logs:**
```
🚀 Processing upload_20250118_143022...
📋 Using user-specific sheet tab: 'mudassir'
✅ Opened user tab: mudassir
🎉 ALL CARRIERS COMPLETE! Auto-filling sheets...
```

**Google Sheets:**
1. Go to: https://docs.google.com/spreadsheets/d/1o94CsCnk3fvvMYjUQidjKNUjnfSaP89vPwYh4U4hKNY/edit
2. Check tabs at bottom
3. Click "mudassir" tab
4. **Verify:** Data populated (NOT in MAIN SHEET!)

---

### ✅ Scenario 5: Multiple Users (Data Isolation)

**User 2 Registration & Upload:**
1. New browser / incognito window
2. Register: username `aamir`
3. Login
4. Upload Allstate policy

**Expected:**
- Backend logs: `📝 Processing upload for user: aamir`
- Google Sheets > `aamir` tab: Shows Allstate data
- Google Sheets > `mudassir` tab: Still shows State Farm (unchanged!)

**Result:** ✅ Data isolation verified!

---

## Troubleshooting

### Issue 1: Login Shows "Username not found"
**Cause:** User not registered
**Solution:** Register first at `/register`, then login

### Issue 2: Data Going to MAIN SHEET Instead of Username Tab
**Logs:**
```bash
docker-compose logs celery_worker | grep "User tab"
```
**Expected:**
```
✅ Opened user tab: mudassir
```
**If shows:**
```
⚠️  User tab 'mudassir' not found. Falling back to MAIN SHEET
```
**Solution:** Pre-create sheet tabs (optional, system falls back gracefully)

### Issue 3: LocalStorage Shows Old Format
**Check:**
```javascript
localStorage.getItem('user')
```
**Old (wrong):**
```
{"user_id":"user_1","email":"mudassir@gmail.com"}
```
**New (correct):**
```
{"username":"mudassir"}
```
**Fix:** Clear localStorage → Log out → Log in again
```javascript
localStorage.clear()
```

### Issue 4: Backend Crashes on Login
**Check logs:**
```bash
docker-compose logs backend -f
```
**Common issues:**
- Database file corrupted → rebuild
- Old auth.py still in use → check git pull worked

**Solution:**
```bash
git status  # Verify all changes pulled
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Data Flow Verification

### Check 1: Database Structure
```bash
# Access GCS backend bucket to verify metadata
gsutil cat gs://deployment/metadata/users.json
```
**Expected format:**
```json
{
  "mudassir": {
    "username": "mudassir",
    "password": "password123",
    "created_at": "2025-01-18T14:30:22.123456"
  },
  "aamir": {
    "username": "aamir",
    "password": "password123",
    "created_at": "2025-01-18T14:35:45.654321"
  }
}
```

### Check 2: Upload Metadata
```bash
gsutil cat gs://deployment/metadata/uploads.json
```
**Expected format:**
```json
{
  "uploads": [
    {
      "uploadId": "upload_20250118_143022",
      "username": "mudassir",  ← NEW: username here!
      "uploadedAt": "2025-01-18T14:30:22.123456",
      "totalCarriers": 1,
      "totalFiles": 1,
      "carriers": [...]
    }
  ]
}
```

---

## Testing Checklist

- [ ] Register user "mudassir" successfully
- [ ] Login with "mudassir" - redirects to dashboard
- [ ] localStorage shows `{"username":"mudassir"}` only
- [ ] Upload Policy - header sends X-User-ID: mudassir
- [ ] Backend logs: `📝 Processing upload for user: mudassir`
- [ ] Backend logs: `📋 Using user-specific sheet tab: 'mudassir'`
- [ ] Google Sheets shows data in "mudassir" tab (not MAIN SHEET)
- [ ] Register user "aamir" and repeat steps 2-6
- [ ] "aamir" tab has separate data (isolation verified)
- [ ] "mudassir" tab unchanged after aamir upload

---

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Register | <1s | Fast, new user created |
| Login | <1s | Username lookup |
| Upload | 5-30s | File upload to GCS |
| Phase 1-3 | 2-10min | Background processing |
| Sheet population | <10s | When all phases done |

---

## Rollback Plan (If Needed)

If major issues occur:

```bash
# Restore old user metadata
gsutil cp gs://deployment/metadata/users.json.backup gs://deployment/metadata/users.json

# Revert code
git reset --hard HEAD~1

# Rebuild
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Success Criteria

✅ All tests pass
✅ No errors in console
✅ Usernames directly map to sheet tabs
✅ Data isolation between users works
✅ Sheet tabs match exactly with usernames

---

## Next Steps

1. Deploy code
2. Run through all scenarios
3. Monitor logs during processing
4. Verify sheet tabs contain correct data
5. Test with multiple users simultaneously
6. Monitor system for 24 hours

---

## Questions?

If issues arise:
1. Check backend logs: `docker-compose logs backend -f`
2. Check celery logs: `docker-compose logs celery_worker -f`
3. Check browser console: F12
4. Check localStorage: `localStorage.getItem('user')`
5. Review this guide: troubleshooting section

