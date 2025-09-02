import { Component, ElementRef, OnDestroy, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl, SafeHtml } from '@angular/platform-browser';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AGENT_IFRAME_URL, AGENT_IFRAME_ORIGIN } from '../../../core/config/app-config';
import { CurrencyService } from '../../../shared/services/currency.service';
import { HawkAgentSimpleService } from '../services/hawk-agent-simple.service';
import { PromptTemplatesService, PromptTemplate } from '../../configuration/prompt-templates/prompt-templates.service';
import { OptimizedDifyService } from '../../../services/optimized-dify.service';
import { GitHubPagesDifyService } from '../../../services/github-pages-dify-service';
import { DialogModule } from 'primeng/dialog';

@Component({
  selector: 'app-hawk-prompt-templates',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule],
  template: `
    <div class="p-6 space-y-4 min-h-full flex flex-col">
      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">{{ isAgentMode ? 'Agent Mode' : 'Template Mode' }}</h2>
          <div class="text-xs text-gray-500">HAWK Agent</div>
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

      <!-- Agent Mode Content (placed directly under header) -->
      <div *ngIf="isAgentMode" class="space-y-6 flex-1 flex flex-col min-h-0">
        <div class="bg-white rounded-lg border border-gray-200 overflow-hidden relative flex-1 min-h-0">
          <!-- Floating prompt toast (does not affect iframe layout) -->
          <div *ngIf="incomingPrompt && showPromptToast && !isMinimized" class="absolute z-30 top-4 right-4 max-w-xl pointer-events-none">
            <div class="flex items-center gap-3 bg-gray-900/90 text-white rounded-md px-3 py-2 shadow-lg border border-gray-800 pointer-events-auto">
              <div class="text-sm truncate flex-1">
                <span class="font-medium">Prompt ready:</span>
                <span class="ml-1">{{ incomingPrompt }}</span>
              </div>
              <button class="btn btn-secondary" (click)="copyPrompt()" title="Copy to clipboard">
                <i class="pi pi-copy"></i>
                <span>{{ copied ? 'Copied' : 'Copy' }}</span>
              </button>
              <button class="btn btn-primary" (click)="sendPromptToIframe()">
                <i class="pi pi-send"></i>
                <span>Send</span>
              </button>
              <button class="btn btn-tertiary" (click)="minimizePromptToast()" title="Minimize">
                <i class="pi pi-minus"></i>
              </button>
              <button class="btn btn-tertiary" (click)="dismissPromptToast()" title="Dismiss">
                <i class="pi pi-times"></i>
              </button>
            </div>
          </div>
          <!-- Minimized chip (stay top-right; avoid layout shift) -->
          <div *ngIf="incomingPrompt && showPromptToast && isMinimized" class="absolute z-30 top-4 right-4 pointer-events-none">
            <div class="flex items-center gap-2 bg-gray-900/90 text-white rounded-full px-3 py-1.5 shadow-md border border-gray-800 pointer-events-auto">
              <i class="pi pi-comment"></i>
              <span class="text-xs truncate max-w-[260px]">Prompt ready</span>
              <button class="btn btn-secondary" (click)="copyPrompt()" title="Copy">
                <i class="pi pi-copy text-xs"></i>
              </button>
              <button class="btn btn-primary" (click)="expandPromptToast()" title="Expand">
                <i class="pi pi-angle-up"></i>
              </button>
              <button class="btn btn-tertiary" (click)="dismissPromptToast()" title="Dismiss">
                <i class="pi pi-times"></i>
              </button>
            </div>
          </div>
          <!-- Iframe wrapper (top) -->
          <div class="w-full h-full flex-1 min-h-0">
            <iframe
              #agentFrame
              [src]="agentUrlSafe"
              allow="microphone; clipboard-write;"
              frameborder="0"
              style="width: 100%; height: 100%; min-height: 700px; display: block;"
              class="transition-opacity duration-300">
            </iframe>
          </div>
        </div>
      </div>

      <!-- Template Mode Content -->
      <div *ngIf="!isAgentMode" class="flex flex-col space-y-6">
        <!-- Template Families Tabs -->
        <div class="bg-white border-b border-gray-200 px-6 py-3">
          <div class="flex flex-wrap gap-2">
            <button *ngFor="let type of instructionTypes; trackBy: trackByKey"
                    (click)="onInstructionTypeSelect(type.key)"
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    [ngClass]="activeInstructionType === type.key ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'">
              {{ type.label }} <span class="text-xs opacity-75">({{ type.count }})</span>
            </button>
          </div>
        </div>

        <!-- Main Content with Sidebar -->
        <div class="flex bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style="min-height: 600px;">
          <!-- Category Sidebar -->
          <div class="w-72 bg-gray-50 border-r border-gray-200 flex flex-col">
            <!-- Sidebar Header -->
            <div class="px-6 py-4 border-b border-gray-200 bg-white">
              <h3 class="text-lg font-semibold text-gray-900">Categories</h3>
              <p class="text-sm text-gray-600 mt-1">{{ getSelectedInstructionTypeLabel() }}</p>
            </div>
            
            <!-- Recent Templates Section -->
            <div *ngIf="recentTemplates.length > 0" class="p-4 border-b border-gray-200">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Recent</h4>
              <div class="space-y-1">
                <button *ngFor="let recent of recentTemplates.slice(0, 3)"
                        (click)="loadRecentTemplate(recent)"
                        class="w-full text-left px-3 py-2 text-xs bg-white hover:bg-blue-50 hover:text-blue-700 rounded-md text-gray-700 transition-colors border border-gray-200">
                  {{ recent.label }}
                </button>
              </div>
            </div>
            
            <!-- Category List -->
            <div class="flex-1 overflow-y-auto">
              <div class="p-4 space-y-3">
                <button 
                  *ngFor="let category of getCurrentCategories(); trackBy: trackByKey" 
                  (click)="onCategorySelect(category.key)"
                  [class]="getCategoryTabClass(category.key)"
                  class="w-full text-left px-5 py-4 rounded-lg text-sm font-medium transition-all duration-200 group">
                  <div class="flex items-center justify-between">
                    <span class="flex-1">{{ category.label }}</span>
                    <span class="px-3 py-1 rounded-full text-xs font-medium"
                          [class]="activeCategory === category.key ? 'bg-white bg-opacity-20 text-white' : 'bg-gray-200 text-gray-700'">
                      {{ category.count }}
                    </span>
                  </div>
                </button>
                
                <div *ngIf="getCurrentCategories().length === 0" class="text-center py-12 text-gray-500">
                  <div class="text-4xl mb-2">📂</div>
                  <div class="text-sm font-medium">No categories available</div>
                  <div class="text-xs text-gray-400 mt-1">Select a different family type above</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Main Content Area -->
          <div class="flex-1 flex flex-col min-w-0">

            <!-- Header for Selected Category -->
            <div class="bg-white border-b border-gray-200 px-6 py-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-semibold text-gray-900">{{ getSelectedCategoryLabel() }}</h3>
                  <p class="text-sm text-gray-600 mt-1">{{ currentPrompts.length }} template{{ currentPrompts.length !== 1 ? 's' : '' }} available</p>
                </div>
                <div class="text-sm text-gray-500">
                  Template Mode
                </div>
              </div>
            </div>

            <!-- Template Selection -->
            <div class="bg-white flex-1 overflow-hidden flex flex-col">
              <div class="px-6 py-4 border-b border-gray-100">
                <h3 class="text-lg font-semibold text-gray-900">Select Template</h3>
              </div>
              
              <!-- Template List -->
              <div class="flex-1 overflow-y-auto">
                <div class="divide-y divide-gray-50">
              <label *ngFor="let p of currentPrompts; let i = index; trackBy: trackByIndex" 
                     class="flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors">
                <div class="flex items-center justify-center">
                  <input type="radio" name="prompt" class="text-blue-600"
                         [checked]="selectedPromptIndex === i"
                         (change)="selectPrompt(i)" />
                </div>
                <div class="flex items-center gap-4 flex-1 min-w-0">
                  <!-- Template Number Column (Fixed Width) -->
                  <div class="w-20 flex-shrink-0 text-center">
                    <div class="text-sm font-medium text-gray-900">Template {{ i + 1 }}</div>
                  </div>
                  
                  <!-- Template Text Column (Flexible) -->
                  <div class="flex-1 min-w-0">
                    <div class="text-sm text-gray-700 leading-relaxed">{{ p.template }}</div>
                    <div *ngIf="p.isDynamic" class="text-xs text-blue-600 mt-1">
                      <i class="pi pi-cog mr-1"></i>Dynamic Template ({{ p.inputFields?.length || 0 }} input fields)
                    </div>
                  </div>
                  
                  <!-- Metrics Column (Fixed Width) -->
                  <div class="w-24 flex-shrink-0 flex items-center justify-center gap-2">
                    <!-- Usage Count Circle -->
                    <div class="flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium text-gray-700 bg-blue-100"
                         [title]="p.usageCount + ' uses'">
                      {{ formatUsageCount(p.usageCount) }}
                    </div>
                    
                    <!-- Success Rate Circle -->
                    <div class="flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium text-gray-700 bg-green-100"
                         [title]="p.successRate + '% success rate'">
                      {{ p.successRate }}%
                    </div>
                  </div>
                </div>
              </label>
              <!-- Empty state -->
              <div *ngIf="(!currentPrompts || currentPrompts.length === 0)" class="px-6 py-10 text-sm text-gray-500">
                No templates found for this type.
              </div>
            </div>
          </div>

          <!-- Parameters Section -->
          <div *ngIf="selectedPromptIndex >= 0" class="border-t border-gray-200 bg-gray-50">
            <div class="px-6 py-4">
              <h4 class="text-md font-semibold text-gray-900 mb-4">Configure Parameters</h4>
              
              <!-- Live Preview -->
              <div class="bg-white rounded-lg p-4 border border-gray-300 mb-4">
                <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Live Preview</div>
                
                <!-- Static Template Preview (existing templates) -->
                <div *ngIf="!isSelectedTemplateDynamic()" class="text-sm text-gray-900 font-mono leading-relaxed flex flex-wrap items-center gap-2">
                  <ng-container *ngFor="let part of previewParts; trackBy: trackByPart">
                    <span *ngIf="part.type === 'text'" class="text-gray-800">{{ part.text }}</span>
                    <ng-container *ngIf="part.type === 'placeholder'">
                      <input *ngIf="part.name === 'amount'" 
                             type="number" 
                             class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-24 font-semibold" 
                             placeholder="0.00" 
                             [(ngModel)]="amount" />
                      <input *ngIf="part.name === 'date'" 
                             type="date" 
                             class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-36 font-semibold" 
                             [(ngModel)]="date" />
                      <select *ngIf="part.name !== 'amount' && part.name !== 'date'" 
                              class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-auto min-w-32 font-semibold"
                              [ngModel]="placeholderValues[part.name]"
                              (ngModelChange)="onPlaceholderChange(part.name, $event)">
                        <option *ngFor="let opt of getOptionsFor(part.name); trackBy: trackByIndex" [value]="opt">{{ opt }}</option>
                      </select>
                    </ng-container>
                  </ng-container>
                </div>
                
                <!-- Dynamic Template Preview (database templates) with inline inputs -->
                <div *ngIf="isSelectedTemplateDynamic()" class="space-y-4">
                  <div class="text-sm text-gray-900 font-mono leading-relaxed flex flex-wrap items-center gap-2">
                    <ng-container *ngFor="let part of previewParts; trackBy: trackByPart">
                      <span *ngIf="part.type === 'text'" class="text-gray-800">{{ part.text }}</span>
                      <ng-container *ngIf="part.type === 'placeholder'">
                        <input *ngIf="part.name === 'amount'" 
                               type="number" 
                               class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-24 font-semibold" 
                               placeholder="0.00" 
                               [ngModel]="dynamicInputValues[part.name]"
                               (ngModelChange)="dynamicInputValues[part.name]=$event; onDynamicInputChange()" />
                        <input *ngIf="part.name === 'date'" 
                               type="date" 
                               class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-36 font-semibold" 
                               [ngModel]="dynamicInputValues[part.name]"
                               (ngModelChange)="dynamicInputValues[part.name]=$event; onDynamicInputChange()" />
                        <input *ngIf="part.name !== 'amount' && part.name !== 'date'"
                               type="text"
                               class="inline-input bg-blue-50 border border-blue-300 rounded px-2 py-1 text-sm w-auto min-w-32 font-semibold"
                               [placeholder]="formatFieldLabel(part.name)"
                               [ngModel]="dynamicInputValues[part.name]"
                               (ngModelChange)="dynamicInputValues[part.name]=$event; onDynamicInputChange()" />
                      </ng-container>
                    </ng-container>
                  </div>
                  
                  <!-- Filled Template Preview -->
                  <div *ngIf="getSelectedTemplateInputFields().length > 0" class="mt-4 p-3 bg-green-50 border border-green-200 rounded">
                    <div class="text-xs font-medium text-green-700 mb-2">Filled Template Preview:</div>
                    <div class="text-sm text-green-800 leading-relaxed whitespace-pre-wrap">{{ getFilledTemplate() }}</div>
                  </div>
                </div>
              </div>


              <!-- Submit Button -->
              <div class="flex items-center justify-between">
                <button class="btn btn-secondary" (click)="saveAsTemplate()">
                  <i class="pi pi-bookmark"></i>
                  Save Template
                </button>
                <button class="btn btn-primary btn-lg" (click)="usePrompt()" [disabled]="isLoading || !isFormValid()">
                  <span *ngIf="isLoading" class="flex items-center gap-2">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Processing...
                  </span>
                  <span *ngIf="!isLoading" class="flex items-center gap-2">
                    <i class="pi pi-send"></i>
                    Submit
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>


        <!-- History Tab -->
        <div *ngIf="showHistory" class="bg-white rounded-xl shadow-sm border border-gray-200 mt-6">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">Query History</h3>
            <button class="btn btn-tertiary" (click)="toggleHistory()">
              <i class="pi pi-times"></i>
            </button>
          </div>
          <div class="divide-y divide-gray-100">
            <div *ngFor="let item of queryHistory; let i = index" 
                 class="px-6 py-4 hover:bg-gray-50 cursor-pointer"
                 (click)="loadHistoryItem(item)">
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="text-sm font-medium text-gray-900">{{ item.query }}</div>
                  <div class="text-xs text-gray-500 mt-1">{{ formatDate(item.timestamp) }}</div>
                  <div *ngIf="item.msgUid" class="flex items-center gap-4 mt-2">
                    <div class="flex items-center gap-1">
                      <i class="pi pi-id-card text-xs text-gray-400"></i>
                      <span class="text-xs font-mono text-gray-600">{{ item.msgUid }}</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <i class="pi pi-bookmark text-xs text-gray-400"></i>
                      <span class="text-xs font-mono text-gray-600">{{ item.instructionId || 'N/A' }}</span>
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="px-2 py-1 text-xs rounded-full" [ngClass]="getHistoryStatusClass(item.status)">
                    {{ item.status }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      

      <!-- Results Section - Full Width Outside All Mode Content -->
      <div #resultsSection *ngIf="showResults" class="bg-white rounded-xl shadow-sm border border-gray-200 mt-6 w-full overflow-hidden">
        <div class="divide-y divide-gray-100">
          <div class="px-6 py-4 flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Results</h3>
              <p class="text-sm text-gray-600 mt-1">{{ lastQuery }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button class="btn btn-tertiary" (click)="clearResults()">
                <i class="pi pi-times"></i>
                Clear Results
              </button>
            </div>
          </div>

          <div class="p-6 max-w-full overflow-hidden">
            <!-- Loading State -->
            <div *ngIf="isLoading" class="text-center py-12">
              <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p class="mt-4 text-gray-600">Processing your request...</p>
              <div class="w-64 bg-gray-200 rounded-full h-2 mx-auto mt-2">
                <div class="bg-blue-600 h-2 rounded-full animate-pulse" style="width: 60%"></div>
              </div>
            </div>

            <!-- Results -->
            <div *ngIf="!isLoading && apiResponse" class="space-y-6">
              <!-- Status Badge -->
              <div class="flex items-center gap-3">
                <div class="flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium"
                     [ngClass]="getStatusBadgeClass()">
                  <i [class]="getStatusIcon()"></i>
                  {{ getResultStatus() }}
                </div>
                <span class="text-xs text-gray-500">{{ getCurrentDateTime() }}</span>
              </div>

              <!-- Unique Identifiers -->
              <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 mb-4">
                <div class="text-sm font-medium text-gray-700 mb-3">Request Identifiers</div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div class="flex items-center gap-2">
                    <i class="pi pi-id-card text-gray-500"></i>
                    <div>
                      <div class="text-xs text-gray-500">Message UID</div>
                      <div class="font-mono text-sm font-semibold text-gray-800">{{ currentMsgUid }}</div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <i class="pi pi-bookmark text-gray-500"></i>
                    <div>
                      <div class="text-xs text-gray-500">Instruction ID</div>
                      <div class="font-mono text-sm font-semibold text-gray-800">{{ currentInstructionId }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Key Information -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
                  <div class="text-sm font-medium text-blue-900">Amount</div>
                  <div class="text-lg font-semibold text-blue-700">{{ amount?.toLocaleString() || 'N/A' }} {{ currency }}</div>
                </div>
                <div class="bg-green-50 rounded-lg p-4 border border-green-200">
                  <div class="text-sm font-medium text-green-900">Date</div>
                  <div class="text-lg font-semibold text-green-700">{{ date || 'N/A' }}</div>
                </div>
                <div class="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <div class="text-sm font-medium text-purple-900">Type</div>
                  <div class="text-lg font-semibold text-purple-700">{{ getCategoryLabel(activeCategory) }}</div>
                </div>
              </div>

              <!-- Main Response -->
              <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 overflow-hidden w-full">
                <div class="p-6 max-w-full overflow-hidden">
                  <div class="w-full max-w-none overflow-auto max-h-96">
                    <div class="text-gray-800 leading-relaxed text-sm font-sans w-full prose prose-sm max-w-none" 
                         style="word-break: break-word; overflow-wrap: anywhere; max-width: 100%; font-family: inherit;"
                         [innerHTML]="getFormattedResponse()"></div>
                    
                    <!-- Streaming indicator at the end of content -->
                    <div *ngIf="isStreaming" class="flex items-center gap-2 mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                      <span class="text-sm text-blue-700 font-medium">Receiving response...</span>
                      <div class="flex gap-1 ml-2">
                        <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></div>
                        <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.2s"></div>
                        <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.4s"></div>
                      </div>
                    </div>
                  </div>
                </div>
                <div *ngIf="getResponseMetadata()" class="px-6 py-3 bg-blue-100 border-t border-blue-200">
                  <div class="text-xs text-blue-700 font-mono">{{ getResponseMetadata() }}</div>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="flex flex-wrap gap-3 mb-6">
                <button class="btn btn-secondary" (click)="exportReport()">
                  <i class="pi pi-download"></i>
                  Export Report
                </button>
                <button class="btn btn-secondary" (click)="createTicket()">
                  <i class="pi pi-ticket"></i>
                  Create Ticket
                </button>
                <button class="btn btn-secondary" (click)="scheduleReview()">
                  <i class="pi pi-calendar"></i>
                  Schedule Review
                </button>
                <button class="btn btn-secondary" (click)="shareResults()">
                  <i class="pi pi-share-alt"></i>
                  Share
                </button>
              </div>

              <!-- Rating System -->
              <div class="border-t border-gray-200 pt-6">
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <h4 class="text-sm font-medium text-gray-900 mb-2">Rate this response</h4>
                    <p class="text-xs text-gray-600 mb-3">Help improve template accuracy by rating the quality of this result</p>
                    
                    <div class="flex items-center gap-2">
                      <!-- Star Rating -->
                      <div class="flex items-center gap-1">
                        <button *ngFor="let star of [1,2,3,4,5]; trackBy: trackByIndex"
                                (click)="setRating(star)"
                                class="text-lg transition-colors duration-200"
                                [class]="star <= currentRating ? 'text-yellow-400 hover:text-yellow-500' : 'text-gray-300 hover:text-yellow-300'">
                          <i class="pi pi-star-fill"></i>
                        </button>
                      </div>
                      
                      <!-- Quick Rating Buttons -->
                      <div class="flex items-center gap-2 ml-4">
                        <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                                [class]="currentRating >= 4 ? 'bg-green-100 text-green-700 border-green-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-green-50'"
                                (click)="setRating(5)">
                          <i class="pi pi-check-circle mr-1"></i>
                          Correct
                        </button>
                        <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                                [class]="currentRating <= 2 ? 'bg-red-100 text-red-700 border-red-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-red-50'"
                                (click)="setRating(1)">
                          <i class="pi pi-times-circle mr-1"></i>
                          Incorrect
                        </button>
                      </div>
                      
                      <!-- Completion Status Buttons -->
                      <div class="flex items-center gap-2 ml-4 border-l border-gray-300 pl-4">
                        <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                                [class]="completionStatus === 'complete' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-blue-50'"
                                (click)="setCompletionStatus('complete')">
                          <i class="pi pi-check mr-1"></i>
                          Complete
                        </button>
                        <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                                [class]="completionStatus === 'incomplete' ? 'bg-orange-100 text-orange-700 border-orange-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-orange-50'"
                                (click)="setCompletionStatus('incomplete')">
                          <i class="pi pi-exclamation-triangle mr-1"></i>
                          Incomplete
                        </button>
                      </div>
                    </div>

                    <!-- Rating Feedback -->
                    <div *ngIf="currentRating > 0" class="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div class="flex items-center gap-2 text-sm">
                        <i class="pi pi-info-circle text-blue-600"></i>
                        <span class="text-blue-800">
                          <span *ngIf="currentRating >= 4">Thank you! This positive feedback helps improve template accuracy.</span>
                          <span *ngIf="currentRating === 3">Thank you for the feedback. We'll work to improve this template.</span>
                          <span *ngIf="currentRating <= 2">Thanks for reporting this issue. We'll review and improve this template.</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Rating Stats -->
                  <div class="text-right ml-6">
                    <div class="text-xs text-gray-500">Template Success Rate</div>
                    <div class="text-lg font-semibold" [class]="getSuccessRateClass(getCurrentTemplateSuccessRate())">
                      {{ getCurrentTemplateSuccessRate() }}%
                    </div>
                    <div class="text-xs text-gray-500">{{ getCurrentTemplateUsageCount() }} total uses</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  `,
  styles: [`
    .line-clamp-2 {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  `]
})
export class PromptTemplatesComponent implements OnInit, OnDestroy {
  @ViewChild('agentFrame') agentFrameRef?: ElementRef<HTMLIFrameElement>;

