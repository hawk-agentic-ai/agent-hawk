import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/hedge/dashboard',
    pathMatch: 'full'
  },
  { path: 'hedge/positions', redirectTo: '/hedge/dashboard/positions-nav', pathMatch: 'full' },
  {
    path: 'hedge/dashboard',
    loadComponent: () => import('./features/hedge/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  // SFX Positions table hidden; using Positions NAV read-only view under Analytics
  { path: 'hedge/dashboard/positions-nav', loadComponent: () => import('./features/configuration/positions-nav/positions-nav.component').then(m => m.PositionsNavComponent) },
  { path: 'hedge/dashboard/hedging-instruments', loadComponent: () => import('./features/analytics/hedging-instruments/hedging-instruments.component').then(m => m.HedgingInstrumentsComponent) },
  { path: 'hedge/dashboard/hedge-effectiveness', loadComponent: () => import('./features/analytics/hedge-effectiveness/hedge-effectiveness.component').then(m => m.HedgeEffectivenessComponent) },
  { path: 'hedge/dashboard/threshold-monitoring', loadComponent: () => import('./features/analytics/threshold-monitoring/threshold-monitoring.component').then(m => m.ThresholdMonitoringComponent) },
  { path: 'hedge/dashboard/performance-metrics', loadComponent: () => import('./features/analytics/performance-metrics/performance-metrics.component').then(m => m.PerformanceMetricsComponent) },
  { path: 'hedge/dashboard/exceptions-alerts', loadComponent: () => import('./features/analytics/exceptions-alerts/exceptions-alerts.component').then(m => m.ExceptionsAlertsComponent) },
  { path: 'hedge/dashboard/regulatory-reporting', loadComponent: () => import('./features/analytics/regulatory-reporting/regulatory-reporting.component').then(m => m.RegulatoryReportingComponent) },
  {
    path: 'configuration',
    loadChildren: () => import('./features/configuration/configuration.routes').then(m => m.configurationRoutes)
  }
  ,
  { path: 'hawk-agent', redirectTo: 'hawk-agent/prompt-templates', pathMatch: 'full' },
  // Use enhanced version with unified smart backend (now working!)
  { path: 'hawk-agent/prompt-templates', loadComponent: () => import('./features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component').then(m => m.EnhancedPromptTemplatesV2Component) },
  // All legacy routes redirect to the main enhanced version
  { path: 'hawk-agent/prompt-templates-enhanced', redirectTo: 'hawk-agent/prompt-templates', pathMatch: 'full' },
  { path: 'hawk-agent/prompt-templates-v2', redirectTo: 'hawk-agent/prompt-templates', pathMatch: 'full' },
  { path: 'hawk-agent/prompt-templates-legacy', redirectTo: 'hawk-agent/prompt-templates', pathMatch: 'full' },
  { path: 'hawk-agent/prompt-history', loadComponent: () => import('./features/hawk-agent/prompt-history/prompt-history.component').then(m => m.PromptHistoryComponent) },
  { path: 'hawk-agent/manual-mode', loadComponent: () => import('./features/hawk-agent/manual-mode/manual-mode.component').then(m => m.ManualModeComponent) },
  { path: 'hawk-agent/agent-mode', loadComponent: () => import('./features/hawk-agent/agent-mode/agent-mode.component').then(m => m.AgentModeComponent) },
  // Operations
  { path: 'operations', redirectTo: 'operations/hedge-instructions', pathMatch: 'full' },
  { path: 'operations/hedge-instructions', loadComponent: () => import('./features/operations/hedge-instructions/hedge-instructions.component').then(m => m.HedgeInstructionsComponent) },
  { path: 'operations/hedge-business-events', loadComponent: () => import('./features/operations/hedge-business-events/hedge-business-events.component').then(m => m.HedgeBusinessEventsComponent) },
  { path: 'operations/apportionment-table', loadComponent: () => import('./features/operations/apportionment-table/apportionment-table.component').then(m => m.ApportionmentTableComponent) },
  { path: 'operations/murex-booking', loadComponent: () => import('./features/operations/murex-booking/murex-booking.component').then(m => m.MurexBookingComponent) },
  { path: 'operations/accounting-hub', loadComponent: () => import('./features/operations/accounting-hub/accounting-hub.component').then(m => m.AccountingHubComponent) },
  { path: 'operations/externalization-management', loadComponent: () => import('./features/operations/externalization-management/externalization-management.component').then(m => m.ExternalizationManagementComponent) },
  { path: 'operations/daily-monitoring', loadComponent: () => import('./features/operations/daily-monitoring/daily-monitoring.component').then(m => m.DailyMonitoringComponent) },
  { path: 'operations/hedge-failure-management', loadComponent: () => import('./features/operations/hedge-failure-management/hedge-failure-management.component').then(m => m.HedgeFailureManagementComponent) }
  ,
  // Audit & System Logs
  { path: 'audit', redirectTo: 'audit/audit-logs', pathMatch: 'full' },
  { path: 'audit/audit-logs', loadComponent: () => import('./features/audit/audit-logs/audit-logs.component').then(m => m.AuditLogsComponent) },
  { path: 'audit/system-logs', loadComponent: () => import('./features/audit/system-logs/system-logs.component').then(m => m.SystemLogsComponent) },
  { path: 'audit/data-lineage', loadComponent: () => import('./features/audit/data-lineage/data-lineage.component').then(m => m.DataLineageComponent) },
  { path: 'audit/config-change-history', loadComponent: () => import('./features/audit/config-change-history/config-change-history.component').then(m => m.ConfigChangeHistoryComponent) }
];