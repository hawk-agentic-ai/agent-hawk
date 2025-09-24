import { Injectable } from '@angular/core';
import { getSupabase } from '../../../core/data/supabase.client';

export interface AgentConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  thinking_time?: string;
}

export interface AgentConversation {
  id?: number;
  conversation_id: string;
  user_id: string;
  title: string;
  messages: AgentConversationMessage[];
  message_count: number;
  created_at?: string;
  updated_at?: string;
  status: 'active' | 'archived';
}

@Injectable({
  providedIn: 'root'
})
export class HawkAgentConversationsService {

  // Create a new conversation
  async createConversation(conversationId: string, userMessage: string, title: string): Promise<AgentConversation> {
    const conversation: Omit<AgentConversation, 'id'> = {
      conversation_id: conversationId,
      user_id: 'test-user',
      title: title,
      messages: [{
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      }],
      message_count: 1,
      status: 'active'
    };

    console.log('🚀 Creating conversation:', conversationId);
    
    try {
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('hawk_agent_conversations')
        .insert([conversation])
        .select()
        .single();

      if (error) {
        console.error('❌ Error creating conversation:', error);
        throw error;
      }

      console.log('✅ Conversation created successfully:', data);
      return data;
    } catch (error) {
      console.error('❌ Failed to create conversation:', error);
      throw error;
    }
  }

  // Add message to existing conversation
  async addMessage(conversationId: string, message: AgentConversationMessage, thinkingTime?: string): Promise<void> {
    try {
      const supabase = getSupabase();
      
      // First get current conversation
      const { data: currentConv, error: fetchError } = await supabase
        .from('hawk_agent_conversations')
        .select('messages, message_count')
        .eq('conversation_id', conversationId)
        .single();

      if (fetchError || !currentConv) {
        console.error('❌ Error fetching conversation:', fetchError);
        throw fetchError;
      }

      // Add thinking time if provided (for assistant messages)
      if (thinkingTime && message.role === 'assistant') {
        message.thinking_time = thinkingTime;
      }

      // Update messages array
      const updatedMessages = [...currentConv.messages, message];
      
      // Update conversation with new message
      const { error: updateError } = await supabase
        .from('hawk_agent_conversations')
        .update({
          messages: updatedMessages,
          message_count: updatedMessages.length,
          updated_at: new Date().toISOString()
        })
        .eq('conversation_id', conversationId);

      if (updateError) {
        console.error('❌ Error updating conversation:', updateError);
        throw updateError;
      }

      console.log('✅ Message added to conversation:', conversationId);
    } catch (error) {
      console.error('❌ Failed to add message:', error);
      throw error;
    }
  }

  // Get all conversations for a user
  async getConversations(userId: string = 'test-user'): Promise<AgentConversation[]> {
    try {
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('hawk_agent_conversations')
        .select('*')
        .eq('user_id', userId)
        .eq('status', 'active')
        .order('updated_at', { ascending: false });

      if (error) {
        console.error('❌ Error fetching conversations:', error);
        throw error;
      }

      console.log(`✅ Loaded ${data?.length || 0} conversations`);
      return data || [];
    } catch (error) {
      console.error('❌ Failed to load conversations:', error);
      return [];
    }
  }

  // Get a specific conversation by ID
  async getConversation(conversationId: string): Promise<AgentConversation | null> {
    try {
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('hawk_agent_conversations')
        .select('*')
        .eq('conversation_id', conversationId)
        .single();

      if (error) {
        console.error('❌ Error fetching conversation:', error);
        return null;
      }

      return data;
    } catch (error) {
      console.error('❌ Failed to load conversation:', error);
      return null;
    }
  }

  // Delete a conversation (soft delete by archiving)
  async deleteConversation(conversationId: string): Promise<void> {
    try {
      const supabase = getSupabase();
      const { error } = await supabase
        .from('hawk_agent_conversations')
        .update({ 
          status: 'archived',
          updated_at: new Date().toISOString()
        })
        .eq('conversation_id', conversationId);

      if (error) {
        console.error('❌ Error archiving conversation:', error);
        throw error;
      }

      console.log('✅ Conversation archived:', conversationId);
    } catch (error) {
      console.error('❌ Failed to archive conversation:', error);
      throw error;
    }
  }

  // Search conversations by title or content
  async searchConversations(query: string, userId: string = 'test-user'): Promise<AgentConversation[]> {
    try {
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('hawk_agent_conversations')
        .select('*')
        .eq('user_id', userId)
        .eq('status', 'active')
        .or(`title.ilike.%${query}%,messages::text.ilike.%${query}%`)
        .order('updated_at', { ascending: false });

      if (error) {
        console.error('❌ Error searching conversations:', error);
        throw error;
      }

      console.log(`✅ Found ${data?.length || 0} conversations matching "${query}"`);
      return data || [];
    } catch (error) {
      console.error('❌ Failed to search conversations:', error);
      return [];
    }
  }

  // Generate conversation title from first message (helper method)
  generateConversationTitle(firstMessage: string): string {
    if (!firstMessage) return 'New Conversation';
    
    // Take first 60 characters and add ellipsis if longer
    let title = firstMessage.length > 60 ? firstMessage.substring(0, 57) + '...' : firstMessage;
    
    // Remove line breaks and normalize whitespace
    title = title.replace(/\s+/g, ' ').trim();
    
    return title || 'Untitled Conversation';
  }

  // Generate unique conversation ID (helper method)
  generateConversationId(): string {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }
}