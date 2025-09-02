import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PromptTemplatesService, PromptTemplate } from '../../configuration/prompt-templates/prompt-templates.service';
import { PromptFiltersPanelComponent } from './prompt-filters-panel.component';
import { TemplateCardListComponent } from './template-card-list.component';
import { TemplatePreviewComponent } from './template-preview.component';
import { TemplateResultsComponent } from './template-results.component';
import { ActivatedRoute, Router } from '@angular/router';
import { HawkAgentSimpleService } from '../services/hawk-agent-simple.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AGENT_IFRAME_URL } from '../../../core/config/app-config';

@Component({
  selector: 'app-hawk-prompt-templates-v2',
  standalone: true,
  imports: [CommonModule, FormsModule, PromptFiltersPanelComponent, TemplateCardListComponent, TemplatePreviewComponent, TemplateResultsComponent],
  template: `
    <div class="p-6 min-h-full flex flex-col">
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
            [fields]="selectedFields"
            [streaming]="isStreaming"
            (onSend)="submit($event)"></app-pt-preview>
        </div>
      </div>
      <div class="mt-4 bg-white border rounded-lg p-3 overflow-auto">
        <app-pt-results
          [responseText]="responseText"
          [streaming]="isStreaming"
          [rating]="currentRating"
          [completion]="completionStatus"
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
    </div>
  `
})
export class PromptTemplatesV2Component implements OnInit {
  families: {label: string, value: string}[] = [];
  categories: {label: string, value: string, count: number}[] = [];
  selectedFamily = '';
  selectedCategory = '';
  search = '';
  loading = false;
  responseText = '';
  // Streaming + session state (mirrors legacy UI behavior)
  private isLoading = false;
  public isStreaming = false;
  private streamBuffer = '';
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private currentMsgUid = '';
  private currentInstructionId = '';

  all: PromptTemplate[] = [];
  filtered: PromptTemplate[] = [];
  selectedIndex = -1;
  currentRating = 0;
  completionStatus: 'complete'|'incomplete'|null = null;
  feedbackText = '';
  // Streaming robustness
  private endedEvent = false;
  private retryCount = 0;
  private readonly maxRetries = 3;
  // Agent toggle + URL
  isAgentMode = false;
  agentUrlSafe: SafeResourceUrl;
  // Success rates map for cards
  successRates: Record<string, number> = {};

  constructor(private svc: PromptTemplatesService, private route: ActivatedRoute, private router: Router, private sessions: HawkAgentSimpleService, private sanitizer: DomSanitizer) {
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(AGENT_IFRAME_URL);
  }

  async ngOnInit(){
    // Load persisted state
    const savedFamily = localStorage.getItem('pt.family') || '';
    const savedCategory = localStorage.getItem('pt.category') || '';
    const savedSearch = localStorage.getItem('pt.search') || '';
    const savedIndex = parseInt(localStorage.getItem('pt.index') || '-1', 10);

    this.route.queryParams.subscribe(async (params) => {
      this.loading = true;
      try {
        this.families = await this.svc.getUniqueFamilyTypes();
        // Query params override persisted; else default to Instructions & Processing / Inception
        const defFam = (this.families.find(f => (f.label||'').toLowerCase().includes('instructions'))?.value) || '';
        this.selectedFamily = (params['family'] ?? savedFamily) || defFam;
        this.selectedCategory = params['category'] ?? savedCategory;
        this.search = params['search'] ?? savedSearch;
        await this.refreshTemplates();
        await this.refreshCategories();
        if (!this.selectedCategory && this.categories?.length){
          const inception = this.categories.find(c => (c.label||'').toLowerCase().includes('inception'))?.value;
          this.selectedCategory = inception || this.categories[0]?.value || '';
        }
        this.applyFilters();
        const qIndex = params['template'] != null ? parseInt(params['template'], 10) : NaN;
        this.selectedIndex = Number.isFinite(qIndex) ? qIndex : (Number.isFinite(savedIndex) ? savedIndex : -1);
        // Clamp index
        if (this.selectedIndex >= this.filtered.length) this.selectedIndex = -1;
      } finally { this.loading = false; }
    });
  }

