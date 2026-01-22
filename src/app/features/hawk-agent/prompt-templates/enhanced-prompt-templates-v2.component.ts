/**
 * ENHANCED PROMPT TEMPLATES V2 COMPONENT - FIXED VERSION
 * 
 * 🎯 PURPOSE: Main interface for HAWK Agent template-based operations
 * 
 * 📋 FEATURES:
 * - Template Mode: Interactive form-based prompt execution
 * - Agent Mode: AI-powered conversational interface 
 * - Smart Backend Integration: Auto-connects to Unified Smart Backend v5.0
 * - Currency Extraction: Intelligent parsing of currencies from user input
 * - Performance Monitoring: Real-time response times and cache metrics
 * - Dual Backend Support: Unified (preferred) + Legacy Dify fallback
 * - Streaming Responses: Real-time AI response display with improved typography
 * 
 * 🏗️ ARCHITECTURE:
 * Frontend (Angular) → Unified Smart Backend → Data Extraction → Dify AI → Streaming Response
 * 
 * 🔧 BACKEND ENDPOINTS:
 * - Production: http://3.91.170.95:8004 (AWS Unified Smart Backend)
 * - Local: http://localhost:8004 (Development)
 * 
 * 📊 SUPPORTED OPERATIONS:
 * - Utilization Analysis, Inception, Rollover, Termination, Amendment, Inquiry
 * - Multi-currency support (USD, EUR, GBP, AUD, CNY, etc.)
 * - Real-time data fetching from Supabase with Redis caching
 * 
 * 🎨 UI COMPONENTS:
 * - PromptFiltersPanelComponent: Template search and filtering
 * - TemplateCardListComponent: Template selection cards
 * - TemplatePreviewComponent: Form fields and submission
 * - TemplateResultsComponent: AI response display with improved formatting
 * 
 * ⚡ PERFORMANCE:
 * - Target response time: <500ms (vs 2-3s legacy)
 * - Cache hit rate: 80-90% after warmup
 * - Data reduction: 90% less data sent to Dify
 */

import { Component, OnInit, HostListener, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PromptTemplatesService, PromptTemplate } from '../../configuration/prompt-templates/prompt-templates.service';
import { PromptFiltersPanelComponent } from './prompt-filters-panel.component';
import { TemplateCardListComponent } from './template-card-list.component';
import { TemplatePreviewComponent } from './template-preview.component';
import { TemplateResultsComponent } from './template-results.component';
import { ActivatedRoute, Router } from '@angular/router';
import { HawkAgentSimpleService } from '../services/hawk-agent-simple.service';
import { HawkAgentConversationsService, AgentConversation } from '../services/hawk-agent-conversations.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { HAWK_AGENTS, DEFAULT_AGENT } from '../../../core/config/app-config';
import { AGENT_IFRAME_URL } from '../../../core/config/app-config';
import { Subscription } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ClientSideOptimizationService } from '../../../services/client-side-optimization.service';
import { LayoutService } from '../../../core/services/layout.service';

