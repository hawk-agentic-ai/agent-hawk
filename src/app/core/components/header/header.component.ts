import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CalendarModule } from 'primeng/calendar';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, CalendarModule, FormsModule],
  template: `
    <header class="bg-background/80 backdrop-blur-md border-b border-border px-6 py-5 shadow-sm z-10 sticky top-0" style="height: 86px;">
      <div class="flex items-center justify-between h-full">
        <!-- Title Section -->
        <div class="flex flex-col">
          <h1 class="text-2xl font-bold text-foreground flex items-center tracking-tight">
            {{ title }}
            <span *ngIf="badge" class="ml-3 px-2 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full ring-1 ring-primary/20">{{ badge }}</span>
          </h1>
          <span class="text-sm text-muted-foreground mt-1">{{ subtitle }}</span>
        </div>

        <!-- Date Picker Section -->
        <div class="flex items-center bg-card rounded-lg px-4 py-2.5 border border-border shadow-sm hover:border-primary/50 hover:shadow-md transition-all duration-200">
          <label class="text-sm font-medium text-muted-foreground mr-3">As of Date:</label>
          <p-calendar 
            [(ngModel)]="selectedDate"
            [showIcon]="true"
            [iconDisplay]="'input'"
            [dateFormat]="'dd/mm/yy'"
            [placeholder]="'Select Date'"
            styleClass="header-calendar"
            class="text-sm">
          </p-calendar>
        </div>
      </div>
    </header>
  `,
  styles: [`
    :host ::ng-deep .header-calendar .p-calendar {
      border: none;
      background-color: transparent;
    }
    :host ::ng-deep .header-calendar .p-inputtext {
      border: none;
      background-color: transparent;
      font-weight: 500;
      color: hsl(var(--primary));
      padding-left: 0;
      min-width: 110px;
    }
    :host ::ng-deep .header-calendar .p-button {
      background-color: transparent;
      border: none;
      color: hsl(var(--primary));
    }
    :host ::ng-deep .header-calendar .p-datepicker-trigger:hover {
      background-color: hsl(var(--primary) / 0.1);
      border-radius: 9999px;
    }
  `]
})
export class HeaderComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() badge?: string;

  selectedDate: Date = new Date();
}