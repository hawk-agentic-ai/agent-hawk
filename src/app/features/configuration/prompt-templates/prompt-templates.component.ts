import { Component, OnInit, OnDestroy, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { DialogModule } from 'primeng/dialog';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridOptions, GridReadyEvent } from 'ag-grid-community';
import { PromptTemplatesService, PromptTemplate } from './prompt-templates.service';

@Component({
  selector: 'app-prompt-templates',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule,
    AgGridAngular,
    InputTextModule,
    DropdownModule,
    DialogModule,
    InputTextareaModule,
    FormsModule
  ],
  template: `
<div class="p-6">
  <!-- Page Header -->
  <div class="mb-6">
    <h2 class="text-xl font-semibold text-gray-900 mb-2">Prompt Templates Configuration</h2>
    <p class="text-gray-600">Manage and configure prompt templates for HAWK Agent Template Mode</p>
  </div>

  <!-- Horizontal Family Type Tabs -->
  <div class="mb-3 overflow-x-auto">
    <div class="flex gap-2">
      <button *ngFor="let f of familyTypeOptions"
              class="px-3 py-1.5 rounded-full border text-sm whitespace-nowrap"
              [class.bg-blue-600]="selectedFamilyType===f.value"
              [class.text-white]="selectedFamilyType===f.value"
              [class.border-blue-600]="selectedFamilyType===f.value"
              [class.bg-white]="selectedFamilyType!==f.value"
              [class.text-gray-700]="selectedFamilyType!==f.value"
              [class.border-gray-300]="selectedFamilyType!==f.value"
              (click)="onFamilyTabChange(f.value)">{{ f.label }}</button>
    </div>
  </div>

  <!-- Search and Add Button Section -->
  <div class="flex items-center gap-4 mb-4">
    <div class="flex-1 flex items-center gap-2">
      <label class="filter-label">Search:</label>
      <input type="text" placeholder="Search templates..." [(ngModel)]="search" (ngModelChange)="onSearchChange($event)" class="filter-input flex-1 max-w-xs">
    </div>
    <button class="btn btn-primary ml-auto" (click)="openAdd()">
      <i class="pi pi-plus"></i>
      <span>Add Template</span>
    </button>
  </div>

  <!-- Data Grid -->
  <div class="bg-white rounded-lg shadow-sm border border-gray-200">
    <ag-grid-angular
      class="ag-theme-alpine w-full"
      style="height: 600px;"
      [columnDefs]="columnDefs"
      [rowData]="filteredTemplates"
      [defaultColDef]="defaultColDef"
      [gridOptions]="gridOptions"
      (gridReady)="onGridReady($event)">
    </ag-grid-angular>
  </div>

  <!-- Add/Edit Template Dialog -->
  <p-dialog 
    header="{{ mode === 'edit' ? 'Edit Template' : 'Add Template' }}" 
    [(visible)]="showSheet"
    [modal]="true"
    [style]="{width: '100vw', height: '90vh', 'border-top-left-radius': '16px', 'border-top-right-radius': '16px', 'max-width': '100vw', 'max-height': '90vh'}"
    [closable]="true"
    styleClass="entity-dialog entity-dialog-full">
    <form class="space-y-6 p-2">
      
      <!-- Section: Basic Info -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-center">
            <div class="text-sm font-semibold text-gray-700">Basic Information</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Template Name</label>
                <input type="text" class="filter-input w-full" [(ngModel)]="form.name" name="name" placeholder="Enter template name" />
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Family Type</label>
                <p-dropdown [options]="familyTypeOptions" [(ngModel)]="form.family_type" name="family_type" placeholder="Select family type" optionLabel="label" optionValue="value" class="w-full" styleClass="filter-input" [style]="{width:'100%'}" (onChange)="onFamilyTypeChange($event)"></p-dropdown>
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Template Category</label>
                <p-dropdown [options]="templateCategoryOptions" [(ngModel)]="form.template_category" name="template_category" placeholder="Select category" optionLabel="label" optionValue="value" class="w-full" styleClass="filter-input" [style]="{width:'100%'}" [disabled]="!form.family_type"></p-dropdown>
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <p-dropdown [options]="[{label: 'Active', value: 'active'}, {label: 'Inactive', value: 'inactive'}]" [(ngModel)]="form.status" name="status" placeholder="Select status" optionLabel="label" optionValue="value" class="w-full" styleClass="filter-input" [style]="{width:'100%'}"></p-dropdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Section: Template Content -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-start">
            <div class="text-sm font-semibold text-gray-700">Template Content</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="space-y-4">
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea rows="3" class="filter-input w-full" [(ngModel)]="form.description" name="description" placeholder="Enter template description"></textarea>
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Prompt Text</label>
                <div class="text-xs text-gray-500 mb-2">Use {{"{{input_field_name}}"}} to create dynamic input fields for users</div>
                <textarea rows="8" class="filter-input w-full font-mono text-sm" [(ngModel)]="form.prompt_text" name="prompt_text" [placeholder]="placeholderText"></textarea>
                <div class="text-xs text-gray-500 mt-1">
                  <strong>Example:</strong><br>
                  Analyze the {{"{{transaction_type}}"}} for {{"{{entity_name}}"}} with amount {{"{{amount}}"}} in {{"{{currency}}"}}<br>
                  <em>This will create input fields for: transaction_type, entity_name, amount, and currency</em>
                </div>
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Template Filters</label>
                <input type="text" class="filter-input w-full" [(ngModel)]="form.template_filters" name="template_filters" placeholder="Enter comma-separated filters (e.g., hedge, swap, options)" />
                <div class="text-xs text-gray-500 mt-1">Add filters to help users find this template easily</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Section: Metadata -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-center">
            <div class="text-sm font-semibold text-gray-700">Metadata</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Display Order</label>
                <input type="number" class="filter-input w-full" [(ngModel)]="form.display_order" name="display_order" placeholder="Enter display order" />
              </div>
              <div class="field">
                <label class="block text-sm font-medium text-gray-700 mb-1">Usage Count</label>
                <input type="number" class="filter-input w-full" [(ngModel)]="form.usage_count" name="usage_count" readonly />
              </div>
            </div>
          </div>
        </div>
      </div>

    </form>
    <ng-template pTemplate="footer">
      <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button class="btn btn-secondary" (click)="showSheet = false">Cancel</button>
        <button class="btn btn-primary" (click)="confirmSave()">{{ mode === 'edit' ? 'Update Template' : 'Save Template' }}</button>
      </div>
    </ng-template>
  </p-dialog>
</div>
  `,
  styleUrls: []
})
export class PromptTemplatesComponent implements OnInit, OnDestroy {
  defaultColDef: ColDef = { resizable: true, sortable: true, filter: 'agSetColumnFilter', minWidth: 100 };
  templates: PromptTemplate[] = [];
  filteredTemplates: PromptTemplate[] = [];
  templateSub: any;
  search = '';
  selectedFamilyType = '';
  showSheet = false;
  mode: 'add' | 'edit' = 'add';
  form: Partial<PromptTemplate> = {};
  placeholderText = `Enter your prompt template here...

 TEMPLATE PATTERN: Use {{field_name}} for input fields

 RECOMMENDED EXAMPLES:

Risk Management:
Calculate VaR for {{portfolio_name}} with {{confidence_level}}% confidence over {{time_horizon}} days using {{methodology}} method.

Hedge Analysis:
Analyze {{hedge_type}} effectiveness for {{entity}} covering {{currency}} exposure of {{amount}} from {{start_date}} to {{end_date}}.

Compliance Check:
Review {{regulation_type}} compliance for {{business_line}} with threshold {{threshold_amount}} in {{base_currency}}.

 FIELD NAMING BEST PRACTICES:
 Use lowercase with underscores: {{field_name}}
 Common fields: {{entity}}, {{currency}}, {{amount}}, {{date}}
 Descriptive names: {{start_date}}, {{end_date}}, {{risk_type}}

 FIELD TYPES SUPPORTED:
 Text: {{entity}}, {{currency}}, {{description}}
 Numbers: {{amount}}, {{rate}}, {{percentage}}  
 Dates: {{date}}, {{maturity_date}}

Input fields will be automatically created from {{field_name}} patterns.`;
  
