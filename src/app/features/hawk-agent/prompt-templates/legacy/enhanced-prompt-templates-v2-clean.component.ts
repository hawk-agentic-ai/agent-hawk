import { Component, OnInit, HostListener, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PromptTemplatesService, PromptTemplate } from '../../../configuration/prompt-templates/prompt-templates.service';
import { PromptFiltersPanelComponent } from '../prompt-filters-panel.component';
import { TemplateCardListComponent } from '../template-card-list.component';
import { TemplatePreviewComponent } from '../template-preview.component';
import { TemplateResultsComponent } from '../template-results.component';
import { ActivatedRoute, Router } from '@angular/router';
import { HawkAgentSimpleService } from '../../services/hawk-agent-simple.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AGENT_IFRAME_URL } from '../../../../core/config/app-config';
import { Subscription } from 'rxjs';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-enhanced-prompt-templates-v2',
  standalone: true,
  imports: [CommonModule, FormsModule, PromptFiltersPanelComponent, TemplateCardListComponent, TemplatePreviewComponent, TemplateResultsComponent],
  template: `
    <div class="p-6 min-h-full flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900 flex items-center gap-3">
            {{ isAgentMode ? 'Agent Mode' : 'Template Mode' }}
            <!-- Backend Status Indicator -->
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full animate-pulse" 
                   [class]="backendStatus.healthy ? 'bg-green-500' : 'bg-red-500'"></div>
              <span class="text-xs font-medium px-2 py-1 rounded-full" 
                    [class]="backendStatus.healthy ? 
                            (backendStatus.type === 'unified' ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700') : 
                            'bg-red-100 text-red-700'">
                {{ backendStatusText }}
              </span>
            </div>
          </h2>
          <div class="text-xs text-gray-500 flex items-center gap-4">
            <span>HAWK Agent v5.0</span>
            <!-- Performance Metrics -->
            <span *ngIf="performanceMetrics" class="text-green-600">
               {{ performanceMetrics.response_time_ms }}ms |  {{ performanceMetrics.cache_hit_rate }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <!-- Backend Toggle (for testing/fallback) -->
          <button *ngIf="showBackendToggle" 
                  class="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                  (click)="toggleBackend()"
                  title="Toggle between Unified and Legacy backend">
            {{ backendStatus.type === 'unified' ? ' Unified' : ' Legacy' }}
          </button>
          
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

      <!-- Horizontal family tabs -->
      <div class="mb-3 overflow-x-auto">
        <div class="flex gap-2">
          <button *ngFor="let f of families"
                  class="px-3 py-1.5 rounded-full border text-sm whitespace-nowrap"
                  [class.bg-blue-600]="selectedFamily===f.value"
                  [class.text-white]="selectedFamily===f.value"
                  [class.border-blue-600]="selectedFamily===f.value"
                  [class.bg-white]="selectedFamily!==f.value"
                  [class.text-gray-700]="selectedFamily!==f.value"
                  [class.border-gray-300]="selectedFamily!==f.value"
                  (click)="onFamilyChange(f.value)">{{ f.label }}</button>
        </div>
      </div>

      <div class="flex-1 grid gap-4" style="grid-template-columns: 280px 1fr 400px; min-height: 0;">
        <div class="bg-white border rounded-lg p-3 overflow-auto">
          <app-pt-filters [families]="families" [categories]="categories" [selectedFamily]="selectedFamily"
                          [selectedCategory]="selectedCategory" [search]="search" [hideFamily]="true"
                          (familyChange)="onFamilyChange($event)" (categoryChange)="onCategoryChange($event)"
                          (searchChange)="onSearchChange($event)"></app-pt-filters>
        </div>
        <div class="bg-white border rounded-lg p-3 overflow-auto min-h-0" style="max-height: 520px;">
          <div *ngIf="loading" class="text-sm text-gray-500">Loading templates...</div>
          <app-pt-card-list *ngIf="!loading" [templates]="filtered" [selectedIndex]="selectedIndex" [successMap]="successRates" (select)="select($event)"></app-pt-card-list>
        </div>
        <div class="bg-white border rounded-lg p-3 overflow-auto">
          <app-pt-preview
            [template]="selectedTemplate"
            [fields]="getSelectedFieldsArray()"
            [streaming]="isStreaming"
            (onSend)="submit($event)"></app-pt-preview>
        </div>
      </div>
      
      <div class="mt-4 bg-white border rounded-lg p-3 overflow-auto">
        <!-- Enhanced Results Component with Backend Metrics -->
        <div *ngIf="responseText || isStreaming" class="mb-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-lg font-semibold text-gray-900">Response</h3>
            <div class="flex items-center gap-3">
              <!-- Real-time Processing Indicator -->
              <div *ngIf="isStreaming" class="flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-full">
                <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                <span class="text-xs text-blue-700 font-medium">
                  {{ backendStatus.type === 'unified' ? 'Unified Backend Processing...' : 'Legacy Processing...' }}
                </span>
              </div>
              <!-- Performance Metrics Display -->
              <div *ngIf="performanceMetrics && !isStreaming" 
                   class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded-full">
                 {{ performanceMetrics.response_time_ms }}ms | 
                 {{ performanceMetrics.cache_hit_rate }} |
                 {{ performanceMetrics.total_records }} records
              </div>
            </div>
          </div>
        </div>
        
        <app-pt-results
          [responseText]="responseText"
          [streaming]="isStreaming"
          [rating]="currentRating"
          [completion]="getCompletionStatus()"
          [feedback]="feedbackText"
          (export)="exportReport()"
          (ticket)="createTicket()"
          (schedule)="scheduleReview()"
          (share)="shareResults()"
          (rate)="setRating($event)"
          (setCompletion)="setCompletionStatus($event)"
          (feedbackChange)="onFeedbackChange($event)"
        ></app-pt-results>
      </div>

      <!-- Enhanced Footer with Backend Management -->
      <div class="mt-4 border-t border-gray-200 pt-3">
        <div class="flex items-center justify-between text-xs text-gray-500">
          <div class="flex items-center gap-4">
            <span>Backend: {{ backendStatus.url || 'Legacy Dify' }}</span>
            <span *ngIf="performanceMetrics">
              Avg Response: {{ performanceMetrics.response_time_ms }}ms
            </span>
          </div>
          <div class="flex items-center gap-3">
            <button class="text-gray-600 hover:text-gray-700" 
                    (click)="showPerformanceStats()"
                    title="View detailed performance statistics">
              Performance Stats
            </button>
            <button *ngIf="backendStatus.type === 'unified' && getSelectedCurrency()" 
                    class="text-gray-600 hover:text-gray-700"
                    (click)="clearCurrencyCache(getSelectedCurrency())"
                    title="Clear cache for {{ getSelectedCurrency() }}">
              Clear {{ getSelectedCurrency() }} Cache
            </button>
            <button class="text-gray-600 hover:text-gray-700"
                    (click)="refreshBackendStatus()"
                    title="Refresh backend connection">
               Refresh
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class EnhancedPromptTemplatesV2Component implements OnInit, OnDestroy {
  // Existing properties (from original v2 component)
  families: {label: string, value: string}[] = [];
  categories: {label: string, value: string, count: number}[] = [];
  selectedFamily = '';
  selectedCategory = '';
  search = '';
  loading = false;
  responseText = '';
  isLoading = false;
  public isStreaming = false;

  // Enhanced properties for backend integration (simplified types)
  backendStatus: {
    type: 'legacy' | 'unified';
    healthy: boolean;
    url?: string;
    performance?: any;
  } = {
    type: 'unified',
    healthy: true,
    performance: null,
    url: 'http://localhost:8004'
  };
  performanceMetrics: any = null;
  showBackendToggle = false; // Set to true for testing/debugging
  
  // Existing properties continued...
  templates: PromptTemplate[] = [];
  filtered: PromptTemplate[] = [];
  selectedIndex = -1;
  selectedTemplate: PromptTemplate | null = null;
  selectedFields: Record<string, any> = {};
  successRates: Record<string, number> = {};
  currentRating = 0;
  completionStatus = '';
  feedbackText = '';
  isAgentMode = false;
  agentUrlSafe?: SafeResourceUrl;

  // Session tracking
  currentMsgUid = '';
  currentInstructionId = '';
  private msgUidCounter = 1;
  private instructionIdCounter = 1;

  // Subscriptions (simplified)
  private subscriptions: Subscription[] = [];

  constructor(
    private svc: PromptTemplatesService,
    private sessions: HawkAgentSimpleService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer,
    private cdr: ChangeDetectorRef
  ) {
    // Initialize agent URL
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(AGENT_IFRAME_URL);
    
    // Enable backend toggle in development
    this.showBackendToggle = !environment.production;
  }

  async ngOnInit() {
    await this.loadData();
    this.loadFromUrl();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  get backendStatusText(): string {
    if (!this.backendStatus.healthy) return 'Backend Offline';
    return this.backendStatus.type === 'unified' 
      ? 'Unified Smart Backend v5.0' 
      : 'Legacy Dify Backend';
  }

  // Helper methods for template binding
  getSelectedFieldsArray(): string[] {
    if (!this.selectedTemplate) return [];
    
    // Use the same field extraction method as v2 component
    const fields = this.svc.extractFieldNamesFromTemplate(this.selectedTemplate);
    console.log(`Selected fields for template "${this.selectedTemplate.name}":`, fields);
    return fields;
  }

  getCompletionStatus(): 'complete' | 'incomplete' | null {
    if (this.completionStatus === 'complete' || this.completionStatus === 'incomplete') {
      return this.completionStatus;
    }
    return null;
  }

  getSelectedCurrency(): string {
    return this.selectedFields['currency'] || '';
  }

  // Working stream processing methods from v2 component
  private streamBuffer = '';
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private endedEvent = false;
  private retryCount = 0;
  private readonly maxRetries = 3;

  private sendToUnifiedBackend(query: string) {
    const payload = {
      user_prompt: query,
      template_category: this.selectedCategory || 'general',
      msg_uid: this.currentMsgUid,
      instruction_id: this.currentInstructionId,
      stream_response: true
    };

    console.log(' Calling Unified Smart Backend:', payload);

    fetch('http://localhost:8004/hawk-agent/process-prompt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('Empty response body');
      this.isLoading = false;
      this.reader = response.body.getReader();
      return this.processUnifiedStream(this.reader!);
    }).catch(err => {
      console.error('Unified Backend error:', err);
      // Retry on network/HTTP errors if not ended and retries remain
      if (!this.endedEvent && this.retryCount < this.maxRetries){
        this.retryCount++;
        setTimeout(()=> this.sendToUnifiedBackend(query), Math.min(1500 * this.retryCount, 5000));
        return;
      }
      this.isLoading = false;
      this.isStreaming = false;
      this.responseText += `\n\n[Backend Error: ${err?.message || err}]`;
      this.updateDatabaseSession('failed').catch(()=>{});
    });
  }

  private async processUnifiedStream(reader: ReadableStreamDefaultReader<Uint8Array>) {
    const decoder = new TextDecoder();
    let buffer = '';
    let tokenUsage: any = null;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          this.isStreaming = false;
          this.finishUnifiedStream(tokenUsage);
          break;
        }
        if (!value) continue;
        const chunk = decoder.decode(value, { stream: true });
        
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.trim() === '') continue;
          
          if (line.startsWith('data: ')) {
            let dataContent = line.substring(6);
            // Handle nested data: data: {...} format
            if (dataContent.startsWith('data: ')) {
              dataContent = dataContent.substring(6);
            }
            
            if (dataContent === 'event: ping') {
              continue;
            }
            
            try {
              const json = JSON.parse(dataContent);
              
              if (json.event === 'error') {
                this.responseText = ` **Error from Dify AI:** ${json.message || json.code || 'Unknown error'}\n\n${JSON.stringify(json, null, 2)}`;
                this.isStreaming = false;
                return;
              }
              
              // Accept both 'agent_message' and generic 'message' events
              if ((json.event === 'agent_message' || json.event === 'message') && (json.answer || json.output_text || json.data?.answer)) {
                // Only add the clean answer content, not the raw JSON
                const chunkText = json.answer || json.output_text || json.data?.answer || '';
                this.streamBuffer += chunkText;
                // Display streamed content directly
                this.responseText = this.streamBuffer;
              }
              
              if (json.event === 'message_end') {
                this.endedEvent = true;
                if (json.metadata?.usage) {
                  tokenUsage = json.metadata.usage;
                }
                this.isStreaming = false;
                this.finishUnifiedStream(tokenUsage);
                return;
              }
              
              // Ignore agent_thought events - they're just duplicates
              if (json.event === 'agent_thought') {
                continue;
              }
              
            } catch (parseError) {
              // Not JSON, treat as plain text only if it looks like real content
              if (dataContent.trim() && !dataContent.includes('{') && !dataContent.includes('event:')) {
                this.streamBuffer += dataContent;
                this.responseText = this.streamBuffer;
              }
            }
          } else {
            // Non-data line, treat as plain text if substantial
            if (line.trim() && line.length > 5) {
              this.streamBuffer += line + '\n';
              this.responseText = this.streamBuffer;
            }
          }
        }
      }
    } catch (e) {
      this.isStreaming = false;
      this.responseText += '\n\n[Stream interrupted due to error: ' + e + ']';
      this.updateDatabaseSession('failed').catch(()=>{});
    } finally {
      reader.releaseLock();
    }
  }

  private finishUnifiedStream(tokenUsage?: any){
    // Stream completed
    
    let metadata = '\n\n---\n';
    metadata += `**Message UID:** ${this.currentMsgUid}\n`;
    metadata += `**Instruction ID:** ${this.currentInstructionId}\n`;
    metadata += `**Backend:** Enhanced Unified Smart Backend v5.0\n`;
    metadata += `**Category:** ${this.selectedCategory || 'general'}`;
    if (tokenUsage) {
      metadata += `\n**Input Tokens:** ${tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0}`;
      metadata += `\n**Output Tokens:** ${tokenUsage.output_tokens || tokenUsage.completion_tokens || 0}`;
      metadata += `\n**Total Tokens:** ${tokenUsage.total_tokens || ((tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0) + (tokenUsage.output_tokens || tokenUsage.completion_tokens || 0))}`;
      metadata += `\n**Processing Cost:** $${(Number(tokenUsage.total_price) || 0).toFixed(4)} USD`;
    }
    this.responseText += metadata;
    this.updateDatabaseSession('completed', tokenUsage).catch(()=>{});
  }

  // Enhanced submit method that uses direct backend calls (like v2 component)
  async submit(payload: { text: string; values: Record<string,string> }){
    const base = payload?.text || '';
    const filled = this.svc.fillTemplate(base, payload?.values || {});
    if (!filled) return;
    
    this.responseText = '';
    this.isStreaming = true;
    this.isLoading = true;
    
    // Generate identifiers for this request
    this.currentMsgUid = this.generateMsgUID();
    this.currentInstructionId = this.generateInstructionId();
    
    // Store selected fields for smart parameter extraction
    this.selectedFields = payload.values || {};
    
    // Create DB session (pending) but do not block on failure
    await this.sessions.createSession(
      filled,
      this.currentMsgUid,
      this.currentInstructionId,
      this.selectedCategory || 'template',
      this.selectedIndex + 1
    );
    
    // Optimistic usage increment
    const id = this.selectedTemplate?.id; 
    if (id) this.svc.incrementUsageCount(id).catch(()=>{});
    
    // Send to backend with streaming (same approach as v2 component)
    this.sendToUnifiedBackend(filled);
  }

  // Backend management methods (simplified - using direct fetch)
  toggleBackend(): void {
    // Toggle between unified and legacy for testing
    this.backendStatus.type = this.backendStatus.type === 'unified' ? 'legacy' : 'unified';
    this.cdr.detectChanges();
  }

  async refreshBackendStatus(): Promise<void> {
    // Check if backend is responding
    try {
      const response = await fetch('http://localhost:8004/health', { method: 'GET' });
      this.backendStatus.healthy = response.ok;
    } catch {
      this.backendStatus.healthy = false;
    }
    this.cdr.detectChanges();
  }

  async showPerformanceStats(): Promise<void> {
    try {
      // Mock stats for now  
      const stats = { response_time_ms: 500, cache_hit_rate: '95%' };
      console.log(' Detailed Performance Stats:', stats);
      
      // For now, show in console/alert - could be enhanced with modal
      const summary = this.backendStatus.type === 'unified' 
        ? `Unified Backend Stats:\n- Response Time: ${stats.response_time_ms}ms\n- Cache Hit Rate: ${stats.cache_hit_rate}\n- Backend: Unified Smart Backend v5.0`
        : `Legacy Backend: Performance tracking not available`;
      
      alert(summary);
    } catch (error) {
      console.error(' Failed to get performance stats:', error);
      alert('Failed to load performance statistics');
    }
  }

  async clearCurrencyCache(currency: string): Promise<void> {
    if (!currency) return;
    
    try {
      // Direct API call to clear cache
      const response = await fetch(`http://localhost:8004/cache/clear/${currency}`, { method: 'DELETE' });
      if (response.ok) {
        alert(`Cache cleared for ${currency}`);
      } else {
        throw new Error('Cache clear failed');
      }
    } catch (error) {
      console.error(' Failed to clear cache:', error);
      alert(`Failed to clear cache for ${currency}`);
    }
  }

  // All existing methods from original v2 component...
  // (Keeping all the sophisticated template management, filtering, URL persistence, etc.)
  
  private async loadData() {
    this.loading = true;
    try {
      // Load templates using the existing service method
      await this.svc.loadTemplates();
      this.svc.templates$.subscribe(templates => {
        this.templates = templates;
      });
      this.buildFilters();
      this.applyFilters();
      this.loadSuccessRates();
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      this.loading = false;
    }
  }

  private buildFilters() {
    const familySet = new Set<string>();
    const categoryMap = new Map<string, number>();

    this.templates.forEach(t => {
      if (t.family_type) familySet.add(t.family_type);
      const cat = t.template_category || 'uncategorized';
      categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1);
    });

    this.families = [
      { label: 'All Templates', value: '' },
      ...Array.from(familySet).map(f => ({ label: f, value: f }))
    ];

    this.categories = [
      { label: 'All Categories', value: '', count: this.templates.length },
      ...Array.from(categoryMap.entries()).map(([cat, count]) => ({
        label: cat,
        value: cat,
        count
      }))
    ];
  }

  private applyFilters() {
    this.filtered = this.templates.filter(t => {
      const familyMatch = !this.selectedFamily || t.family_type === this.selectedFamily;
      const categoryMatch = !this.selectedCategory || t.template_category === this.selectedCategory;
      const searchMatch = !this.search || 
        t.name?.toLowerCase().includes(this.search.toLowerCase()) ||
        t.description?.toLowerCase().includes(this.search.toLowerCase());
      return familyMatch && categoryMatch && searchMatch;
    });

    if (this.selectedIndex >= this.filtered.length) {
      this.selectedIndex = Math.max(0, this.filtered.length - 1);
    }
    this.selectedTemplate = this.filtered[this.selectedIndex] || null;
  }

  private loadSuccessRates() {
    // Mock success rates since getSuccessRate method doesn't exist in service
    this.templates.forEach((t) => {
      if (t.id) {
        // Generate mock success rate based on usage count or random
        this.successRates[t.id] = t.usage_count ? Math.min(95, (t.usage_count * 10) % 100) : Math.floor(Math.random() * 100);
      }
    });
  }

  onFamilyChange(family: string) {
    this.selectedFamily = family;
    this.selectedIndex = -1;
    this.applyFilters();
    this.persistAndSyncUrl();
  }

  onCategoryChange(category: string) {
    this.selectedCategory = category;
    this.selectedIndex = -1;
    this.applyFilters();
    this.persistAndSyncUrl();
  }

  onSearchChange(search: string) {
    this.search = search;
    this.selectedIndex = -1;
    this.applyFilters();
    this.persistAndSyncUrl();
  }

  select(index: number) {
    this.selectedIndex = index;
    this.selectedTemplate = this.filtered[index] || null;
    this.persistAndSyncUrl();
  }

  onAgentModeToggle(enabled: boolean) {
    this.isAgentMode = enabled;
  }

  // Results actions (existing stubs)
  exportReport(){ console.log('Export report clicked'); }
  createTicket(){ console.log('Create ticket clicked'); }
  scheduleReview(){ console.log('Schedule review clicked'); }
  shareResults(){ console.log('Share results clicked'); }

  setRating(rating: number) { this.currentRating = rating; }
  setCompletionStatus(status: string) { this.completionStatus = status; }
  onFeedbackChange(feedback: string) { this.feedbackText = feedback; }

  // ID generation (existing logic)
  private generateMsgUID(): string {
    return `MSG_${Date.now()}_${this.msgUidCounter++}`;
  }

  private generateInstructionId(): string {
    return `INST_${Date.now()}_${this.instructionIdCounter++}`;
  }

  // Database session management (existing logic)
  private async updateDatabaseSession(status: 'completed' | 'failed', tokenUsage?: any) {
    try {
      await this.sessions.updateSession(this.currentMsgUid, {
        agent_status: status,
        agent_end_time: new Date().toISOString(),
        agent_response: {
          text: this.responseText,
          ...(tokenUsage ? { usage: tokenUsage } : {}),
          backend_type: this.backendStatus.type
        }
      });
    } catch (err) {
      console.error('update session error', err);
    }
  }

  // URL persistence (existing logic)
  private loadFromUrl() {
    this.route.queryParams.subscribe(params => {
      if (params['family']) this.selectedFamily = params['family'];
      if (params['category']) this.selectedCategory = params['category'];
      if (params['search']) this.search = params['search'];
      if (params['template'] !== undefined) {
        const idx = parseInt(params['template'], 10);
        if (idx >= 0 && idx < this.filtered.length) {
          this.selectedIndex = idx;
          this.selectedTemplate = this.filtered[idx];
        }
      }
      this.applyFilters();
    });
  }

  private persistAndSyncUrl() {
    const qp: any = {};
    if (this.selectedFamily) qp.family = this.selectedFamily;
    if (this.selectedCategory) qp.category = this.selectedCategory;
    if (this.search) qp.search = this.search;
    if (this.selectedIndex >= 0) qp.template = this.selectedIndex;
    this.router.navigate([], { queryParams: qp, queryParamsHandling: 'merge' });
  }

  // Keyboard navigation (existing logic)
  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent){
    if (!this.filtered?.length) return;
    if (e.key === 'ArrowDown'){ 
      this.selectedIndex = Math.min(this.filtered.length - 1, Math.max(0, this.selectedIndex) + 1); 
      e.preventDefault(); 
      this.persistAndSyncUrl(); 
    }
    if (e.key === 'ArrowUp'){ 
      this.selectedIndex = Math.max(0, (this.selectedIndex<0?0:this.selectedIndex) - 1); 
      e.preventDefault(); 
      this.persistAndSyncUrl(); 
    }
    if (e.key === 'Enter'){ 
      this.submit({ text: this.selectedTemplate?.prompt_text || '', values: {} }); 
      e.preventDefault(); 
    }
  }
}