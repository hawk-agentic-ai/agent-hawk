# Quick Fix Commands - Hedge Agent Local Setup

## 🚨 **IMMEDIATE FIX: Proxy Configuration Error**

If you get: `Proxy configuration file does not exist`

```bash
# The proxy.conf.json file is now included in the repo
# Just run:
npm run start

# Or:
ng serve
```

## 🔧 **Quick Development Setup**

### **1. Fix Package Dependencies**
```bash
cd hedge-agent

# Clear any cached issues
rm -rf node_modules package-lock.json

# Install all dependencies
npm install

# If Angular CLI is not installed globally:
npm install -g @angular/cli@18
```

### **2. Start Backend Services**
```bash
# Terminal 1: Create Python environment
python -m venv hedge_agent_env

# Windows:
hedge_agent_env\Scripts\activate

# macOS/Linux:
source hedge_agent_env/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start main backend
python unified_smart_backend.py
```

### **3. Start Frontend (New Terminal)**
```bash
cd hedge-agent

# This should now work without proxy errors:
npm run start
```

## 🚨 **TypeScript Error Fixes**

### **PrimeNG Template Errors**
If you see `'pTemplate' is not a known property`:

```bash
# Quick fix - temporarily disable strict mode
# Edit tsconfig.json:
{
  "compilerOptions": {
    "strict": false,
    "noImplicitAny": false
  }
}

# Then restart:
ng serve
```

### **Missing Component Errors**
If you see `Cannot find module './features/.../component'`:

```bash
# Check which components are missing:
find src -name "*.component.ts" | grep enhanced-prompt-templates

# If missing, create placeholder:
mkdir -p src/app/features/hawk-agent/prompt-templates
touch src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts

# Add minimal component:
echo 'import { Component } from "@angular/core";
@Component({
  selector: "app-enhanced-prompt-templates-v2",
  standalone: true,
  template: "<div>Loading...</div>"
})
export class EnhancedPromptTemplatesV2Component {}' > src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts
```

## 🎯 **Emergency Development Mode**

If you just need to get it running quickly:

```bash
# Start with minimal error checking
ng serve --aot=false --build-optimizer=false --source-map=false

# Or skip some validations
ng serve --skip-nx-cache --disable-host-check
```

## ✅ **Success Verification**

After running the fixes:

1. **Backend running**: http://localhost:8004/api/health should return {"status":"healthy"}
2. **Frontend loading**: http://localhost:4200 should show the Angular app
3. **No proxy errors**: Console should not show proxy configuration errors
4. **TypeScript compiling**: `ng serve` should complete without critical errors

## 📋 **Troubleshooting Checklist**

- [ ] `proxy.conf.json` exists in root directory
- [ ] `node_modules` directory exists (run `npm install` if not)
- [ ] Python virtual environment activated
- [ ] `requirements.txt` dependencies installed
- [ ] Backend service responding on port 8004
- [ ] No TypeScript strict mode blocking compilation
- [ ] Angular CLI version 18+ installed

## 🚀 **Development Ready Commands**

Once everything is working:

```bash
# Full development setup
# Terminal 1 - Backend:
hedge_agent_env\Scripts\activate
python unified_smart_backend.py

# Terminal 2 - Frontend:
npm run start

# Terminal 3 - Optional MCP servers:
python mcp_server_production.py     # Port 8009
python mcp_allocation_server.py     # Port 8010
```

---

*Last Updated: September 24, 2025*
*Emergency Fix Guide for New Machine Setup*