import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridOptions, GridReadyEvent } from 'ag-grid-community';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { HedgeBusinessEventsService, HedgeBusinessEvent } from './hedge-business-events.service';

@Component({
  selector: 'app-operations-hedge-business-events',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular, DialogModule, ButtonModule],
  template: `
    <div class="p-6 h-full flex flex-col">
      <!-- Page Header -->
      <div class="mb-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-2">Hedge Business Events</h2>
        <p class="text-gray-600">Live from hedge_business_events (Supabase)</p>
      </div>

      <!-- Filters -->
      <div class="filter-bar">
        <div class="filter-row w-full">
          <div class="flex items-center space-x-2">
            <label class="filter-label">Search:</label>
            <input class="filter-input w-72" placeholder="event_id, instruction_id, event_type..." [(ngModel)]="search" (ngModelChange)="load()" />
          </div>
          <div class="flex items-center space-x-2">
            <label class="filter-label">Event Status:</label>
            <select class="filter-input w-48" [(ngModel)]="status" (ngModelChange)="load()">
              <option [ngValue]="null">All</option>
              <option>Active</option>
              <option>Completed</option>
              <option>Failed</option>
              <option>Cancelled</option>
            </select>
          </div>
          <div class="flex items-center space-x-2">
            <label class="filter-label">From:</label>
            <input type="date" class="filter-input" [(ngModel)]="fromDate" (ngModelChange)="load()"/>
          </div>
          <div class="flex items-center space-x-2">
            <label class="filter-label">To:</label>
            <input type="date" class="filter-input" [(ngModel)]="toDate" (ngModelChange)="load()"/>
          </div>
        </div>
      </div>

      <!-- Grid -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200" style="height: calc(100vh - 300px); min-height: 400px;">
        <ag-grid-angular class="ag-theme-alpine" style="width: 100%; height: 100%;"
          [columnDefs]="columnDefs" [rowData]="events" [defaultColDef]="defaultColDef" [gridOptions]="gridOptions" (gridReady)="onGridReady($event)">
        </ag-grid-angular>
      </div>

      <!-- View Dialog -->
      <p-dialog header="Event Details" [(visible)]="showDialog" [modal]="true" [style]="{width: '100vw', height: '95vh', 'max-width': '100vw', 'max-height': '95vh', 'border-top-left-radius': '16px', 'border-top-right-radius': '16px'}" styleClass="entity-dialog entity-dialog-full">
        <div class="space-y-4 p-2" *ngIf="selected">
          <!-- Identifiers -->
          <div class="rounded-lg border border-gray-200 p-4 bg-white">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 md:col-span-3"><div class="text-sm font-semibold text-gray-700">Identifiers</div></div>
              <div class="col-span-12 md:col-span-9 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div><div class="text-gray-500">Event ID</div><div class="font-medium">{{selected.event_id}}</div></div>
                <div><div class="text-gray-500">Instruction ID</div><div class="font-mono">{{selected.instruction_id}}</div></div>
                <div><div class="text-gray-500">Event Type</div><div class="font-medium">{{selected.event_type}}</div></div>
                <div><div class="text-gray-500">Event Status</div><div class="font-medium">{{selected.event_status}}</div></div>
              </div>
            </div>
          </div>

          <!-- Stage Status -->
          <div class="rounded-lg border border-gray-200 p-4 bg-white">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 md:col-span-3"><div class="text-sm font-semibold text-gray-700">Stage Status</div></div>
              <div class="col-span-12 md:col-span-9 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div><div class="text-gray-500">Stage 1A Status</div><div class="font-medium">{{selected.stage_1a_status}}</div></div>
                <div><div class="text-gray-500">Stage 2 Status</div><div class="font-medium">{{selected.stage_2_status}}</div></div>
                <div><div class="text-gray-500">Stage 3 Status</div><div class="font-medium">{{selected.stage_3_status}}</div></div>
                <div><div class="text-gray-500">Booking Model</div><div class="font-medium">{{selected.assigned_booking_model}}</div></div>
              </div>
            </div>
          </div>

          <!-- Deal Counts -->
          <div class="rounded-lg border border-gray-200 p-4 bg-white">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 md:col-span-3"><div class="text-sm font-semibold text-gray-700">Deal Counts</div></div>
              <div class="col-span-12 md:col-span-9 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div><div class="text-gray-500">Expected Deals</div><div class="font-medium">{{selected.expected_deal_count}}</div></div>
                <div><div class="text-gray-500">Actual Deals</div><div class="font-medium">{{selected.actual_deal_count}}</div></div>
              </div>
            </div>
          </div>

          <!-- Timestamps -->
          <div class="rounded-lg border border-gray-200 p-4 bg-white">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 md:col-span-3"><div class="text-sm font-semibold text-gray-700">Timestamps</div></div>
              <div class="col-span-12 md:col-span-9 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div><div class="text-gray-500">Created Date</div><div class="font-medium">{{selected.created_date}}</div></div>
                <div><div class="text-gray-500">Updated Date</div><div class="font-medium">{{selected.updated_date}}</div></div>
                <div><div class="text-gray-500">Created By</div><div class="font-medium">{{selected.created_by}}</div></div>
                <div><div class="text-gray-500">Updated By</div><div class="font-medium">{{selected.updated_by}}</div></div>
              </div>
            </div>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button class="btn btn-secondary" (click)="showDialog=false">Close</button>
          </div>
        </ng-template>
      </p-dialog>
    </div>
  `,
  styles: []
})
export class HedgeBusinessEventsComponent implements OnInit {
  events: HedgeBusinessEvent[] = [];
  search = '';
  status: string | null = null;
  fromDate: string | null = null;
  toDate: string | null = null;
  showDialog = false;
  selected: HedgeBusinessEvent | null = null;
  private gridApi: any;