  async onFamilyChange(fam: string){
    this.selectedFamily = fam || '';
    this.selectedCategory = '';
    await this.refreshTemplates();
    await this.refreshCategories();
    // Pick first available category by default
    if (this.categories && this.categories.length) {
      this.selectedCategory = this.categories[0].value;
    }
    this.applyFilters();
    // Pick first template by default
    if (this.filtered && this.filtered.length) {
      this.selectedIndex = 0;
    } else {
      this.selectedIndex = -1;
    }
    // Refresh success rates for visible list
    this.refreshSuccessRates().catch(()=>{});
    this.persistAndSyncUrl();
  }
  async onCategoryChange(cat: string){
    this.selectedCategory = cat || '';
    this.applyFilters();
    // Default to first template on category switch
    if (this.filtered && this.filtered.length) {
      this.selectedIndex = 0;
    } else {
      this.selectedIndex = -1;
    }
    this.refreshSuccessRates().catch(()=>{});
    this.persistAndSyncUrl();
  }
  onSearchChange(q: string){ this.search = q || ''; this.applyFilters(); this.persistAndSyncUrl(); }

  private async refreshTemplates(){
    if (this.selectedFamily) {
      this.all = await this.svc.getTemplatesByFamilyType(this.selectedFamily);
    } else {
      // fallback: service loadTemplates populates BehaviorSubject; we can call search without family
      this.all = await this.svc.searchTemplates(this.search || '');
    }
  }

  private async refreshCategories(){
    if (!this.selectedFamily){ this.categories = []; return; }
    const cats = await this.svc.getTemplateCategoriesByFamily(this.selectedFamily);
    const counts: Record<string, number> = {};
    this.all.forEach(t => { const k = t.template_category || ''; counts[k] = (counts[k]||0)+1; });
    this.categories = cats.map(c => ({ ...c, count: counts[c.value] || 0 }));
  }

  private applyFilters(){
    const q = (this.search||'').toLowerCase();
    this.filtered = this.all.filter(t => {
      const okCat = this.selectedCategory ? (t.template_category === this.selectedCategory) : true;
      const okSearch = q ? ((t.name||'').toLowerCase().includes(q) || (t.description||'').toLowerCase().includes(q) || (t.prompt_text||'').toLowerCase().includes(q)) : true;
      return okCat && okSearch;
    });
    // Show up to 8 templates; keep list scroll height constant
    this.filtered = (this.filtered || []).slice(0, 8);
    if (this.filtered.length === 0) this.selectedIndex = -1;
    // refresh success rates when list changes
    this.refreshSuccessRates().catch(()=>{});
  }

  select(i: number){ this.selectedIndex = i; this.persistAndSyncUrl(); }

  get selectedTemplate(): PromptTemplate | null { return (this.selectedIndex>=0 ? this.filtered[this.selectedIndex] : null) || null; }
  get selectedFields(): string[] {
    const storedRaw: any[] = (this.selectedTemplate as any)?.input_fields || [];
    const stored: string[] = Array.isArray(storedRaw) ? storedRaw.map(v => (v==null ? '' : String(v))) : [];
    const extracted: string[] = this.svc.getInputFields(this.selectedTemplate?.prompt_text || '') || [];
    // Merge unique, prefer order from prompt extraction; coerce to strings defensively
    const set = new Set<string>();
    const merged: string[] = [];
    const accept = (s: string) => {
      const t = (s||'').trim();
      if (!t) return false;
      if (t === '[object Object]') return false;
      if (t.length > 80) return false;
      if (!/[a-zA-Z]/.test(t)) return false;
      return true;
    };
    (extracted || []).forEach(f => { const s = String(f || '').trim(); const k=s.toLowerCase(); if(accept(s) && !set.has(k)){ set.add(k); merged.push(s); } });
    (stored || []).forEach(f => { const s = String(f || '').trim(); const k=s.toLowerCase(); if(accept(s) && !set.has(k)){ set.add(k); merged.push(s); } });
    return merged;
  }

  async submit(payload: { text: string; values: Record<string,string> }){
    // Ensure replacements are applied using service (defensive)
    const base = payload?.text || '';
    const filled = this.svc.fillTemplate(base, payload?.values || {});
    if (!filled) return;
    this.responseText = '';
    // Generate identifiers for this request
    this.currentMsgUid = this.generateMsgUID();
    this.currentInstructionId = this.generateInstructionId();
    // Create DB session (pending) but do not block on failure
    await this.sessions.createSession(
      filled,
      this.currentMsgUid,
      this.currentInstructionId,
      this.selectedCategory || 'template',
      this.selectedIndex + 1
    );
    // Optimistic usage increment
    const id = this.selectedTemplate?.id; if (id) this.svc.incrementUsageCount(id).catch(()=>{});
    // Send to executor (Dify) with streaming
    this.sendToDifyAgent(filled);
  }

  // Results actions (stubs)
  exportReport(){ console.log('Export report clicked'); }
  createTicket(){ console.log('Create ticket clicked'); }
  scheduleReview(){ console.log('Schedule review clicked'); }
  shareResults(){ console.log('Share results clicked'); }

