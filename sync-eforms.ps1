#!/usr/bin/env pwsh
# Sync Eforms Updates Script
# This script pulls latest changes from Eforms repo and copies only changed files to your project
#
# USAGE:
#   .\sync-eforms.ps1
#
# WHAT IT DOES:
#   1. Pulls latest changes from eforms/ repo
#   2. Shows what changed (commits and files)
#   3. Copies ONLY changed files to frontend/
#   4. Shows git status and next steps
#
# REQUIREMENTS:
#   - eforms/ folder must exist (clone Eforms repo first)
#   - Must be run from project root (deployment2/)

# Color output functions
function Write-Success { 
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green 
}
function Write-Info { 
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan 
}
function Write-Warning { 
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow 
}
function Write-ErrorMsg { 
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red 
}

Write-Host "`n🔄 Eforms Sync Script`n" -ForegroundColor Magenta

# Configuration
$EFORMS_SOURCE = "eforms"
$PROJECT_ROOT = Get-Location

# Check if eforms source directory exists
if (-not (Test-Path $EFORMS_SOURCE)) {
    Write-ErrorMsg "Eforms source directory not found: $EFORMS_SOURCE"
    Write-Info "Please clone the Eforms repository first:"
    Write-Host "  git clone YOUR-EFORMS-REPO-URL $EFORMS_SOURCE" -ForegroundColor Gray
    exit 1
}

# Step 1: Pull latest from Eforms repo
Write-Info "Pulling latest changes from Eforms repository..."
Set-Location $EFORMS_SOURCE

# Check if it's a git repo
if (-not (Test-Path ".git")) {
    Write-ErrorMsg "$EFORMS_SOURCE is not a git repository"
    Set-Location $PROJECT_ROOT
    exit 1
}

# Get current commit before pull
$BEFORE_COMMIT = git rev-parse HEAD

# Pull latest changes
try {
    git pull origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Git pull failed, trying 'master' branch..."
        git pull origin master 2>&1 | Out-Null
    }
} catch {
    Write-ErrorMsg "Failed to pull from remote repository"
    Set-Location $PROJECT_ROOT
    exit 1
}

# Get current commit after pull
$AFTER_COMMIT = git rev-parse HEAD

Set-Location $PROJECT_ROOT

# Step 2: Check if there are any changes
if ($BEFORE_COMMIT -eq $AFTER_COMMIT) {
    Write-Success "Already up to date! No changes from Eforms repository."
    exit 0
}

# Step 3: Show what changed
Write-Info "Changes detected! Showing recent commits..."
Write-Host ""
Set-Location $EFORMS_SOURCE
git log --oneline --graph --decorate -5
Write-Host ""

# Get list of changed files
$CHANGED_FILES = git diff --name-only "$BEFORE_COMMIT..$AFTER_COMMIT"
Write-Info "Files changed in Eforms repository:"
$CHANGED_FILES | ForEach-Object { Write-Host "  📄 $_" -ForegroundColor Yellow }
Write-Host ""

Set-Location $PROJECT_ROOT

# Step 4: Define file mappings (source -> destination)
$FILE_MAPPINGS = @{
    # Pages
    "app/page.tsx" = "frontend/app/cstore/page.tsx"
    "app/auth/page.tsx" = "frontend/app/cstore/auth/page.tsx"
    
    # API Routes
    "app/api/prefill/route.ts" = "frontend/app/api/prefill/route.ts"
    "app/api/ghl/route.ts" = "frontend/app/api/ghl/route.ts"
    "app/api/ghl/resume/route.ts" = "frontend/app/api/ghl/resume/route.ts"
    "app/api/autocomplete/route.ts" = "frontend/app/api/autocomplete/route.ts"
    
    # Components
    "components/FormSection.tsx" = "frontend/components/eforms/FormSection.tsx"
    "components/AuthProvider.tsx" = "frontend/components/eforms/AuthProvider.tsx"
    "components/AreaMeasurementModal.tsx" = "frontend/components/eforms/AreaMeasurementModal.tsx"
    "components/ComprehensiveSidePanel.tsx" = "frontend/components/eforms/ComprehensiveSidePanel.tsx"
    
    # Types
    "types/form.ts" = "frontend/types/eforms/form.ts"
    
    # Lib
    "lib/pdf.ts" = "frontend/lib/eforms/pdf.ts"
    "lib/prefill.js" = "frontend/lib/eforms/prefill.js"
    
    # Styles
    "app/globals.css" = "frontend/styles/eforms.css"
}

# Step 5: Copy only changed files
Write-Info "Copying changed files to your project..."
$COPIED_COUNT = 0
$SKIPPED_COUNT = 0

foreach ($mapping in $FILE_MAPPINGS.GetEnumerator()) {
    $source = $mapping.Key
    $destination = $mapping.Value
    $sourcePath = Join-Path $EFORMS_SOURCE $source
    
    # Check if this file was changed
    $isChanged = $CHANGED_FILES | Where-Object { $_ -eq $source }
    
    if ($isChanged) {
        if (Test-Path $sourcePath) {
            # Create destination directory if it doesn't exist
            $destDir = Split-Path $destination -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            
            # Copy file
            Copy-Item -Path $sourcePath -Destination $destination -Force
            Write-Success "Copied: $source → $destination"
            $COPIED_COUNT++
        } else {
            Write-Warning "Source file not found: $sourcePath"
        }
    } else {
        $SKIPPED_COUNT++
    }
}

Write-Host ""
Write-Info "Summary: Copied $COPIED_COUNT files, Skipped $SKIPPED_COUNT unchanged files"
Write-Host ""

# Step 6: Show git status in your project
if ($COPIED_COUNT -gt 0) {
    Write-Info "Changes in your project:"
    git status --short
    Write-Host ""
    
    # Step 7: Next steps
    Write-Host "[NEXT STEPS]" -ForegroundColor Magenta
    Write-Host "  1. Review changes:" -ForegroundColor Gray
    Write-Host "     git diff" -ForegroundColor White
    Write-Host ""
    Write-Host "  2. Test locally:" -ForegroundColor Gray
    Write-Host "     cd frontend" -ForegroundColor White
    Write-Host "     npm run dev" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Commit changes:" -ForegroundColor Gray
    Write-Host "     git add ." -ForegroundColor White
    Write-Host "     git commit -m 'sync: update Eforms to latest version'" -ForegroundColor White
    Write-Host ""
    Write-Host "  4. Push to GitHub:" -ForegroundColor Gray
    Write-Host "     git push origin testing" -ForegroundColor White
    Write-Host ""
    
    Write-Success "Sync complete! Review changes and test before committing"
} else {
    Write-Success "No files needed to be copied - changes were in non-tracked files"
}

