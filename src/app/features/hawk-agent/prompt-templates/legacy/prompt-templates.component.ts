import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PromptTemplatesService, PromptTemplate } from '../../configuration/prompt-templates/prompt-templates.service';
import { ActivatedRoute, Router } from '@angular/router';
import { HawkAgentService } from '../services/hawk-agent.service';
import { SafeResourceUrl, DomSanitizer } from '@angular/platform-browser';
import { AGENT_IFRAME_URL } from '../../../core/config/app-config';

@Component({
  selector: 'app-hawk-prompt-templates',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 min-h-full flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">{{ isAgentMode ? 'Agent Mode' : 'Template Mode' }}</h2>
          <div class="text-xs text-gray-500">HAWK Agent</div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm" [ngClass]="isAgentMode ? 'text-gray-400' : 'text-blue-700 font-medium'">Template Mode</span>
          <label class="inline-flex items-center cursor-pointer">
            <input type="checkbox" class="sr-only" [ngModel]="isAgentMode" (ngModelChange)="onAgentModeToggle($event)">
            <div class="relative" role="switch" [attr.aria-checked]="isAgentMode">
              <div class="w-12 h-7 rounded-full transition-colors duration-200 shadow-inner ring-1" [ngClass]="isAgentMode ? 'bg-blue-600 ring-blue-600' : 'bg-gray-300 ring-gray-300'"></div>
              <div class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transform transition duration-200" [class.translate-x-5]="isAgentMode"></div>
            </div>
          </label>
          <span class="text-sm" [ngClass]="isAgentMode ? 'text-blue-700 font-medium' : 'text-gray-400'">Agent Mode</span>
        </div>
      </div>

      <!-- Template Mode Content -->
      <div *ngIf="!isAgentMode" class="space-y-6 flex-1">
        <div class="flex space-x-4 mb-6">
          <!-- Family Selector -->
          <div class="w-1/3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Template Family</label>
            <select [(ngModel)]="selectedFamily" (ngModelChange)="onFamilyChange($event)" class="form-select w-full">
              <option value="">All Templates</option>
              <option *ngFor="let family of families" [value]="family.value">{{ family.label }}</option>
            </select>
          </div>
          
          <!-- Category Selector -->
          <div class="w-1/3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Category</label>
            <select [(ngModel)]="selectedCategory" (ngModelChange)="onCategoryChange($event)" class="form-select w-full">
              <option value="">All Categories</option>
              <option *ngFor="let cat of categories" [value]="cat.value">{{ cat.label }} ({{ cat.count }})</option>
            </select>
          </div>
          
          <!-- Search -->
          <div class="w-1/3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Search Templates</label>
            <input type="text" [(ngModel)]="search" (ngModelChange)="onSearchChange($event)" 
                   class="form-input w-full" placeholder="Search templates...">
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Template List -->
          <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 border-b">
              <h3 class="font-medium text-gray-900">Available Templates ({{ filtered.length }})</h3>
            </div>
            <div class="max-h-96 overflow-y-auto">
              <div *ngFor="let template of filtered; let i = index" 
                   class="p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50"
                   [class.bg-blue-50]="selectedIndex === i"
                   [class.border-blue-200]="selectedIndex === i"
                   (click)="selectTemplate(i)">
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <h4 class="font-medium text-gray-900">{{ template.name }}</h4>
                    <p class="text-sm text-gray-600 mt-1">{{ template.description }}</p>
                    <div class="flex items-center gap-4 mt-2">
                      <span class="text-xs text-gray-500">Family: {{ template.family_type }}</span>
                      <span class="text-xs text-gray-500">Category: {{ template.template_category }}</span>
                      <span class="text-xs text-gray-500">Usage: {{ template.usage_count || 0 }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Template Preview -->
          <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-4 py-3 bg-gray-50 border-b">
              <h3 class="font-medium text-gray-900">Template Preview</h3>
            </div>
            <div class="p-4">
              <div *ngIf="selectedTemplate; else noTemplate">
                <h4 class="font-medium text-gray-900 mb-2">{{ selectedTemplate.name }}</h4>
                <p class="text-sm text-gray-600 mb-4">{{ selectedTemplate.description }}</p>
                
                <!-- Field Inputs -->
                <div *ngIf="selectedFields.length > 0" class="space-y-3 mb-4">
                  <h5 class="text-sm font-medium text-gray-700">Template Fields:</h5>
                  <div *ngFor="let field of selectedFields" class="flex flex-col">
                    <label class="text-xs font-medium text-gray-600 mb-1">{{ field }}</label>
                    <input type="text" [(ngModel)]="fieldValues[field]" 
                           class="form-input text-sm" [placeholder]="'Enter ' + field">
                  </div>
                </div>
                
                <!-- Template Content -->
                <div class="bg-gray-50 rounded-lg p-3 mb-4">
                  <div class="text-sm font-mono text-gray-800">{{ getPreviewText() }}</div>
                </div>
                
                <button class="btn btn-primary w-full" 
                        (click)="submitTemplate()" 
                        [disabled]="isLoading">
                  {{ isLoading ? 'Processing...' : 'Submit Template' }}
                </button>
              </div>
              
              <ng-template #noTemplate>
                <div class="text-center py-8 text-gray-500">
                  <p>Select a template from the list to preview</p>
                </div>
              </ng-template>
            </div>
          </div>
        </div>
      </div>

      <!-- Agent Mode Content -->
      <div *ngIf="isAgentMode" class="space-y-6 flex-1">
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">AI Agent Interface</h3>
          
          <div class="w-full h-96 border border-gray-300 rounded-lg overflow-hidden">
            <iframe [src]="agentUrlSafe" 
                    class="w-full h-full border-0"
                    title="HAWK AI Agent Interface">
            </iframe>
          </div>
        </div>
      </div>

      <!-- Response Area -->
      <div *ngIf="responseText" class="bg-white rounded-lg border border-gray-200 p-6 flex-1">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Response</h3>
        <div class="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
          <pre class="whitespace-pre-wrap text-sm text-gray-800">{{ responseText }}</pre>
        </div>
      </div>
    </div>
  `
})
export class PromptTemplatesComponent implements OnInit {
  families: {label: string, value: string}[] = [];
  categories: {label: string, value: string, count: number}[] = [];
  templates: PromptTemplate[] = [];
  filtered: PromptTemplate[] = [];
  
  selectedFamily = '';
  selectedCategory = '';
  search = '';
  selectedIndex = -1;
  selectedTemplate: PromptTemplate | null = null;
  selectedFields: string[] = [];
  fieldValues: Record<string, string> = {};
  
  responseText = '';
  isLoading = false;
  
  // Agent mode
  isAgentMode = false;
  agentUrlSafe: SafeResourceUrl;

  constructor(
    private promptService: PromptTemplatesService,
    private hawkService: HawkAgentService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer
  ) {
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(AGENT_IFRAME_URL);
  }

  async ngOnInit() {
    await this.loadData();
    this.loadFromUrl();
  }

  private async loadData() {
    try {
      await this.promptService.loadTemplates();
      this.promptService.templates$.subscribe(templates => {
        this.templates = templates;
        this.buildFilters();
        this.applyFilters();
      });
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  }

  private buildFilters() {
    // Build families
    const familySet = new Set<string>();
    const categoryMap = new Map<string, number>();

    this.templates.forEach(template => {
      if (template.family_type) {
        familySet.add(template.family_type);
      }
      const category = template.template_category || 'uncategorized';
      categoryMap.set(category, (categoryMap.get(category) || 0) + 1);
    });

    this.families = Array.from(familySet).map(f => ({ label: f, value: f }));
    this.categories = Array.from(categoryMap.entries()).map(([cat, count]) => ({
      label: cat,
      value: cat,
      count
    }));
  }

  private applyFilters() {
    this.filtered = this.templates.filter(template => {
      const familyMatch = !this.selectedFamily || template.family_type === this.selectedFamily;
      const categoryMatch = !this.selectedCategory || template.template_category === this.selectedCategory;
      const searchMatch = !this.search || 
        template.name?.toLowerCase().includes(this.search.toLowerCase()) ||
        template.description?.toLowerCase().includes(this.search.toLowerCase());
      
      return familyMatch && categoryMatch && searchMatch;
    });

    // Reset selection if current selection is no longer valid
    if (this.selectedIndex >= this.filtered.length) {
      this.selectedIndex = -1;
      this.selectedTemplate = null;
    }
  }

  selectTemplate(index: number) {
    this.selectedIndex = index;
    this.selectedTemplate = this.filtered[index];
    this.selectedFields = this.extractFields(this.selectedTemplate.prompt_text);
    this.fieldValues = {};
    this.updateUrl();
  }

  private extractFields(promptText: string): string[] {
    const fieldRegex = /\{([^}]+)\}/g;
    const fields: string[] = [];
    let match;
    while ((match = fieldRegex.exec(promptText)) !== null) {
      if (!fields.includes(match[1])) {
        fields.push(match[1]);
      }
    }
    return fields;
  }

  getPreviewText(): string {
    if (!this.selectedTemplate) return '';
    
    let text = this.selectedTemplate.prompt_text;
    this.selectedFields.forEach(field => {
      const value = this.fieldValues[field] || `{${field}}`;
      text = text.replace(new RegExp(`\\{${field}\\}`, 'g'), value);
    });
    return text;
  }

  async submitTemplate() {
    if (!this.selectedTemplate) return;
    
    this.isLoading = true;
    this.responseText = '';
    
    try {
      const filledPrompt = this.getPreviewText();
      const session = await this.hawkService.createSession({
        prompt: filledPrompt,
        templateId: this.selectedTemplate.id,
        templateName: this.selectedTemplate.name,
        category: this.selectedTemplate.template_category
      });
      
      this.responseText = 'Template submitted successfully. Processing...';
      
      // Increment usage count
      if (this.selectedTemplate.id) {
        await this.promptService.incrementUsageCount(this.selectedTemplate.id);
      }
      
    } catch (error) {
      this.responseText = `Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    } finally {
      this.isLoading = false;
    }
  }

  onFamilyChange(family: string) {
    this.selectedFamily = family;
    this.selectedIndex = -1;
    this.selectedTemplate = null;
    this.applyFilters();
    this.updateUrl();
  }

  onCategoryChange(category: string) {
    this.selectedCategory = category;
    this.selectedIndex = -1;
    this.selectedTemplate = null;
    this.applyFilters();
    this.updateUrl();
  }

  onSearchChange(search: string) {
    this.search = search;
    this.selectedIndex = -1;
    this.selectedTemplate = null;
    this.applyFilters();
    this.updateUrl();
  }

  onAgentModeToggle(enabled: boolean) {
    this.isAgentMode = enabled;
    this.updateUrl();
  }

  private loadFromUrl() {
    this.route.queryParams.subscribe(params => {
      if (params['family']) this.selectedFamily = params['family'];
      if (params['category']) this.selectedCategory = params['category'];
      if (params['search']) this.search = params['search'];
      if (params['agent'] === 'true') this.isAgentMode = true;
      if (params['template'] !== undefined) {
        const idx = parseInt(params['template'], 10);
        if (idx >= 0 && idx < this.filtered.length) {
          this.selectTemplate(idx);
        }
      }
      this.applyFilters();
    });
  }

  private updateUrl() {
    const queryParams: any = {};
    if (this.selectedFamily) queryParams.family = this.selectedFamily;
    if (this.selectedCategory) queryParams.category = this.selectedCategory;
    if (this.search) queryParams.search = this.search;
    if (this.isAgentMode) queryParams.agent = 'true';
    if (this.selectedIndex >= 0) queryParams.template = this.selectedIndex;
    
    this.router.navigate([], { 
      queryParams, 
      queryParamsHandling: 'merge' 
    });
  }

  // Keyboard navigation
  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent) {
    if (!this.isAgentMode && this.filtered.length > 0) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        const newIndex = Math.min(this.filtered.length - 1, this.selectedIndex + 1);
        this.selectTemplate(newIndex);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        const newIndex = Math.max(0, this.selectedIndex - 1);
        this.selectTemplate(newIndex);
      } else if (event.key === 'Enter' && this.selectedTemplate) {
        event.preventDefault();
        this.submitTemplate();
      }
    }
  }
}