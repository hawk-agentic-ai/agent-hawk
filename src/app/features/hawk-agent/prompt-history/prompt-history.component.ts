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
import { HawkAgentSimpleService, SimpleHawkSession } from '../services/hawk-agent-simple.service';

interface PromptHistoryRow {
  id: number;
  msg_uid: string;
  instruction_id: string;
  prompt_text: string;
  response_text: string;
  agent_status: 'completed' | 'failed' | 'pending' | 'cancelled';
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  amount?: number;
  currency?: string;
  transaction_date?: string;
  template_category?: string;
  template_index?: number;
  created_at: Date;
  agent_end_time?: Date | string;
  execution_time_ms?: number;
  user_id: string;
  metadata?: any;
  agent_response?: any;
}

@Component({
  selector: 'app-prompt-history',
  standalone: true,
  imports: [
    CommonModule,
    AgGridAngular,
    FormsModule,
    ButtonModule,
    InputTextModule,
    DropdownModule,
    DialogModule,
    TooltipModule
  ],
  template: `
<div class="p-6 flex flex-col" style="height: 100vh; box-sizing: border-box;">
  <!-- Page Header -->
  <div class="mb-6 flex-shrink-0">
    <h2 class="text-xl font-semibold text-gray-900 mb-2">Prompt History</h2>
    <p class="text-gray-600">View and manage HAWK Agent prompt history and responses</p>
  </div>

  <!-- Search and Add Button Section -->
  <div class="flex items-center gap-4 mb-4 flex-shrink-0">
    <div class="flex-1 flex items-center gap-2">
      <label class="filter-label">Search:</label>
      <input type="text" placeholder="Search prompts, UIDs..." [(ngModel)]="searchTerm" (ngModelChange)="onSearchChange($event)" class="filter-input flex-1 max-w-xs">
    </div>
    <div class="flex items-center gap-2">
      <label class="filter-label">Status:</label>
      <select class="filter-input w-40" [(ngModel)]="selectedStatus" (change)="loadPromptHistory()">
        <option value="">All Status</option>
        <option *ngFor="let option of statusOptions" [value]="option.value">{{ option.label }}</option>
      </select>
    </div>
    <div class="flex items-center gap-2">
      <label class="filter-label">Date Range:</label>
      <select class="filter-input w-40" [(ngModel)]="selectedDateRange" (change)="loadPromptHistory()">
        <option value="all">All Time</option>
        <option value="today">Today</option>
        <option value="7days">Last 7 Days</option>
        <option value="30days">Last 30 Days</option>
        <option value="90days">Last 90 Days</option>
      </select>
    </div>
    <button class="btn btn-secondary ml-auto" (click)="exportData()">
      <i class="pi pi-download"></i>
      <span>Export</span>
    </button>
  </div>

  <!-- Data Grid -->
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 min-h-0" style="overflow: hidden;">
    <ag-grid-angular
      class="ag-theme-alpine"
      style="width: 100%; height: 100%;"
      [columnDefs]="columnDefs"
      [rowData]="promptHistory"
      [defaultColDef]="defaultColDef"
      [gridOptions]="gridOptions"
      (gridReady)="onGridReady($event)">
    </ag-grid-angular>
  </div>

  <!-- View Prompt Dialog -->
  <p-dialog 
    header="View Prompt Details" 
    [(visible)]="showDialog"
    [modal]="true"
    [style]="{width: '100vw', height: '90vh', 'border-top-left-radius': '16px', 'border-top-right-radius': '16px', 'max-width': '100vw', 'max-height': '90vh'}"
    [closable]="true"
    styleClass="entity-dialog entity-dialog-full">
    
    <form class="space-y-6 p-2 h-full flex flex-col" *ngIf="selectedPrompt">
      <!-- Section: Quick Details -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white flex-shrink-0">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-center">
            <div class="text-sm font-semibold text-gray-700">Quick Details</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <div [class]="getStatusClass(selectedPrompt.agent_status)" class="inline-flex items-center px-2 py-1 rounded text-xs font-medium">
                  {{ selectedPrompt.agent_status | titlecase }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Created</label>
                <div class="text-sm">{{ formatShortDate(selectedPrompt.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Section: Prompt Text -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white flex-shrink-0">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-center">
            <div class="text-sm font-semibold text-gray-700">Prompt</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="bg-gray-50 border rounded p-3 text-sm max-h-32 overflow-y-auto">{{ selectedPrompt.prompt_text }}</div>
          </div>
        </div>
      </div>

      <!-- Section: Response Text -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white flex-1 flex flex-col">
        <div class="grid grid-cols-12 gap-4 h-full">
          <div class="col-span-12 md:col-span-3 flex items-start">
            <div class="text-sm font-semibold text-gray-700">Response</div>
          </div>
          <div class="col-span-12 md:col-span-9 flex flex-col h-full">
            <div class="bg-gray-50 border rounded p-3 text-sm flex-1 overflow-y-auto response-text" [innerHTML]="formatResponseText(selectedPrompt.response_text)"></div>
          </div>
        </div>
      </div>

      <!-- Section: Token Info -->
      <div class="rounded-lg border border-gray-200 p-4 bg-white flex-shrink-0">
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-12 md:col-span-3 flex items-center">
            <div class="text-sm font-semibold text-gray-700">Token Usage</div>
          </div>
          <div class="col-span-12 md:col-span-9">
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="bg-blue-50 rounded p-2">
                <div class="text-xs text-gray-500">Input</div>
                <div class="font-semibold">{{ selectedPrompt.input_tokens }}</div>
              </div>
              <div class="bg-green-50 rounded p-2">
                <div class="text-xs text-gray-500">Output</div>
                <div class="font-semibold">{{ selectedPrompt.output_tokens }}</div>
              </div>
              <div class="bg-purple-50 rounded p-2">
                <div class="text-xs text-gray-500">Total</div>
                <div class="font-semibold">{{ selectedPrompt.total_tokens }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </form>

    <ng-template pTemplate="footer">
      <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button class="btn btn-secondary" (click)="showDialog = false">Close</button>
        <button class="btn btn-primary" (click)="downloadPrompt(selectedPrompt!)">
          <i class="pi pi-download mr-2"></i>
          Download
        </button>
      </div>
    </ng-template>
  </p-dialog>
</div>
  `,
  styleUrls: [],
  styles: [`
    :host {
      display: block;
      height: 100%;
      width: 100%;
    }
    
    /* Ensure grid container is properly sized */
    .grid-container {
      position: relative;
      width: 100%;
      height: 100%;
    }
    
    :host ::ng-deep {
      /* AG-Grid container fixes */
      .ag-theme-alpine {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
        font-size: 14px;
        line-height: 1.5;
        width: 100% !important;
        height: 100% !important;
        position: relative;
      }
      
      .ag-root-wrapper {
        width: 100% !important;
        height: 100% !important;
      }
      
      .ag-root {
        width: 100% !important;
        height: 100% !important;
      }
      
      .ag-theme-alpine .ag-row {
        border-bottom: 1px solid #f3f4f6;
      }
      
      .ag-theme-alpine .ag-cell {
        display: flex;
        align-items: center;
        padding: 12px 8px;
        font-family: inherit;
        font-size: 14px;
        line-height: 1.5;
        color: #374151;
      }
      
      .ag-theme-alpine .ag-header-cell {
        font-family: inherit;
        font-size: 14px;
        font-weight: 600;
        color: #1f2937;
        background-color: #f9fafb;
        border-bottom: 2px solid #e5e7eb;
      }
      
      .ag-theme-alpine .ag-header-cell-text {
        font-family: inherit;
        font-weight: 600;
      }
      
      /* Status badge consistency */
      .ag-cell .inline-flex {
        font-family: inherit;
        font-size: 14px;
      }
      
      /* Mono font cells (UIDs) */
      .ag-cell .font-mono {
        font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        font-size: 13px;
      }
      
      /* Action buttons */
      .ag-cell button {
        font-family: inherit;
      }
      
      .ag-cell button i {
        font-size: 14px;
      }
      
      /* Row hover effect */
      .ag-theme-alpine .ag-row:hover {
        background-color: #f9fafb;
      }
      
      /* Dialog styling */
      .prompt-dialog {
        .p-dialog-header {
          @apply bg-white border-b border-gray-200 px-4 py-3;
        }
        .p-dialog-title {
          @apply text-base font-semibold text-gray-900;
        }
        .p-dialog-content {
          @apply bg-white p-0;
          max-height: calc(90vh - 120px);
          overflow-y: auto;
        }
        .p-dialog-footer {
          @apply bg-gray-50 px-4 py-3 border-t border-gray-200;
        }
      }
      
      /* Entity dialog styling */
      .entity-dialog-full {
        .p-dialog {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          margin: 0 !important;
          transform: none !important;
          border-radius: 16px 16px 0 0 !important;
        }
      }
      
      /* Response text formatting */
      .response-text {
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
        
        strong {
          font-weight: 600;
          color: #1f2937;
        }
        
        em {
          font-style: italic;
          color: #374151;
        }
        
        code {
          font-family: inherit;
          font-size: 0.875em;
        }
        
        h2, h3 {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        }
      }
    }
  `]
})
export class PromptHistoryComponent implements OnInit, OnDestroy {
  promptHistory: PromptHistoryRow[] = [];
  totalCount: number = 0;
  isLoading: boolean = false;
  
