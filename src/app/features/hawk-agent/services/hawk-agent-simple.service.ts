import { Injectable } from '@angular/core';
import { getSupabase } from '../../../core/data/supabase.client';

export interface SimpleHawkSession {
  id?: number;
  msg_uid: string;
  instruction_id: string;
  user_id: string;
  session_type: 'template' | 'agent';
  agent_status: 'pending' | 'completed' | 'failed';
  template_category?: string;
  template_index?: number;
  metadata?: any;
  agent_response?: any;
  created_at?: Date | string;
  updated_at?: Date | string;
}

@Injectable({
  providedIn: 'root'
})
export class HawkAgentSimpleService {

  // Create a new session
  async createSession(promptText: string, msgUid: string, instructionId: string, templateCategory?: string, templateIndex?: number): Promise<SimpleHawkSession> {
    const payload: any = {
      msg_uid: msgUid,
      instruction_id: instructionId,
      user_id: 'test-user',
      session_type: templateCategory === 'agent' ? 'agent' : 'template',
      agent_status: 'pending',
      // Remove agent_start_time - let database default handle it
      template_category: templateCategory || 'template',
      template_index: templateIndex || 1,
      metadata: { prompt_text: promptText }
    };
    
    console.log('🚀 Creating session with payload:', payload);
    
    try {
      const supabase = getSupabase();
      console.log('📡 Supabase client initialized:', !!supabase);
      
      // Use upsert on msg_uid to avoid 409 conflicts if a duplicate msg_uid arrives
      const { data, error } = await supabase
        .from('hawk_agent_sessions')
        .upsert([payload], { onConflict: 'msg_uid' })
        .select();
      
      console.log('✅ Supabase upsert result:', { data, error });
      
      if (error) {
        console.error('❌ Supabase error details:', {
          message: error.message,
          details: error.details,
          hint: error.hint,
          code: error.code
        });
        throw error;
      }
      
      console.log('✅ Session created successfully:', data);
      
    } catch (error) {
      console.error('❌ createSession: Failed to save to Supabase:', error);
      console.error('🔍 Check if hawk_agent_sessions table exists and has correct permissions');
      console.error('📊 Payload that failed:', payload);
      console.error('🔗 Full error object:', JSON.stringify(error, null, 2));
      // proceed without throwing to avoid blocking UI, but make error visible
    }
    return {
      msg_uid: msgUid,
      instruction_id: instructionId,
      user_id: 'test-user',
      session_type: templateCategory === 'agent' ? 'agent' : 'template',
      agent_status: 'pending',
      template_category: templateCategory || 'template',
      template_index: templateIndex || 1,
      metadata: { prompt_text: promptText },
      created_at: new Date().toISOString()
    } as SimpleHawkSession;
  }

  // Get all sessions
  async getSessions(): Promise<SimpleHawkSession[]> {
    try {
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('hawk_agent_sessions')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('❌ getSessions: Failed to fetch from Supabase:', error);
      console.error('🔍 Check if hawk_agent_sessions table exists and has correct permissions');
      // Return empty array instead of throwing to avoid breaking UI
      return [];
    }
  }

  // Update session
  async updateSession(msgUid: string, updates: any): Promise<void> {
    try {
      const supabase = getSupabase();
      const { error } = await supabase.from('hawk_agent_sessions').update(updates).eq('msg_uid', msgUid);
      if (error) throw error;
    } catch (error) {
      console.warn('updateSession: non-fatal error:', error);
    }
  }
}
