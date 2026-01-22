import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { LayoutService } from '../../services/layout.service';

@Component({
  selector: 'app-main-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside 
      class="sidenav-root sidebar-transition z-20 glass-sidebar border-r border-sidebar-border fixed top-0 left-0 h-screen flex flex-col"
      [class.collapsed]="effectivelyCollapsed"
      [style.width]="effectivelyCollapsed ? '80px' : '280px'"
      (mouseenter)="onMouseEnter()"
      (mouseleave)="onMouseLeave()">
      
      <!-- Brand Section -->
      <div class="nav-header h-[72px] flex items-center px-5 border-b border-sidebar-border/30">
        <div class="header-full flex items-center gap-4 w-full" [class.justify-center]="effectivelyCollapsed">
          <div class="logo-box flex items-center justify-center shrink-0" style="width: 40px; height: 40px;">
            <!-- Custom DBS Logomark -->
            <img src="assets/Logo/DBS/Logomark.svg" alt="DBS Logo" class="w-8 h-8 object-contain">
          </div>
          <div *ngIf="!effectivelyCollapsed" class="flex flex-col min-w-0">
            <span class="text-[15px] font-bold tracking-tight text-white leading-tight">DBS One <span class="font-normal opacity-70">Finance</span></span>
            <span class="text-[10px] uppercase tracking-widest font-bold text-sidebar-primary mt-1">Corporate Treasury</span>
          </div>
        </div>
      </div>

      <!-- Navigation Menu -->
      <nav class="menu flex-1 overflow-y-auto scrollbar-hide p-4 space-y-2">
        <label *ngIf="!effectivelyCollapsed" class="text-xs font-bold text-sidebar-foreground/40 uppercase tracking-wider px-3 mb-2 block">Main Menu</label>
        
        <div class="menu-block">
          <!-- Main Menu Item -->
          <button 
            class="menu-button w-full flex items-center px-4 py-3 rounded-xl transition-all duration-300 group relative overflow-hidden" 
            [ngClass]="{
              'bg-sidebar-primary/20 text-white shadow-lg shadow-sidebar-primary/5 ring-1 ring-sidebar-primary/20': activeMenu === 'hedge-accounting',
              'text-sidebar-foreground hover:bg-white/5 hover:text-white': activeMenu !== 'hedge-accounting'
            }"
            (click)="toggleGroup(); onMenuItemClick({key: 'hedge-accounting', label: 'Hedge Accounting SFX'})">
            
            <div class="absolute inset-0 bg-gradient-to-r from-sidebar-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" *ngIf="activeMenu !== 'hedge-accounting'"></div>

            <div class="icon-text flex items-center gap-4 relative z-10">
              <i class="pi pi-chart-line text-[20px]" [class.text-sidebar-primary]="activeMenu === 'hedge-accounting'" [class.mr-0]="effectivelyCollapsed"></i>
              <span *ngIf="!effectivelyCollapsed" class="text-sm font-semibold tracking-wide">Hedge Accounting SFX</span>
            </div>
            <i *ngIf="!effectivelyCollapsed" class="pi text-xs ml-auto transition-transform duration-300 relative z-10" 
               [class.pi-chevron-down]="groupExpanded" 
               [class.pi-chevron-right]="!groupExpanded"
               [class.text-sidebar-foreground]="activeMenu !== 'hedge-accounting'"
               [class.text-sidebar-primary]="activeMenu === 'hedge-accounting'"></i>
          </button>

          <!-- Submenu Items (only visible when expanded) -->
          <div *ngIf="!effectivelyCollapsed && groupExpanded" class="submenu pl-4 mt-2 space-y-1 relative">
            <div class="absolute left-6 top-0 bottom-0 w-px bg-white/10"></div>
            
            <a routerLink="/hedge/dashboard" 
               routerLinkActive="text-sidebar-primary bg-white/5"
               class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium text-sidebar-foreground/70 hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3"
               (click)="onMenuItemClick({key: 'dashboard', label: 'Analytics'})">
              <i class="pi pi-th-large text-[16px]"></i>
              Analytics
            </a>
            <a 
              [ngClass]="{
                'text-sidebar-primary bg-white/5': isRouteActive('/configuration'),
                'text-sidebar-foreground/70': !isRouteActive('/configuration')
              }"
              class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3 cursor-pointer"
              (click)="onMenuItemClick({key: 'configuration', label: 'Configuration'})">
              <i class="pi pi-cog text-[16px]"></i>
              Configuration
            </a>
            <a routerLink="/operations" 
               routerLinkActive="text-sidebar-primary bg-white/5"
               class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium text-sidebar-foreground/70 hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3"
               (click)="onMenuItemClick({key: 'operations', label: 'Operations'})">
              <i class="pi pi-briefcase text-[16px]"></i>
              Operations
            </a>
            <a routerLink="/hedge/reports" 
               routerLinkActive="text-sidebar-primary bg-white/5"
               class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium text-sidebar-foreground/70 hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3"
               (click)="onMenuItemClick({key: 'reports', label: 'Reports'})">
              <i class="pi pi-file-pdf text-[16px]"></i>
              Reports
            </a>
            <a routerLink="/hawk-agent" 
               routerLinkActive="text-sidebar-primary bg-white/5"
               class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium text-sidebar-foreground/70 hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3"
               (click)="onMenuItemClick({key: 'hawk-agent', label: 'HAWK Agent'})">
              <i class="pi pi-microchip-ai text-[16px]"></i>
              HAWK Agent
            </a>
            <a routerLink="/audit" 
               routerLinkActive="text-sidebar-primary bg-white/5"
               class="block py-2.5 px-4 ml-6 rounded-lg text-[13px] font-medium text-sidebar-foreground/70 hover:text-white hover:bg-white/5 transition-all duration-200 flex items-center gap-3"
               (click)="onMenuItemClick({key: 'audit', label: 'Audit & System Logs'})">
              <i class="pi pi-history text-[16px]"></i>
              Audit & System Logs
            </a>
          </div>
        </div>
      </nav>

      <!-- Footer -->
      <div class="nav-footer p-4 bg-black/20 backdrop-blur-sm border-t border-white/5">
        <!-- Collapse Toggle -->
        <button 
          (click)="toggleCollapse.emit()"
          class="menu-button w-full flex items-center justify-center p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-sidebar-foreground hover:text-white transition-all duration-200 mb-3 group">
          <i class="pi group-hover:scale-110 transition-transform" [class.pi-angle-left]="!effectivelyCollapsed" [class.pi-angle-right]="effectivelyCollapsed"></i>
        </button>

        <!-- User Profile -->
        <div class="profile flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group">
          <div class="profile-pic w-9 h-9 rounded-full bg-gradient-to-br from-sidebar-primary to-blue-600 flex items-center justify-center text-sm font-bold text-white shadow-lg ring-2 ring-white/10 group-hover:ring-sidebar-primary/50 transition-all">
            <span>SL</span>
          </div>
          <div *ngIf="!effectivelyCollapsed" class="flex flex-col overflow-hidden">
            <span class="truncate font-semibold text-sm text-white group-hover:text-sidebar-primary transition-colors">Sensie Larusso</span>
            <span class="text-xs text-sidebar-foreground/50">Admin User</span>
          </div>
        </div>
      </div>
    </aside>
  `
})
export class MainSidebarComponent implements OnInit, OnChanges {
  @Input() isCollapsed = false;
  @Output() toggleCollapse = new EventEmitter<void>();
  @Output() menuItemClick = new EventEmitter<any>();

  activeMenu: string = 'hedge-accounting';
  groupExpanded: boolean = true;
  effectivelyCollapsed: boolean = false;

  constructor(private router: Router, private layoutService: LayoutService) {
    // Update effective collapsed state based on both collapsed and hover states
    this.updateEffectiveCollapsedState();
  }

  ngOnInit() {
    this.updateEffectiveCollapsedState();
  }

  ngOnChanges() {
    this.updateEffectiveCollapsedState();
  }

  private updateEffectiveCollapsedState() {
    this.effectivelyCollapsed = this.layoutService.isMainSidebarEffectivelyCollapsed();
  }

  onMouseEnter() {
    this.layoutService.setMainSidebarHovered(true);
    this.updateEffectiveCollapsedState();
  }

  onMouseLeave() {
    this.layoutService.setMainSidebarHovered(false);
    this.updateEffectiveCollapsedState();
  }

  onMenuItemClick(menuItem: any) {
    this.activeMenu = menuItem.key;
    this.layoutService.setNavigationInProgress(true);
    this.menuItemClick.emit(menuItem);

    // Complete navigation after a short delay to allow route change
    setTimeout(() => {
      this.layoutService.completeNavigation();
      this.updateEffectiveCollapsedState();
    }, 1000);
  }

  toggleGroup() {
    this.groupExpanded = !this.groupExpanded;
  }

  isRouteActive(route: string): boolean {
    return this.router.url.includes(route);
  }
}
