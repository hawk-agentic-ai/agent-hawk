import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class LayoutService {
  // Default both sidebars to collapsed; expand on hover/navigation only
  private mainSidebarCollapsed = signal(true);
  private subSidebarCollapsed = signal(true);
  private subSidebarVisible = signal(false);
  private mainSidebarHovered = signal(false);
  private subSidebarHovered = signal(false);
  private navigationInProgress = signal(false);
  // Track Agent Mode to hide sidebars
  private agentMode = signal(false);

  isMainSidebarCollapsed() {
    return this.mainSidebarCollapsed();
  }

  isSubSidebarCollapsed() {
    return this.subSidebarCollapsed();
  }

  isSubSidebarVisible() {
    return this.subSidebarVisible();
  }

  toggleMainSidebar() {
    this.mainSidebarCollapsed.update(value => !value);
  }

  toggleSubSidebar() {
    this.subSidebarCollapsed.update(value => !value);
  }

  showSubSidebar() {
    this.subSidebarVisible.set(true);
  }

  hideSubSidebar() {
    this.subSidebarVisible.set(false);
  }

  getMainSidebarWidth(): string {
    return this.isMainSidebarCollapsed() ? '80px' : '280px';
  }

  getSubSidebarWidth(): string {
    return this.isSubSidebarCollapsed() ? '80px' : '240px';
  }

  // Hover state management
  setMainSidebarHovered(hovered: boolean) {
    this.mainSidebarHovered.set(hovered);
  }

  setSubSidebarHovered(hovered: boolean) {
    this.subSidebarHovered.set(hovered);
  }

  isMainSidebarHovered() {
    return this.mainSidebarHovered();
  }

  isSubSidebarHovered() {
    return this.subSidebarHovered();
  }

  // Effective state considering hover
  isMainSidebarEffectivelyCollapsed() {
    return this.mainSidebarCollapsed() && !this.mainSidebarHovered();
  }

  isSubSidebarEffectivelyCollapsed() {
    return this.subSidebarCollapsed() && !this.subSidebarHovered();
  }

  // Navigation state management
  setNavigationInProgress(inProgress: boolean) {
    this.navigationInProgress.set(inProgress);
  }

  isNavigationInProgress() {
    return this.navigationInProgress();
  }

  // Auto-collapse after navigation
  completeNavigation() {
    this.setNavigationInProgress(false);
    // Auto-collapse both sidebars after navigation completes
    setTimeout(() => {
      if (!this.mainSidebarHovered() && !this.subSidebarHovered()) {
        this.mainSidebarCollapsed.set(true);
        this.subSidebarCollapsed.set(true);
      }
    }, 500); // 500ms delay to allow user to continue hovering if needed
  }

  // Agent Mode Management
  setAgentMode(enabled: boolean) {
    this.agentMode.set(enabled);
  }

  isAgentMode() {
    return this.agentMode();
  }
}