  // Mode toggle
  isAgentMode = false;
  
  // UI state - removed progressive steps
  
  // Results section
  showResults = false;
  isLoading = false;
  isStreaming = false;
  apiResponse: string = '';
  lastQuery: string = '';
  currentMsgUid: string = '';
  currentInstructionId: string = '';
  
  // Completion status tracking
  completionStatus: 'complete' | 'incomplete' | null = null;
  private msgUidCounter: number = 21; // Start from 21 as database has up to 20
  private instructionIdCounter: number = 21; // Start from 21 as database has up to 20
  private streamBuffer: string = '';
  private reader?: ReadableStreamDefaultReader<Uint8Array>;
  @ViewChild('resultsSection') resultsSectionRef?: ElementRef<HTMLDivElement>;
  
  // Enhanced features
  recentTemplates: Array<{label: string, category: string, index: number}> = [];
  queryHistory: Array<{query: string, response: string, timestamp: Date, status: string, msgUid?: string, instructionId?: string}> = [];
  showHistory = false;
  
  // Rating system
  currentRating = 0;
  hasRated = false;

  // Agent Mode properties
  iframeLoaded = false;
  agentUrl: string = AGENT_IFRAME_URL;
  agentUrlSafe!: SafeResourceUrl;
  private agentOrigin: string = AGENT_IFRAME_ORIGIN;
  loadNotice = false;
  private noticeTimer?: any;
  incomingPrompt: string | null = null;
  copied = false;
  showPromptToast = false;
  isMinimized = false;

