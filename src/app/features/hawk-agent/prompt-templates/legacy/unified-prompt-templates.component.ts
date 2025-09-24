import { Component, ElementRef, OnDestroy, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl, SafeHtml } from '@angular/platform-browser';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { environment } from '../../../../environments/environment';

// Import existing services
import { CurrencyService } from '../../../shared/services/currency.service';
import { PromptTemplatesService, PromptTemplate } from '../../configuration/prompt-templates/prompt-templates.service';
import { DialogModule } from 'primeng/dialog';

// Import new unified services
import { UnifiedBackendService } from '../../../services/unified-backend.service';
import { UnifiedHawkAgentService, StreamingResponse } from '../services/unified-hawk-agent.service';
import { HawkAgentService, HawkAgentSession } from '../services/hawk-agent.service';

interface Currency {
  code: string;
  name: string;
}

interface TemplateCategory {
  id: string;
  name: string;
  description: string;
  templates: PromptTemplate[];
}

@Component({
  selector: 'app-unified-prompt-templates',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule],
  template: `
    <div class="p-6 space-y-4 min-h-full flex flex-col">
      <!-- Page Header with Backend Status -->
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-gray-900 flex items-center gap-3">
            {{ isAgentMode ? 'Agent Mode' : 'Template Mode' }}
            <!-- Unified Backend Status Indicator -->
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full" 
                   [class]="backendConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'"></div>
              <span class="text-xs" 
                    [class]="backendConnected ? 'text-green-700' : 'text-red-700'">
                {{ backendConnected ? 'Unified Backend Connected' : 'Backend Offline' }}
              </span>
            </div>
          </h2>
          <div class="text-xs text-gray-500">HAWK Agent v5.0 - Unified Smart Backend</div>
        </div>
        
        <!-- Performance Stats -->
        <div class="flex items-center gap-4">
          <div *ngIf="performanceStats" class="text-xs text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
             Cache: {{ performanceStats.cache?.cache_hit_rate || '0%' }} | 
             Avg: {{ performanceStats.cache?.avg_extraction_time_ms || 0 }}ms
          </div>
          
          <!-- Toggle Button -->
          <div class="flex items-center gap-3">
            <span class="text-sm"
                  [ngClass]="isAgentMode ? 'text-gray-400' : 'text-blue-700 font-medium'">Template Mode</span>
            <label class="inline-flex items-center cursor-pointer">
              <input type="checkbox" class="sr-only" [(ngModel)]="isAgentMode" (ngModelChange)="onAgentModeToggle($event)">
              <div class="relative" role="switch" [attr.aria-checked]="isAgentMode">
                <div class="w-12 h-7 rounded-full transition-colors duration-200 shadow-inner ring-1"
                     [ngClass]="isAgentMode ? 'bg-blue-600 ring-blue-600' : 'bg-gray-300 ring-gray-300'"></div>
                <div class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transform transition duration-200"
                     [class.translate-x-5]="isAgentMode"></div>
              </div>
            </label>
            <span class="text-sm"
                  [ngClass]="isAgentMode ? 'text-blue-700 font-medium' : 'text-gray-400'">Agent Mode</span>
          </div>
        </div>
      </div>

      <!-- Template Mode Content -->
      <div *ngIf="!isAgentMode" class="space-y-6 flex-1">
        <!-- Template Selection -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Categories -->
          <div class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Template Categories</h3>
            <div class="space-y-2">
              <div *ngFor="let category of templateCategories" 
                   class="p-3 rounded-lg cursor-pointer transition-colors"
                   [class]="activeCategory === category.id ? 'bg-blue-50 border border-blue-200 text-blue-900' : 'bg-gray-50 hover:bg-gray-100 text-gray-700'"
                   (click)="selectCategory(category.id)">
                <div class="font-medium">{{ category.name }}</div>
                <div class="text-sm opacity-75">{{ category.description }}</div>
                <div class="text-xs mt-1">{{ category.templates.length }} templates</div>
              </div>
            </div>
          </div>

          <!-- Templates -->
          <div class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Available Templates</h3>
            <div class="space-y-2">
              <div *ngFor="let template of getActiveTemplates(); let i = index" 
                   class="p-3 rounded-lg cursor-pointer transition-colors"
                   [class]="activeTemplateIndex === i ? 'bg-green-50 border border-green-200 text-green-900' : 'bg-gray-50 hover:bg-gray-100 text-gray-700'"
                   (click)="selectTemplate(i)">
                <div class="font-medium">{{ template.title }}</div>
                <div class="text-sm opacity-75">{{ template.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Template Configuration -->
        <div *ngIf="activeTemplate" class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Configure Template: {{ activeTemplate.title }}</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <!-- Currency Selection -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Currency</label>
              <select [(ngModel)]="currency" class="form-select w-full">
                <option value="">Select Currency</option>
                <option *ngFor="let curr of currencies" [value]="curr.code">
                  {{ curr.code }} - {{ curr.name }}
                </option>
              </select>
            </div>

            <!-- Amount Input -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Amount</label>
              <input type="number" [(ngModel)]="amount" 
                     class="form-input w-full" placeholder="Enter amount">
            </div>

            <!-- Date Input -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Transaction Date</label>
              <input type="date" [(ngModel)]="date" class="form-input w-full">
            </div>
          </div>

          <!-- Advanced Options (Optional - Unified Backend handles these) -->
          <div class="mb-6">
            <details class="group">
              <summary class="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                Advanced Options (Optional)
              </summary>
              <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">NAV Type</label>
                  <select [(ngModel)]="navType" class="form-select w-full">
                    <option value="">Auto-detect</option>
                    <option value="COI">Cost of Investment</option>
                    <option value="NAV">Net Asset Value</option>
                    <option value="ASSET">Asset Value</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">Entity Scope</label>
                  <input type="text" [(ngModel)]="entityScope" 
                         class="form-input w-full" placeholder="e.g., All entities">
                </div>
              </div>
            </details>
          </div>

          <!-- Generate Preview Button -->
          <button class="btn btn-primary w-full" 
                  (click)="generatePreview()" 
                  [disabled]="isLoading || !currency">
            <i class="pi pi-eye mr-2"></i>
            Generate Preview
          </button>
        </div>

        <!-- Template Preview -->
        <div *ngIf="promptPreview" class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Preview & Submit</h3>
          
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <div class="text-sm font-mono">{{ promptPreview }}</div>
          </div>

          <div class="flex items-center gap-3 mb-4">
            <button class="btn btn-success" 
                    (click)="submitTemplate()" 
                    [disabled]="isLoading || !backendConnected">
              <i class="pi pi-send mr-2"></i>
              {{ isLoading ? 'Processing...' : 'Submit to Unified Backend' }}
            </button>
            <button class="btn btn-secondary" (click)="editTemplate()">
              <i class="pi pi-pencil mr-2"></i>
              Edit
            </button>
          </div>
        </div>
      </div>

      <!-- Agent Mode Content -->
      <div *ngIf="isAgentMode" class="space-y-6 flex-1">
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Free-form Agent Prompt</h3>
          
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Enter your prompt (natural language)
              </label>
              <textarea [(ngModel)]="agentPrompt" 
                        class="form-textarea w-full" 
                        rows="4" 
                        placeholder="e.g., Check CNY hedge capacity and provide recommendations...">
              </textarea>
            </div>

            <!-- Smart Template Detection -->
            <div *ngIf="detectedTemplate" class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div class="text-sm font-medium text-blue-900"> Smart Detection</div>
              <div class="text-sm text-blue-700">
                Detected template category: <strong>{{ detectedTemplate }}</strong>
              </div>
            </div>

            <button class="btn btn-primary" 
                    (click)="submitAgentPrompt()" 
                    [disabled]="!agentPrompt || isLoading || !backendConnected">
              <i class="pi pi-robot mr-2"></i>
              {{ isLoading ? 'Processing...' : 'Process with AI Agent' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Response Area -->
      <div *ngIf="apiResponse || isLoading" class="bg-white rounded-lg border border-gray-200 p-6 flex-1">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">Response</h3>
          <div class="flex items-center gap-2">
            <!-- Performance indicator -->
            <div *ngIf="responseMetadata" class="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
               {{ responseMetadata.extraction_time_ms }}ms | 
               {{ responseMetadata.cache_hit_rate }}
            </div>
            <!-- Loading indicator -->
            <div *ngIf="isLoading" class="flex items-center gap-2">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span class="text-sm text-blue-700">Processing with Unified Backend...</span>
            </div>
          </div>
        </div>

        <!-- Streaming Response -->
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 overflow-hidden">
          <div class="p-6 max-w-full overflow-hidden">
            <div class="w-full max-w-none overflow-auto max-h-96">
              <div class="text-gray-800 leading-relaxed text-sm font-sans w-full prose prose-sm max-w-none" 
                   style="word-break: break-word; overflow-wrap: anywhere; max-width: 100%;"
                   [innerHTML]="getFormattedResponse()"></div>
              
              <!-- Streaming indicator -->
              <div *ngIf="isLoading" class="flex items-center gap-2 mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span class="text-sm text-blue-700 font-medium">Receiving streaming response...</span>
                <div class="flex gap-1 ml-2">
                  <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></div>
                  <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.2s"></div>
                  <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.4s"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Backend Status Footer -->
      <div class="border-t border-gray-200 pt-4">
        <div class="flex items-center justify-between text-xs text-gray-500">
          <div class="flex items-center gap-4">
            <span>Unified Smart Backend v5.0</span>
            <span>{{ backendUrl }}</span>
            <button *ngIf="!backendConnected" 
                    class="text-blue-600 hover:text-blue-700" 
                    (click)="checkBackendConnection()">
              Retry Connection
            </button>
          </div>
          <div class="flex items-center gap-4">
            <button class="text-gray-600 hover:text-gray-700" (click)="showPerformanceStats()">
              Performance Stats
            </button>
            <button *ngIf="currency" 
                    class="text-gray-600 hover:text-gray-700" 
                    (click)="clearCurrencyCache()">
              Clear {{ currency }} Cache
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .btn {
      @apply px-4 py-2 rounded-lg font-medium transition-colors;
    }
    .btn-primary {
      @apply bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400;
    }
    .btn-success {
      @apply bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-400;
    }
    .btn-secondary {
      @apply bg-gray-600 text-white hover:bg-gray-700;
    }
    .form-input, .form-select, .form-textarea {
      @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500;
    }
  `]
})
export class UnifiedPromptTemplatesComponent implements OnInit, OnDestroy {
  // Mode state
  isAgentMode = false;
  
