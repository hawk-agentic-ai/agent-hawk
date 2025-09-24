import { Injectable } from '@angular/core';
import { getSupabase } from 'src/app/core/data/supabase.client';

export interface HedgeBusinessEvent {
  event_id?: string;
  instruction_id?: string;
  event_type?: string;
  event_status?: string;
  stage_1a_status?: string;
  stage_1a_start_time?: string;
  stage_1a_completion_time?: string;
  stage_2_status?: string;
  stage_2_start_time?: string;
  stage_2_completion_time?: string;
  stage_3_status?: string;
  stage_3_start_time?: string;
  stage_3_completion_time?: string;
  assigned_booking_model?: string;
  expected_deal_count?: number;
  actual_deal_count?: number;
  created_date?: string;
  created_by?: string;
  updated_date?: string;
  updated_by?: string;
}

@Injectable({ providedIn: 'root' })
export class HedgeBusinessEventsService {
  private table = 'hedge_business_events';
  private channel: any;

  async list(params?: {
    search?: string;
    status?: string | null;
    fromDate?: string | null;
    toDate?: string | null;
    limit?: number;
  }) {
    try {
      const supabase = getSupabase();
      let q = supabase.from(this.table).select('*').order('created_date', { ascending: false });

      if (params?.limit) {
        q = q.limit(params.limit);
      } else {
        q = q.limit(1000);
      }

      if (params?.search?.trim()) {
        const s = params.search.trim();
        q = q.or(`event_id.ilike.%${s}%,instruction_id.ilike.%${s}%,event_type.ilike.%${s}%,event_status.ilike.%${s}%,assigned_booking_model.ilike.%${s}%`);
      }

      if (params?.status) {
        q = q.eq('event_status', params.status);
      }

      if (params?.fromDate) {
        q = q.gte('created_date', params.fromDate);
      }

      if (params?.toDate) {
        q = q.lte('created_date', params.toDate);
      }

      const { data, error } = await q;
      if (error) throw error;
      return (data as HedgeBusinessEvent[]) || [];
    } catch (e) {
      console.error('Failed to load hedge_business_events', e);
      return [];
    }
  }

  subscribeRealtime(onChange: () => void) {
    try {
      const supabase = getSupabase();
      this.channel = supabase
        .channel('hedge_business_events_changes')
        .on('postgres_changes', { event: '*', schema: 'public', table: this.table }, () => onChange())
        .subscribe();
    } catch (e) {
      console.warn('Realtime subscription unavailable for hedge_business_events', e);
    }
  }

  async add(payload: Partial<HedgeBusinessEvent>) {
    const supabase = getSupabase();
    const { error } = await supabase.from(this.table).insert([payload]);
    if (error) throw error;
  }

  async updateById(event_id: string, changes: Partial<HedgeBusinessEvent>) {
    const supabase = getSupabase();
    const { error } = await supabase.from(this.table).update(changes).eq('event_id', event_id);
    if (error) throw error;
  }

  async deleteById(event_id: string) {
    const supabase = getSupabase();
    const { error } = await supabase.from(this.table).delete().eq('event_id', event_id);
    if (error) throw error;
  }

  unsubscribeRealtime() {
    if (this.channel) {
      const supabase = getSupabase();
      supabase.removeChannel(this.channel);
      this.channel = null;
    }
  }
}