  private onMessage = (event: MessageEvent) => {
    // Basic safety: only react to messages from the configured origin (if known)
    if (this.agentOrigin !== '*' && event.origin !== this.agentOrigin) return;
    // Placeholder: log any messages for future interop
    // console.debug('Agent iframe message:', event.data);
  };
  // Internal types
  previewParts: ({ type: 'text'; text: string } | { type: 'placeholder'; name: string })[] = [];
  currentPrompts: Array<{template: string, templateName?: string, usageCount: number, successRate: number, inputFields?: string[], originalTemplate?: PromptTemplate, isDynamic?: boolean}> = [];
  dynamicInputValues: { [key: string]: string } = {};
  // Instruction Types (Template Families) - populated from DB
  instructionTypes: Array<{ key: string; label: string; count: number }> = [];
  activeInstructionType = '';

  // Categories (template_category per family) - populated from DB
  categories: Array<{ key: string; label: string; count: number; instructionType: string; familyType: string; templateCategory: string }> = [];
  activeCategory = '';

  // Store all converted templates directly
  allConvertedTemplates: Array<{template: string, templateName?: string, usageCount: number, successRate: number, inputFields?: string[], originalTemplate?: PromptTemplate, isDynamic?: boolean, familyType: string, templateCategory: string}> = [];
  
  // Enhanced prompt template data with usage statistics and success rates (keeping for backward compatibility)
  promptsMap: Record<string, Array<{template: string, usageCount: number, successRate: number}>> = {};

  selectedPromptIndex = -1;

  // Form controls
  currencies: string[] = []; // Will be fetched from currency config table
  currency = 'SGD';
  amount: number | null = null;
  date: string = new Date().toISOString().split('T')[0]; // Default to today
  scopes = ['Branch', 'Subsidiary', 'Associate', 'TMU'];
  subsidiaryLevels = ['Entity', 'Subsidiary', 'Branch'];
  riskFactors = ['FX Rate', 'Interest Rate', 'Commodity', 'Equity'];
  genericOptions = ['Option A', 'Option B', 'Option C'];
  placeholderValues: Record<string, string> = {};

  constructor(
    private sanitizer: DomSanitizer, 
    private http: HttpClient,
    private currencyService: CurrencyService,
    private hawkAgentService: HawkAgentSimpleService,
    private promptTemplatesService: PromptTemplatesService,
    private optimizedDifyService: OptimizedDifyService,
    private githubPagesDifyService: GitHubPagesDifyService,
    private cdr: ChangeDetectorRef
  ) {}

  // Generate MSG_UID in format MSG_UID_0000
  private generateMsgUID(): string {
    const formattedNumber = this.msgUidCounter.toString().padStart(4, '0');
    const msgUid = `MSG_UID_${formattedNumber}`;
    this.msgUidCounter++;
    return msgUid;
  }

  // Generate instruction ID in format INST0000
  private generateInstructionId(): string {
    const formattedNumber = this.instructionIdCounter.toString().padStart(4, '0');
    const instructionId = `INST${formattedNumber}`;
    this.instructionIdCounter++;
    return instructionId;
  }

  // Initialize counters from localStorage to persist across sessions
  private initializeCounters() {
    const savedMsgUidCounter = localStorage.getItem('msgUidCounter');
    const savedInstructionIdCounter = localStorage.getItem('instructionIdCounter');
    
    this.msgUidCounter = savedMsgUidCounter ? parseInt(savedMsgUidCounter) : 21;
    this.instructionIdCounter = savedInstructionIdCounter ? parseInt(savedInstructionIdCounter) : 21;
  }

  // Save counters to localStorage
  private saveCounters() {
    localStorage.setItem('msgUidCounter', this.msgUidCounter.toString());
    localStorage.setItem('instructionIdCounter', this.instructionIdCounter.toString());
  }

  // Reset counters (for administrative use if needed)
  resetIdCounters(msgUidStart: number = 21, instructionIdStart: number = 21) {
    this.msgUidCounter = msgUidStart;
    this.instructionIdCounter = instructionIdStart;
    this.saveCounters();
    console.log(`ID counters reset: MSG_UID starts at ${msgUidStart}, INST starts at ${instructionIdStart}`);
  }

  ngOnInit() {
    // Initialize ID counters from localStorage
    this.initializeCounters();
    
    // Load currencies from service
    this.loadCurrencies();
    
    // Load templates from configuration database
    this.loadTemplatesFromDatabase();
    
    // Template mode initialization with hardcoded templates
    this.refreshPromptsForCategory();
    this.initPlaceholdersForSelectedPrompt();
    this.buildPreviewParts();

    // Agent mode initialization
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(this.agentUrl);
    window.addEventListener('message', this.onMessage);
    
    // Capture preset prompt from navigation state if present
    const state = (history?.state || {}) as any;
    if (state && typeof state.presetPrompt === 'string' && state.presetPrompt.trim()) {
      this.incomingPrompt = state.presetPrompt.trim();
      this.showPromptToast = true;
      this.isAgentMode = true; // Switch to agent mode when prompt is present
    }
    
    // Simplified: no iframe timing or warnings
  }

