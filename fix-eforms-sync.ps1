#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated fix script for Eforms sync conflicts
    
.DESCRIPTION
    This script automatically fixes structural differences between the Eforms source repo
    and the integrated structure in deployment2/frontend:
    
    1. Import paths: @/components/FormSection -> @/components/eforms/FormSection
    2. Route paths: /auth -> /cstore/auth
    3. Backdrop overlay: Removes full-screen backdrop, keeps left-side panel only
    4. Dependency checks: Detects new npm packages that need installation
    
.NOTES
    Run this script AFTER sync-eforms.ps1 to apply all necessary fixes
#>

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

Write-Host "`n🔧 Eforms Sync Fix Script`n" -ForegroundColor Magenta

$PROJECT_ROOT = Get-Location
$CSTORE_PAGE = "frontend/app/cstore/page.tsx"
$AUTH_PAGE = "frontend/app/cstore/auth/page.tsx"

# ============================================================================
# FIX 1: Import Paths
# ============================================================================
Write-Info "Fixing import paths..."

$importFixes = @{
    '@/components/FormSection' = '@/components/eforms/FormSection'
    '@/types/form' = '@/types/eforms/form'
    '@/lib/pdf' = '@/lib/eforms/pdf'
    '@/components/AreaMeasurementModal' = '@/components/eforms/AreaMeasurementModal'
    '@/components/ComprehensiveSidePanel' = '@/components/eforms/ComprehensiveSidePanel'
    '@/components/AuthProvider' = '@/components/eforms/AuthProvider'
}

$fixedImports = 0
if (Test-Path $CSTORE_PAGE) {
    $content = Get-Content $CSTORE_PAGE -Raw
    $originalContent = $content
    
    foreach ($old in $importFixes.Keys) {
        $new = $importFixes[$old]
        if ($content -match [regex]::Escape($old)) {
            $content = $content -replace [regex]::Escape($old), $new
            $fixedImports++
        }
    }
    
    if ($content -ne $originalContent) {
        $content | Set-Content $CSTORE_PAGE -NoNewline
        Write-Success "Fixed $fixedImports import path(s) in $CSTORE_PAGE"
    } else {
        Write-Info "No import path fixes needed in $CSTORE_PAGE"
    }
} else {
    Write-Warning "$CSTORE_PAGE not found, skipping import fixes"
}

# ============================================================================
# FIX 2: Route Paths
# ============================================================================
Write-Info "Fixing route paths..."