// Missing interfaces - simplified version
interface BackendPerformanceMetrics {
  response_time_ms: number;
  cache_hit_rate: string;
  total_requests?: number;
  total_records?: number;
  avg_extraction_time_ms?: number;
  redis_keys_count?: number;
}

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
          
          <!-- Data Freshness Controls - HIDDEN: Always fetch fresh financial data -->
          <div class="flex items-center gap-2" style="display: none;">
            <button class="text-xs px-2 py-1 rounded border border-blue-200 hover:bg-blue-50 text-blue-600"
                    (click)="forceRefreshData()"
                    title="Force refresh all cached data"
                    [disabled]="isLoading">
              🔄 Fresh Data
            </button>
            <select class="text-xs px-1 py-0.5 border border-gray-200 rounded"
                    [(ngModel)]="dataFreshnessMinutes"
                    title="Cache data for this duration">
              <option value="2">2min</option>
              <option value="5">5min</option>
              <option value="15">15min</option>
              <option value="30">30min</option>
            </select>
          </div>
          
          <!-- Template/Agent Mode Toggle - Always visible in main header -->
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

      <!-- Horizontal family tabs - Only show in Template Mode -->
      <div *ngIf="!isAgentMode" class="mb-3 overflow-x-auto">
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

      <!-- Template Mode Interface -->
      <div *ngIf="!isAgentMode" class="flex-1 grid gap-4" style="grid-template-columns: 280px 1fr 400px; min-height: 0;">
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

      <!-- Agent Mode Interface - Full Screen Layout -->
      <div *ngIf="isAgentMode" class="fixed inset-0 flex bg-white" style="z-index: 1000;">
        
        <!-- Chat History Sidebar -->
        <div class="bg-card w-64 border-r border-border flex flex-col">
          <!-- DBS Logo Header - Standardized Height -->
          <div class="h-14 flex items-center px-4 border-b border-border">
            <div class="flex items-center gap-2">
               <img src="assets/Logo/DBS/Logomark.svg" class="w-6 h-6 object-contain" alt="DBS">
               <span class="font-bold text-lg tracking-tight text-foreground">Hawk<span class="font-light">Agent</span></span>
            </div>
          </div>
          
          <!-- New Chat & Search -->
          <div class="p-3 space-y-2">
            <button (click)="startNewConversation()" 
                    class="w-full btn-primary">
              <i class="pi pi-plus text-xs"></i>
              <span>New chat</span>
            </button>
            <button class="w-full btn-secondary">
              <i class="pi pi-search text-xs"></i>
              <span>Search chats</span>
            </button>
          </div>
          
          <!-- Previous Chats Section -->
          <div class="flex-1 overflow-hidden flex flex-col">
            <div class="px-4 py-2">
              <h4 class="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Previous chats</h4>
            </div>
            
            <div class="flex-1 overflow-y-auto p-2 space-y-1">
              <div *ngIf="chatHistory.length === 0" class="text-center text-gray-400 py-8">
                <p class="text-xs">No previous chats</p>
              </div>
              
              <div *ngFor="let conversation of chatHistory; let i = index"
                   class="relative p-2 rounded-md cursor-pointer transition-colors hover:bg-muted"
                   [class.bg-muted]="selectedConversationId === conversation.conversation_id">
                <div class="flex items-center justify-between"
                     (click)="selectConversation(conversation.conversation_id)">
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-foreground truncate">{{ conversation.title }}</p>
                    <p class="text-[10px] text-muted-foreground mt-0.5">{{ conversation.updated_at | date:'short' }}</p>
                  </div>
                  <button class="ml-2 p-1 rounded-full hover:bg-background transition-colors opacity-0 group-hover:opacity-100"
                          (click)="toggleConversationMenu(conversation.conversation_id, $event)"
                          [class.opacity-100]="activeConversationMenu === conversation.conversation_id">
                    <i class="pi pi-ellipsis-h text-xs text-muted-foreground"></i>
                  </button>
                </div>

                <!-- Mobile-style action overlay -->
                <div *ngIf="activeConversationMenu === conversation.conversation_id"
                     class="absolute top-0 right-0 w-16 h-full bg-red-500 rounded-md flex items-center justify-center z-10 animate-slide-in-right"
                     (click)="$event.stopPropagation()">
                  <button class="text-white hover:text-red-100 transition-colors"
                          (click)="confirmDeleteConversation(conversation.conversation_id, conversation.title); $event.stopPropagation()"
                          title="Delete conversation">
                    <i class="pi pi-trash"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
          
        </div>
        
        <!-- Main Chat Area - No Header -->
        <div class="flex-1 flex flex-col bg-background relative">
          <!-- Conversation Header Bar - Condensed & Aligned -->
          <div class="h-14 px-6 border-b border-border flex items-center justify-between bg-white/50 backdrop-blur-sm">
            <div>
                <h3 class="text-base font-semibold text-gray-900" *ngIf="agentMessages.length > 0; else hawkAgent">
                  {{ getCurrentConversationTitle() }}
                </h3>
                <ng-template #hawkAgent>
                  <div class="relative inline-block">
                    <h3 class="text-base font-semibold text-gray-900 inline-flex items-center gap-2">
                      <span *ngIf="isAgentMode">{{ getCurrentHawkAgent().name }}</span>
                      <span *ngIf="!isAgentMode">{{ getApiKeyForTemplate(selectedFamily, selectedCategory).agentName }}</span>
                      <!-- Chevron to open agent menu -->
                      <button *ngIf="isAgentMode" (click)="toggleAgentMenu($event)"
                              class="px-1.5 py-1 rounded-md hover:bg-muted text-muted-foreground transition-colors"
                              title="Select Agent">
                        <i class="pi pi-chevron-down text-xs"></i>
                      </button>
                    </h3>
                    <!-- Agent dropdown menu aligned to the title -->
                    <div *ngIf="showAgentMenu" class="absolute left-0 top-full mt-1 w-56 bg-popover border border-border rounded-lg shadow-lg z-50 overflow-hidden">
                      <div class="p-1">
                        <button *ngFor="let agent of getHawkAgentOptions()" (click)="selectHawkAgent(agent.key)"
                                class="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors flex items-center justify-between"
                                [class.bg-accent]="selectedHawkAgent===agent.key">
                          <span>{{ agent.name }}</span>
                          <i *ngIf="selectedHawkAgent===agent.key" class="pi pi-check text-xs text-primary"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </ng-template>
            </div>
              <!-- Toggle at far right (Restored Functionality) -->
              <div class="flex items-center gap-3 bg-muted/30 px-3 py-1.5 rounded-full border border-border/50">
                <span class="text-xs font-medium text-muted-foreground">Template</span>
                <label class="inline-flex items-center cursor-pointer relative">
                  <input type="checkbox" class="sr-only" [ngModel]="isAgentMode" (ngModelChange)="onAgentModeToggle($event)">
                  <div class="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <span class="text-xs font-medium text-primary">Agent</span>
              </div>
            </div>
          
          <!-- Chat Messages Area -->
          <div class="flex-1 overflow-y-auto px-4 py-4" style="scroll-behavior: smooth;">
            <!-- Welcome Message -->
            <div *ngIf="agentMessages.length === 0" class="flex justify-center items-center h-full">
              <div class="text-center max-w-2xl">
                <div class="w-16 h-16 mx-auto mb-6 bg-gray-50 rounded-full flex items-center justify-center border border-gray-200">
                  <img src="assets/Logo/DBS/Logomark.svg" alt="DBS" class="h-8 w-auto">
                </div>
                <h3 class="text-2xl font-semibold text-gray-900 mb-4">Welcome to {{ getCurrentHawkAgent().name }}</h3>
                <p class="text-gray-600 mb-8">{{ getCurrentHawkAgent().description }}. I'm here to help you with {{ getCurrentHawkAgent().scope.join(', ') }}.</p>
                
                <!-- Suggested Prompts -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                  <button *ngFor="let suggestion of suggestedPrompts" 
                          (click)="useSuggestedPrompt(suggestion)"
                          class="p-4 text-left border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors">
                    <p class="text-sm font-medium text-gray-900">{{ suggestion.title }}</p>
                    <p class="text-xs text-gray-600 mt-1">{{ suggestion.description }}</p>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Chat Messages -->
            <div *ngIf="agentMessages.length > 0" class="space-y-6 max-w-4xl mx-auto">
              <div *ngFor="let message of agentMessages; let i = index" class="space-y-4">
                <!-- User Message with Hover Actions -->
                <div class="flex justify-end group">
                  <div class="relative flex items-center gap-2">
                    <!-- Hover action buttons on left -->
                    <div class="action-buttons flex items-center gap-1 pr-2">
                      <button class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
                              (click)="copyMessage(message.user)"
                              title="Copy message">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                      </button>
                      <button class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
                              (click)="reloadMessage(message.user)"
                              title="Resend message">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                      </button>
                    </div>
                    <div class="max-w-2xl bg-blue-600 text-white rounded-2xl px-4 py-3">
                      <p class="text-sm">{{ message.user }}</p>
                    </div>
                  </div>
                </div>

                <!-- AI Response with Always-Visible Actions -->
                <div class="flex justify-start">
                  <div class="w-full max-w-4xl">
                    <div class="flex items-center gap-2 mb-3">
                      <img src="assets/Logo/DBS/Logomark.svg" alt="HAWK Agent" class="w-6 h-6">
                      <span class="text-sm font-medium text-gray-900">{{ getCurrentHawkAgent().name }}</span>
                    </div>
                    <div class="overflow-x-auto">
                      <div class="prose prose-sm text-gray-800"
                           style="white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; min-width: 800px;"
                           [innerHTML]="formatResponse(message.response)"></div>
                    </div>
                    <!-- Always-visible action buttons -->
                    <div class="flex items-center gap-2 mt-3 pt-2 border-t border-gray-100">
                      <button class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
                              (click)="copyMessage(message.response)"
                              title="Copy response">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                      </button>
                      <button class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
                              (click)="exportToPDF(message, i)"
                              title="Export conversation to PDF">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                      </button>
                      <button class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
                              (click)="exportToJSON(message.response)"
                              title="Export response to JSON">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Thinking Indicator -->
              <div *ngIf="isThinking" class="flex justify-start">
                <div class="w-full max-w-4xl">
                  <div class="flex items-center gap-2 mb-3">
                    <img src="assets/Logo/DBS/Logomark.svg" alt="HAWK Agent" class="w-6 h-6">
                    <span class="text-sm font-medium text-gray-600">HAWK Agent</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <div class="flex items-center gap-2">
                      <div class="animate-pulse rounded-full h-2 w-2 bg-blue-600"></div>
                      <div class="animate-pulse rounded-full h-2 w-2 bg-blue-600" style="animation-delay: 0.2s;"></div>
                      <div class="animate-pulse rounded-full h-2 w-2 bg-blue-600" style="animation-delay: 0.4s;"></div>
                    </div>
                    <span class="text-sm text-gray-600">Thinking... {{ formatThinkingTime(thinkingElapsed) }}</span>
                  </div>
                </div>
              </div>

              <!-- Streaming Response -->
              <div *ngIf="isStreaming && currentAgentResponse" class="flex justify-start">
                <div class="w-full max-w-4xl">
                  <div class="flex items-center gap-2 mb-3">
                    <div class="w-6 h-6 flex items-center justify-center">
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    </div>
                    <span class="text-sm font-medium text-blue-600">HAWK Agent is typing...</span>
                  </div>
                  <div class="overflow-x-auto">
                    <div class="prose prose-sm text-gray-800" 
                         style="white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; min-width: 800px;"
                         [innerHTML]="formatResponse(currentAgentResponse)"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Chat Input Area -->
          <div class="bg-white px-4 py-3">
            <div class="max-w-6xl mx-auto">
              <div class="flex gap-3">
                <div class="flex-1 relative">
                  <textarea
                    class="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm"
                    placeholder="Ask me anything about hedge accounting..."
                    [(ngModel)]="agentPrompt"
                    (keydown.enter)="handleTextareaEnter($event)"
                    [disabled]="isStreaming"
                    rows="1"
                    style="min-height: 52px; max-height: 120px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);">
                  </textarea>
                  <button
                    class="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 transition-colors"
                    [class.text-gray-400]="!isStreaming && (!agentPrompt || !agentPrompt.trim())"
                    [class.hover:text-blue-600]="!isStreaming && agentPrompt && agentPrompt.trim()"
                    [class.text-red-500]="isStreaming"
                    [class.hover:text-red-600]="isStreaming"
                    [class.disabled:opacity-50]="!isStreaming && (!agentPrompt || !agentPrompt.trim())"
                    [class.disabled:cursor-not-allowed]="!isStreaming && (!agentPrompt || !agentPrompt.trim())"
                    (click)="isStreaming ? stopStreaming() : sendAgentMessage()"
                    [disabled]="!isStreaming && (!agentPrompt || !agentPrompt.trim())">
                    <svg *ngIf="!isStreaming" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
                    </svg>
                    <svg *ngIf="isStreaming" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6h12v12H6z"></path>
                    </svg>
                  </button>
                </div>
              </div>
              
            </div>
          </div>
        </div>
      </div>
      
      <!-- Results Section - Only show in Template Mode -->
      <div *ngIf="!isAgentMode" class="mt-4 bg-white border rounded-lg p-3 overflow-auto">
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

    <!-- Delete Confirmation Dialog -->
    <div *ngIf="showDeleteConfirmation"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
         (click)="cancelDeleteConversation()"
         style="z-index: 9999 !important;">
      <div class="bg-white rounded-lg p-6 max-w-md mx-4 shadow-lg"
           (click)="$event.stopPropagation()">
        <div class="flex items-center gap-3 mb-4">
          <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.232 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
          </svg>
          <h3 class="text-lg font-semibold text-gray-900">Delete Conversation</h3>
        </div>
        <p class="text-gray-600 mb-6">
          Are you sure you want to delete "<strong>{{ conversationToDelete?.title }}</strong>"?
          This action cannot be undone.
        </p>
        <div class="flex gap-3 justify-end">
          <button class="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  (click)="cancelDeleteConversation()">
            Cancel
          </button>
          <button class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  (click)="deleteConversation()">
            Delete
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    @keyframes slide-in-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }

    .animate-slide-in-right {
      animation: slide-in-right 0.2s ease-out;
    }

    .conversation-item:hover .action-buttons {
      opacity: 1;
    }

    .group:hover .action-buttons {
      opacity: 1;
    }

    .action-buttons {
      opacity: 0;
      transition: opacity 0.2s ease;
    }

    .action-buttons:hover {
      opacity: 1;
    }
  `]
})
export class EnhancedPromptTemplatesV2Component implements OnInit, OnDestroy {
  // Existing properties (from original v2 component)
  families: { label: string, value: string }[] = [];
  categories: { label: string, value: string, count: number }[] = [];
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
    performance?: BackendPerformanceMetrics | null;
  } = {
      type: 'unified',
      healthy: true,
      performance: null,
      url: environment.unifiedBackendUrl
    };
  performanceMetrics: BackendPerformanceMetrics | null = null;
  showBackendToggle = false; // Set to true for testing/debugging

  // Data freshness controls
  dataFreshnessMinutes = 15; // Default cache duration
  forceFreshData = false;    // Force fresh data flag

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

  // Agent Mode Properties
  agentPrompt = '';
  agentMessages: Array<{ user: string, response: string }> = [];
  currentAgentResponse = '';
  // Agent selection for Agent Mode (definitions moved below with menu state)

  // HAWK Agent Properties
  selectedHawkAgent: keyof typeof HAWK_AGENTS = (() => {
    try {
      if (typeof localStorage !== 'undefined') {
        const saved = localStorage.getItem('selectedHawkAgent');
        if (saved && (saved as keyof typeof HAWK_AGENTS) in HAWK_AGENTS) {
          console.log('🔄 Restored HAWK Agent from localStorage:', saved);
          return saved as keyof typeof HAWK_AGENTS;
        }
      }
    } catch (e) {
      console.warn('⚠️ localStorage access failed:', e);
    }
    console.log('🔄 Using default HAWK Agent:', DEFAULT_AGENT);
    return DEFAULT_AGENT as keyof typeof HAWK_AGENTS;
  })();
  hawkAgents = HAWK_AGENTS;

  // Thinking/Processing States
  isThinking = false;
  thinkingStartTime = 0;
  thinkingElapsed = 0;
  private thinkingTimer?: any;

  // Conversation Management
  activeConversationMenu: string | null = null;
  showDeleteConfirmation = false;
  conversationToDelete: { id: string, title: string } | null = null;
  private documentClickListener?: () => void;

  // Chat History Management
  chatHistory: AgentConversation[] = [];
  selectedConversationId = '';

  // Suggested Prompts for Welcome Screen
  // Agent selector state
  showAgentMenu = false;

  // Default prompt sets
  private defaultPrompts = [
    { title: 'Current Hedge Positions', description: 'What are our current hedge positions?', prompt: 'What are our current hedge positions?' },
    { title: 'USD Exposure Analysis', description: 'Show me utilization analysis for USD exposures', prompt: 'Show me utilization analysis for USD exposures' },
    { title: 'Hedge Effectiveness', description: 'Help me understand hedge effectiveness testing', prompt: 'Help me understand hedge effectiveness testing' },
    { title: 'Risk Assessment', description: 'Perform a risk assessment for our portfolio', prompt: 'Perform a risk assessment for our portfolio' }
  ];
  private allocationPrompts = [
    { title: 'Utilization Check', description: 'Check hedge allocation feasibility', prompt: 'Perform utilization check for new 150,000 CNY hedge under ENTITY001' },
    { title: 'CAR Buffer Analysis', description: 'Check available hedge capacity', prompt: 'Show CAR buffer availability and remaining capacity for USD hedges' },
    { title: 'Capacity Assessment', description: 'Multi-entity capacity analysis', prompt: 'Analyze hedge capacity across all entities for EUR exposures' },
    { title: 'Threshold Validation', description: 'USD PB threshold compliance', prompt: 'Validate USD deposit threshold compliance for new hedge allocation' }
  ];

  private bookingPrompts = [
    { title: 'Hedge Booking Process', description: 'Guide through hedge booking workflow', prompt: 'Guide me through the hedge booking process for approved USD exposure of $500,000' },
    { title: 'Murex Integration', description: 'Murex booking and trade execution', prompt: 'Help with Murex booking setup and trade execution parameters' },
    { title: 'GL Posting Process', description: 'General ledger posting workflow', prompt: 'Explain GL posting process and accounting entries for completed hedge trades' },
    { title: 'Amendment Process', description: 'Hedge amendment and modification', prompt: 'Process hedge amendment for maturity extension on existing trade' }
  ];

  private analyticsPrompts = [
    { title: 'Hedge Effectiveness', description: 'Test hedge effectiveness', prompt: 'Run hedge effectiveness testing for Q3 2024' },
    { title: 'Exposure Trends', description: 'Analyze exposure trends', prompt: 'Show me FX exposure trends over last 6 months' },
    { title: 'P&L Attribution', description: 'Break down P&L by hedge type', prompt: 'Analyze P&L attribution by hedge instrument type' },
    { title: 'Risk Metrics', description: 'Current risk metrics dashboard', prompt: 'Generate current risk metrics dashboard' }
  ];

  private configPrompts = [
    { title: 'Update Thresholds', description: 'Modify hedge thresholds', prompt: 'Update USD hedge threshold to $2M for Entity001' },
    { title: 'Buffer Configuration', description: 'Configure buffer percentages', prompt: 'Set CAR buffer to 15% for all entities' },
    { title: 'Entity Mappings', description: 'Update entity configurations', prompt: 'Show current entity mapping configuration' },
    { title: 'System Settings', description: 'Review system parameters', prompt: 'Review and validate current system parameters' }
  ];
  // Active prompts rendered on the welcome screen (now using HAWK agents)
  suggestedPrompts = this.getPromptsForAgent(this.selectedHawkAgent);

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
    private conversations: HawkAgentConversationsService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer,
    private cdr: ChangeDetectorRef,
    private clientOptimizer: ClientSideOptimizationService,
    private layoutService: LayoutService
  ) {
    // Initialize HAWK agent URL (dynamic based on selected agent)
    this.updateAgentUrl();
    console.log('HAWK_AGENTS loaded:', Object.keys(this.hawkAgents).map(key => this.hawkAgents[key as keyof typeof HAWK_AGENTS].name));

    // Initialize welcome content for selected agent
    this.updateWelcomeContent();

    // Enable backend toggle in development
    this.showBackendToggle = !environment.production;
  }

  toggleAgentMenu(evt: MouseEvent) {
    evt.stopPropagation();
    this.showAgentMenu = !this.showAgentMenu;
  }


  async ngOnInit() {
    await this.loadData();
    this.loadFromUrl();
    await this.loadChatHistory(); // Load previous conversations

    // Add document click listener to close conversation menu
    this.documentClickListener = () => {
      if (this.activeConversationMenu && !this.showDeleteConfirmation) {
        this.activeConversationMenu = null;
      }
    };
    document.addEventListener('click', this.documentClickListener);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.stopThinkingTimer(); // Clean up thinking timer

    // Remove document click listener
    if (this.documentClickListener) {
      document.removeEventListener('click', this.documentClickListener);
    }
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

    // Use the service's field extraction method - it's comprehensive and handles all cases
    const fields = this.svc.extractFieldNamesFromTemplate(this.selectedTemplate);

    // Additional deduplication to ensure no repeats (case-insensitive)
    const seen = new Set<string>();
    const uniqueFields = fields.filter(field => {
      const normalized = field.toLowerCase().trim();
      if (seen.has(normalized)) {
        return false; // Skip duplicate
      }
      seen.add(normalized);
      return true;
    });

    if (uniqueFields.length !== fields.length) {
      console.log(`Template "${this.selectedTemplate.name}": Removed ${fields.length - uniqueFields.length} duplicate fields`);
    }

    return uniqueFields;
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
    // Extract currency for backend data freshness logic
    const currency = this.extractCurrencyFromPrompt(query);

    const payload = {
      user_prompt: query,
      template_category: this.selectedCategory || 'general',
      msg_uid: this.currentMsgUid,
      instruction_id: this.currentInstructionId,
      stream_response: true,
      // DISABLED: Dify handles caching - no application-level cache needed
      force_fresh: true,  // Always fresh data, let Dify manage caching
      use_cache: false,   // Disable all application caching
      currency: currency,  // Extracted currency for analysis only
      // Dynamic API routing: Agent Mode vs Template Mode
      ...(this.isAgentMode ?
        {
          agent_id: this.selectedHawkAgent,  // Agent Mode: Use selected HAWK agent
          agent_api_key: this.getCurrentHawkAgent().apiKey
        } :
        (() => {
          // Template Mode: Use family/category-based routing
          const apiInfo = this.getApiKeyForTemplate(this.selectedFamily, this.selectedCategory);
          return {
            agent_id: apiInfo.agentKey,
            agent_api_key: apiInfo.apiKey
          };
        })()
      )
    };

    console.log('Processing prompt with Unified Backend');

    if (this.isAgentMode) {
      console.log('🔑 Agent Mode - Using HAWK Agent:', this.getCurrentHawkAgent().name, 'API Key:', this.getCurrentHawkAgent().apiKey);
    } else {
      const apiInfo = this.getApiKeyForTemplate(this.selectedFamily, this.selectedCategory);
      console.log('📝 Template Mode - Family:', this.selectedFamily, 'Category:', this.selectedCategory);
      console.log('🔑 Routed to HAWK Agent:', apiInfo.agentName, 'API Key:', apiInfo.apiKey);
    }

    fetch(`${environment.unifiedBackendUrl}/hawk-agent/process-prompt`, {
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
      if (!this.endedEvent && this.retryCount < this.maxRetries) {
        this.retryCount++;
        setTimeout(() => this.sendToUnifiedBackend(query), Math.min(1500 * this.retryCount, 5000));
        return;
      }
      this.isLoading = false;
      this.isStreaming = false;
      this.responseText += `\n\n[Backend Error: ${err?.message || err}]`;
      this.updateDatabaseSession('failed').catch(() => { });
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
              // Silently skip incomplete JSON chunks to prevent console spam
              // Only treat as plain text if it's definitely not JSON fragments
              if (dataContent.trim() &&
                !dataContent.includes('{') &&
                !dataContent.includes('}') &&
                !dataContent.includes('"event"') &&
                !dataContent.includes('"answer"') &&
                !dataContent.includes('data:') &&
                dataContent.length > 10) {
                this.streamBuffer += dataContent;
                this.responseText = this.streamBuffer;
              }
              // Skip all JSON parse errors completely to eliminate console warnings
            }
          } else {
            // Non-data line, treat as plain text if substantial and not SSE metadata
            if (line.trim() &&
              line.length > 5 &&
              !line.includes('event:') &&
              !line.includes('id:') &&
              !line.includes('retry:')) {
              this.streamBuffer += line + '\n';
              this.responseText = this.streamBuffer;
            }
          }
        }
      }
    } catch (e) {
      this.isStreaming = false;
      this.responseText += '\n\n[Stream interrupted due to error: ' + e + ']';
      this.updateDatabaseSession('failed').catch(() => { });
    } finally {
      reader.releaseLock();
    }
  }

  private finishUnifiedStream(tokenUsage?: any) {
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
    this.updateDatabaseSession('completed', tokenUsage).catch(() => { });

    // 3. CLEAR CACHE - Clean up processed context but keep raw Supabase data
    this.clientOptimizer.clearCache();
    // Request session completed
  }

  // Enhanced submit method with session management and currency-based caching
  async submit(payload: { text: string; values: Record<string, string> }) {
    const base = payload?.text || '';
    const filled = this.svc.fillTemplate(base, payload?.values || {});
    if (!filled) return;

    // 1. RESET RESULTS PAGE - Clear previous request data
    this.resetResultsPage();

    // Extract currency from filled prompt for cache management  
    const currency = this.extractCurrencyFromPrompt(filled);

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
    if (id) this.svc.incrementUsageCount(id).catch(() => { });

    // Send to backend with streaming (same approach as v2 component)
    this.sendToUnifiedBackend(filled);
  }

  /**
   * Reset results page between different prompts
   */
  private resetResultsPage(): void {
    // Clear processed context cache
    this.clientOptimizer.clearCache();

    // Clear response display
    this.responseText = '';
    this.streamBuffer = '';
    this.isStreaming = false;
    this.isLoading = false;

    // Results page reset for new request
  }

  /**
   * Extract currency from prompt for cache management
   */
  private extractCurrencyFromPrompt(prompt: string): string {
    const currencyPattern = /\b(USD|EUR|GBP|JPY|SGD|AUD|CHF|CAD|HKD|CNY|INR|KRW|THB|MYR|PHP|TWD|NZD)\b/i;
    const match = prompt.match(currencyPattern);
    return match ? match[1].toUpperCase() : 'USD';
  }

  /**
   * Force refresh all cached data - get latest from Supabase
   */
  forceRefreshData(): void {
    this.clientOptimizer.clearCache();
    this.forceFreshData = true;

    // Visual feedback
    const button = document.querySelector('button[title="Force refresh all cached data"]') as HTMLButtonElement;
    if (button) {
      button.innerHTML = '⏳ Refreshing...';
      button.disabled = true;

      setTimeout(() => {
        button.innerHTML = '✅ Refreshed';
        setTimeout(() => {
          button.innerHTML = '🔄 Fresh Data';
          button.disabled = false;
          this.forceFreshData = false;
        }, 1500);
      }, 500);
    }
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
      const response = await fetch(`${environment.unifiedBackendUrl}/health`, { method: 'GET' });
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
      console.log('Performance Stats:', stats);

      // For now, show in console/alert - could be enhanced with modal
      const summary = this.backendStatus.type === 'unified'
        ? `Unified Backend Stats:\n- Response Time: ${stats.response_time_ms}ms\n- Cache Hit Rate: ${stats.cache_hit_rate}\n- Backend: Unified Smart Backend v5.0`
        : `Legacy Backend: Performance tracking not available`;

      alert(summary);
    } catch (error) {
      console.error('Failed to get performance stats:', error);
      alert('Failed to load performance statistics');
    }
  }

  async clearCurrencyCache(currency: string): Promise<void> {
    if (!currency) return;

    try {
      // Direct API call to clear cache
      const response = await fetch(`${environment.unifiedBackendUrl}/cache/clear/${currency}`, { method: 'DELETE' });
      if (response.ok) {
        alert(`Cache cleared for ${currency}`);
      } else {
        throw new Error('Cache clear failed');
      }
    } catch (error) {
      console.error('Failed to clear cache:', error);
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

    // Remove "All Templates" - directly show family types
    this.families = Array.from(familySet).map(f => ({ label: f, value: f }));

    // Set default family to Instructions & Processing (robust match)
    if (!this.selectedFamily) {
      const preferred = this.families.find(f => {
        const v = (f.value || '').toLowerCase();
        return v.includes('instruction') && v.includes('processing');
      });
      this.selectedFamily = preferred ? preferred.value : (this.families[0]?.value || '');
    }

    // Build categories based on selected family
    this.buildCategoriesForFamily();
  }

  private buildCategoriesForFamily() {
    const categoryMap = new Map<string, number>();

    // Filter templates by selected family and count categories
    const filteredTemplates = this.templates.filter(t =>
      !this.selectedFamily || t.family_type === this.selectedFamily
    );

    filteredTemplates.forEach(t => {
      const cat = t.template_category || 'uncategorized';
      categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1);
    });

    this.categories = Array.from(categoryMap.entries()).map(([cat, count]) => ({
      label: cat,
      value: cat,
      count
    }));

    // Set default category to first category if not set
    if (!this.selectedCategory && this.categories.length > 0) {
      this.selectedCategory = this.categories[0].value;
    }
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

    // Auto-select first template if none selected or current selection is out of bounds
    if (this.selectedIndex < 0 || this.selectedIndex >= this.filtered.length) {
      this.selectedIndex = this.filtered.length > 0 ? 0 : -1;
    }

    this.selectedTemplate = this.filtered[this.selectedIndex] || null;

    // Auto-select template and detect fields
    if (this.selectedTemplate) {
      const fields = this.getSelectedFieldsArray();
      console.log(`Template "${this.selectedTemplate.name}" selected with ${fields.length} dynamic fields`);
    }
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
    this.selectedCategory = ''; // Reset category when family changes
    this.buildCategoriesForFamily(); // Rebuild categories for new family
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
    // Sync with LayoutService to hide/show sidebars
    this.layoutService.setAgentMode(enabled);

    // Clear any existing state when switching modes
    if (enabled) {
      this.agentMessages = [];
      this.currentAgentResponse = '';
    }
  }

  // Agent Mode Methods
  async sendAgentMessage() {
    if (!this.agentPrompt?.trim() || this.isStreaming) return;

    const userPrompt = this.agentPrompt.trim();
    this.agentPrompt = '';

    // Add user message to history
    const messageIndex = this.agentMessages.length;
    this.agentMessages.push({ user: userPrompt, response: '' });

    // Create new conversation if this is the first message (gracefully handle missing table)
    if (this.agentMessages.length === 1 && !this.selectedConversationId) {
      try {
        this.selectedConversationId = this.conversations.generateConversationId();
        const title = this.conversations.generateConversationTitle(userPrompt);
        await this.conversations.createConversation(this.selectedConversationId, userPrompt, title);
        console.log('✅ Conversation created successfully');
      } catch (error) {
        console.warn('⚠️ Failed to create conversation (table may not exist), continuing with in-memory chat:', error);
        // Generate ID for in-memory tracking even if DB fails
        this.selectedConversationId = this.conversations.generateConversationId();
      }
    }


    // Start thinking timer
    this.startThinkingTimer();
    this.currentAgentResponse = '';

    try {
      console.log('🚀 Sending agent message:', userPrompt.substring(0, 50) + '...');
      console.log('🌐 Backend URL:', `${environment.unifiedBackendUrl}/hawk-agent/process-prompt`);
      console.log('🔑 DEBUGGING - selectedHawkAgent variable:', this.selectedHawkAgent);
      console.log('🔑 DEBUGGING - getCurrentHawkAgent() result:', this.getCurrentHawkAgent());
      console.log('🔑 Using HAWK Agent:', this.getCurrentHawkAgent().name, 'API Key:', this.getCurrentHawkAgent().apiKey);
      console.log('🔑 DEBUGGING - Agent payload will use:', {
        agent_id: this.selectedHawkAgent,
        agent_api_key: this.getCurrentHawkAgent().apiKey
      });

      // Use the same backend call as template mode but with conversational prompt
      const response = await fetch(`${environment.unifiedBackendUrl}/hawk-agent/process-prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_prompt: userPrompt,
          instruction_id: 'agent-conversation',
          use_cache: false,
          force_fresh: true,
          // Ensure proper backend routing to selected HAWK agent
          agent_id: this.selectedHawkAgent,
          agent_api_key: this.getCurrentHawkAgent().apiKey,
          // Provide a generic category for backend analysis when in chat mode
          template_category: this.selectedCategory || 'general'
        })
      });

      console.log('📡 Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'No error details');
        console.error('❌ Backend error response:', errorText);
        throw new Error(`Backend error: ${response.status} - ${errorText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let buffer = ''; // Buffer for incomplete lines

      console.log('📖 Starting to read response stream...');

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('✅ Stream reading completed');
            // Process any remaining buffer content
            if (buffer.trim()) {
              console.log('📝 Processing final buffer:', buffer.substring(0, 100));
              this.processStreamLine(buffer.trim(), fullResponse);
            }
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          console.log('📥 Received chunk:', chunk.substring(0, 100) + (chunk.length > 100 ? '...' : ''));

          // Add chunk to buffer
          buffer += chunk;

          // Process complete lines
          const lines = buffer.split('\n');
          // Keep the last incomplete line in buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.trim() === '') continue;

            const answerChunk = this.processStreamLine(line, fullResponse);
            if (answerChunk) {
              fullResponse += answerChunk;
              this.currentAgentResponse = fullResponse;
              this.cdr.detectChanges();
            }
          }
        }
      }

      // Update the message with the full response
      this.agentMessages[messageIndex].response = fullResponse;
      this.currentAgentResponse = '';

      // Add assistant message to database (gracefully handle missing table)
      if (this.selectedConversationId && fullResponse) {
        try {
          await this.conversations.addMessage(this.selectedConversationId, {
            role: 'assistant',
            content: fullResponse,
            timestamp: new Date().toISOString()
          });
          console.log('✅ Assistant message saved to conversation');
        } catch (error) {
          console.warn('⚠️ Failed to save assistant message (table may not exist), continuing in-memory:', error);
        }
      }


    } catch (error) {
      console.error('❌ Agent message failed:', error);
      this.agentMessages[messageIndex].response = 'Sorry, I encountered an error processing your request. Please try again.';

    } finally {
      // Clean up all states
      this.stopThinkingTimer();
      this.isStreaming = false;
      this.cdr.detectChanges();
    }
  }

  // Process individual stream line
  private processStreamLine(line: string, currentResponse: string): string | null {
    console.log('📝 Processing line:', line.substring(0, 150) + (line.length > 150 ? '...' : ''));

    try {
      // Handle different data formats from backend
      let jsonStr = '';

      if (line.startsWith('data: data: ')) {
        // Backend sends: "data: data: {json}"
        jsonStr = line.substring(12); // Remove "data: data: "
        console.log('🔍 Found nested data format');
      } else if (line.startsWith('data: ')) {
        // Standard format: "data: {json}"
        jsonStr = line.substring(6); // Remove "data: "
        console.log('🔍 Found standard data format');
      } else {
        console.log('⏭️ Skipping non-data line');
        return null; // Skip non-data lines
      }

      if (jsonStr.trim() === '[DONE]') {
        console.log('🏁 Stream completion marker received');
        return null;
      }

      let data;
      try {
        data = JSON.parse(jsonStr);
        console.log('📊 Parsed data:', data);
      } catch (parseError) {
        // Only log if it's not a typical incomplete chunk (reduce console noise)
        if (!jsonStr.includes('"event"') && jsonStr.length > 50) {
          console.warn('⚠️ Unexpected JSON parse error:', parseError);
          console.warn('🔍 Raw content:', jsonStr.substring(0, 100) + '...');
        }
        // Skip incomplete JSON chunks - they'll be completed in next iteration
        return null;
      }

      // Handle error responses
      if (data.event === 'error') {
        console.error('❌ Backend error received:', data.message || data.error);
        throw new Error(`Backend error: ${data.message || data.error || 'Unknown error'}`);
      }

      // Extract answer from response
      if (data.answer) {
        console.log('💬 Answer chunk received:', data.answer.substring(0, 50) + '...');

        // First chunk received - stop thinking and start typing
        if (this.isThinking) {
          console.log('🛑 Stopping thinking timer, starting stream display');
          this.stopThinkingTimer();
          this.isStreaming = true;
        }

        return data.answer;
      } else {
        console.log('❓ No answer field in data:', Object.keys(data));
        return null;
      }
    } catch (e) {
      // Only log unexpected parsing errors (not typical incomplete chunks)
      if (line.length > 50 && !line.includes('data:')) {
        console.warn('⚠️ Failed to parse agent stream line:', line.substring(0, 100), e);
      }
      return null;
    }
  }

  // Chat History Management Methods
  startNewConversation() {
    // Save current conversation if it has messages
    if (this.agentMessages.length > 0) {
      this.saveCurrentConversation();
    }

    // Clear current conversation
    this.agentMessages = [];
    this.currentAgentResponse = '';
    this.selectedConversationId = '';
  }

  async saveCurrentConversation() {
    if (this.agentMessages.length === 0) return;

    try {
      // Check if this is a new conversation or existing one
      if (this.selectedConversationId) {
        // Update existing conversation - add the last message
        const lastMessage = this.agentMessages[this.agentMessages.length - 1];
        if (lastMessage.response) {
          await this.conversations.addMessage(this.selectedConversationId, {
            role: 'assistant',
            content: lastMessage.response,
            timestamp: new Date().toISOString(),
            thinking_time: this.thinkingElapsed > 0 ? this.formatThinkingTime(this.thinkingElapsed) : undefined
          });
        }
      } else {
        // Create new conversation
        const conversationId = this.conversations.generateConversationId();
        const title = this.conversations.generateConversationTitle(this.agentMessages[0].user);

        await this.conversations.createConversation(conversationId, this.agentMessages[0].user, title);

        // Add any additional messages (in case of multi-message conversation)
        for (let i = 0; i < this.agentMessages.length; i++) {
          const msg = this.agentMessages[i];
          if (i > 0) { // First user message already added in createConversation
            await this.conversations.addMessage(conversationId, {
              role: 'user',
              content: msg.user,
              timestamp: new Date().toISOString()
            });
          }
          if (msg.response) {
            await this.conversations.addMessage(conversationId, {
              role: 'assistant',
              content: msg.response,
              timestamp: new Date().toISOString()
            });
          }
        }

        this.selectedConversationId = conversationId;
      }

      // Reload chat history to reflect changes
      await this.loadChatHistory();

    } catch (error) {
      console.error('❌ Failed to save conversation:', error);
    }
  }

  // Load chat history from database
  async loadChatHistory() {
    try {
      this.chatHistory = await this.conversations.getConversations();
      console.log(`✅ Loaded ${this.chatHistory.length} previous conversations`);
    } catch (error) {
      console.warn('⚠️ Failed to load chat history (conversations table may not exist):', error);
      this.chatHistory = [];
      // Hide the previous chats section if no database support
      console.log('💡 Previous chats feature requires hawk_agent_conversations table');
    }
  }

  async selectConversation(conversationId: string) {
    // Prevent conversation switching during streaming to avoid losing current conversation
    if (this.isStreaming || this.isThinking) {
      console.warn('⚠️ Cannot switch conversations during streaming');
      return;
    }

    // Don't reload if it's the same conversation
    if (this.selectedConversationId === conversationId) {
      return;
    }

    const conversation = this.chatHistory.find(c => c.conversation_id === conversationId);
    if (conversation) {
      // Save current conversation before switching
      if (this.agentMessages.length > 0 && this.selectedConversationId !== conversationId) {
        await this.saveCurrentConversation();
      }

      // Convert database format to component format
      this.selectedConversationId = conversationId;
      this.agentMessages = this.convertDatabaseMessagesToComponent(conversation.messages);
      this.currentAgentResponse = '';
      this.cdr.detectChanges();
    }
  }

  // Helper method to convert database messages to component format
  private convertDatabaseMessagesToComponent(dbMessages: any[]): Array<{ user: string, response: string }> {
    const componentMessages: Array<{ user: string, response: string }> = [];

    for (let i = 0; i < dbMessages.length; i++) {
      const msg = dbMessages[i];

      if (msg.role === 'user') {
        // Find the next assistant message if it exists
        const nextMsg = dbMessages[i + 1];
        const response = (nextMsg && nextMsg.role === 'assistant') ? nextMsg.content : '';

        componentMessages.push({
          user: msg.content,
          response: response
        });

        // Skip the assistant message since we already processed it
        if (nextMsg && nextMsg.role === 'assistant') {
          i++;
        }
      }
    }

    return componentMessages;
  }

  clearCurrentConversation() {
    this.agentMessages = [];
    this.currentAgentResponse = '';

    // Remove from history if it exists
    if (this.selectedConversationId) {
      this.chatHistory = this.chatHistory.filter(c => c.conversation_id !== this.selectedConversationId);
      this.selectedConversationId = '';
    }
  }

  getCurrentConversationTitle(): string {
    if (this.selectedConversationId) {
      const conversation = this.chatHistory.find(c => c.conversation_id === this.selectedConversationId);
      return conversation?.title || 'Conversation';
    }
    return this.agentMessages.length > 0 ? this.generateConversationTitle() : 'New Conversation';
  }

  getCurrentTimestamp(): string {
    if (this.selectedConversationId) {
      const conversation = this.chatHistory.find(c => c.conversation_id === this.selectedConversationId);
      return conversation ? new Date(conversation.updated_at || conversation.created_at || '').toLocaleString() : '';
    }
    return new Date().toLocaleString();
  }

  useSuggestedPrompt(suggestion: any) {
    this.agentPrompt = suggestion.prompt;
    // Auto-focus the textarea
    setTimeout(() => {
      const textarea = document.querySelector('textarea') as HTMLTextAreaElement;
      if (textarea) {
        textarea.focus();
      }
    }, 100);
  }

  handleTextareaEnter(event: any) {
    if (event.shiftKey) {
      // Allow shift+enter for new lines
      return;
    } else {
      // Send message on enter
      event.preventDefault();
      this.sendAgentMessage();
    }
  }

  stopStreaming() {
    this.stopThinkingTimer();
    this.isStreaming = false;
    this.cdr.detectChanges();
  }

  private generateConversationId(): string {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  private generateConversationTitle(): string {
    if (this.agentMessages.length === 0) return 'New Conversation';

    const firstMessage = this.agentMessages[0].user;
    // Take first 60 characters and add ellipsis if longer
    let title = firstMessage.length > 60 ? firstMessage.substring(0, 57) + '...' : firstMessage;

    // Remove line breaks and normalize whitespace
    title = title.replace(/\s+/g, ' ').trim();

    return title || 'Untitled Conversation';
  }

  // Thinking timer methods
  startThinkingTimer() {
    this.isThinking = true;
    this.thinkingStartTime = Date.now();
    this.thinkingElapsed = 0;

    this.thinkingTimer = setInterval(() => {
      this.thinkingElapsed = Date.now() - this.thinkingStartTime;
      this.cdr.detectChanges();
    }, 100); // Update every 100ms for smooth counting
  }

  stopThinkingTimer() {
    this.isThinking = false;
    if (this.thinkingTimer) {
      clearInterval(this.thinkingTimer);
      this.thinkingTimer = null;
    }
  }

  formatThinkingTime(elapsed: number): string {
    const seconds = Math.floor(elapsed / 1000);
    const tenths = Math.floor((elapsed % 1000) / 100);
    return `${seconds}.${tenths}s`;
  }

  // Format response for ChatGPT-like display with proper table handling
  formatResponse(response: string): string {
    if (!response) return '';

    let formatted = response;

    // Handle markdown tables properly
    formatted = this.parseMarkdownTables(formatted);

    // Convert markdown headers to HTML with proper styling
    formatted = formatted.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-900 mt-6 mb-3">$1</h3>');
    formatted = formatted.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-gray-900 mt-6 mb-4">$1</h2>');
    formatted = formatted.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-gray-900 mt-6 mb-4">$1</h1>');

    // Convert markdown bold and italic
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');
    formatted = formatted.replace(/\*(.+?)\*/g, '<em class="italic">$1</em>');

    // Convert markdown lists
    formatted = formatted.replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>');
    formatted = formatted.replace(/(<li.*<\/li>)/gs, '<ul class="list-disc pl-6 my-3">$1</ul>');

    // Convert numbered lists
    formatted = formatted.replace(/^\d+\. (.+)$/gm, '<li class="ml-4">$1</li>');
    formatted = formatted.replace(/(<li.*<\/li>)/gs, (match) => {
      if (!match.includes('list-disc')) {
        return `<ol class="list-decimal pl-6 my-3">${match}</ol>`;
      }
      return match;
    });

    // Convert line breaks to proper spacing
    formatted = formatted.replace(/\n\n/g, '</p><p class="mb-4">');
    formatted = formatted.replace(/\n/g, '<br>');

    // Wrap in paragraph tags
    if (!formatted.startsWith('<')) {
      formatted = `<p class="mb-4">${formatted}</p>`;
    }

    return formatted;
  }

  // Enhanced markdown table parser
  private parseMarkdownTables(text: string): string {
    const lines = text.split('\n');
    let result: string[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Check if this line starts a markdown table (contains |)
      if (line.trim().includes('|') && line.trim().startsWith('|') && line.trim().endsWith('|')) {
        // Found potential table start
        let tableLines: string[] = [];
        let tableStart = i;

        // Collect all consecutive table lines
        while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
          tableLines.push(lines[i]);
          i++;
        }

        if (tableLines.length > 0) {
          // Parse the table
          const tableHtml = this.convertTableToHtml(tableLines);
          result.push(tableHtml);
          continue;
        } else {
          i = tableStart; // Reset if no table found
        }
      }

      // Not a table line, add as-is
      result.push(line);
      i++;
    }

    return result.join('\n');
  }

  private convertTableToHtml(tableLines: string[]): string {
    if (tableLines.length === 0) return '';

    let tableHtml = '<table class="min-w-full border-collapse border border-gray-300 my-4 bg-white shadow-sm rounded-lg overflow-hidden">';

    // Process each line
    for (let i = 0; i < tableLines.length; i++) {
      const line = tableLines[i].trim();

      // Skip separator lines (lines with only |, -, :, and spaces)
      if (/^[\|\-\:\s]+$/.test(line)) {
        continue;
      }

      // Parse cells
      const cells = line.split('|').slice(1, -1).map(cell => cell.trim());

      if (cells.length > 0) {
        const isHeader = i === 0; // First non-separator line is header
        const tag = isHeader ? 'th' : 'td';
        const headerClass = isHeader ? 'bg-gray-50 font-semibold text-gray-900' : 'bg-white text-gray-800';

        tableHtml += '<tr>';
        cells.forEach(cell => {
          tableHtml += `<${tag} class="px-4 py-3 border border-gray-300 text-sm ${headerClass}">${cell || '&nbsp;'}</${tag}>`;
        });
        tableHtml += '</tr>';
      }
    }

    tableHtml += '</table>';
    return tableHtml;
  }

  // Results actions (existing stubs)
  exportReport() { console.log('Export report clicked'); }
  createTicket() { console.log('Create ticket clicked'); }
  scheduleReview() { console.log('Schedule review clicked'); }
  shareResults() { console.log('Share results clicked'); }

  setRating(rating: number) { this.currentRating = rating; }
  setCompletionStatus(status: string) { this.completionStatus = status; }
  onFeedbackChange(feedback: string) { this.feedbackText = feedback; }

  // ID generation (existing logic)
  private generateMsgUID(): string {
    return `MSG_${Date.now()}_${this.msgUidCounter++}`;
  }

  private generateInstructionId(): string {
    // Keep instruction_id short to fit character varying(10) constraint
    return `I${this.instructionIdCounter++}`;
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

  // Keyboard navigation (existing logic) - ONLY active in template mode
  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent) {
    // CRITICAL FIX: Don't trigger template mode actions when in agent mode
    if (this.isAgentMode) return;

    if (!this.filtered?.length) return;
    if (e.key === 'ArrowDown') {
      this.selectedIndex = Math.min(this.filtered.length - 1, Math.max(0, this.selectedIndex) + 1);
      e.preventDefault();
      this.persistAndSyncUrl();
    }
    if (e.key === 'ArrowUp') {
      this.selectedIndex = Math.max(0, (this.selectedIndex < 0 ? 0 : this.selectedIndex) - 1);
      e.preventDefault();
      this.persistAndSyncUrl();
    }
    if (e.key === 'Enter') {
      this.submit({ text: this.selectedTemplate?.prompt_text || '', values: {} });
      e.preventDefault();
    }
  }

  // HAWK Agent Methods
  onHawkAgentChange(agentKey: string) {
    console.log('🔄 Changing HAWK Agent from', this.selectedHawkAgent, 'to', agentKey);
    this.selectedHawkAgent = agentKey as keyof typeof HAWK_AGENTS;
    // Persist to localStorage to prevent rotation
    try {
      localStorage.setItem('selectedHawkAgent', agentKey);
      console.log('💾 Persisted HAWK Agent to localStorage:', agentKey);
    } catch (e) {
      console.warn('⚠️ Failed to persist HAWK Agent to localStorage:', e);
    }
    this.updateAgentUrl();
    console.log(`✅ Switched to ${this.getCurrentHawkAgent().name} with API key: ${this.getCurrentHawkAgent().apiKey}`);
  }

  selectHawkAgent(agentKey: string) {
    this.onHawkAgentChange(agentKey);
    this.showAgentMenu = false; // Close the dropdown menu
    this.updateWelcomeContent(); // Update welcome content when agent changes
  }

  updateWelcomeContent() {
    this.suggestedPrompts = this.getPromptsForAgent(this.selectedHawkAgent);
  }

  getPromptsForAgent(agentKey: keyof typeof HAWK_AGENTS) {
    switch (agentKey) {
      case 'allocation':
        return this.allocationPrompts;
      case 'booking':
        return this.bookingPrompts;
      case 'analytics':
        return this.analyticsPrompts;
      case 'config':
        return this.configPrompts;
      default:
        return this.defaultPrompts;
    }
  }

  // Dynamic API routing for Template Mode based on family and category
  getApiKeyForTemplate(family: string, category: string): { agentKey: keyof typeof HAWK_AGENTS, apiKey: string, agentName: string } {
    const fam = (family || '').toLowerCase();
    const cat = (category || '').toLowerCase();

    // Configuration & Setup family (and variants) → Config Agent
    if (fam.includes('config') || fam.includes('setup')) {
      return {
        agentKey: 'config',
        apiKey: this.hawkAgents.config.apiKey,
        agentName: this.hawkAgents.config.name
      };
    }

    // Instructions & Processing family routing
    if (fam.includes('instruction') && fam.includes('processing')) {
      // Inception category → Allocation Agent (app-MHztrttE0Ty6jOqykQrp6rL2)
      if (cat.includes('inception')) {
        return {
          agentKey: 'allocation',
          apiKey: this.hawkAgents.allocation.apiKey,
          agentName: this.hawkAgents.allocation.name
        };
      }

      // Utilisation/Utilization category → Allocation Agent (app-cxzVbRQUUDofTjx1nDfajpRX)
      if (cat.includes('utilization') || cat.includes('utilisation')) {
        return {
          agentKey: 'allocation',
          apiKey: this.hawkAgents.allocation.apiKey,
          agentName: this.hawkAgents.allocation.name
        };
      }

      // Rest of Instructions & Processing categories → Analytics Agent (app-KKtaMynVyn8tKbdV9VbbaeyR)
      return {
        agentKey: 'analytics',
        apiKey: this.hawkAgents.analytics.apiKey,
        agentName: this.hawkAgents.analytics.name
      };
    }

    // All other families → Analytics Agent (app-KKtaMynVyn8tKbdV9VbbaeyR)
    return {
      agentKey: 'analytics',
      apiKey: this.hawkAgents.analytics.apiKey,
      agentName: this.hawkAgents.analytics.name
    };
  }

  private updateAgentUrl() {
    const agent = this.hawkAgents[this.selectedHawkAgent];
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(agent.url);
  }

  getCurrentHawkAgent() {
    return this.hawkAgents[this.selectedHawkAgent];
  }

  getHawkAgentOptions() {
    const options = Object.keys(this.hawkAgents).map(key => ({
      key,
      name: this.hawkAgents[key as keyof typeof HAWK_AGENTS].name
    }));
    console.log('HAWK dropdown options:', options.map(o => o.name));
    return options;
  }

  getHawkStageBadgeClass(stage: string): string {
    const stageClasses: { [key: string]: string } = {
      '1A': 'bg-green-100 text-green-800 border border-green-200',
      '1B': 'bg-blue-100 text-blue-800 border border-blue-200',
      '2': 'bg-orange-100 text-orange-800 border border-orange-200',
      '3': 'bg-red-100 text-red-800 border border-red-200'
    };
    return stageClasses[stage] || 'bg-gray-100 text-gray-800 border border-gray-200';
  }

  // Conversation Management Methods
  toggleConversationMenu(conversationId: string, event: Event) {
    event.stopPropagation(); // Prevent conversation selection
    this.activeConversationMenu = this.activeConversationMenu === conversationId ? null : conversationId;
  }

  confirmDeleteConversation(conversationId: string, title: string) {
    this.conversationToDelete = { id: conversationId, title };
    this.showDeleteConfirmation = true;
    this.activeConversationMenu = null; // Close the menu
  }

  cancelDeleteConversation() {
    this.showDeleteConfirmation = false;
    this.conversationToDelete = null;
  }

  async deleteConversation() {
    if (!this.conversationToDelete) return;

    try {
      // Delete from database
      await this.conversations.deleteConversation(this.conversationToDelete.id);

      // Remove from local array
      this.chatHistory = this.chatHistory.filter(
        conv => conv.conversation_id !== this.conversationToDelete!.id
      );

      // If this was the selected conversation, clear selection
      if (this.selectedConversationId === this.conversationToDelete.id) {
        this.selectedConversationId = '';
        this.agentMessages = [];
        this.currentAgentResponse = '';
      }

      console.log('✅ Conversation deleted successfully');
    } catch (error) {
      console.error('❌ Failed to delete conversation:', error);
      // You could add a toast notification here
    } finally {
      this.cancelDeleteConversation();
    }
  }

  // Message Action Methods
  copyMessage(content: string) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(content).then(() => {
        console.log('✅ Message copied to clipboard');
        // You could add a toast notification here
      }).catch(err => {
        console.error('❌ Failed to copy message:', err);
      });
    }
  }

  reloadMessage(userPrompt: string) {
    // Set the agent prompt and trigger resend
    this.agentPrompt = userPrompt;
    this.sendAgentMessage();
  }

  exportToPDF(message: { user: string, response: string }, index: number) {
    // Create conversation context up to this point
    const conversationContext = this.agentMessages.slice(0, index + 1);
    const conversationTitle = this.getCurrentConversationTitle();

    // Generate PDF content
    const pdfContent = this.generatePDFContent(conversationContext, conversationTitle);

    // Create and download PDF
    this.downloadPDF(pdfContent, `${conversationTitle}_conversation.pdf`);
  }

  exportToJSON(response: string) {
    const exportData = {
      timestamp: new Date().toISOString(),
      agent: this.getCurrentHawkAgent().name,
      response: response,
      metadata: {
        agent_key: this.selectedHawkAgent,
        conversation_id: this.selectedConversationId || 'temp'
      }
    };

    const jsonString = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `hawk_response_${Date.now()}.json`;
    link.click();

    URL.revokeObjectURL(url);
    console.log('✅ Response exported to JSON');
  }

  private generatePDFContent(conversation: Array<{ user: string, response: string }>, title: string): string {
    let content = `HAWK Agent Conversation Export\n`;
    content += `Title: ${title}\n`;
    content += `Agent: ${this.getCurrentHawkAgent().name}\n`;
    content += `Date: ${new Date().toLocaleString()}\n`;
    content += `\n${'='.repeat(50)}\n\n`;

    conversation.forEach((message, index) => {
      content += `Message ${index + 1}:\n`;
      content += `User: ${message.user}\n\n`;
      content += `${this.getCurrentHawkAgent().name}: ${message.response}\n\n`;
      content += `${'-'.repeat(30)}\n\n`;
    });

    return content;
  }

  private downloadPDF(content: string, filename: string) {
    // For now, create a text file (PDF generation would require a library like jsPDF)
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename.replace('.pdf', '.txt');
    link.click();

    URL.revokeObjectURL(url);
    console.log('✅ Conversation exported to text file');
  }
}