  familyTypeOptions: {label: string, value: string}[] = [];
  templateCategoryOptions: {label: string, value: string}[] = [];

  constructor(
    private ngZone: NgZone,
    private promptTemplatesService: PromptTemplatesService
  ) {}

  columnDefs: ColDef[] = [
    // Reordered: Family Type, Category, Template Name, Prompt Text
    { field: 'family_type', headerName: 'Family Type', width: 160, sortable: true },
    { field: 'template_category', headerName: 'Category', width: 160, sortable: true },
    { field: 'name', headerName: 'Template Name', width: 220, sortable: true },
    { field: 'prompt_text', headerName: 'Prompt Text', flex: 1, sortable: true },
    { field: 'usage_count', headerName: 'Usage', width: 100, sortable: true, cellClass: 'text-center' },
    { field: 'status', headerName: 'Status', width: 100, cellRenderer: (p: any) => {
      const val = p.value === 'active' ? 'Active' : 'Inactive';
      const cls = val === 'Active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
      const span = document.createElement('span');
      span.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`;
      span.textContent = val;
      return span;
    } },
    { field: 'created_at', headerName: 'Created', width: 140, sortable: true },
    { field: 'updated_at', headerName: 'Updated', width: 140, sortable: true },
    { headerName: 'Actions', width: 120, pinned: 'right', cellRenderer: (p: any) => {
      const container = document.createElement('div');
      container.className = 'flex items-center justify-center space-x-2';
      const editBtn = document.createElement('button');
      editBtn.className = 'text-gray-500 hover:text-blue-600 p-1';
      editBtn.title = 'Edit Template';
      editBtn.innerHTML = '<i class="pi pi-pencil text-sm"></i>';
      editBtn.addEventListener('click', () => p.context.componentParent.editRow(p.data));
      const delBtn = document.createElement('button');
      delBtn.className = 'text-gray-500 hover:text-red-600 p-1';
      delBtn.title = 'Delete Template';
      delBtn.innerHTML = '<i class="pi pi-trash text-sm"></i>';
      delBtn.addEventListener('click', () => p.context.componentParent.deleteRow(p.data));
      container.appendChild(editBtn);
      container.appendChild(delBtn);
      return container;
    } }
  ];

  gridOptions: GridOptions = { 
    pagination: true, 
    paginationPageSize: 20, 
    animateRows: true, 
    context: { componentParent: this } 
  };
  
  private gridApi?: any;
  private searchTimer: any;

  async ngOnInit() {
    // Initialize with empty options first
    this.familyTypeOptions = [{ label: 'All Types', value: '' }];
    // Set default selection to 'All Types' 
    this.selectedFamilyType = '';
    
    this.templateSub = this.promptTemplatesService.templates$.subscribe(data => {
      this.templates = data;
      this.applyFilters(); // Apply filters which will update filteredTemplates
      setTimeout(() => this.gridApi?.sizeColumnsToFit(), 0);
    });
    
    // Load dynamic family types asynchronously without blocking
    this.loadFamilyTypes().catch(err => {
      console.error('Failed to load family types:', err);
    });
  }

  private async loadFamilyTypes() {
    try {
      const familyTypes = await this.promptTemplatesService.getUniqueFamilyTypes();
      // Add "All Types" option at the beginning
      this.familyTypeOptions = [
        { label: 'All Types', value: '' },
        ...familyTypes
      ];
    } catch (error) {
      console.error('Error loading family types:', error);
      // Provide fallback options even if database call fails
      this.familyTypeOptions = [
        { label: 'All Types', value: '' },
        { label: 'Hedge Accounting', value: 'hedge_accounting' },
        { label: 'Risk Management', value: 'risk_management' },
        { label: 'Compliance', value: 'compliance' }
      ];
    }
  }

  async onFamilyTypeChange(event: any) {
    const familyType = event.value;
    if (familyType) {
      try {
        this.templateCategoryOptions = await this.promptTemplatesService.getTemplateCategoriesByFamily(familyType);
        // Reset category selection when family type changes
        this.form.template_category = '';
      } catch (error) {
        console.error('Error loading template categories:', error);
        this.templateCategoryOptions = [];
      }
    } else {
      this.templateCategoryOptions = [];
      this.form.template_category = '';
    }
  }

  ngOnDestroy() {
    if (this.templateSub) this.templateSub.unsubscribe();
  }

  onGridReady(e: GridReadyEvent) { 
    this.gridApi = e.api; 
    e.api.sizeColumnsToFit();
    // Apply initial filters when grid is ready
    this.applyFilters();
  }

  onSearchChange(v: string) {
    this.search = v;
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.applyFilters(), 300);
  }

  onFilterChange() {
    this.applyFilters();
  }

  onFamilyTabChange(familyValue: string) {
    this.selectedFamilyType = familyValue;
    this.applyFilters();
  }

  applyFilters() {
    let filtered = this.templates;
    if (this.search.trim()) {
      const s = this.search.trim().toLowerCase();
      filtered = filtered.filter(t =>
        (t.name?.toLowerCase().includes(s) ||
          t.prompt_text?.toLowerCase().includes(s) ||
          t.family_type?.toLowerCase().includes(s) ||
          t.template_category?.toLowerCase().includes(s))
      );
    }
    if (this.selectedFamilyType && this.selectedFamilyType !== '') {
      filtered = filtered.filter(t => t.family_type === this.selectedFamilyType);
    }
    
    this.filteredTemplates = filtered;
    setTimeout(() => this.gridApi?.sizeColumnsToFit(), 0);
  }

  openAdd() {
    this.mode = 'add';
    this.form = { status: 'active', usage_count: 0, display_order: 1 };
    this.ngZone.run(() => this.showSheet = true);
  }

  async editRow(row: PromptTemplate) {
    this.mode = 'edit';
    this.form = { ...row };
    
    // Load categories for the selected family type
    if (row.family_type) {
      try {
        this.templateCategoryOptions = await this.promptTemplatesService.getTemplateCategoriesByFamily(row.family_type);
      } catch (error) {
        console.error('Error loading template categories for edit:', error);
      }
    }
    
    this.ngZone.run(() => this.showSheet = true);
  }

  deleteRow(row: PromptTemplate) {
    if (confirm('Are you sure you want to delete this template?')) {
      this.promptTemplatesService.deleteTemplate(row.id!);
    }
  }

  async confirmSave() {
    if (this.mode === 'edit' && this.form.id) {
      await this.promptTemplatesService.updateTemplate(this.form.id, this.form);
    } else {
      await this.promptTemplatesService.addTemplate(this.form);
    }
    this.showSheet = false;
    this.mode = 'add';
    this.form = {};
  }
}