$routeFixes = @{
    "router.push\('/auth'\)" = "router.push('/cstore/auth')"
    "router.push\(`"/auth`"\)" = "router.push('/cstore/auth')"
    'href="/auth"' = 'href="/cstore/auth"'
}

$fixedRoutes = 0
if (Test-Path $CSTORE_PAGE) {
    $content = Get-Content $CSTORE_PAGE -Raw
    $originalContent = $content
    
    foreach ($old in $routeFixes.Keys) {
        $new = $routeFixes[$old]
        if ($content -match $old) {
            $content = $content -replace $old, $new
            $fixedRoutes++
        }
    }
    
    if ($content -ne $originalContent) {
        $content | Set-Content $CSTORE_PAGE -NoNewline
        Write-Success "Fixed $fixedRoutes route path(s) in $CSTORE_PAGE"
    } else {
        Write-Info "No route path fixes needed in $CSTORE_PAGE"
    }
} else {
    Write-Warning "$CSTORE_PAGE not found, skipping route fixes"
}

# ============================================================================
# FIX 3: Backdrop Overlay (Complex Multi-line Fix)
# ============================================================================
Write-Info "Fixing backdrop overlay..."

if (Test-Path $CSTORE_PAGE) {
    $content = Get-Content $CSTORE_PAGE -Raw
    
    # Pattern 1: Full backdrop structure with onClick handler
    $backdropPattern1 = '(?s)<div className="fixed inset-0 z-50 flex">\s*\{/\* Backdrop \*/\}\s*<div\s+className="absolute inset-0 bg-black bg-opacity-50"\s+onClick=\{\(\) => setShowResumePanel\(false\)\}\s*></div>\s*\{/\* Panel \*/\}\s*<div className="relative w-96 bg-white shadow-2xl overflow-y-auto">'
    
    $backdropReplacement1 = '<div className="fixed inset-y-0 left-0 z-50 w-96">
          {/* Panel */}
          <div className="relative w-full h-full bg-white shadow-2xl overflow-y-auto">'
    
    if ($content -match $backdropPattern1) {
        $content = $content -replace $backdropPattern1, $backdropReplacement1
        $content | Set-Content $CSTORE_PAGE -NoNewline
        Write-Success "Fixed backdrop overlay (removed full-screen backdrop)"
    } else {
        # Pattern 2: Alternative backdrop structure
        $backdropPattern2 = '(?s)<div className="fixed inset-0 z-50">\s*<div\s+className="[^"]*bg-black[^"]*"\s+onClick=\{\(\) => setShowResumePanel\(false\)\}[^>]*></div>'
        
        if ($content -match $backdropPattern2) {
            $content = $content -replace '<div className="fixed inset-0 z-50">', '<div className="fixed inset-y-0 left-0 z-50 w-96">'
            $content = $content -replace '(?s)<div\s+className="[^"]*bg-black[^"]*"\s+onClick=\{\(\) => setShowResumePanel\(false\)\}[^>]*></div>\s*', ''
            $content | Set-Content $CSTORE_PAGE -NoNewline
            Write-Success "Fixed backdrop overlay (alternative pattern)"
        } else {
            Write-Info "No backdrop overlay fixes needed (already correct or not found)"
        }
    }
} else {
    Write-Warning "$CSTORE_PAGE not found, skipping backdrop fixes"
}

# ============================================================================
# FIX 4: Check for New Dependencies
# ============================================================================
Write-Info "Checking for new dependencies..."

if (Test-Path "eforms/package.json") {
    Push-Location eforms
    
    # Get list of added dependencies from last commit
    $gitDiff = git diff HEAD~1 HEAD -- package.json 2>$null
    
    if ($gitDiff) {
        $newDeps = $gitDiff | Select-String '^\+\s*"[^"]+"\s*:\s*"' | ForEach-Object {
            if ($_ -match '^\+\s*"([^"]+)"\s*:\s*"([^"]+)"') {
                [PSCustomObject]@{
                    Package = $matches[1]
                    Version = $matches[2]
                }
            }
        }
        
        if ($newDeps) {
            Write-Warning "New dependencies detected in Eforms repo:"
            $newDeps | ForEach-Object {
                Write-Host "  - $($_.Package)@$($_.Version)" -ForegroundColor Yellow
            }
            Write-Host "`n  Run: cd frontend && npm install" -ForegroundColor Cyan
            Write-Host "  Or install specific packages:" -ForegroundColor Cyan
            $packageList = ($newDeps | ForEach-Object { $_.Package }) -join ' '
            Write-Host "  npm install $packageList" -ForegroundColor White
        } else {
            Write-Info "No new dependencies detected"
        }
    } else {
        Write-Info "No package.json changes detected"
    }
    
    Pop-Location
} else {
    Write-Warning "eforms/package.json not found, skipping dependency check"
}

# ============================================================================
# FIX 5: Check for New Environment Variables
# ============================================================================
Write-Info "Checking for new environment variables..."

$envVarsFound = @()

# Check all API route files for new env vars
$apiRoutes = Get-ChildItem -Path "frontend/app/api" -Recurse -Filter "*.ts" -ErrorAction SilentlyContinue

foreach ($file in $apiRoutes) {
    $content = Get-Content $file.FullName -Raw
    $envMatches = [regex]::Matches($content, 'process\.env\.([A-Z_]+)')
    
    foreach ($match in $envMatches) {
        $envVar = $match.Groups[1].Value
        if ($envVar -notin $envVarsFound) {
            $envVarsFound += $envVar
        }
    }
}

if ($envVarsFound.Count -gt 0) {
    Write-Warning "Environment variables used in API routes:"
    $envVarsFound | Sort-Object | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor Yellow
    }
    Write-Host "`n  Make sure these are set in:" -ForegroundColor Cyan
    Write-Host "  - frontend/.env.local (local development)" -ForegroundColor White
    Write-Host "  - Vercel dashboard (production)" -ForegroundColor White
} else {
    Write-Info "No environment variables detected"
}

# ============================================================================
# Summary
# ============================================================================
Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -NoNewline -ForegroundColor Gray
Write-Host "=" -ForegroundColor Gray
Write-Success "Sync fixes complete!"
Write-Host "`n📋 Next Steps:" -ForegroundColor Magenta
Write-Host "  1. Test locally: cd frontend && npm run dev" -ForegroundColor Gray
Write-Host "  2. Check for errors in the console" -ForegroundColor Gray
Write-Host "  3. Test Eforms functionality (prefill, submit, resume)" -ForegroundColor Gray
Write-Host "  4. If everything works:" -ForegroundColor Gray
Write-Host '     git add .' -ForegroundColor White
Write-Host '     git commit -m "sync: update Eforms with automated fixes"' -ForegroundColor White
Write-Host '     git push origin testing' -ForegroundColor White
Write-Host "`n"

