import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';

import { MainSidebarComponent } from './core/components/main-sidebar/main-sidebar.component';
import { SubSidebarComponent } from './core/components/sub-sidebar/sub-sidebar.component';
import { HeaderComponent } from './core/components/header/header.component';
import { LayoutService } from './core/services/layout.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MainSidebarComponent,
    SubSidebarComponent,
    HeaderComponent
  ],
  template: `
    <div class="flex h-screen bg-background text-foreground font-sans">
      <!-- Main Sidebar -->
      <app-main-sidebar 
        *ngIf="!layoutService.isAgentMode()"
        [isCollapsed]="layoutService.isMainSidebarCollapsed()"
        (toggleCollapse)="layoutService.toggleMainSidebar()"
        (menuItemClick)="onMainMenuClick($event)"
        [style.z-index]="20">
      </app-main-sidebar>

      <!-- Sub Sidebar -->
      <app-sub-sidebar 
        *ngIf="!layoutService.isAgentMode() && layoutService.isSubSidebarVisible()"
        [isCollapsed]="layoutService.isSubSidebarCollapsed()"
        [isMainSidebarCollapsed]="layoutService.isMainSidebarCollapsed()"
        [menuItems]="currentSubMenuItems"
        [title]="currentSubtitle"
        [icon]="currentSubSidebarIcon"
        [style.z-index]="15"
        (toggleCollapse)="layoutService.toggleSubSidebar()">
      </app-sub-sidebar>

      <!-- Main Content Area -->
      <div class="flex flex-col flex-1 overflow-hidden transition-all duration-300 relative" [style.margin-left]="getContentMarginLeft()">
        <!-- Header -->
        <app-header 
          *ngIf="!layoutService.isAgentMode()"
          [title]="currentTitle"
          [subtitle]="currentSubtitle">
        </app-header>

        <!-- Page Content -->
        <main class="flex-1 overflow-auto bg-muted/20 relative" 
              [class.p-6]="!layoutService.isAgentMode()"
              [class.p-0]="layoutService.isAgentMode()">
          <div class="rounded-lg min-h-full flex flex-col relative overflow-hidden"
               [class.bg-card]="!layoutService.isAgentMode()"
               [class.shadow-sm]="!layoutService.isAgentMode()"
               [class.border]="!layoutService.isAgentMode()"
               [class.border-border]="!layoutService.isAgentMode()">
            <!-- Inner padding for breathing space on all screens -->
            <div class="flex-1 overflow-auto z-0" [class.p-4]="!layoutService.isAgentMode()">
              <router-outlet></router-outlet>
            </div>
          </div>
        </main>
      </div>
    </div>
  `
})
export class AppComponent implements OnInit {
  currentTitle = 'Hedge Accounting SFX';
  currentSubtitle = 'Configuration';
  currentSubMenuItems: any[] = [];
  currentSubSidebarIcon: string = 'pi pi-cog';

  constructor(public layoutService: LayoutService, private router: Router) { }