  // Backend connection
  backendConnected = false;
  backendUrl = '';
  performanceStats: any = null;
  
  // Template mode properties
  templateCategories: TemplateCategory[] = [];
  activeCategory = '';
  activeTemplateIndex = -1;
  activeTemplate: PromptTemplate | null = null;
  
  // Form data
  currency = '';
  amount: number | null = null;
  date = '';
  navType = '';
  entityScope = '';
  
  // Agent mode
  agentPrompt = '';
  detectedTemplate: string | null = null;
  
  // Response handling
  promptPreview = '';
  apiResponse = '';
  isLoading = false;
  responseMetadata: any = null;
  
  // Session tracking
  currentMsgUid = '';
  currentInstructionId = '';
  currentSession: HawkAgentSession | null = null;
  
  // Data
  currencies: Currency[] = [];
  
  // Subscriptions
  private subscriptions: Subscription[] = [];

  constructor(
    private unifiedBackendService: UnifiedBackendService,
    private unifiedHawkService: UnifiedHawkAgentService,
    private hawkAgentService: HawkAgentService,
    private promptTemplatesService: PromptTemplatesService,
    private currencyService: CurrencyService,
    private cdr: ChangeDetectorRef
  ) {
    this.backendUrl = this.unifiedBackendService.getBackendUrl();
  }