  private msgUidCounter = 1;
  private instructionIdCounter = 1;

  private generateMsgUID(): string {
    const formattedNumber = this.msgUidCounter.toString().padStart(4, '0');
    const msgUid = `MSG_UID_${formattedNumber}`;
    this.msgUidCounter++;
    return msgUid;
  }
  
  private generateInstructionId(): string {
    const formattedNumber = this.instructionIdCounter.toString().padStart(4, '0');
    const instructionId = `INST${formattedNumber}`;
    this.instructionIdCounter++;
    return instructionId;
  }

  private async updateDatabaseSession(status: 'completed' | 'failed', tokenUsage?: any) {
    try {
      await this.sessions.updateSession(this.currentMsgUid, {
        agent_status: status,
        agent_response: {
          text: this.responseText,
          ...(tokenUsage ? { usage: tokenUsage } : {})
        }
      });
    } catch (err) {
      console.error('update session error', err);
    }
  }

  private sendToDifyAgent(query: string) {
    // Enhanced prompt with unique identifiers
    const enhancedQuery = `[MSG_UID: ${this.currentMsgUid}] [INSTRUCTION_ID: ${this.currentInstructionId}] ${query}`;
    const payload = {
      conversation_id: '',
      inputs: { msg_uid: this.currentMsgUid, instruction_id: this.currentInstructionId },
      query: enhancedQuery,
      user: 'test-user',
      response_mode: 'streaming'
    } as any;

    // Reset streaming state
    this.streamBuffer = '';
    this.responseText = '';
    this.isStreaming = true;
    this.isLoading = true;

    // Use the same Dify app key for all templates
    const appKey = 'app-KKtaMynVyn8tKbdV9VbbaeyR';

    // Reset retry/ended flags
    this.retryCount = 0;
    this.endedEvent = false;
    this.doDifyFetch(appKey, payload);
  }

  private doDifyFetch(appKey: string, payload: any){
    fetch('https://api.dify.ai/v1/chat-messages', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${appKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('Empty response body');
      this.isLoading = false;
      this.reader = response.body.getReader();
      return this.processStream(this.reader!, appKey, payload);
    }).catch(err => {
      console.error('Dify error:', err);
      // Retry on network/HTTP errors if not ended and retries remain
      if (!this.endedEvent && this.retryCount < this.maxRetries){
        this.retryCount++;
        setTimeout(()=> this.doDifyFetch(appKey, payload), Math.min(1500 * this.retryCount, 5000));
        return;
      }
      this.isLoading = false;
      this.isStreaming = false;
      this.responseText += `\n\n[Stream stopped: ${err?.message || err}]`;
      this.updateDatabaseSession('failed').catch(()=>{});
    });
  }