  // Search and filters
  searchTerm: string = '';
  selectedStatus: string | null = null;
  selectedDateRange: string = 'all';
  private searchTimer: any;

  // Dialog
  showDialog: boolean = false;
  dialogMode: 'view' | 'share' = 'view';
  selectedPrompt: PromptHistoryRow | null = null;
  isDialogLoading: boolean = false;

  // Subscriptions
  private sessionsSubscription?: Subscription;

  // Grid
  private gridApi?: GridApi;
  columnDefs: ColDef[] = [
    { 
      field: 'created_at', 
      headerName: 'Date', 
      minWidth: 150, 
      width: 150, 
      sortable: true, 
      sort: 'desc',
      cellClass: 'flex items-center text-sm text-gray-700',
      valueFormatter: (params) => this.formatShortDate(params.value) 
    },
    { 
      field: 'msg_uid', 
      headerName: 'Message UID', 
      minWidth: 140, 
      width: 140, 
      sortable: true,
      cellClass: 'flex items-center text-sm text-gray-700', 
      cellRenderer: (params: any) => `<span class="font-mono text-sm">${params.value || ''}</span>` 
    },
    { 
      field: 'instruction_id', 
      headerName: 'Instruction ID', 
      minWidth: 130, 
      width: 130, 
      sortable: true,
      cellClass: 'flex items-center text-sm text-gray-700', 
      cellRenderer: (params: any) => `<span class="font-mono text-sm">${params.value || ''}</span>` 
    },
    { 
      field: 'prompt_text', 
      headerName: 'Prompt', 
      flex: 2, 
      minWidth: 300, 
      sortable: true,
      cellClass: 'flex items-center text-sm text-gray-700',
      cellRenderer: (params: any) => {
        const text = params.value || 'No prompt available';
        const truncated = text.length > 120 ? text.substring(0, 120) + '...' : text;
        return `<div class="text-sm" title="${text}" style="word-wrap: break-word;">${truncated}</div>`;
      }
    },
    {
      field: 'agent_status',
      headerName: 'Status',
      minWidth: 110,
      width: 110,
      sortable: true,
      cellClass: 'flex items-center justify-center text-sm text-gray-700',
      cellRenderer: (params: any) => {
        const status = params.value || '';
        let className = '';
        switch (status) {
          case 'completed':
            className = 'bg-green-100 text-green-800';
            break;
          case 'failed':
            className = 'bg-red-100 text-red-800';
            break;
          case 'pending':
            className = 'bg-yellow-100 text-yellow-800';
            break;
          case 'cancelled':
            className = 'bg-gray-100 text-gray-800';
            break;
          default:
            className = 'bg-blue-100 text-blue-800';
        }
        const span = document.createElement('span');
        span.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${className}`;
        span.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        return span;
      }
    },
    { 
      field: 'total_tokens', 
      headerName: 'Tokens', 
      minWidth: 90, 
      width: 90, 
      sortable: true, 
      cellClass: 'flex items-center justify-center text-sm text-gray-700' 
    },
    {
      headerName: 'Actions',
      minWidth: 120,
      width: 120,
      sortable: false,
      pinned: 'right',
      cellClass: 'flex items-center justify-center text-sm text-gray-700',
      cellRenderer: (params: any) => {
        const container = document.createElement('div');
        container.className = 'flex items-center justify-center space-x-2';
        
        const viewBtn = document.createElement('button');
        viewBtn.className = 'text-gray-500 hover:text-blue-600 p-1 transition-colors duration-200';
        viewBtn.title = 'View Prompt Details';
        viewBtn.innerHTML = '<i class="pi pi-eye text-sm"></i>';
        viewBtn.addEventListener('click', () => params.context.componentParent.viewPrompt(params.data));
        
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'text-gray-500 hover:text-green-600 p-1 transition-colors duration-200';
        downloadBtn.title = 'Download Prompt';
        downloadBtn.innerHTML = '<i class="pi pi-download text-sm"></i>';
        downloadBtn.addEventListener('click', () => params.context.componentParent.downloadPrompt(params.data));
        
        container.appendChild(viewBtn);
        container.appendChild(downloadBtn);
        return container;
      }
    }
  ];

  defaultColDef: ColDef = { 
    resizable: true, 
    sortable: true, 
    filter: 'agSetColumnFilter', 
    minWidth: 100,
    suppressSizeToFit: false // Allow columns to participate in flex sizing
  };

  gridOptions: GridOptions = {
    animateRows: false, // Disable animations for better performance
    rowHeight: 48,
    headerHeight: 40,
    suppressRowClickSelection: true,
    suppressCellFocus: true,
    suppressHorizontalScroll: false,
    pagination: true,
    paginationPageSize: 50,
    paginationPageSizeSelector: [25, 50, 100],
    skipHeaderOnAutoSize: true, // Don't auto-size based on header content
    context: { componentParent: this }
  };

  statusOptions = [
    { label: 'Completed', value: 'completed' },
    { label: 'Failed', value: 'failed' },
    { label: 'Pending', value: 'pending' },
    { label: 'Cancelled', value: 'cancelled' }
  ];

  constructor(private hawkAgentService: HawkAgentSimpleService, private route: ActivatedRoute) {}

  ngOnInit() {
    // Read deep-link query params for auto-open
    this.route.queryParams.subscribe((params) => {
      const msg = params['msg_uid'];
      const instr = params['instruction_id'];
      if (msg || instr) {
        // store and try open after load
        (this as any)._pendingOpen = { msg_uid: msg, instruction_id: instr };
      }
      this.loadPromptHistory();
    });
    this.setupRealtimeUpdates();
  }
  
  @HostListener('window:resize', ['$event'])
  onWindowResize() {
    // Handle window resize to ensure grid adjusts properly
    if (this.gridApi) {
      setTimeout(() => {
        this.gridApi?.sizeColumnsToFit();
      }, 100);
    }
  }

  ngOnDestroy() {
    if (this.sessionsSubscription) {
      this.sessionsSubscription.unsubscribe();
    }
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
  }

  private setupRealtimeUpdates() {
    // Real-time updates will be implemented later
    console.log('Real-time updates placeholder');
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api;
    
    // Force grid to recalculate size after initialization
    setTimeout(() => {
      if (this.gridApi) {
        this.gridApi.sizeColumnsToFit();
        // Force grid to refresh its layout and check container size
        this.gridApi.refreshCells();
      }
    }, 100);
  }

  onCellClicked(event: CellClickedEvent) {
    // Handle row clicks if needed
  }

  onSearchChange(term: string) {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.loadPromptHistory();
    }, 500); // Increased debounce time to reduce database calls
  }

  async loadPromptHistory() {
    this.isLoading = true;
    
    try {
      const sessions = await this.hawkAgentService.getSessions();
      
      // Apply filters and search
      let filteredSessions = sessions;
      
      // Apply status filter
      if (this.selectedStatus) {
        filteredSessions = filteredSessions.filter(session => session.agent_status === this.selectedStatus);
      }
      
      // Apply search filter
      if (this.searchTerm && this.searchTerm.trim()) {
        const searchLower = this.searchTerm.toLowerCase();
        filteredSessions = filteredSessions.filter(session => 
          session.msg_uid?.toLowerCase().includes(searchLower) ||
          session.instruction_id?.toLowerCase().includes(searchLower) ||
          session.metadata?.prompt_text?.toLowerCase().includes(searchLower)
        );
      }
      
      // Apply date range filter (simplified)
      if (this.selectedDateRange !== 'all') {
        const now = new Date();
        const cutoffDate = new Date();
        
        switch (this.selectedDateRange) {
          case 'today':
            cutoffDate.setHours(0, 0, 0, 0);
            break;
          case '7days':
            cutoffDate.setDate(now.getDate() - 7);
            break;
          case '30days':
            cutoffDate.setDate(now.getDate() - 30);
            break;
          case '90days':
            cutoffDate.setDate(now.getDate() - 90);
            break;
        }
        
        filteredSessions = filteredSessions.filter(session => {
          const sessionDate = new Date(session.created_at!);
          return sessionDate >= cutoffDate;
        });
      }
      
      // Limit to recent 1000 records for performance
      const limitedSessions = filteredSessions.slice(0, 1000);
      
      // Convert sessions to PromptHistoryRow interface
      this.promptHistory = limitedSessions.map(session => this.mapSessionToHistoryRow(session));
      this.totalCount = filteredSessions.length;
      
      // Update grid efficiently
      if (this.gridApi) {
        this.gridApi.setGridOption('rowData', this.promptHistory);
        // Force grid to recalculate after data update
        setTimeout(() => {
          this.gridApi?.sizeColumnsToFit();
        }, 50);
      }
      // Handle deep-link open once data is loaded
      const pending = (this as any)._pendingOpen as { msg_uid?: string; instruction_id?: string } | undefined;
      if (pending && this.promptHistory?.length) {
        let match = this.promptHistory.find(r => (pending.msg_uid && r.msg_uid === pending.msg_uid) || (pending.instruction_id && r.instruction_id === pending.instruction_id));
        if (match) {
          this.viewPrompt(match);
          // clear so it doesn't reopen
          (this as any)._pendingOpen = undefined;
        }
      }
    } catch (error) {
      console.error('Error loading prompt history:', error);
      // Fall back to generating mock data if database fails
      this.generateMockData();
    } finally {
      this.isLoading = false;
    }
  }

  private mapSessionToHistoryRow(session: SimpleHawkSession): PromptHistoryRow {
    
    // Extract token information from various possible locations
    const getTokens = () => {
      // Check if tokens are in agent_response
      if (session.agent_response?.usage) {
        return {
          input: session.agent_response.usage.input_tokens || session.agent_response.usage.prompt_tokens || 0,
          output: session.agent_response.usage.output_tokens || session.agent_response.usage.completion_tokens || 0,
          total: session.agent_response.usage.total_tokens || 0
        };
      }
      
      // Check if tokens are directly in agent_response
      if (session.agent_response?.input_tokens || session.agent_response?.output_tokens) {
        return {
          input: session.agent_response.input_tokens || 0,
          output: session.agent_response.output_tokens || 0,
          total: session.agent_response.total_tokens || 0
        };
      }
      
      // Check if tokens are in metadata
      if (session.metadata?.usage) {
        return {
          input: session.metadata.usage.input_tokens || session.metadata.usage.prompt_tokens || 0,
          output: session.metadata.usage.output_tokens || session.metadata.usage.completion_tokens || 0,
          total: session.metadata.usage.total_tokens || 0
        };
      }
      
      // Check if tokens are directly in metadata
      if (session.metadata?.input_tokens || session.metadata?.output_tokens) {
        return {
          input: session.metadata.input_tokens || 0,
          output: session.metadata.output_tokens || 0,
          total: session.metadata.total_tokens || 0
        };
      }
      
      return { input: 0, output: 0, total: 0 };
    };

    const tokens = getTokens();
    // Calculate total if not provided
    if (tokens.total === 0 && (tokens.input > 0 || tokens.output > 0)) {
      tokens.total = tokens.input + tokens.output;
    }

    const mapped = {
      id: session.id || 0,
      msg_uid: session.msg_uid || '',
      instruction_id: session.instruction_id || '',
      prompt_text: session.metadata?.prompt_text || 'No prompt text available',
      response_text: session.agent_response?.text || 'No response available',
      agent_status: session.agent_status as any,
      input_tokens: tokens.input,
      output_tokens: tokens.output, 
      total_tokens: tokens.total,
      amount: session.metadata?.amount,
      currency: session.metadata?.currency,
      transaction_date: session.metadata?.transaction_date,
      template_category: session.template_category || 'template',
      template_index: session.template_index || 1,
      created_at: typeof session.created_at === 'string' ? new Date(session.created_at) : (session.created_at || new Date()),
      agent_end_time: session.updated_at || session.created_at,
      execution_time_ms: 0,
      user_id: session.user_id || '',
      metadata: session.metadata,
      agent_response: session.agent_response
    };
    return mapped;
  }

  private generateMockData() {
    // Mock data for fallback
    this.promptHistory = [];
    this.totalCount = 0;
  }

  viewPrompt(row: PromptHistoryRow) {
    if (!row || this.isDialogLoading) return;
    
    // Set data immediately for faster response
    this.selectedPrompt = row;
    this.dialogMode = 'view';
    this.showDialog = true;
    this.isDialogLoading = false;
  }

  sharePrompt(row: PromptHistoryRow) {
    // Implement sharing functionality
    console.log('Share prompt:', row);
  }

  downloadPrompt(row: PromptHistoryRow) {
    if (!row) return;

    const data = {
      message_uid: row.msg_uid,
      instruction_id: row.instruction_id,
      prompt: row.prompt_text,
      response: row.response_text,
      agent_status: row.agent_status,
      tokens: {
        input: row.input_tokens,
        output: row.output_tokens,
        total: row.total_tokens
      },
      created_at: row.created_at,
      agent_end_time: row.agent_end_time
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prompt-${row.msg_uid}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  exportData() {
    // TODO: Implement bulk export
    console.log('Export data functionality to be implemented');
  }

  formatShortDate(date: Date | string): string {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatDate(date: Date | string): string {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleString();
  }

  formatResponseText(text: string): string {
    if (!text) return '';
    
    // Convert markdown-like formatting to HTML
    let formatted = text
      // Convert **bold** to <strong>
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Convert *italic* to <em>
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Convert code blocks ```code``` to <code>
      .replace(/```([\s\S]*?)```/g, '<code class="block bg-gray-100 p-2 rounded text-xs">$1</code>')
      // Convert inline code `code` to <code>
      .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded text-xs">$1</code>')
      // Convert numbered lists 1. item to proper list items
      .replace(/^(\d+)\.\s+(.+)$/gm, '<div class="ml-4">$1. $2</div>')
      // Convert bullet points - item to proper list items
      .replace(/^[-*]\s+(.+)$/gm, '<div class="ml-4"> $1</div>')
      // Convert headers ## Header to styled headers
      .replace(/^##\s+(.+)$/gm, '<h3 class="text-base font-semibold mt-4 mb-2 text-gray-900">$1</h3>')
      .replace(/^#\s+(.+)$/gm, '<h2 class="text-lg font-bold mt-4 mb-2 text-gray-900">$1</h2>')
      // Convert double newlines to paragraph breaks
      .replace(/\n\n/g, '<br><br>')
      // Convert single newlines to line breaks
      .replace(/\n/g, '<br>');

    return formatted;
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  }
}