  ngOnDestroy() {
    window.removeEventListener('message', this.onMessage);
    if (this.noticeTimer) clearTimeout(this.noticeTimer);
    
    // Clean up streaming resources
    if (this.reader && !this.reader.closed) {
      try {
        this.reader.cancel();
      } catch (error) {
        console.warn('Reader cleanup error:', error);
      }
      this.reader = undefined;
    }
    this.isStreaming = false;
  }

  private loadCurrencies() {
    this.currencyService.getCurrencyCodes().subscribe({
      next: (currencyCodes) => {
        this.currencies = currencyCodes;
        // Update default currency if SGD is available
        if (currencyCodes.includes('SGD')) {
          this.currency = 'SGD';
        } else if (currencyCodes.length > 0) {
          this.currency = currencyCodes[0];
        }
      },
      error: (error) => {
        console.error('Error loading currencies:', error);
        // Fallback to default currencies if service fails
        this.currencies = ['USD', 'EUR', 'GBP', 'JPY', 'SGD', 'AUD'];
      }
    });
  }

  private async loadTemplatesFromDatabase() {
    try {
      // Subscribe to configuration templates and keep Template Mode in sync
      this.promptTemplatesService.templates$.subscribe((templates) => {
        if (Array.isArray(templates)) {
          this.updateTemplatesFromDatabase(templates);
        }
      });
      // Ensure initial load
      await this.promptTemplatesService.loadTemplates();
    } catch (err) {
      console.error('Failed to load templates from database:', err);
    }
  }

  private updateTemplatesFromDatabase(templates: PromptTemplate[]) {
    // Reset everything
    this.allConvertedTemplates = [];
    this.categories = [];
    this.instructionTypes = [];

    // Step 1: Convert all templates to our format and store them
    const activeTemplates = templates.filter(t => t.status === 'active');
    
    this.allConvertedTemplates = activeTemplates.map(template => {
      const derivedFields = (template.input_fields && template.input_fields.length > 0)
        ? template.input_fields
        : (template.prompt_text ? this.promptTemplatesService.getInputFields(template.prompt_text) : []);
      
      return {
        template: template.prompt_text || template.name || 'No prompt text available',
        templateName: template.name || 'Unnamed Template',
        usageCount: template.usage_count || 0,
        successRate: 85,
        inputFields: derivedFields || [],
        originalTemplate: template,
        isDynamic: (derivedFields && derivedFields.length > 0) ||
                   (template.prompt_text ? /\{\{[^}]+\}\}/.test(template.prompt_text) : false),
        familyType: template.family_type,
        templateCategory: template.template_category || 'general'
      };
    });

    // Step 2: Build instruction types from unique family types
    const uniqueFamilies = [...new Set(activeTemplates.map(t => t.family_type))];
    this.instructionTypes = uniqueFamilies.map(family => ({
      key: this.normalizeKeySegment(family),
      label: this.formatFamilyLabel(family),
      count: activeTemplates.filter(t => t.family_type === family).length
    }));

    // Step 3: Build categories from unique family+category combinations
    const uniqueCategories = new Map<string, {familyType: string, templateCategory: string, count: number}>();
    
    activeTemplates.forEach(template => {
      const key = `${template.family_type}__${template.template_category || 'general'}`;
      if (!uniqueCategories.has(key)) {
        uniqueCategories.set(key, {
          familyType: template.family_type,
          templateCategory: template.template_category || 'general',
          count: 0
        });
      }
      const category = uniqueCategories.get(key)!;
      category.count++;
    });

    this.categories = Array.from(uniqueCategories.entries()).map(([key, data]) => ({
      key,
      label: this.formatCategoryLabel(data.templateCategory),
      count: data.count,
      instructionType: this.normalizeKeySegment(data.familyType),
      familyType: data.familyType,
      templateCategory: data.templateCategory
    }));

    // Step 4: Set initial active states
    if (!this.activeInstructionType || !this.instructionTypes.some(t => t.key === this.activeInstructionType)) {
      this.activeInstructionType = this.instructionTypes[0]?.key || '';
    }

    const familyCategories = this.getCurrentCategories();
    if (!this.activeCategory || !familyCategories.some(c => c.key === this.activeCategory)) {
      this.activeCategory = familyCategories[0]?.key || '';
    }
    
    // Step 5: Load current prompts
    this.refreshPromptsForCategory();
    
