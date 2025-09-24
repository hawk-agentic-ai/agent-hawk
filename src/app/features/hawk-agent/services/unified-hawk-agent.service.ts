import { Injectable } from '@angular/core';
import { Observable, Subject, BehaviorSubject } from 'rxjs';
import { map, tap, catchError } from 'rxjs/operators';
import { UnifiedBackendService, UnifiedBackendRequest, StreamingChunk } from '../../../services/unified-backend.service';
import { HawkAgentService, HawkAgentSession } from './hawk-agent.service';

export interface UnifiedHawkResponse {
  success: boolean;
  streaming: boolean;
  sessionId?: string;
  response?: string;
  metadata?: {
    intent: string;
    confidence: number;
    extraction_time_ms: number;
    cache_hit_rate: string;
    total_records: number;
  };
  error?: string;
}

export interface StreamingResponse {
  event: string;
  data: any;
  complete: boolean;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UnifiedHawkAgentService {
  private streamingSubject = new BehaviorSubject<StreamingResponse | null>(null);
  private currentSessionSubject = new BehaviorSubject<HawkAgentSession | null>(null);
  
  public streamingResponse$ = this.streamingSubject.asObservable();
  public currentSession$ = this.currentSessionSubject.asObservable();

  constructor(
    private unifiedBackendService: UnifiedBackendService,
    private hawkAgentService: HawkAgentService
  ) {
    // Subscribe to streaming responses from unified backend
    this.unifiedBackendService.getStreamingObservable().subscribe(
      (chunk: StreamingChunk) => this.handleStreamingChunk(chunk)
    );
  }

  /**
   * Process a template-based prompt using the Unified Smart Backend
   */
  async processTemplate(params: {
    promptText: string;
    templateCategory: string;
    templateIndex: number;
    msgUid: string;
    instructionId: string;
    amount?: number;
    currency?: string;
    transactionDate?: string;
    entityScope?: string;
    navType?: string;
    hedgeMethod?: string;
  }): Promise<HawkAgentSession> {
    console.log(' Processing template with Unified Backend:', {
      template: params.templateCategory,
      currency: params.currency,
      amount: params.amount
    });

    // Create session in database first
    const sessionData = this.hawkAgentService.createSessionFromTemplate(
      params.msgUid,
      params.instructionId,
      params.promptText,
      params.templateCategory,
      params.templateIndex,
      params.amount,
      params.currency,
      params.transactionDate,
      params.entityScope
    );

    let session: HawkAgentSession;
    try {
      session = await this.hawkAgentService.createSession(sessionData);
      this.currentSessionSubject.next(session);
      console.log(' Session created:', session.id);
    } catch (error) {
      console.error(' Failed to create session:', error);
      throw error;
    }

    // Prepare request for Unified Backend
    const unifiedRequest: UnifiedBackendRequest = {
      user_prompt: params.promptText,
      template_category: params.templateCategory,
      currency: params.currency,
      nav_type: params.navType,
      amount: params.amount,
      entity_scope: params.entityScope,
      transaction_date: params.transactionDate,
      hedge_method: params.hedgeMethod
    };

    try {
      // Start streaming request
      await this.unifiedBackendService.processPromptStreaming(unifiedRequest);
      
      // Update session as processing
      await this.hawkAgentService.updateSession(session.id!, {
        agent_status: 'pending',
        metadata: {
          ...session.metadata,
          unified_backend: true,
          processing_start: new Date().toISOString()
        }
      });

      return session;
    } catch (error) {
      console.error(' Unified Backend processing failed:', error);
      
      // Update session as failed
      await this.hawkAgentService.updateSession(session.id!, {
        agent_status: 'failed',
        error_details: {
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString()
        }
      });

      throw error;
    }
  }

  /**
   * Process a free-form agent prompt
   */
  async processAgentPrompt(params: {
    promptText: string;
    msgUid: string;
    instructionId: string;
    templateCategory?: string;
  }): Promise<HawkAgentSession> {
    console.log(' Processing agent prompt with Unified Backend:', {
      prompt: params.promptText.substring(0, 100) + '...',
      detectedCategory: params.templateCategory
    });

    // Create session for agent mode
    const sessionData = {
      msg_uid: params.msgUid,
      instruction_id: params.instructionId,
      user_id: 'test-user-v2',
      session_type: 'agent' as const,
      agent_status: 'pending' as const,
      template_category: params.templateCategory,
      agent_start_time: new Date().toISOString(),
      metadata: {
        prompt_text: params.promptText,
        unified_backend: true,
        smart_template_detection: true
      }
    };

    let session: HawkAgentSession;
    try {
      session = await this.hawkAgentService.createSession(sessionData);
      this.currentSessionSubject.next(session);
      console.log(' Agent session created:', session.id);
    } catch (error) {
      console.error(' Failed to create agent session:', error);
      throw error;
    }

    try {
      // Use smart prompt processing
      await this.unifiedBackendService.processSmartPrompt(params.promptText, {
        template_category: params.templateCategory
      });

      return session;
    } catch (error) {
      console.error(' Agent processing failed:', error);
      
      await this.hawkAgentService.updateSession(session.id!, {
        agent_status: 'failed',
        error_details: {
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString()
        }
      });

      throw error;
    }
  }

  /**
   * Handle streaming chunks from the unified backend
   */
  private handleStreamingChunk(chunk: StreamingChunk): void {
    console.log(' Processing streaming chunk:', chunk);

    if (chunk.event === 'error') {
      this.streamingSubject.next({
        event: 'error',
        data: chunk.data,
        complete: true,
        error: chunk.data?.error || 'Streaming error'
      });
      this.completeCurrentSession('failed', chunk.data);
      return;
    }

    if (chunk.event === 'stream_complete') {
      this.streamingSubject.next({
        event: 'complete',
        data: null,
        complete: true
      });
      this.completeCurrentSession('completed');
      return;
    }

    if (chunk.event === 'ping') {
      // Handle ping events
      this.streamingSubject.next({
        event: 'ping',
        data: null,
        complete: false
      });
      return;
    }

    if (chunk.event === 'data' && chunk.data) {
      // Handle different types of data chunks
      if (chunk.data.event === 'agent_message') {
        this.streamingSubject.next({
          event: 'agent_message',
          data: {
            answer: chunk.data.answer,
            conversation_id: chunk.data.conversation_id,
            message_id: chunk.data.message_id,
            created_at: chunk.data.created_at
          },
          complete: false
        });
      } else if (chunk.data.event === 'agent_thought') {
        this.streamingSubject.next({
          event: 'agent_thought',
          data: {
            thought: chunk.data.thought,
            observation: chunk.data.observation,
            tool: chunk.data.tool
          },
          complete: false
        });
      } else if (chunk.data.event === 'message_end') {
        this.streamingSubject.next({
          event: 'message_end',
          data: {
            conversation_id: chunk.data.conversation_id,
            message_id: chunk.data.message_id,
            metadata: chunk.data.metadata
          },
          complete: false
        });
        this.completeCurrentSession('completed', chunk.data.metadata);
      }
    }
  }

  /**
   * Complete the current session
   */
  private async completeCurrentSession(status: 'completed' | 'failed', metadata?: any): Promise<void> {
    const currentSession = this.currentSessionSubject.value;
    if (!currentSession?.id) return;

    try {
      const updatedSession = await this.hawkAgentService.updateSession(currentSession.id, {
        agent_status: status,
        agent_end_time: new Date().toISOString(),
        metadata: {
          ...currentSession.metadata,
          completion_metadata: metadata,
          unified_backend_performance: metadata?.usage || null
        }
      });

      this.currentSessionSubject.next(updatedSession);
      console.log(` Session ${status}:`, updatedSession.id);
    } catch (error) {
      console.error(' Failed to complete session:', error);
    }
  }

  /**
   * Get current streaming state
   */
  getCurrentStreamingResponse(): StreamingResponse | null {
    return this.streamingSubject.value;
  }

  /**
   * Get current session
   */
  getCurrentSession(): HawkAgentSession | null {
    return this.currentSessionSubject.value;
  }

  /**
   * Check backend connectivity
   */
  async checkBackendHealth(): Promise<boolean> {
    try {
      await this.unifiedBackendService.getHealthStatus().toPromise();
      return true;
    } catch (error) {
      console.error(' Backend health check failed:', error);
      return false;
    }
  }

  /**
   * Get performance statistics
   */
  async getPerformanceStats(): Promise<any> {
    try {
      const [systemStatus, cacheStats] = await Promise.all([
        this.unifiedBackendService.getSystemStatus().toPromise(),
        this.unifiedBackendService.getCacheStats().toPromise()
      ]);

      return {
        system: systemStatus,
        cache: cacheStats,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error(' Failed to get performance stats:', error);
      throw error;
    }
  }

  /**
   * Clear cache for specific currency
   */
  async clearCurrencyCache(currency: string): Promise<void> {
    try {
      const result = await this.unifiedBackendService.clearCacheForCurrency(currency).toPromise();
      console.log(' Cache cleared:', result);
    } catch (error) {
      console.error(' Failed to clear cache:', error);
      throw error;
    }
  }

  /**
   * Reset service state
   */
  resetState(): void {
    this.streamingSubject.next(null);
    this.currentSessionSubject.next(null);
    this.unifiedBackendService.resetStreaming();
  }

  /**
   * Extract key parameters from prompt for optimization
   */
  extractPromptParameters(prompt: string): {
    currency?: string;
    amount?: number;
    hedgeMethod?: string;
    navType?: string;
  } {
    const promptLower = prompt.toLowerCase();
    
    // Extract currency
    const currencyMatch = prompt.match(/\b(USD|EUR|GBP|JPY|CNY|CHF|CAD|AUD)\b/i);
    const currency = currencyMatch ? currencyMatch[1].toUpperCase() : undefined;

    // Extract amount
    const amountMatch = prompt.match(/\$?([\d,]+(?:\.\d{2})?)/);
    const amount = amountMatch ? parseFloat(amountMatch[1].replace(/,/g, '')) : undefined;

    // Extract hedge method
    let hedgeMethod: string | undefined;
    if (promptLower.includes('coh') || promptLower.includes('cash on hand')) hedgeMethod = 'COH';
    else if (promptLower.includes('coi') || promptLower.includes('cost of investment')) hedgeMethod = 'COI';
    else if (promptLower.includes('forward')) hedgeMethod = 'FWD';
    else if (promptLower.includes('swap')) hedgeMethod = 'SWAP';

    // Extract NAV type
    let navType: string | undefined;
    if (promptLower.includes('coi')) navType = 'COI';
    else if (promptLower.includes('nav')) navType = 'NAV';
    else if (promptLower.includes('asset')) navType = 'ASSET';

    return {
      currency,
      amount,
      hedgeMethod,
      navType
    };
  }
}