  ngOnInit() {
    // Ensure sub-sidebar only shows on configuration routes
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e: NavigationEnd) => {
        const url = e.urlAfterRedirects;
        if (url.includes('/configuration')) {
          this.setConfigurationSubmenu();
          this.layoutService.showSubSidebar();
          this.currentSubtitle = 'Configuration';
        } else if (url.includes('/hedge/dashboard')) {
          this.setAnalyticsSubmenu();
          this.layoutService.showSubSidebar();
          this.currentSubtitle = 'Analytics';
        } else if (url.includes('/hawk-agent')) {
          this.setHawkAgentSubmenu();
          this.layoutService.showSubSidebar();
          this.currentSubtitle = 'HAWK Agent';
        } else if (url.includes('/operations')) {
          this.setOperationsSubmenu();
          this.layoutService.showSubSidebar();
          this.currentSubtitle = 'Operations';
        } else if (url.includes('/audit')) {
          this.setAuditSubmenu();
          this.layoutService.showSubSidebar();
          this.currentSubtitle = 'Audit & System Logs';
        } else {
          this.layoutService.hideSubSidebar();
        }
      });
  }

  onMainMenuClick(menuItem: any) {
    if (menuItem.key === 'configuration') {
      this.setConfigurationSubmenu();
      this.layoutService.showSubSidebar();
      this.currentSubtitle = 'Configuration';
    } else if (menuItem.key === 'dashboard') {
      this.setAnalyticsSubmenu();
      this.layoutService.showSubSidebar();
      this.currentSubtitle = 'Analytics';
    } else if (menuItem.key === 'hawk-agent') {
      this.setHawkAgentSubmenu();
      this.layoutService.showSubSidebar();
      this.currentSubtitle = 'HAWK Agent';
    } else if (menuItem.key === 'operations') {
      this.setOperationsSubmenu();
      this.layoutService.showSubSidebar();
      this.currentSubtitle = 'Operations';
    } else if (menuItem.key === 'audit') {
      this.setAuditSubmenu();
      this.layoutService.showSubSidebar();
      this.currentSubtitle = 'Audit & System Logs';
    } else {
      this.layoutService.hideSubSidebar();
      this.currentSubtitle = menuItem.label;
    }
  }

  private setConfigurationSubmenu() {
    this.currentSubMenuItems = [
      { label: 'Hedge Framework', icon: 'pi pi-chart-line', link: '/configuration/hedge-framework' },
      { label: 'Currency', icon: 'pi pi-money-bill', link: '/configuration/currency' },
      { label: 'Entity', icon: 'pi pi-building', link: '/configuration/entity' },
      { label: 'Portfolios', icon: 'pi pi-briefcase', link: '/configuration/portfolios' },
      { label: 'Products', icon: 'pi pi-tags', link: '/configuration/products' },
      { label: 'Prompt Templates', icon: 'pi pi-file-edit', link: '/configuration/prompt-templates' },
      { label: 'Threshold Configuration', icon: 'pi pi-sliders-h', link: '/configuration/threshold-configuration' },
      { label: 'Buffer Configuration', icon: 'pi pi-sliders-v', link: '/configuration/buffer-configuration' },
      { label: 'Business Rules Engine', icon: 'pi pi-cog', link: '/configuration/business-rules-engine' },
      { label: 'Booking Model Config', icon: 'pi pi-book', link: '/configuration/booking-model-config' }
    ];
    this.currentSubSidebarIcon = 'pi pi-cog';
  }

  private setAnalyticsSubmenu() {
    this.currentSubMenuItems = [
      { label: 'Dashboard', icon: 'pi pi-th-large', link: '/hedge/dashboard', exact: true },
      { label: 'SFX Positions', icon: 'pi pi-table', link: '/hedge/dashboard/positions-nav' },
      { label: 'Hedging Instruments', icon: 'pi pi-tags', link: '/hedge/dashboard/hedging-instruments' },
      { label: 'Hedge Effectiveness', icon: 'pi pi-chart-line', link: '/hedge/dashboard/hedge-effectiveness' },
      { label: 'Threshold Monitoring', icon: 'pi pi-sliders-h', link: '/hedge/dashboard/threshold-monitoring' },
      { label: 'Performance Metrics', icon: 'pi pi-chart-bar', link: '/hedge/dashboard/performance-metrics' },
      { label: 'Exceptions & Alerts', icon: 'pi pi-exclamation-triangle', link: '/hedge/dashboard/exceptions-alerts' },
      { label: 'Regulatory Reporting', icon: 'pi pi-file', link: '/hedge/dashboard/regulatory-reporting' }
    ];
    this.currentSubSidebarIcon = 'pi pi-th-large';
  }

  private setHawkAgentSubmenu() {
    this.currentSubMenuItems = [
      { label: 'Agentic AI', icon: 'pi pi-file', link: '/hawk-agent/prompt-templates' },
      { label: 'Prompt History', icon: 'pi pi-history', link: '/hawk-agent/prompt-history' }
    ];
    this.currentSubSidebarIcon = 'pi pi-microchip-ai';
  }

  private setOperationsSubmenu() {
    this.currentSubMenuItems = [
      { label: 'Hedge Instructions', icon: 'pi pi-pencil', link: '/operations/hedge-instructions' },
      { label: 'Hedge Business Events', icon: 'pi pi-calendar', link: '/operations/hedge-business-events' },
      { label: 'Apportionment Table', icon: 'pi pi-table', link: '/operations/apportionment-table' },
      { label: 'Murex Booking', icon: 'pi pi-database', link: '/operations/murex-booking' },
      { label: 'Accounting Hub / GL Bookings', icon: 'pi pi-book', link: '/operations/accounting-hub' },
      { label: 'Externalization Management', icon: 'pi pi-share-alt', link: '/operations/externalization-management' },
      { label: 'Daily Monitoring', icon: 'pi pi-clock', link: '/operations/daily-monitoring' },
      { label: 'Hedge Failure Management', icon: 'pi pi-exclamation-triangle', link: '/operations/hedge-failure-management' }
    ];
    this.currentSubSidebarIcon = 'pi pi-briefcase';
  }

  private setAuditSubmenu() {
    this.currentSubMenuItems = [
      { label: 'Audit Logs', icon: 'pi pi-list', link: '/audit/audit-logs' },
      { label: 'System Logs', icon: 'pi pi-cog', link: '/audit/system-logs' },
      { label: 'Data Lineage Tracking', icon: 'pi pi-sitemap', link: '/audit/data-lineage' },
      { label: 'Configuration Change History', icon: 'pi pi-history', link: '/audit/config-change-history' }
    ];
    this.currentSubSidebarIcon = 'pi pi-history';
  }

  getContentMarginLeft(): string {
    // Use stable state (not effective state) to prevents layout jumps on hover
    const mainSidebarWidth = this.layoutService.isMainSidebarCollapsed() ? 80 : 280;

    // Sub-sidebar should also only push content if it's pinned open
    const subSidebarWidth = this.layoutService.isSubSidebarVisible()
      ? (this.layoutService.isSubSidebarCollapsed() ? 80 : 240)
      : 0;

    return `${mainSidebarWidth + subSidebarWidth}px`;
  }
}
