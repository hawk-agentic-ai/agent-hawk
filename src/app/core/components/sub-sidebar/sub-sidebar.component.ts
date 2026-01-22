import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { LayoutService } from '../../services/layout.service';

@Component({
  selector: 'app-sub-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside 
      class="sidenav-root sub-sidenav sidebar-transition z-30 bg-muted/30 border-r border-border backdrop-blur-md fixed inset-y-0 shadow-2xl transition-[left,width] duration-300 ease-in-out"
      [style.left]="effectiveMainSidebarWidth"
      [style.width]="effectivelyCollapsed ? '80px' : '240px'"
      [class.collapsed]="effectivelyCollapsed"
      (mouseenter)="onMouseEnter()"
      (mouseleave)="onMouseLeave()">
      
      <!-- Header -->
      <div class="nav-header border-b border-border/50 h-16 flex items-center px-4">
        <div class="header-full flex items-center gap-3 overflow-hidden" [class.justify-center]="effectivelyCollapsed">
          <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
             <i [class]="icon || 'pi pi-cog'" class="text-primary text-[20px]"></i>
          </div>
          <span *ngIf="!effectivelyCollapsed" class="text-sm font-semibold text-foreground whitespace-nowrap">{{ title || 'Configuration' }}</span>
        </div>
      </div>

      <!-- Navigation Menu -->
      <nav class="menu p-3 space-y-1 overflow-y-auto flex-1">
        <div *ngFor="let item of menuItems" class="menu-block">
          <a 
            [routerLink]="item.link || ['/configuration', item.key]"
            routerLinkActive="bg-white shadow-sm ring-1 ring-black/5 text-primary"
            [routerLinkActiveOptions]="{ exact: item.exact ?? true }"
            class="menu-button flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-white/50 transition-all cursor-pointer"
            [title]="effectivelyCollapsed ? item.label : ''"
            (click)="onMenuItemClick(item)">
            <div class="icon-text flex items-center gap-3 min-w-0">
              <i [ngClass]="item.icon" [class.mr-0]="effectivelyCollapsed" class="text-[16px] shrink-0"></i>
              <span *ngIf="!effectivelyCollapsed" class="truncate font-medium">{{ item.label }}</span>
            </div>
          </a>
        </div>
      </nav>

      <!-- Footer -->
      <div class="nav-footer p-4 border-t border-border/50">
        <!-- Collapse Toggle -->
        <button 
          (click)="toggleCollapse.emit()"
          class="menu-button w-full flex items-center justify-center p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors">
          <i class="pi" [class.pi-angle-left]="effectivelyCollapsed" [class.pi-angle-right]="!effectivelyCollapsed"></i>
        </button>
      </div>
    </aside>
  `
})
export class SubSidebarComponent implements OnInit, OnChanges {
  @Input() isCollapsed = false;
  @Input() isMainSidebarCollapsed = false;
  @Input() menuItems: any[] = [];
  @Input() title: string = 'Configuration';
  @Input() icon: string = 'pi pi-cog';
  @Output() toggleCollapse = new EventEmitter<void>();

  effectivelyCollapsed: boolean = false;
  effectiveMainSidebarWidth: string = '290px';

  // Track active submenu item using the Router
  constructor(private router: Router, private layoutService: LayoutService) {
    this.updateEffectiveStates();
  }

  ngOnInit() {
    this.updateEffectiveStates();
  }

  ngOnChanges() {
    this.updateEffectiveStates();
  }

  private updateEffectiveStates() {
    this.effectivelyCollapsed = this.layoutService.isSubSidebarEffectivelyCollapsed();
    // Match the new MainSidebar dimensions (80px collapsed / 280px expanded)
    this.effectiveMainSidebarWidth = this.layoutService.isMainSidebarEffectivelyCollapsed() ? '80px' : '280px';
  }

  onMouseEnter() {
    this.layoutService.setSubSidebarHovered(true);
    this.updateEffectiveStates();
  }

  onMouseLeave() {
    this.layoutService.setSubSidebarHovered(false);
    this.updateEffectiveStates();
  }

  isSubMenuActive(key: string): boolean {
    return this.router.url.includes(`/configuration/${key}`);
  }

  onMenuItemClick(item: any) {
    this.layoutService.setNavigationInProgress(true);

    // Complete navigation after a short delay to allow route change
    setTimeout(() => {
      this.layoutService.completeNavigation();
      this.updateEffectiveStates();
    }, 1000);
  }
}