  columnDefs: ColDef[] = [
    {
      headerName: 'Event ID',
      field: 'event_id',
      minWidth: 120,
      flex: 1,
      pinned: 'left'
    },
    {
      headerName: 'Instruction ID',
      field: 'instruction_id',
      minWidth: 140,
      flex: 1
    },
    {
      headerName: 'Event Type',
      field: 'event_type',
      minWidth: 100,
      flex: 1
    },
    {
      headerName: 'Event Status',
      field: 'event_status',
      minWidth: 100,
      flex: 1,
      cellRenderer: (params: any) => {
        const status = params.value;
        const colorClass = status === 'Completed' ? 'text-green-600' :
                          status === 'Failed' ? 'text-red-600' :
                          status === 'Active' ? 'text-blue-600' : 'text-gray-600';
        return `<span class="font-medium ${colorClass}">${status || ''}</span>`;
      }
    },
    {
      headerName: 'Stage 1A Status',
      field: 'stage_1a_status',
      minWidth: 110,
      flex: 1,
      cellRenderer: (params: any) => this.renderStageStatus(params.value)
    },
    {
      headerName: 'Stage 2 Status',
      field: 'stage_2_status',
      minWidth: 100,
      flex: 1,
      cellRenderer: (params: any) => this.renderStageStatus(params.value)
    },
    {
      headerName: 'Stage 3 Status',
      field: 'stage_3_status',
      minWidth: 100,
      flex: 1,
      cellRenderer: (params: any) => this.renderStageStatus(params.value)
    },
    {
      headerName: 'Booking Model',
      field: 'assigned_booking_model',
      minWidth: 110,
      flex: 1
    },
    {
      headerName: 'Expected Deals',
      field: 'expected_deal_count',
      minWidth: 110,
      flex: 1,
      type: 'numericColumn'
    },
    {
      headerName: 'Actual Deals',
      field: 'actual_deal_count',
      minWidth: 100,
      flex: 1,
      type: 'numericColumn',
      cellRenderer: (params: any) => {
        const actual = params.value || 0;
        const expected = params.data?.expected_deal_count || 0;
        const isMatch = actual === expected && actual > 0;
        const colorClass = isMatch ? 'text-green-600' : actual > 0 ? 'text-orange-600' : 'text-gray-400';
        return `<span class="${colorClass}">${actual}</span>`;
      }
    },
    {
      headerName: 'Created Date',
      field: 'created_date',
      minWidth: 140,
      flex: 1,
      cellRenderer: (params: any) => params.value ? new Date(params.value).toLocaleString() : ''
    },
    {
      headerName: 'Updated Date',
      field: 'updated_date',
      minWidth: 140,
      flex: 1,
      cellRenderer: (params: any) => params.value ? new Date(params.value).toLocaleString() : ''
    },
    {
      headerName: 'Actions',
      width: 80,
      pinned: 'right',
      suppressSizeToFit: true,
      cellRenderer: (p: any)=> {
        const btn = document.createElement('button');
        btn.className = 'text-gray-500 hover:text-blue-600 p-1';
        btn.title = 'View Details';
        btn.innerHTML = '<i class="pi pi-eye"></i>';
        btn.addEventListener('click', () => p.context.componentParent.viewRow(p.data));
        return btn;
      }
    }
  ];
  defaultColDef: ColDef = {
    resizable: true,
    sortable: true,
    filter: 'agSetColumnFilter'
  };
  gridOptions: GridOptions = {
    pagination: true,
    paginationPageSize: 25,
    animateRows: true,
    context: { componentParent: this }
  };

  constructor(private hedgeBusinessEventsService: HedgeBusinessEventsService) {}

  ngOnInit() { this.load(); this.hedgeBusinessEventsService.subscribeRealtime(() => this.load()); }

  async load() {
    this.events = await this.hedgeBusinessEventsService.list({
      search: this.search || undefined,
      status: this.status || undefined,
      fromDate: this.fromDate || undefined,
      toDate: this.toDate || undefined
    });
  }

  onGridReady(e: GridReadyEvent) { this.gridApi = e.api; }
  viewRow(row: HedgeBusinessEvent) { this.selected = row; this.showDialog = true; }

  private renderStageStatus(status: string): string {
    if (!status) return '';

    const colorClass = status === 'Completed' ? 'text-green-600' :
                      status === 'In_Progress' ? 'text-blue-600' :
                      status === 'Failed' ? 'text-red-600' :
                      status === 'Pending' ? 'text-gray-600' : 'text-gray-400';

    return `<span class="${colorClass}">${status}</span>`;
  }
}