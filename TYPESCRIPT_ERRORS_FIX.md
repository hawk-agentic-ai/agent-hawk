# TypeScript Errors Fix Guide - Hawk Agent

## 🎯 Common TypeScript Errors & Solutions

When downloading and setting up the Hawk Agent project on a new machine, you may encounter several TypeScript compilation errors. Here are the most common issues and their fixes:

## 🚨 Error 1: PrimeNG Template Directive Errors

### **Issue**: `pTemplate` directive errors
```typescript
// Error in prompt-history.component.ts line 184:
'pTemplate' is not a known property of 'ng-template'
```

### **Root Cause**:
- Missing PrimeNG template imports
- Incorrect PrimeNG version compatibility
- Angular 18 standalone component issues

### **Solution**:
```typescript
// Fix: Update imports in prompt-history.component.ts
import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridOptions, GridReadyEvent, GridApi, CellClickedEvent } from 'ag-grid-community';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { DialogModule } from 'primeng/dialog';
import { TooltipModule } from 'primeng/tooltip';
// ADD THIS LINE:
import { SharedModule } from 'primeng/api'; // For pTemplate directive
```

### **Alternative Fix**: Replace `pTemplate` with standard Angular template
```html
<!-- CHANGE FROM: -->
<ng-template pTemplate="footer">

<!-- CHANGE TO: -->
<ng-template #footer>

<!-- And update the dialog: -->
<p-dialog
    header="View Prompt Details"
    [(visible)]="showDialog"
    [modal]="true">
    <!-- content -->
    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button class="btn btn-secondary" (click)="showDialog = false">Close</button>
        <button class="btn btn-primary" (click)="downloadPrompt(selectedPrompt!)">
            <i class="pi pi-download mr-2"></i>
            Download
        </button>
    </div>
</p-dialog>
```

## 🚨 Error 2: Angular Router Issues in app.routes.ts

### **Issue**: Component import path errors
```typescript
// Error: Cannot find module './features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component'
```

### **Solution**:
1. **Check if components exist**:
```bash
find src -name "*enhanced-prompt-templates-v2*" -type f
```

2. **Update import paths** if components are missing or renamed:
```typescript
// In app.routes.ts, replace missing components:

// IF enhanced-prompt-templates-v2.component.ts is missing:
{ path: 'hawk-agent/prompt-templates',
  loadComponent: () => import('./features/hawk-agent/prompt-templates/prompt-templates.component').then(m => m.PromptTemplatesComponent)
},

// OR create a fallback component:
{ path: 'hawk-agent/prompt-templates',
  loadComponent: () => import('./shared/fallback/fallback.component').then(m => m.FallbackComponent)
}
```

## 🚨 Error 3: Missing Service Dependencies

### **Issue**: Service import errors
```typescript
// Error: Cannot find module '../services/hawk-agent-simple.service'
```

### **Solution**: Check service file exists and create if missing:
```bash
# Check if service exists:
find src -name "*hawk-agent-simple.service*" -type f

# If missing, the service file should be at:
# src/app/features/hawk-agent/services/hawk-agent-simple.service.ts
```

## 🚨 Error 4: Supabase Client Issues

### **Issue**: Supabase import errors
```typescript
// Error: Cannot find module '../../../core/data/supabase.client'
```

### **Solution**: Verify Supabase client setup:
```bash
# Check if file exists:
find src -name "supabase.client.ts" -type f

# Should be at: src/app/core/data/supabase.client.ts
```

## 🛠️ Complete Fix Commands

### **Step 1: Install All Dependencies**
```bash
cd hedge-agent

# Clear any cached modules
rm -rf node_modules package-lock.json

# Install dependencies
npm install

# If PrimeNG issues persist:
npm install primeng@17.18.0 primeicons@7.0.0 --save

# Ensure AG-Grid compatibility:
npm install ag-grid-angular@32.0.0 ag-grid-community@32.0.0 --save
```

### **Step 2: Fix TypeScript Configuration**
```bash
# Update tsconfig.json if needed
# Ensure these compiler options:
{
  "compilerOptions": {
    "strict": false,  # Temporarily disable for initial setup
    "noImplicitAny": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true
  }
}
```

### **Step 3: Create Missing Components (if needed)**
```bash
# If enhanced-prompt-templates-v2.component is missing:
ng generate component features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2 --standalone

# If hawk-agent-simple.service is missing:
ng generate service features/hawk-agent/services/hawk-agent-simple
```

### **Step 4: Fix PrimeNG Template Issues**
Create a quick fix component to replace problematic templates:

```typescript
// Create: src/app/shared/dialog-footer/dialog-footer.component.ts
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-dialog-footer',
  standalone: true,
  imports: [CommonModule, ButtonModule],
  template: `
    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
      <button class="btn btn-secondary" (click)="onClose()">Close</button>
      <button class="btn btn-primary" (click)="onDownload()">
        <i class="pi pi-download mr-2"></i>
        Download
      </button>
    </div>
  `
})
export class DialogFooterComponent {
  @Input() selectedPrompt: any;
  @Output() close = new EventEmitter<void>();
  @Output() download = new EventEmitter<any>();

  onClose() { this.close.emit(); }
  onDownload() { this.download.emit(this.selectedPrompt); }
}
```

## 🚀 Quick Start Commands

### **For Development (Ignore Errors Temporarily)**
```bash
# Start with type checking disabled
ng serve --skip-nx-cache --disable-host-check

# Or with reduced type checking
ng serve --configuration development --aot=false
```

### **For Production Build Fix**
```bash
# Fix errors systematically then build
npm run build

# If build fails, try:
ng build --configuration production --aot=false --build-optimizer=false
```

## 📋 Checklist for New Machine Setup

- [ ] Node.js 18+ installed
- [ ] Angular CLI 18+ installed (`npm install -g @angular/cli@18`)
- [ ] All npm packages installed (`npm install`)
- [ ] PrimeNG templates fixed or replaced
- [ ] Missing components created or paths updated
- [ ] Supabase client configuration verified
- [ ] TypeScript compiler options relaxed if needed
- [ ] Development server starts without critical errors

## 🎯 Priority Fixes

1. **Critical**: Fix missing component imports in `app.routes.ts`
2. **High**: Replace `pTemplate` directives with standard Angular templates
3. **Medium**: Ensure all service imports are correct
4. **Low**: Update TypeScript strict mode settings

## 💡 Pro Tips

- **Start with `ng serve --aot=false`** to bypass complex build optimizations initially
- **Check Angular/PrimeNG version compatibility** - Angular 18 + PrimeNG 17.18.0 is tested
- **Use `find` commands** to locate missing files before fixing import paths
- **Create placeholder components** for missing routes to avoid runtime errors
- **Gradually enable TypeScript strict mode** after basic functionality works

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*Angular 18 + PrimeNG 17.18 Compatibility Guide*