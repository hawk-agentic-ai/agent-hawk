# Setup Troubleshooting Guide

## Issue: "Cannot find module" errors after cloning

If you're seeing errors like:
```
Error: Can't resolve './features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component'
Error: Cannot find module '../services/hawk-agent-simple.service'
```

### Root Cause
The files ARE in the repository but may not have been pulled correctly during clone.

---

## Solution 1: Clean Clone (Recommended)

```bash
# Remove the existing directory
rm -rf agent-hawk

# Clone fresh from GitHub
git clone https://github.com/hawk-agentic-ai/agent-hawk.git
cd agent-hawk

# Verify files exist
ls -la src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts
ls -la src/app/features/hawk-agent/services/hawk-agent-simple.service.ts

# Both should show file sizes around 90KB and 20KB respectively
```

---

## Solution 2: Force Pull Latest Changes

```bash
cd agent-hawk

# Reset to latest remote state
git fetch origin
git reset --hard origin/main

# Verify files exist
ls -la src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts
ls -la src/app/features/hawk-agent/services/hawk-agent-simple.service.ts
```

---

## Solution 3: Check Git LFS (if files are very large)

```bash
# Check if Git LFS is installed
git lfs version

# If not installed:
# Mac: brew install git-lfs
# Windows: Download from https://git-lfs.github.com/
# Linux: sudo apt-get install git-lfs

# Initialize Git LFS
git lfs install

# Pull LFS files
git lfs pull
```

---

## Verify Files Exist in Repository

Run this command to check if files are tracked in git:

```bash
git ls-tree -r HEAD --name-only | grep -E "enhanced-prompt-templates-v2.component.ts|hawk-agent-simple.service.ts"
```

**Expected output:**
```
src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts
src/app/features/hawk-agent/services/hawk-agent-simple.service.ts
```

If you don't see this output, the files aren't in your local copy.

---

## Complete Setup Steps After Clone

### 1. Install Dependencies
```bash
npm install
```

**Expected:** ~1500+ packages installed in `node_modules/`

### 2. Verify Angular CLI
```bash
ng version
```

**Expected output includes:**
- Angular CLI: 15.x or higher
- Node: 18.x or higher
- Package Manager: npm 9.x or higher

### 3. Check TypeScript Configuration
```bash
cat tsconfig.json | grep "strict"
```

**Should show:**
```json
"strict": false
```

If strict mode is `true`, change it to `false` to avoid type errors.

### 4. Start Development Server
```bash
npm start
# OR
ng serve --port 4200
```

### 5. Access the Application
Open browser to: **http://localhost:4200/hawk-agent**

**Important:** Don't go to just `http://localhost:4200/` - the app redirects to `/hawk-agent`

---

## Common Compilation Errors & Fixes

### Error: "Cannot find module" or "TS2307"

**Cause:** Missing TypeScript files or wrong import paths

**Fix:**
1. Verify file exists: `ls -la src/app/features/hawk-agent/services/hawk-agent-simple.service.ts`
2. If missing, re-clone or force pull (see Solution 1 or 2 above)
3. Clear Angular cache: `rm -rf .angular/`
4. Reinstall: `npm ci`

### Error: "No suitable injection token" or "NG2003"

**Cause:** TypeScript strict mode or wrong service import

**Fix in `tsconfig.json`:**
```json
{
  "compilerOptions": {
    "strict": false,
    "strictPropertyInitialization": false,
    "strictNullChecks": false
  }
}
```

Then restart: `ng serve`

### Error: "Parameter 'X' implicitly has an 'any' type"

**Fix in `tsconfig.json`:**
```json
{
  "compilerOptions": {
    "noImplicitAny": false
  }
}
```

---

## File Checksums for Verification

If you want to verify you have the correct files, check these file sizes:

| File | Approximate Size |
|------|-----------------|
| `enhanced-prompt-templates-v2.component.ts` | ~93 KB |
| `hawk-agent-simple.service.ts` | ~18 KB |

```bash
# Check file sizes
ls -lh src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts
ls -lh src/app/features/hawk-agent/services/hawk-agent-simple.service.ts
```

---

## Still Having Issues?

### Debug Information to Collect

1. **Git status:**
```bash
git status
git log --oneline -3
```

2. **File existence:**
```bash
find src/app/features/hawk-agent -name "*.component.ts" | head -10
find src/app/features/hawk-agent -name "*.service.ts" | head -10
```

3. **Node/npm versions:**
```bash
node --version
npm --version
ng version
```

4. **Build output:**
```bash
ng build 2>&1 | tee build-error.log
```

### Contact Support
Share the output of the above commands along with:
- Your operating system (Mac/Windows/Linux)
- Git version: `git --version`
- Full error message from `ng serve`

---

## Quick Checklist

- [ ] Cloned repository fresh
- [ ] Ran `npm install` (no errors)
- [ ] Verified files exist (both .component.ts and .service.ts)
- [ ] Set `strict: false` in tsconfig.json
- [ ] Cleared Angular cache (`rm -rf .angular/`)
- [ ] Started server with `npm start`
- [ ] Accessed `http://localhost:4200/hawk-agent` (not just root)

If all checkboxes are ticked and it still doesn't work, there may be a platform-specific issue.