  async ngOnInit() {
    // Initialize identifiers
    this.generateIdentifiers();
    
    // Load template data
    await this.loadTemplateCategories();
    await this.loadCurrencies();
    
    // Check backend connection
    await this.checkBackendConnection();
    
    // Subscribe to streaming responses
    this.subscribeToStreaming();
    
    // Load performance stats
    await this.loadPerformanceStats();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  private generateIdentifiers() {
    this.currentMsgUid = 'MSG_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    this.currentInstructionId = 'INST_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  private async loadTemplateCategories() {
    try {
      const templates = await this.promptTemplatesService.getAllTemplates();
      
      // Group templates by category
      const categoryMap = new Map<string, PromptTemplate[]>();
      templates.forEach(template => {
        const category = template.category || 'general';
        if (!categoryMap.has(category)) {
          categoryMap.set(category, []);
        }
        categoryMap.get(category)!.push(template);
      });

      // Create category objects
      this.templateCategories = [
        {
          id: 'hedge_accounting',
          name: 'Hedge Accounting',
          description: 'I-U-R-T-A-Q hedge instructions and capacity queries',
          templates: categoryMap.get('hedge_accounting') || []
        },
        {
          id: 'risk_analysis',
          name: 'Risk Analysis',
          description: 'Portfolio risk assessment and compliance checks',
          templates: categoryMap.get('risk_analysis') || []
        },
        {
          id: 'performance',
          name: 'Performance Monitoring',
          description: 'System metrics and performance reports',
          templates: categoryMap.get('performance') || []
        },
        {
          id: 'compliance',
          name: 'Compliance',
          description: 'Regulatory compliance and audit reports',
          templates: categoryMap.get('compliance') || []
        },
        {
          id: 'monitoring',
          name: 'System Monitoring',
          description: 'System health and operational monitoring',
          templates: categoryMap.get('monitoring') || []
        }
      ];

      // Set default category
      if (this.templateCategories.length > 0) {
        this.activeCategory = this.templateCategories[0].id;
      }
    } catch (error) {
      console.error(' Failed to load template categories:', error);
    }
  }

  private async loadCurrencies() {
    try {
      this.currencies = await this.currencyService.getCurrencies();
    } catch (error) {
      console.error(' Failed to load currencies:', error);
      // Fallback currencies
      this.currencies = [
        { code: 'USD', name: 'US Dollar' },
        { code: 'EUR', name: 'Euro' },
        { code: 'GBP', name: 'British Pound' },
        { code: 'JPY', name: 'Japanese Yen' },
        { code: 'CNY', name: 'Chinese Yuan' },
        { code: 'CHF', name: 'Swiss Franc' },
        { code: 'CAD', name: 'Canadian Dollar' },
        { code: 'AUD', name: 'Australian Dollar' }
      ];
    }
  }

  private async checkBackendConnection() {
    try {
      this.backendConnected = await this.unifiedBackendService.checkBackendConnectivity();
      console.log(' Backend connection status:', this.backendConnected);
    } catch (error) {
      this.backendConnected = false;
      console.error(' Backend connection check failed:', error);
    }
  }

  private subscribeToStreaming() {
    const streamingSub = this.unifiedHawkService.streamingResponse$.subscribe(
      (response: StreamingResponse | null) => {
        if (response) {
          this.handleStreamingResponse(response);
        }
      }
    );
    this.subscriptions.push(streamingSub);

    const sessionSub = this.unifiedHawkService.currentSession$.subscribe(
      (session: HawkAgentSession | null) => {
        this.currentSession = session;
      }
    );
    this.subscriptions.push(sessionSub);
  }

  private handleStreamingResponse(response: StreamingResponse) {
    console.log(' Handling streaming response:', response);

    if (response.event === 'agent_message' && response.data?.answer) {
      // Append to existing response
      this.apiResponse += response.data.answer;
      this.cdr.detectChanges();
    } else if (response.event === 'message_end') {
      // Response complete
      this.isLoading = false;
      this.responseMetadata = response.data?.metadata;
      this.cdr.detectChanges();
    } else if (response.event === 'error') {
      // Handle error
      this.isLoading = false;
      this.apiResponse = `Error: ${response.error || 'Unknown error occurred'}`;
      this.cdr.detectChanges();
    }
  }

  private async loadPerformanceStats() {
    if (!this.backendConnected) return;
    
    try {
      this.performanceStats = await this.unifiedHawkService.getPerformanceStats();
    } catch (error) {
      console.error(' Failed to load performance stats:', error);
    }
  }

  // Template mode methods
  selectCategory(categoryId: string) {
    this.activeCategory = categoryId;
    this.activeTemplateIndex = -1;
    this.activeTemplate = null;
  }

  selectTemplate(index: number) {
    this.activeTemplateIndex = index;
    this.activeTemplate = this.getActiveTemplates()[index];
  }

  getActiveTemplates(): PromptTemplate[] {
    const category = this.templateCategories.find(c => c.id === this.activeCategory);
    return category ? category.templates : [];
  }

  generatePreview() {
    if (!this.activeTemplate) return;

    // Build preview using template
    let preview = this.activeTemplate.prompt_text;
    
    // Replace placeholders
    preview = preview.replace(/\{currency\}/g, this.currency || '{currency}');
    preview = preview.replace(/\{amount\}/g, this.amount?.toString() || '{amount}');
    preview = preview.replace(/\{date\}/g, this.date || '{date}');
    preview = preview.replace(/\{nav_type\}/g, this.navType || '{nav_type}');
    preview = preview.replace(/\{entity_scope\}/g, this.entityScope || '{entity_scope}');

    this.promptPreview = preview;
  }

  async submitTemplate() {
    if (!this.promptPreview || !this.backendConnected) return;

    this.isLoading = true;
    this.apiResponse = '';
    this.generateIdentifiers(); // New identifiers for each request

    try {
      await this.unifiedHawkService.processTemplate({
        promptText: this.promptPreview,
        templateCategory: this.activeCategory,
        templateIndex: this.activeTemplateIndex,
        msgUid: this.currentMsgUid,
        instructionId: this.currentInstructionId,
        amount: this.amount || undefined,
        currency: this.currency,
        transactionDate: this.date,
        entityScope: this.entityScope,
        navType: this.navType
      });

      console.log(' Template submitted to Unified Backend');
    } catch (error) {
      console.error(' Template submission failed:', error);
      this.isLoading = false;
      this.apiResponse = `Error: ${error instanceof Error ? error.message : 'Submission failed'}`;
    }
  }

  editTemplate() {
    this.promptPreview = '';
  }

  // Agent mode methods
  onAgentModeToggle(enabled: boolean) {
    this.isAgentMode = enabled;
    if (enabled) {
      // Reset agent state
      this.agentPrompt = '';
      this.detectedTemplate = null;
      this.apiResponse = '';
    } else {
      // Reset template state
      this.promptPreview = '';
      this.apiResponse = '';
    }
  }

  onAgentPromptChange() {
    // Smart template detection
    if (this.agentPrompt) {
      this.detectedTemplate = this.unifiedBackendService.detectTemplateCategory(this.agentPrompt);
    } else {
      this.detectedTemplate = null;
    }
  }

  async submitAgentPrompt() {
    if (!this.agentPrompt || !this.backendConnected) return;

    this.isLoading = true;
    this.apiResponse = '';
    this.generateIdentifiers();

    try {
      await this.unifiedHawkService.processAgentPrompt({
        promptText: this.agentPrompt,
        msgUid: this.currentMsgUid,
        instructionId: this.currentInstructionId,
        templateCategory: this.detectedTemplate || undefined
      });

      console.log(' Agent prompt submitted to Unified Backend');
    } catch (error) {
      console.error(' Agent prompt submission failed:', error);
      this.isLoading = false;
      this.apiResponse = `Error: ${error instanceof Error ? error.message : 'Submission failed'}`;
    }
  }

  // Utility methods
  getFormattedResponse(): SafeHtml {
    if (!this.apiResponse) return '';
    
    // Basic formatting for better readability
    let formatted = this.apiResponse
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');

    return formatted;
  }

  async showPerformanceStats() {
    try {
      const stats = await this.unifiedHawkService.getPerformanceStats();
      console.log(' Performance Stats:', stats);
      // Could show in a modal or toast
      alert(JSON.stringify(stats, null, 2));
    } catch (error) {
      console.error(' Failed to get performance stats:', error);
    }
  }

  async clearCurrencyCache() {
    if (!this.currency) return;
    
    try {
      await this.unifiedHawkService.clearCurrencyCache(this.currency);
      console.log(` Cache cleared for ${this.currency}`);
      await this.loadPerformanceStats(); // Refresh stats
    } catch (error) {
      console.error(' Failed to clear cache:', error);
    }
  }
}