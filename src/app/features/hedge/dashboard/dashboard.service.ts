import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { getSupabase } from '../../../core/data/supabase.client';

export type DashboardMetrics = {
  totalHedged: number;
  totalHedgedChangePct?: number; // vs previous day
  hedgeEffectiveness: number; // 0-100
  hedgeEffectivenessChangePct?: number; // vs previous month
  activeEntities: number;
  activeEntitiesChange?: number; // delta vs previous day
  riskAlerts: number;
  riskAlertsChange?: number; // delta vs previous day
  currencyBreakdown: Array<{ label: string; value: number }>;
  positionValueOverTime: Array<{ label: string; value: number; currency?: string }>;
  navVsPosition: Array<{ label: string; nav: number; position: number; currency?: string }>;
  entityExposure: Array<{ label: string; value: number; currency?: string }>;
  hedgeCoverageRatio: Array<{ label: string; value: number; currency?: string }>;
  positionStatusDistribution: Array<{ label: string; value: number; color: string; currency?: string }>;
  rawData?: any[]; // Add raw data for filtering
};

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private supabase = getSupabase();
  private table = 'position_nav_master';

  private _metrics = new BehaviorSubject<DashboardMetrics | null>(null);
  readonly metrics$ = this._metrics.asObservable();

  private channel: ReturnType<typeof this.supabase.channel> | null = null;
  private currentCurrencyFilter?: string;

  async init() {
    await this.refresh();
    // subscribe to realtime changes
    this.channel = this.supabase
      .channel('position_nav_master_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: this.table }, async () => {
        await this.refresh(this.currentCurrencyFilter);
      })
      .subscribe();
  }

  async refreshWithCurrencyFilter(currencyFilter?: string) {
    this.currentCurrencyFilter = currencyFilter;
    await this.refresh(currencyFilter);
  }

  async refresh(currencyFilter?: string) {
    const { data, error } = await this.supabase
      .from(this.table)
      .select('*');
    if (error) return; // silently ignore for now
    let rows = data || [] as any[];
    
    // Apply currency filter if specified
    if (currencyFilter) {
      rows = rows.filter(r => r.currency_code === currencyFilter);
    }

    // KPI: total hedged  sum of current_position (fallback to 0)
    const totalHedged = rows.reduce((sum, r) => sum + (Number(r.current_position) || 0), 0);

    // KPI: active entities  distinct non-null entity_id
    const entities = new Set<string>();
    rows.forEach(r => { if (r.entity_id) entities.add(r.entity_id); });
    const activeEntities = entities.size;

    // KPI: risk alerts  rows with data_quality_status not null and not in ['ok','normal']
    const riskAlerts = rows.filter(r => r.data_quality_status && !['ok', 'normal', 'good'].includes(String(r.data_quality_status).toLowerCase())).length;

    // Hedge effectiveness: aggregate by month ratio (sum(current_position)/sum(computed_total_nav)) and take last month as headline
    const perfByMonth = new Map<string, { hedged: number; nav: number }>();
    rows.forEach(r => {
      const d = r.as_of_date ? new Date(r.as_of_date) : null;
      if (!d) return;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const m = perfByMonth.get(key) || { hedged: 0, nav: 0 };
      m.hedged += Number(r.current_position) || 0;
      m.nav += Number(r.computed_total_nav) || 0;
      perfByMonth.set(key, m);
    });
    
    // Position Value Over Time - daily aggregation of positions
    const positionByDate = new Map<string, number>();
    rows.forEach(r => {
      const d = r.as_of_date ? new Date(r.as_of_date) : null;
      if (!d) return;
      const key = d.toISOString().split('T')[0]; // YYYY-MM-DD format
      positionByDate.set(key, (positionByDate.get(key) || 0) + (Number(r.current_position) || 0));
    });
    const positionValueOverTimeEntries = Array.from(positionByDate.entries())
      .sort((a, b) => a[0] < b[0] ? -1 : 1)
      .slice(-30); // Last 30 days
    const positionValueOverTime = positionValueOverTimeEntries.map(([k, v]) => ({ label: new Date(k).toLocaleDateString(), value: Math.abs(v) }));

    // NAV vs Position Comparison - daily comparison
    const navPositionByDate = new Map<string, { nav: number; position: number }>();
    rows.forEach(r => {
      const d = r.as_of_date ? new Date(r.as_of_date) : null;
      if (!d) return;
      const key = d.toISOString().split('T')[0];
      const existing = navPositionByDate.get(key) || { nav: 0, position: 0 };
      existing.nav += Number(r.computed_total_nav) || 0;
      existing.position += Number(r.current_position) || 0;
      navPositionByDate.set(key, existing);
    });
    const navVsPositionEntries = Array.from(navPositionByDate.entries())
      .sort((a, b) => a[0] < b[0] ? -1 : 1)
      .slice(-15); // Last 15 days for clarity
    const navVsPosition = navVsPositionEntries.map(([k, v]) => ({ label: new Date(k).toLocaleDateString(), nav: Math.abs(v.nav), position: Math.abs(v.position) }));

    // Entity Exposure Distribution - top 10 entities by absolute position value
    const byEntity = new Map<string, number>();
    rows.forEach(r => {
      const entity = r.entity_id || 'Unknown';
      byEntity.set(entity, (byEntity.get(entity) || 0) + Math.abs(Number(r.current_position) || 0));
    });
    // Entity Exposure  Top N with Others bucket
    const sortedEnt = Array.from(byEntity.entries()).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const TOP_ENT = 10;
    const topEnt = sortedEnt.slice(0, TOP_ENT);
    const othersEnt = sortedEnt.slice(TOP_ENT);
    const entityExposure = topEnt.map(([label, value]) => ({ label, value }));
    if (othersEnt.length) {
      const othersVal = othersEnt.reduce((s, [, v]) => s + v, 0);
      entityExposure.push({ label: 'Others', value: othersVal });
    }

    // Hedge Coverage Ratio Trend - daily coverage ratios
    const hedgeCoverageRatio = Array.from(navPositionByDate.entries())
      .sort((a, b) => a[0] < b[0] ? -1 : 1)
      .slice(-15)
      .map(([k, v]) => ({ 
        label: new Date(k).toLocaleDateString(), 
        value: v.nav > 0 ? +((Math.abs(v.position) / Math.abs(v.nav)) * 100).toFixed(2) : 0 
      }));

    // Position Status Distribution - count by data quality status
    const statusCounts = new Map<string, number>();
    const statusColors = new Map<string, string>([
      ['ok', '#10B981'], ['good', '#10B981'], ['normal', '#10B981'],
      ['warning', '#F59E0B'], ['alert', '#EF4444'], ['error', '#EF4444'],
      ['unknown', '#6B7280'], ['pending', '#3B82F6']
    ]);
    rows.forEach(r => {
      const status = r.data_quality_status ? String(r.data_quality_status).toLowerCase() : 'unknown';
      statusCounts.set(status, (statusCounts.get(status) || 0) + 1);
    });
    const positionStatusDistribution = Array.from(statusCounts.entries())
      .map(([label, value]) => ({ 
        label: label.charAt(0).toUpperCase() + label.slice(1), 
        value, 
        color: statusColors.get(label) || '#6B7280' 
      }))
      .sort((a, b) => b.value - a.value);

    const hedgeEffSeries = Array.from(perfByMonth.entries())
      .sort((a, b) => a[0] < b[0] ? -1 : 1)
      .map(([k, v]) => ({ label: k, value: v.nav > 0 ? +(100 * v.hedged / v.nav).toFixed(2) : 0 }));
    const hedgeEffectiveness = hedgeEffSeries.slice(-1)[0]?.value || 0;
    const hedgeEffectivenessPrev = hedgeEffSeries.slice(-2, -1)[0]?.value ?? hedgeEffectiveness;

    // Currency breakdown  sum current_position by currency_code (top 6)
    const byCcy = new Map<string, number>();
    rows.forEach(r => {
      const c = r.currency_code || 'UNK';
      byCcy.set(c, (byCcy.get(c) || 0) + (Number(r.current_position) || 0));
    });
    // Currency breakdown  Top N with Others bucket
    const sortedCcy = Array.from(byCcy.entries()).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const TOP_CCY = 6;
    const topCcy = sortedCcy.slice(0, TOP_CCY);
    const othersCcy = sortedCcy.slice(TOP_CCY);
    const currencyBreakdown = topCcy.map(([label, value]) => ({ label, value }));
    if (othersCcy.length) {
      const othersVal = othersCcy.reduce((s, [, v]) => s + v, 0);
      currencyBreakdown.push({ label: 'Others', value: othersVal });
    }

    // KPI changes
    const prevDayTotal = positionValueOverTimeEntries.slice(-2, -1)[0]?.[1] ?? totalHedged;
    const totalHedgedChangePct = prevDayTotal !== 0 ? +(((totalHedged - prevDayTotal) / Math.abs(prevDayTotal)) * 100).toFixed(1) : 0;
    const activeEntitiesPrev = activeEntities; // without historical series, treat change as 0
    const riskAlertsPrev = riskAlerts; // same

    this._metrics.next({ 
      totalHedged, 
      totalHedgedChangePct,
      hedgeEffectiveness, 
      hedgeEffectivenessChangePct: +(hedgeEffectiveness - hedgeEffectivenessPrev).toFixed(1),
      activeEntities, 
      activeEntitiesChange: activeEntities - activeEntitiesPrev,
      riskAlerts, 
      riskAlertsChange: riskAlerts - riskAlertsPrev,
      currencyBreakdown, 
      positionValueOverTime,
      navVsPosition,
      entityExposure,
      hedgeCoverageRatio,
      positionStatusDistribution,
      rawData: data || []
    });
  }

  destroy() {
    if (this.channel) {
      this.supabase.removeChannel(this.channel);
      this.channel = null;
    }
  }
}
