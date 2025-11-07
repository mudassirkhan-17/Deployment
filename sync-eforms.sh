#!/bin/bash
# Sync Eforms Updates Script
# This script pulls latest changes from Eforms repo and copies only changed files to your project

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${MAGENTA}\n🔄 Eforms Sync Script\n${NC}"

# Configuration
EFORMS_SOURCE="eforms"
PROJECT_ROOT=$(pwd)

# Check if eforms source directory exists
if [ ! -d "$EFORMS_SOURCE" ]; then
    echo -e "${RED}❌ Eforms source directory not found: $EFORMS_SOURCE${NC}"
    echo -e "${CYAN}ℹ️  Please clone the Eforms repository first:${NC}"
    echo "  git clone <eforms-repo-url> $EFORMS_SOURCE"
    exit 1
fi

# Step 1: Pull latest from Eforms repo
echo -e "${CYAN}ℹ️  Pulling latest changes from Eforms repository...${NC}"
cd "$EFORMS_SOURCE"

# Check if it's a git repo
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ $EFORMS_SOURCE is not a git repository${NC}"
    cd "$PROJECT_ROOT"
    exit 1
fi

# Get current commit before pull
BEFORE_COMMIT=$(git rev-parse HEAD)

# Pull latest changes
if ! git pull origin main 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Git pull from 'main' failed, trying 'master' branch...${NC}"
    git pull origin master 2>/dev/null || {
        echo -e "${RED}❌ Failed to pull from remote repository${NC}"
        cd "$PROJECT_ROOT"
        exit 1
    }
fi

# Get current commit after pull
AFTER_COMMIT=$(git rev-parse HEAD)

cd "$PROJECT_ROOT"

# Step 2: Check if there are any changes
if [ "$BEFORE_COMMIT" = "$AFTER_COMMIT" ]; then
    echo -e "${GREEN}✅ Already up to date! No changes from Eforms repository.${NC}"
    exit 0
fi

# Step 3: Show what changed
echo -e "${CYAN}ℹ️  Changes detected! Showing recent commits...${NC}"
echo ""
cd "$EFORMS_SOURCE"
git log --oneline --graph --decorate -5
echo ""

# Get list of changed files
CHANGED_FILES=$(git diff --name-only "$BEFORE_COMMIT..$AFTER_COMMIT")
echo -e "${CYAN}ℹ️  Files changed in Eforms repository:${NC}"
echo "$CHANGED_FILES" | while read -r file; do
    echo -e "  ${YELLOW}📄 $file${NC}"
done
echo ""

cd "$PROJECT_ROOT"

# Step 4: Define file mappings (source -> destination)
declare -A FILE_MAPPINGS=(
    # Pages
    ["app/page.tsx"]="frontend/app/cstore/page.tsx"
    ["app/auth/page.tsx"]="frontend/app/cstore/auth/page.tsx"
    
    # API Routes
    ["app/api/prefill/route.ts"]="frontend/app/api/prefill/route.ts"
    ["app/api/ghl/route.ts"]="frontend/app/api/ghl/route.ts"
    ["app/api/ghl/resume/route.ts"]="frontend/app/api/ghl/resume/route.ts"
    ["app/api/autocomplete/route.ts"]="frontend/app/api/autocomplete/route.ts"
    
    # Components
    ["components/FormSection.tsx"]="frontend/components/eforms/FormSection.tsx"
    ["components/AuthProvider.tsx"]="frontend/components/eforms/AuthProvider.tsx"
    ["components/AreaMeasurementModal.tsx"]="frontend/components/eforms/AreaMeasurementModal.tsx"
    ["components/ComprehensiveSidePanel.tsx"]="frontend/components/eforms/ComprehensiveSidePanel.tsx"
    
    # Types
    ["types/form.ts"]="frontend/types/eforms/form.ts"
    
    # Lib
    ["lib/pdf.ts"]="frontend/lib/eforms/pdf.ts"
    ["lib/prefill.js"]="frontend/lib/eforms/prefill.js"
    
    # Styles
    ["app/globals.css"]="frontend/styles/eforms.css"
)

# Step 5: Copy only changed files
echo -e "${CYAN}ℹ️  Copying changed files to your project...${NC}"
COPIED_COUNT=0
SKIPPED_COUNT=0

for source in "${!FILE_MAPPINGS[@]}"; do
    destination="${FILE_MAPPINGS[$source]}"
    source_path="$EFORMS_SOURCE/$source"
    
    # Check if this file was changed
    if echo "$CHANGED_FILES" | grep -q "^$source$"; then
        if [ -f "$source_path" ]; then
            # Create destination directory if it doesn't exist
            dest_dir=$(dirname "$destination")
            mkdir -p "$dest_dir"
            
            # Copy file
            cp "$source_path" "$destination"
            echo -e "${GREEN}✅ Copied: $source → $destination${NC}"
            ((COPIED_COUNT++))
        else
            echo -e "${YELLOW}⚠️  Source file not found: $source_path${NC}"
        fi
    else
        ((SKIPPED_COUNT++))
    fi
done

echo ""
echo -e "${CYAN}ℹ️  Summary: Copied $COPIED_COUNT files, Skipped $SKIPPED_COUNT unchanged files${NC}"
echo ""

# Step 6: Show git status in your project
if [ $COPIED_COUNT -gt 0 ]; then
    echo -e "${CYAN}ℹ️  Changes in your project:${NC}"
    git status --short
    echo ""
    
    # Step 7: Next steps
    echo -e "${MAGENTA}📋 Next Steps:${NC}"
    echo -e "  ${NC}1. Review changes:${NC}"
    echo -e "     ${NC}git diff${NC}"
    echo ""
    echo -e "  ${NC}2. Check for import path issues:${NC}"
    echo -e "     ${NC}grep -r \"from '@/types/form'\" frontend/app/cstore/${NC}"
    echo -e "     ${NC}grep -r \"from '@/components/\" frontend/app/cstore/${NC}"
    echo ""
    echo -e "  ${NC}3. Test locally:${NC}"
    echo -e "     ${NC}cd frontend && npm run dev${NC}"
    echo ""
    echo -e "  ${NC}4. Commit changes:${NC}"
    echo -e "     ${NC}git add .${NC}"
    echo -e "     ${NC}git commit -m \"sync: update Eforms to latest version\"${NC}"
    echo ""
    echo -e "  ${NC}5. Push to GitHub:${NC}"
    echo -e "     ${NC}git push origin testing${NC}"
    echo ""
    
    echo -e "${GREEN}✅ Sync complete! Review changes and test before committing.${NC}"
else
    echo -e "${GREEN}✅ No files needed to be copied (changes were in non-tracked files).${NC}"
fi