    if (this.currentPrompts.length > 0) {
      this.selectedPromptIndex = 0;
      this.initPlaceholdersForSelectedPrompt();
      this.buildPreviewParts();
    }
  }

  // Removed - no longer needed with simplified approach

  private formatFamilyLabel(family: string): string {
    const map: Record<string, string> = {
      hedge_accounting: 'Hedge Accounting',
      risk_management: 'Risk Management',
      compliance: 'Compliance',
      reporting: 'Reporting',
      analysis: 'Analysis',
      operations: 'Operations'
    };
    return map[family] || this.formatCategoryLabel(family);
  }

  // Removed - no longer needed with simplified approach

  private formatCategoryLabel(category: string): string {
    return category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }

  private ensureActiveCategoryForFamily() {
    const familyCategories = this.getCurrentCategories();
    if (!familyCategories || familyCategories.length === 0) {
      this.activeCategory = '';
      return;
    }
    // If current activeCategory doesn't belong to this family or is empty, switch to the first
    const belongs = this.activeCategory && familyCategories.some(c => c.key === this.activeCategory);
    if (!belongs) {
      this.activeCategory = familyCategories[0].key;
    }
  }

  // Key normalization to make category selection robust across labels/casing/spaces
  private normalizeKeySegment(seg: string): string {
    return (seg || '')
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '_');
  }

  // Removed - no longer needed with simplified approach

  private getFamilyTypeForInstructionType(instructionType: string): string {
    // Map instruction types back to family types
    const instructionToFamily: { [key: string]: string } = {
      'instructions': 'hedge_accounting',
      'monitoring': 'risk_management',
      'risk': 'compliance',
      'analysis': 'reporting',
      'resolution': 'operations',
      'setup': 'operations'
    };
    
    return instructionToFamily[instructionType] || instructionType;
  }

  private getCategoryKeyForFamilyType(familyType: string): string | null {
    // This method is deprecated - using getCategoryKeyForTemplate instead
    return null;
  }

  // Removed - no longer needed with simplified approach

  private refreshPromptsForCategory() {
    // Find the active category object
    const activeCategoryObj = this.categories.find(c => c.key === this.activeCategory);
    if (!activeCategoryObj) {
      this.currentPrompts = [];
      this.cdr.detectChanges();
      return;
    }
    
    // Filter templates directly from allConvertedTemplates
    const newPrompts = this.allConvertedTemplates.filter(template => {
      return template.familyType === activeCategoryObj.familyType && 
             template.templateCategory === activeCategoryObj.templateCategory;
    });
    
    // Force array reference change to trigger Angular change detection
    this.currentPrompts = [...newPrompts];
    
    console.log(`✓ Updated category "${this.activeCategory}" -> ${this.currentPrompts.length} templates:`, 
                this.currentPrompts.map(p => p.templateName));
    
    // Force change detection immediately
    this.cdr.detectChanges();
    
    // Calculate real usage stats from database
    this.calculateRealUsageStats();
  }

  get selectedPromptBase(): string {
    const list = this.currentPrompts;
    return list[this.selectedPromptIndex]?.template || '';
  }

  selectPrompt(i: number) {
    this.selectedPromptIndex = i;
    this.initPlaceholdersForSelectedPrompt(true);
    this.buildPreviewParts();
    
    // Initialize dynamic input values for database templates
    if (this.isSelectedTemplateDynamic()) {
      const inputFields = this.getSelectedTemplateInputFields();
      this.dynamicInputValues = {};
      inputFields.forEach(field => {
        this.dynamicInputValues[field] = '';
      });
    }
  }

  selectFirstPrompt() {
    this.selectedPromptIndex = 0;
    this.initPlaceholdersForSelectedPrompt(true);
    this.buildPreviewParts();
    
    // Initialize dynamic input values for database templates
    if (this.isSelectedTemplateDynamic()) {
      const inputFields = this.getSelectedTemplateInputFields();
      this.dynamicInputValues = {};
      inputFields.forEach(field => {
        this.dynamicInputValues[field] = '';
      });
    }
  }

  // Build inline preview tokens replacing placeholders with input controls
  private buildPreviewParts() {
    const base = this.isSelectedTemplateDynamic()
      ? this.getSelectedTemplateText()
      : this.selectedPromptBase;
    // Detect placeholder syntax present in the template
    let regex: RegExp;
    if (/\{\{[^}]+\}\}/.test(base)) {
      regex = /\{\{([^}]+)\}\}/g; // {{field}}
    } else {
      regex = /\[([^\]]+)\]/g;     // [field]
    }
    const parts: ({ type: 'text'; text: string } | { type: 'placeholder'; name: string })[] = [];
    let lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = regex.exec(base)) !== null) {
      if (m.index > lastIndex) {
        parts.push({ type: 'text', text: base.slice(lastIndex, m.index) });
      }
      const name = m[1].trim().toLowerCase();
      parts.push({ type: 'placeholder', name });
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < base.length) {
      parts.push({ type: 'text', text: base.slice(lastIndex) });
    }
    this.previewParts = parts;
  }

  getOptionsFor(name: string): string[] {
    switch (name) {
      case 'currency':
        return this.currencies;
      case 'entity scope':
      case 'scope':
        return this.scopes;
      case 'subsidiary level':
        return this.subsidiaryLevels;
      case 'risk factor':
        return this.riskFactors;
      default:
        return this.genericOptions;
    }
  }

  private initPlaceholdersForSelectedPrompt(resetNonAmount: boolean = false) {
    const base = this.isSelectedTemplateDynamic()
      ? this.getSelectedTemplateText()
      : this.selectedPromptBase;
    const regex = /\{\{([^}]+)\}\}|\[([^\]]+)\]/g; // support both {{}} and []
    const present: Record<string, true> = {};
    let m: RegExpExecArray | null;
    while ((m = regex.exec(base)) !== null) {
      const name = (m[1] || m[2] || '').trim();
      const lowerName = name.toLowerCase();
      present[lowerName] = true;
      if (this.isSelectedTemplateDynamic()) {
        // Initialize dynamic input values map using original case
        if (!this.dynamicInputValues[name]) {
          this.dynamicInputValues[name] = '';
        }
      } else {
        if (lowerName !== 'amount' && !this.placeholderValues[lowerName]) {
          const opts = this.getOptionsFor(lowerName);
          this.placeholderValues[lowerName] = opts[0] ?? '';
        }
      }
    }
    // Clean up stale placeholders when switching prompts/categories
    if (resetNonAmount) {
      if (this.isSelectedTemplateDynamic()) {
        Object.keys(this.dynamicInputValues).forEach(k => {
          // Check lowercase version for dynamic templates
          if (!present[k.toLowerCase()]) {
            delete this.dynamicInputValues[k];
          }
        });
      } else {
        Object.keys(this.placeholderValues).forEach(k => {
          if (k !== 'amount' && !present[k]) {
            delete this.placeholderValues[k];
          }
        });
      }
    }
  }

  usePrompt() {
    let preview: string;
    
    // Handle dynamic templates
    if (this.isSelectedTemplateDynamic()) {
      preview = this.getFilledTemplate();
    } else {
      // Handle static templates (existing logic)
      preview = this.previewParts
        .map(part => {
          if (part.type === 'text') return part.text;
          if (part.name === 'amount') return (this.amount ?? 0).toFixed(2);
          if (part.name === 'date') return this.date;
          return this.placeholderValues[part.name] ?? '';
        })
        .join('');
    }
    
    // Generate unique identifiers for this request
    this.currentMsgUid = this.generateMsgUID();
    this.currentInstructionId = this.generateInstructionId();
    
    // Save updated counters
    this.saveCounters();
    
    // Create database session
    this.createDatabaseSession(preview);
    
    this.lastQuery = preview;
    this.showResults = true;
    this.isLoading = true;
    this.apiResponse = '';
    
    // Auto-scroll to results section
    this.scrollToResults();
    
    // Reset rating for new query
    this.currentRating = 0;
    this.hasRated = false;
    
    // Update usage count
    this.updateUsageCount();
    
    // Add to recent templates
    this.addToRecentTemplates();
    
    // Send to Dify API with identifiers
    this.sendToDifyAgent(preview);
  }

  private async createDatabaseSession(promptText: string) {
    try {
      console.log('Creating database session with:', {
        promptText,
        msgUid: this.currentMsgUid,
        instructionId: this.currentInstructionId
      });
      
      await this.hawkAgentService.createSession(
        promptText, 
        this.currentMsgUid, 
        this.currentInstructionId,
        this.activeCategory,
        this.selectedPromptIndex + 1  // Convert to 1-based index
      );
      console.log('Database session created successfully');
    } catch (error) {
      console.error('Error creating database session:', error);
    }
  }

  private async updateDatabaseSession(status: 'completed' | 'failed', conversationId?: string, taskId?: string, tokenUsage?: any) {
    try {
      console.log('Updating database session:', {
        msgUid: this.currentMsgUid,
        status,
        conversationId,
        taskId,
        tokenUsage
      });
      
      const updates: any = {
        agent_status: status,
        agent_response: {
          text: this.apiResponse,
          conversation_id: conversationId,
          task_id: taskId,
          ...(tokenUsage && {
            input_tokens: tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0,
            output_tokens: tokenUsage.output_tokens || tokenUsage.completion_tokens || 0,
            total_tokens: tokenUsage.total_tokens || (tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0) + (tokenUsage.output_tokens || tokenUsage.completion_tokens || 0),
            usage: tokenUsage
          })
        }
      };
      
      await this.hawkAgentService.updateSession(this.currentMsgUid, updates);
      console.log('Database session updated successfully');
    } catch (error) {
      console.error('Error updating database session:', error);
    }
  }

  private sendToDifyAgent(query: string) {
    // Use GitHub Pages compatible optimization
    const params = {
      query: query,
      msgUid: this.currentMsgUid,
      instructionId: this.currentInstructionId,
      exposureCurrency: this.extractExposureCurrency(query) || 'USD',
      hedgeMethod: this.extractHedgeMethod(query) || undefined,
      navType: this.extractNavType(query) || undefined,
      useOptimization: true // Enable client-side optimization
    };

    console.log('🚀 Using GitHub Pages optimization for query:', params);

    // Reset streaming state
    this.streamBuffer = '';
    this.apiResponse = '';
    this.isStreaming = true;
    this.isLoading = false;

    this.githubPagesDifyService.sendOptimizedDifyRequest(params).subscribe({
      next: (response) => {
        console.log('✅ GitHub Pages optimization response:', response);
        
        if (response.success && response.response) {
          // Process the response
          this.apiResponse = response.response.answer || '';
          
          // Log detailed performance metrics
          console.log('📊 GitHub Pages Performance Metrics:', {
            totalTime: `${response.metrics.total_time_ms}ms`,
            dataFetchTime: `${response.metrics.data_fetch_time_ms}ms`,
            contextPrepTime: `${response.metrics.context_prep_time_ms}ms`,
            difyTime: `${response.metrics.dify_response_time_ms}ms`,
            dataReduction: `${response.context_reduction.toFixed(1)}%`,
            cacheUsed: response.cache_used ? '💾 Cache Hit' : '🔄 Fresh Data',
            optimizationApplied: response.optimization_applied ? '⚡ Optimized' : '🔄 Direct Call'
          });
          
          // Update database session
          this.updateDatabaseSession(
            'completed', 
            response.response.conversation_id,
            response.response.task_id,
            response.response.usage
          );
        } else {
          console.error('❌ GitHub Pages optimization failed:', response.error);
          this.handleDifyError(response.error || 'Unknown error');
        }
        
        this.isStreaming = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('❌ GitHub Pages Dify service error:', error);
        this.handleDifyError(error.message || 'GitHub Pages optimization failed');
      }
    });
  }

  // Legacy methods kept for reference but now using GitHub Pages optimization
  
  private sendLegacyDifyRequest(query: string) {
    const headers = new HttpHeaders({
      'Authorization': 'Bearer app-KKtaMynVyn8tKbdV9VbbaeyR',
      'Content-Type': 'application/json'
    });

    // Enhanced prompt with unique identifiers
    const enhancedQuery = `[MSG_UID: ${this.currentMsgUid}] [INSTRUCTION_ID: ${this.currentInstructionId}] ${query}`;

    const payload = {
      conversation_id: '',
      inputs: {
        msg_uid: this.currentMsgUid,
        instruction_id: this.currentInstructionId
      },
      query: enhancedQuery,
      user: 'test-user',
      response_mode: 'streaming'
    };

    // Reset streaming state
    this.streamBuffer = '';
    this.apiResponse = '';
    this.isStreaming = true;
    
    console.log('🔄 Using legacy Dify integration...');
    
    // Use fetch for proper streaming support
    fetch('https://api.dify.ai/v1/chat-messages', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer app-KKtaMynVyn8tKbdV9VbbaeyR',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      if (!response.body) {
        throw new Error('Response body is null');
      }

      this.isLoading = false; // Stop initial loading
      const reader = response.body.getReader();
      this.reader = reader;
      
      return this.processStream(reader);
    }).catch(error => {
      console.error('Error sending to Dify:', error);
      this.isLoading = false;
      this.isStreaming = false;
      this.apiResponse = `Error: ${error.message}\n\nPlease check your network connection and API configuration.`;
    });
  }

  private async processStream(reader: ReadableStreamDefaultReader<Uint8Array>) {
    const decoder = new TextDecoder();
    let conversationId = '';
    let taskId = '';
    let buffer = '';
    let tokenUsage: any = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('Stream completed');
          this.isStreaming = false;
          this.finishStream(conversationId, taskId, tokenUsage);
          break;
        }

        // Decode the chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonData = JSON.parse(line.substring(6));
              
              // Extract conversation details
              if (!conversationId && jsonData.conversation_id) {
                conversationId = jsonData.conversation_id;
              }
              if (!taskId && jsonData.task_id) {
                taskId = jsonData.task_id;
              }

              // Process streaming content
              if (jsonData.event === 'agent_message' && jsonData.answer) {
                this.streamBuffer += jsonData.answer;
                this.apiResponse = this.streamBuffer;
              }
              
              // Capture token usage information
              if (jsonData.metadata?.usage || jsonData.usage) {
                tokenUsage = jsonData.metadata?.usage || jsonData.usage;
                console.log('Token usage captured:', tokenUsage);
              }
              
              // Handle stream completion events
              if (jsonData.event === 'message_end' || jsonData.event === 'workflow_finished') {
                console.log('Stream end event received:', jsonData.event);
                console.log('Final token usage:', tokenUsage);
                this.isStreaming = false;
                this.finishStream(conversationId, taskId, tokenUsage);
                return;
              }
              
            } catch (parseError) {
              console.warn('Failed to parse streaming data line:', line, parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream processing error:', error);
      this.isStreaming = false;
      this.apiResponse += '\n\n[Stream interrupted due to error]';
      
      // Update database session as failed
      this.updateDatabaseSession('failed', conversationId, taskId, tokenUsage);
    } finally {
      reader.releaseLock();
    }
  }

  private finishStream(conversationId: string, taskId: string, tokenUsage?: any) {
    // Add metadata including our unique identifiers
    let metadata = '\n\n---\n';
    metadata += `Message UID: ${this.currentMsgUid}\n`;
    metadata += `Instruction ID: ${this.currentInstructionId}\n`;
    if (conversationId) metadata += `Conversation ID: ${conversationId}\n`;
    if (taskId) metadata += `Task ID: ${taskId}`;
    
    // Add token information if available
    if (tokenUsage) {
      metadata += `\nInput Tokens: ${tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0}`;
      metadata += `\nOutput Tokens: ${tokenUsage.output_tokens || tokenUsage.completion_tokens || 0}`;
      metadata += `\nTotal Tokens: ${tokenUsage.total_tokens || (tokenUsage.input_tokens || tokenUsage.prompt_tokens || 0) + (tokenUsage.output_tokens || tokenUsage.completion_tokens || 0)}`;
    }
    
    this.apiResponse += metadata;
    
    // Update database session as completed
    this.updateDatabaseSession('completed', conversationId, taskId, tokenUsage);
    
    // Add to history with identifiers
    this.addToHistory(this.lastQuery, this.apiResponse);
  }

  clearResults() {
    this.showResults = false;
    this.apiResponse = '';
    this.lastQuery = '';
    this.currentMsgUid = '';
    this.currentInstructionId = '';
    this.isLoading = false;
    this.isStreaming = false;
    this.streamBuffer = '';
    this.currentRating = 0;
    this.hasRated = false;
    
    // Cancel ongoing stream if any
    if (this.reader && !this.reader.closed) {
      try {
        this.reader.cancel();
      } catch (error) {
        console.warn('Reader cleanup error in clearResults:', error);
      }
      this.reader = undefined;
    }
  }

  getCleanResponse(): string {
    if (!this.apiResponse) return '';
    
    // Split by the metadata separator
    const parts = this.apiResponse.split('\n\n---\n');
    return parts[0] || this.apiResponse;
  }

  getFormattedResponse(): SafeHtml {
    if (!this.apiResponse) return this.sanitizer.bypassSecurityTrustHtml('');
    
    const cleanResponse = this.getCleanResponse();
    
    // Convert **text** to <strong>text</strong>
    let formattedText = cleanResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert table-like structures (|...| format) to HTML tables
    formattedText = this.convertTablesToHtml(formattedText);
    
    // Escape other HTML but preserve our strong tags, tables, and line breaks
    const escapedText = formattedText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      // Restore our HTML elements
      .replace(/&lt;strong&gt;(.*?)&lt;\/strong&gt;/g, '<strong>$1</strong>')
      .replace(/&lt;table([^&]*)&gt;/g, '<table$1>')
      .replace(/&lt;\/table&gt;/g, '</table>')
      .replace(/&lt;thead([^&]*)&gt;/g, '<thead$1>')
      .replace(/&lt;\/thead&gt;/g, '</thead>')
      .replace(/&lt;tbody([^&]*)&gt;/g, '<tbody$1>')
      .replace(/&lt;\/tbody&gt;/g, '</tbody>')
      .replace(/&lt;tr([^&]*)&gt;/g, '<tr$1>')
      .replace(/&lt;\/tr&gt;/g, '</tr>')
      .replace(/&lt;th([^&]*)&gt;/g, '<th$1>')
      .replace(/&lt;\/th&gt;/g, '</th>')
      .replace(/&lt;td([^&]*)&gt;/g, '<td$1>')
      .replace(/&lt;\/td&gt;/g, '</td>')
      // Convert line breaks to <br> tags
      .replace(/\n/g, '<br>');
    
    return this.sanitizer.bypassSecurityTrustHtml(escapedText);
  }

  private convertTablesToHtml(text: string): string {
    // Split text into lines for processing
    const lines = text.split('\n');
    let result = '';
    let inTable = false;
    let tableRows = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Check if this line looks like a table row (starts and ends with |)
      if (line.startsWith('|') && line.endsWith('|') && line.includes('|')) {
        if (!inTable) {
          inTable = true;
          tableRows = [];
        }
        
        // Parse the row
        const cells = line.split('|').slice(1, -1).map(cell => cell.trim());
        tableRows.push(cells);
        
        // Check if next line is a separator (|---|---|)
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
        const isSeparator = nextLine.match(/^\|[\s\-:]+\|$/);
        
        // If this is the end of table or separator line, convert to HTML
        if (i === lines.length - 1 || !lines[i + 1].trim().startsWith('|') || isSeparator) {
          if (isSeparator) i++; // Skip separator line
          
          // Convert to HTML table
          let tableHtml = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
          
          // Header row (first row)
          if (tableRows.length > 0) {
            tableHtml += '<thead class="bg-gray-50">';
            tableHtml += '<tr>';
            tableRows[0].forEach(cell => {
              tableHtml += `<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">${cell}</th>`;
            });
            tableHtml += '</tr>';
            tableHtml += '</thead>';
          }
          
          // Body rows (remaining rows)
          if (tableRows.length > 1) {
            tableHtml += '<tbody class="bg-white divide-y divide-gray-200">';
            for (let j = 1; j < tableRows.length; j++) {
              tableHtml += '<tr class="hover:bg-gray-50">';
              tableRows[j].forEach(cell => {
                tableHtml += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${cell}</td>`;
              });
              tableHtml += '</tr>';
            }
            tableHtml += '</tbody>';
          }
          
          tableHtml += '</table>';
          result += tableHtml;
          
          inTable = false;
          tableRows = [];
        }
      } else {
        // Not a table line
        if (inTable) {
          // End of table without proper formatting - add accumulated rows as table
          if (tableRows.length > 0) {
            let tableHtml = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
            tableHtml += '<tbody class="bg-white divide-y divide-gray-200">';
            tableRows.forEach(row => {
              tableHtml += '<tr class="hover:bg-gray-50">';
              row.forEach(cell => {
                tableHtml += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${cell}</td>`;
              });
              tableHtml += '</tr>';
            });
            tableHtml += '</tbody>';
            tableHtml += '</table>';
            result += tableHtml;
          }
          inTable = false;
          tableRows = [];
        }
        result += line + '\n';
      }
    }
    
    return result;
  }

  getResponseMetadata(): string {
    if (!this.apiResponse) return '';
    
    // Split by the metadata separator and get the metadata part
    const parts = this.apiResponse.split('\n\n---\n');
    if (parts.length > 1) {
      return parts[1].trim();
    }
    return '';
  }

  // Removed progressive UI methods - now single-step interface

  getCategoryLabel(key: string): string {
    const category = this.categories.find(c => c.key === key);
    return category ? category.label : key;
  }

  isFormValid(): boolean {
    // Handle dynamic templates
    if (this.isSelectedTemplateDynamic()) {
      const inputFields = this.getSelectedTemplateInputFields();
      return inputFields.every(field => {
        const value = this.dynamicInputValues[field];
        // Handle both strings and numbers
        return value !== null && value !== undefined && (
          (typeof value === 'string' && value.trim() !== '') ||
          (typeof value === 'number' && !isNaN(value))
        );
      });
    }
    
    // Handle static templates (existing logic)
    const placeholderParts = this.previewParts.filter(p => p.type === 'placeholder') as Array<{type: 'placeholder', name: string}>;
    const hasAmount = placeholderParts.some(p => p.name === 'amount') ? this.amount !== null && this.amount > 0 : true;
    const hasDate = placeholderParts.some(p => p.name === 'date') ? !!this.date : true;
    const hasOtherFields = placeholderParts
      .filter(p => p.name !== 'amount' && p.name !== 'date')
      .every(p => this.placeholderValues[p.name]);
    
    return hasAmount && hasDate && hasOtherFields;
  }

  getPlaceholderParts(): Array<{type: 'placeholder', name: string}> {
    return this.previewParts.filter(p => p.type === 'placeholder') as Array<{type: 'placeholder', name: string}>;
  }

  getCurrentDateTime(): string {
    return new Date().toLocaleString();
  }

  formatDate(date: Date): string {
    return date.toLocaleString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  // Status and Visual Methods
  getResultStatus(): string {
    if (!this.apiResponse) return 'Processing';
    
    const response = this.getCleanResponse().toLowerCase();
    if (response.includes('approved') || response.includes('confirmed')) return 'Approved';
    if (response.includes('rejected') || response.includes('denied')) return 'Rejected';
    if (response.includes('pending') || response.includes('review')) return 'Pending Review';
    return 'Completed';
  }

  getStatusBadgeClass(): string {
    const status = this.getResultStatus();
    switch (status) {
      case 'Approved': return 'bg-green-100 text-green-800 border border-green-200';
      case 'Rejected': return 'bg-red-100 text-red-800 border border-red-200';
      case 'Pending Review': return 'bg-yellow-100 text-yellow-800 border border-yellow-200';
      default: return 'bg-blue-100 text-blue-800 border border-blue-200';
    }
  }

  getStatusIcon(): string {
    const status = this.getResultStatus();
    switch (status) {
      case 'Approved': return 'pi pi-check-circle';
      case 'Rejected': return 'pi pi-times-circle';
      case 'Pending Review': return 'pi pi-clock';
      default: return 'pi pi-info-circle';
    }
  }

  // Recent Templates Methods
  addToRecentTemplates() {
    const recent = {
      label: `Template ${this.selectedPromptIndex + 1}`,
      category: this.activeCategory,
      index: this.selectedPromptIndex
    };
    
    // Remove if already exists
    this.recentTemplates = this.recentTemplates.filter(r => 
      !(r.category === recent.category && r.index === recent.index)
    );
    
    // Add to beginning
    this.recentTemplates.unshift(recent);
    
    // Keep only last 5
    this.recentTemplates = this.recentTemplates.slice(0, 5);
  }

  loadRecentTemplate(recent: {label: string, category: string, index: number}) {
    this.activeCategory = recent.category;
    this.refreshPromptsForCategory();
    this.selectedPromptIndex = recent.index;
    this.selectPrompt(recent.index);
  }

  // History Methods
  addToHistory(query: string, response: string) {
    const historyItem = {
      query,
      response,
      timestamp: new Date(),
      status: this.getResultStatus(),
      msgUid: this.currentMsgUid,
      instructionId: this.currentInstructionId
    };
    
    this.queryHistory.unshift(historyItem);
    
    // Keep only last 20 items
    this.queryHistory = this.queryHistory.slice(0, 20);
  }

  toggleHistory() {
    this.showHistory = !this.showHistory;
  }

  loadHistoryItem(item: any) {
    this.lastQuery = item.query;
    this.apiResponse = item.response;
    this.currentMsgUid = item.msgUid || '';
    this.currentInstructionId = item.instructionId || '';
    this.showResults = true;
    this.showHistory = false;
  }

  getHistoryStatusClass(status: string): string {
    switch (status) {
      case 'Approved': return 'bg-green-100 text-green-800';
      case 'Rejected': return 'bg-red-100 text-red-800';
      case 'Pending Review': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  }

  // Action Methods (Placeholder implementations)
  saveAsTemplate() {
    // TODO: Implement save template functionality
    console.log('Save template clicked');
  }

  exportReport() {
    // TODO: Implement export functionality
    console.log('Export report clicked');
  }

  createTicket() {
    // TODO: Implement create ticket functionality
    console.log('Create ticket clicked');
  }

  scheduleReview() {
    // TODO: Implement schedule review functionality
    console.log('Schedule review clicked');
  }

  shareResults() {
    // TODO: Implement share functionality
    console.log('Share results clicked');
  }

  async setCompletionStatus(status: 'complete' | 'incomplete') {
    this.completionStatus = status;
    
    try {
      // Update the current session status directly
      if (this.currentMsgUid && this.currentInstructionId) {
        const sessions = await this.hawkAgentService.getSessions();
        const currentSession = sessions.find(s => s.msg_uid === this.currentMsgUid);
        
        if (currentSession) {
          // Set agent_status to completed or failed based on completion status
          const agentStatus = status === 'complete' ? 'completed' : 'failed';
          
          // Update session with new status and completion metadata
          const updatedMetadata = {
            ...currentSession.metadata,
            completion_status: status,
            completion_date: new Date().toISOString(),
            user_marked: true
          };
          
          // Update the session in the database
          await this.hawkAgentService.updateSession(this.currentMsgUid, { 
            agent_status: agentStatus, 
            metadata: updatedMetadata 
          });
          
          console.log(`Task marked as ${status}, agent_status updated to ${agentStatus}`);
          
          // Update template success metrics
          this.updateTemplateMetricsFromCompletion(status);
        }
      }
      
      // Refresh the usage stats to reflect the completion
      await this.calculateRealUsageStats();
    } catch (error) {
      console.error('Error saving completion status:', error);
    }
  }
  
  updateTemplateMetricsFromCompletion(status: 'complete' | 'incomplete') {
    if (this.selectedPromptIndex >= 0 && this.currentPrompts[this.selectedPromptIndex]) {
      const template = this.currentPrompts[this.selectedPromptIndex];
      const isSuccess = status === 'complete';
      
      // Don't update usage count here - it will be updated by calculateRealUsageStats()
      // Just temporarily update the success rate for immediate UI feedback
      const currentSuccesses = Math.round((template.successRate * template.usageCount) / 100);
      const newSuccesses = currentSuccesses + (isSuccess ? 1 : 0);
      const newUsageCount = template.usageCount + 1;
      template.successRate = Math.round((newSuccesses / newUsageCount) * 100);
      template.usageCount = newUsageCount;
      
      // Update master data
      this.updateMasterTemplateData('both');
    }
  }

  // Rating System Methods
  setRating(rating: number) {
    this.currentRating = rating;
    if (!this.hasRated) {
      this.hasRated = true;
      this.updateSuccessRate(rating);
    }
  }

  updateUsageCount() {
    if (this.selectedPromptIndex >= 0 && this.currentPrompts[this.selectedPromptIndex]) {
      this.currentPrompts[this.selectedPromptIndex].usageCount++;
      // Update the master data
      this.updateMasterTemplateData('usage');
    }
  }

  updateSuccessRate(rating: number) {
    if (this.selectedPromptIndex >= 0 && this.currentPrompts[this.selectedPromptIndex]) {
      const template = this.currentPrompts[this.selectedPromptIndex];
      const currentTotal = template.usageCount * template.successRate / 100;
      const isSuccessful = rating >= 4 ? 1 : 0; // 4-5 stars considered successful
      const newTotal = currentTotal + isSuccessful;
      const newSuccessRate = Math.round((newTotal / template.usageCount) * 100);
      
      template.successRate = newSuccessRate;
      // Update the master data
      this.updateMasterTemplateData('success');
    }
  }

  updateMasterTemplateData(_type: 'usage' | 'success' | 'both') {
    // Update the master promptsMap with current data
    if (this.selectedPromptIndex >= 0) {
      const currentTemplate = this.currentPrompts[this.selectedPromptIndex];
      if (currentTemplate) {
        this.promptsMap[this.activeCategory][this.selectedPromptIndex] = { ...currentTemplate };
      }
    }
  }

  getCurrentTemplateSuccessRate(): number {
    if (this.selectedPromptIndex >= 0 && this.currentPrompts[this.selectedPromptIndex]) {
      return this.currentPrompts[this.selectedPromptIndex].successRate;
    }
    return 0;
  }

  getCurrentTemplateUsageCount(): number {
    if (this.selectedPromptIndex >= 0 && this.currentPrompts[this.selectedPromptIndex]) {
      return this.currentPrompts[this.selectedPromptIndex].usageCount;
    }
    return 0;
  }

  private scrollToResults() {
    // Use setTimeout to ensure DOM has updated
    setTimeout(() => {
      const element = this.resultsSectionRef?.nativeElement;
      if (element) {
        // Try multiple scroll methods for better compatibility
        element.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start',
          inline: 'nearest'
        });
        
        // Fallback method
        setTimeout(() => {
          try {
            const rect = element.getBoundingClientRect();
            const offset = window.scrollY + rect.top - 100; // 100px offset from top
            window.scrollTo({
              top: offset,
              behavior: 'smooth'
            });
          } catch (e) {
            // Last resort - simple scroll
            element.scrollIntoView();
          }
        }, 50);
      }
    }, 300); // Increased delay to ensure Results section is fully rendered
  }

  // UI handlers and trackBy helpers
  onInstructionTypeSelect(key: string) {
    if (this.activeInstructionType === key) return;
    this.activeInstructionType = key;
    this.ensureActiveCategoryForFamily();
    this.refreshPromptsForCategory();
    if (this.currentPrompts.length > 0) {
      this.selectFirstPrompt();
    } else {
      this.selectedPromptIndex = -1;
    }
  }

  onCategorySelect(key: string) {
    if (this.activeCategory === key) {
      return;
    }
    
    console.log(`🔄 Category changed: "${this.activeCategory}" -> "${key}"`);
    this.activeCategory = key;
    
    // Reset selection first
    this.selectedPromptIndex = -1;
    
    // Refresh templates for the new category
    this.refreshPromptsForCategory();
    
    // Select first prompt if available
    if (this.currentPrompts.length > 0) {
      this.selectFirstPrompt();
    }
    
    // Force additional change detection to ensure UI updates
    this.cdr.detectChanges();
  }

  getCurrentCategories() {
    return this.categories.filter(c => c.instructionType === this.activeInstructionType);
  }

  getCategoryTabClass(categoryKey: string): string {
    if (this.activeCategory === categoryKey) {
      return 'bg-blue-600 text-white shadow-lg transform scale-105';
    }
    return 'bg-white text-gray-700 hover:bg-blue-50 hover:text-blue-700 shadow-sm';
  }

  getSelectedCategoryLabel(): string {
    const category = this.categories.find(c => c.key === this.activeCategory);
    return category ? category.label : 'Select a Category';
  }

  getSelectedInstructionTypeLabel(): string {
    const type = this.instructionTypes.find(t => t.key === this.activeInstructionType);
    return type ? type.label : '';
  }

  getSuccessRateClass(rate: number): string {
    if (rate >= 95) return 'text-green-600';
    if (rate >= 90) return 'text-blue-600';
    if (rate >= 85) return 'text-yellow-600';
    return 'text-red-600';
  }


  formatUsageCount(count: number): string {
    if (count >= 1000) return Math.floor(count / 1000) + 'K';
    return count.toString();
  }

  getTemplatePreview(template: string): string {
    // Truncate template text for preview, preserving word boundaries
    const maxLength = 120;
    if (template.length <= maxLength) return template;
    
    const truncated = template.substring(0, maxLength);
    const lastSpace = truncated.lastIndexOf(' ');
    if (lastSpace > maxLength * 0.8) {
      return truncated.substring(0, lastSpace) + '...';
    }
    return truncated + '...';
  }

  async calculateRealUsageStats() {
    try {
      const sessions = await this.hawkAgentService.getSessions();
      console.log('All sessions from database:', sessions);
      
      // Update usage counts and success rates for current category
      this.currentPrompts.forEach((prompt, index) => {
        // Filter sessions that match current category and this specific template index
        const matchingSessions = sessions.filter(session => {
          // Check if session template_category matches current category and template_index matches current index
          const categoryMatch = session.template_category === this.activeCategory;
          const templateMatch = session.template_index === index + 1; // template_index is 1-based in database
          
          return categoryMatch && templateMatch;
        });
        
        const usageCount = matchingSessions.length;
        
        // Count successful sessions (completed status or user marked as complete)
        const successfulSessions = matchingSessions.filter(session => {
          const isCompleted = session.agent_status === 'completed';
          const userMarkedComplete = session.metadata?.completion_status === 'complete';
          const userMarkedIncomplete = session.metadata?.completion_status === 'incomplete';
          
          // If user explicitly marked it, use that; otherwise use agent_status
          if (userMarkedComplete) return true;
          if (userMarkedIncomplete) return false;
          return isCompleted;
        });
        
        const successRate = usageCount > 0 ? Math.round((successfulSessions.length / usageCount) * 100) : 0;
        
        prompt.usageCount = usageCount;
        prompt.successRate = successRate;
      });
      
      // Update master data
      this.promptsMap[this.activeCategory] = [...this.currentPrompts];
    } catch (error) {
      console.error('Error calculating usage stats:', error);
      // Fallback to existing mock data if database call fails
    }
  }

  onPlaceholderChange(name: string, value: string) {
    this.placeholderValues[name] = value;
  }

  trackByIndex = (_: number, __: any) => _;
  trackByKey = (_: number, item: { key: string }) => item.key;
  trackByPart = (_: number, part: { type: string; text?: string; name?: string }) => part.type + ':' + (part.text ?? part.name ?? _);

  // Agent Mode methods
  onAgentModeToggle(isAgentMode: boolean) {
    this.isAgentMode = isAgentMode;
  }

  onIframeLoad() {}
  onIframeError() {}

  dismissPromptToast() {
    this.showPromptToast = false;
  }

  minimizePromptToast() {
    this.isMinimized = true;
  }

  expandPromptToast() {
    this.isMinimized = false;
  }

  async copyPrompt() {
    if (!this.incomingPrompt) return;
    try {
      await navigator.clipboard?.writeText(this.incomingPrompt);
      this.copied = true;
      setTimeout(() => (this.copied = false), 1500);
    } catch {
      // ignore
    }
  }

  sendPromptToIframe() {
    if (!this.incomingPrompt) return;
    const frame = this.agentFrameRef?.nativeElement?.contentWindow;
    if (!frame) return;
    const payloads = [
      { type: 'preset_input', text: this.incomingPrompt },
      { type: 'set_input', text: this.incomingPrompt },
      { type: 'prefill', text: this.incomingPrompt },
      { type: 'init_message', text: this.incomingPrompt },
      { event: 'set_input', value: this.incomingPrompt }
    ];
    try {
      const target = this.agentOrigin === '*' ? '*' : this.agentOrigin;
      for (const p of payloads) {
        frame.postMessage(p, target);
      }
    } catch {
      // ignore
    }
  }

  // Helper methods for dynamic templates
  isSelectedTemplateDynamic(): boolean {
    if (this.selectedPromptIndex < 0 || !this.currentPrompts[this.selectedPromptIndex]) {
      return false;
    }
    const selected = this.currentPrompts[this.selectedPromptIndex];
    if (selected.isDynamic) return true;
    // Fallback: detect {{...}} placeholders in text
    const text = this.getSelectedTemplateText();
    return /\{\{[^}]+\}\}/.test(text) || /\[[^\]]+\]/.test(text);
  }

  getSelectedTemplateName(): string {
    if (this.selectedPromptIndex < 0 || !this.currentPrompts[this.selectedPromptIndex]) {
      return '';
    }
    const selectedPrompt = this.currentPrompts[this.selectedPromptIndex];
    return selectedPrompt.templateName || selectedPrompt.originalTemplate?.name || '';
  }

  getSelectedTemplateText(): string {
    if (this.selectedPromptIndex < 0 || !this.currentPrompts[this.selectedPromptIndex]) {
      return '';
    }
    const selectedPrompt = this.currentPrompts[this.selectedPromptIndex];
    return selectedPrompt.originalTemplate?.prompt_text || selectedPrompt.template;
  }

  getSelectedTemplateInputFields(): string[] {
    if (this.selectedPromptIndex < 0 || !this.currentPrompts[this.selectedPromptIndex]) {
      return [];
    }
    const text = this.getSelectedTemplateText();
    return this.extractFieldsFromText(text);
  }

  formatFieldLabel(field: string): string {
    return field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }

  onDynamicInputChange(): void {
    // Update the filled template preview whenever input values change
    // Trigger change detection to refresh the template preview
    this.cdr.detectChanges();
  }

  getFilledTemplate(): string {
    if (this.selectedPromptIndex < 0 || !this.currentPrompts[this.selectedPromptIndex]) {
      return '';
    }
    
    const selectedPrompt = this.currentPrompts[this.selectedPromptIndex];
    const templateText = selectedPrompt.originalTemplate?.prompt_text || selectedPrompt.template;
    
    // Use the prompt templates service to fill the template
    if (selectedPrompt.originalTemplate && this.promptTemplatesService.fillTemplate) {
      return this.promptTemplatesService.fillTemplate(templateText, this.dynamicInputValues);
    }
    
    // Fallback: simple replacement
    let filledText = templateText;
    Object.keys(this.dynamicInputValues).forEach(key => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
      const replacement = this.dynamicInputValues[key] || `{{${key}}}`;
      filledText = filledText.replace(regex, replacement);
    });
    
    return filledText;
  }

  private extractFieldsFromText(text: string): string[] {
    const fieldsSet = new Set<string>();
    // {{field}}
    const braceRe = /\{\{([^}]+)\}\}/g;
    let m: RegExpExecArray | null;
    while ((m = braceRe.exec(text)) !== null) {
      const name = (m[1] || '').trim();
      if (name) fieldsSet.add(name);
    }
    // [field]
    const bracketRe = /\[([^\]]+)\]/g;
    while ((m = bracketRe.exec(text)) !== null) {
      const name = (m[1] || '').trim();
      if (name) fieldsSet.add(name);
    }
    return Array.from(fieldsSet);
  }

  // Helper methods for optimized Dify integration
  private extractExposureCurrency(query: string): string | null {
    // Extract currency from query - look for common currency patterns
    const currencyPattern = /\b(USD|EUR|GBP|JPY|SGD|AUD|CHF|CAD|HKD|CNY|INR|KRW|THB|MYR|PHP|TWD|NZD)\b/i;
    const match = query.match(currencyPattern);
    return match ? match[1].toUpperCase() : null;
  }
  
  private extractHedgeMethod(query: string): string | null {
    const query_lower = query.toLowerCase();
    if (query_lower.includes('cash flow hedge') || query_lower.includes('coh')) return 'COH';
    if (query_lower.includes('fair value hedge') || query_lower.includes('mtm')) return 'MTM';
    if (query_lower.includes('net investment hedge') || query_lower.includes('nih')) return 'NIH';
    return null;
  }
  
  private extractNavType(query: string): string | null {
    const query_lower = query.toLowerCase();
    if (query_lower.includes('coi') || query_lower.includes('core operating')) return 'COI';
    if (query_lower.includes('re') || query_lower.includes('real estate')) return 'RE';
    return null;
  }
  
  private logPerformanceMetrics(metrics: any) {
    console.log('📊 Dify Performance Metrics:', {
      totalTime: `${metrics.total_time_ms}ms`,
      contextPrepTime: `${metrics.context_prep_time_ms}ms`,
      difyResponseTime: `${metrics.dify_response_time_ms}ms`,
      contextSource: metrics.context_source,
      optimization: `${metrics.context_prep_time_ms < 1000 ? '🚀 Fast' : '⚡ Normal'} context preparation`,
      cacheStatus: metrics.context_source === 'cache' ? '💾 Cache Hit' : '🔄 Fresh Data'
    });
    
    // Show performance indicator in UI (optional)
    const performanceClass = metrics.total_time_ms < 3000 ? 'performance-excellent' : 
                           metrics.total_time_ms < 6000 ? 'performance-good' : 'performance-slow';
    
    // You can add visual indicators based on performance
    console.log(`Performance class: ${performanceClass}`);
  }
  
  private handleDifyError(errorMessage: string) {
    this.apiResponse = `Error: ${errorMessage}`;
    this.updateDatabaseSession('failed');
    this.isStreaming = false;
    this.isLoading = false;
    this.cdr.detectChanges();
  }

  // Performance testing method for GitHub Pages optimization
  async testGitHubPagesOptimization(query: string = "Analyze USD hedging position with recent allocations") {
    try {
      console.log('🧪 Testing GitHub Pages optimization vs direct call...');
      
      const comparison = await this.githubPagesDifyService.performanceComparison({
        query: query,
        msgUid: `TEST_${Date.now()}`,
        instructionId: `PERF_TEST_${Date.now()}`,
        exposureCurrency: this.extractExposureCurrency(query) || 'USD',
        hedgeMethod: this.extractHedgeMethod(query) || undefined,
        navType: this.extractNavType(query) || undefined
      });
      
      console.log('🎯 Performance Comparison Results:', {
        optimizedTime: `${comparison.optimized.metrics.total_time_ms}ms`,
        directTime: `${comparison.direct.metrics.total_time_ms}ms`,
        timeSaved: `${comparison.improvement.time_saved_ms}ms (${comparison.improvement.time_saved_percent.toFixed(1)}% faster)`,
        dataReduction: `${comparison.improvement.data_reduction_percent.toFixed(1)}% less data sent to Dify`,
        cacheUsed: comparison.improvement.cache_benefit ? '💾 Cache benefit' : '🔄 No cache benefit'
      });

      return comparison;
    } catch (error) {
      console.error('❌ Performance test failed:', error);
      throw error;
    }
  }

  // Cache management methods
  clearGitHubPagesCache() {
    this.githubPagesDifyService.clearCache();
    console.log('🗑️ GitHub Pages cache cleared');
  }

  getOptimizationStats() {
    const stats = this.githubPagesDifyService.getOptimizationStats();
    console.log('📊 GitHub Pages optimization stats:', stats);
    return stats;
  }
}