  private async processStream(reader: ReadableStreamDefaultReader<Uint8Array>, appKey: string, payload: any) {
    const decoder = new TextDecoder();
    let buffer = '';
    let conversationId = '';
    let taskId = '';
    let tokenUsage: any = null;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          // If we didn't receive an explicit end event, try to resume
          if (!this.endedEvent && this.retryCount < this.maxRetries){
            this.retryCount++;
            if (conversationId) payload.conversation_id = conversationId;
            setTimeout(()=> this.doDifyFetch(appKey, payload), Math.min(1500 * this.retryCount, 5000));
            return;
          }
          this.isStreaming = false;
          this.finishStream(conversationId, taskId, tokenUsage);
          break;
        }
        if (!value) continue;
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const json = JSON.parse(line.substring(6));
            if (!conversationId && json.conversation_id) conversationId = json.conversation_id;
            if (!taskId && json.task_id) taskId = json.task_id;
            if (json.event === 'agent_message' && json.answer) {
              this.streamBuffer += json.answer;
              this.responseText = this.streamBuffer;
            }
            if (json.metadata?.usage || json.usage) tokenUsage = json.metadata?.usage || json.usage;
            if (json.event === 'message_end' || json.event === 'workflow_finished') {
              this.endedEvent = true;
              this.isStreaming = false; this.finishStream(conversationId, taskId, tokenUsage); return;
            }
          } catch {}
        }
      }
    } catch (e) {
      console.error('stream error', e);
      if (!this.endedEvent && this.retryCount < this.maxRetries){
        this.retryCount++;
        setTimeout(()=> this.doDifyFetch(appKey, payload), Math.min(1500 * this.retryCount, 5000));
        return;
      }
      this.isStreaming = false;
      this.responseText += '\n\n[Stream interrupted due to error]';
      this.updateDatabaseSession('failed').catch(()=>{});
    } finally {
      reader.releaseLock();
    }
  }

  private finishStream(conversationId: string, taskId: string, tokenUsage?: any){
    let metadata = '\n\n---\n';
    metadata += `Message UID: ${this.currentMsgUid}\n`;
    metadata += `Instruction ID: ${this.currentInstructionId}`;
    if (conversationId) metadata += `\nConversation ID: ${conversationId}`;
    if (taskId) metadata += `\nTask ID: ${taskId}`;
    if (tokenUsage) {
      metadata += `\nInput Tokens: ${tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0}`;
      metadata += `\nOutput Tokens: ${tokenUsage.output_tokens || tokenUsage.completion_tokens || 0}`;
      metadata += `\nTotal Tokens: ${tokenUsage.total_tokens || ((tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0) + (tokenUsage.output_tokens || tokenUsage.completion_tokens || 0))}`;
    }
    this.responseText += metadata;
    this.updateDatabaseSession('completed', tokenUsage).catch(()=>{});
    this.refreshSuccessRates().catch(()=>{});
  }

  setRating(n: number){
    this.currentRating = n;
    // Persist rating (and any feedback captured) only on action
    const md: any = { rating: n };
    if ((this.feedbackText || '').trim()) md.feedback = this.feedbackText.trim();
    try { this.sessions.updateSession(this.currentMsgUid, { metadata: md }); } catch {}
  }
  setCompletionStatus(s: 'complete'|'incomplete'){
    this.completionStatus = s;
    const agent_status = s === 'complete' ? 'completed' : 'failed';
    const md: any = { completion_status: s };
    if ((this.feedbackText || '').trim()) md.feedback = this.feedbackText.trim();
    try { this.sessions.updateSession(this.currentMsgUid, { agent_status, metadata: md }); this.refreshSuccessRates().catch(()=>{}); } catch {}
  }

  onFeedbackChange(text: string){
    this.feedbackText = text || '';
    // Do not persist here; saved with rating/completion actions
  }

  private async refreshSuccessRates(){
    this.successRates = {};
    if (!this.selectedCategory) return;
    try {
      const sessions = await this.sessions.getSessions();
      const byIndex: Record<number, { total: number; success: number }> = {};
      (sessions||[]).forEach(s => {
        if (s.template_category === this.selectedCategory) {
          const idx = (s.template_index || 0);
          byIndex[idx] = byIndex[idx] || { total: 0, success: 0 };
          byIndex[idx].total++;
          const userMarked = (s.metadata && (s.metadata.completion_status === 'complete' || s.metadata.completion_status === 'incomplete'));
          const ok = userMarked ? (s.metadata.completion_status === 'complete') : (s.agent_status === 'completed');
          if (ok) byIndex[idx].success++;
        }
      });
      this.filtered.forEach((t, i) => {
        const stats = byIndex[i+1];
        if (stats && stats.total>0) {
          const pct = Math.round((stats.success / stats.total) * 100);
          const key = t.id || `idx:${i}`;
          this.successRates[key] = pct;
        }
      });
    } catch (e) { /* non-fatal */ }
  }

  onAgentModeToggle(v: boolean){
    this.isAgentMode = !!v;
    if (this.isAgentMode){ this.router.navigate(['/hawk-agent/agent-mode']); }
  }

  private persistAndSyncUrl(){
    localStorage.setItem('pt.family', this.selectedFamily || '');
    localStorage.setItem('pt.category', this.selectedCategory || '');
    localStorage.setItem('pt.search', this.search || '');
    localStorage.setItem('pt.index', String(this.selectedIndex));
    const qp: any = {};
    if (this.selectedFamily) qp.family = this.selectedFamily;
    if (this.selectedCategory) qp.category = this.selectedCategory;
    if (this.search) qp.search = this.search;
    if (this.selectedIndex >= 0) qp.template = this.selectedIndex;
    this.router.navigate([], { queryParams: qp, queryParamsHandling: 'merge' });
  }

  // Keyboard navigation across the list
  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent){
    if (!this.filtered?.length) return;
    if (e.key === 'ArrowDown'){ this.selectedIndex = Math.min(this.filtered.length - 1, Math.max(0, this.selectedIndex) + 1); e.preventDefault(); this.persistAndSyncUrl(); }
    if (e.key === 'ArrowUp'){ this.selectedIndex = Math.max(0, (this.selectedIndex<0?0:this.selectedIndex) - 1); e.preventDefault(); this.persistAndSyncUrl(); }
    if (e.key === 'Enter'){ this.submit({ text: this.selectedTemplate?.prompt_text || '', values: {} }); e.preventDefault(); }
  }
}
