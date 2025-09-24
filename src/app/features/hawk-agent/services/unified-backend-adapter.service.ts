import { Injectable } from '@angular/core';
import { Observable, Subject, BehaviorSubject, from } from 'rxjs';
import { map, tap, catchError, switchMap } from 'rxjs/operators';
import { UnifiedBackendService, UnifiedBackendRequest } from '../../../services/unified-backend.service';
import { HawkAgentSimpleService, SimpleHawkSession } from './hawk-agent-simple.service';
import { environment } from '../../../../environments/environment';

export interface UnifiedStreamingResponse {
  type: 'data' | 'complete' | 'error' | 'ping';
  content?: string;
  metadata?: any;
  error?: string;
}

export interface BackendPerformanceMetrics {
  response_time_ms: number;
  cache_hit_rate: string;
  extraction_time_ms: number;
  total_records: number;
  backend_type: 'unified' | 'legacy';
}

@Injectable({
  providedIn: 'root'
})
export class UnifiedBackendAdapterService {
  private streamingSubject = new BehaviorSubject<UnifiedStreamingResponse | null>(null);
  private performanceSubject = new BehaviorSubject<BackendPerformanceMetrics | null>(null);
  private backendHealthSubject = new BehaviorSubject<boolean>(false);
  
  public streaming$ = this.streamingSubject.asObservable();
  public performance$ = this.performanceSubject.asObservable();
  public backendHealth$ = this.backendHealthSubject.asObservable();

  private useUnifiedBackend = true;
  private currentSession: SimpleHawkSession | null = null;

  constructor(
    private unifiedBackendService: UnifiedBackendService,
    private hawkAgentSimpleService: HawkAgentSimpleService
  ) {
    this.checkBackendAvailability();
    this.subscribeToUnifiedStreaming();
  }

  /**
   * Main method that existing components can call - it decides which backend to use
   */
  async processPrompt(params: {
    promptText: string;
    msgUid: string;
    instructionId: string;
    templateCategory?: string;
    templateIndex?: number;
    extractedFields?: Record<string, any>;
  }): Promise<SimpleHawkSession> {
    console.log(' Processing prompt via adapter:', {
      backend: this.useUnifiedBackend ? 'Unified Smart Backend' : 'Legacy Dify',
      template: params.templateCategory,
      fields: Object.keys(params.extractedFields || {})
    });

    // Create session using existing service
    const session = await this.hawkAgentSimpleService.createSession(
      params.promptText,
      params.msgUid,
      params.instructionId,
      params.templateCategory,
      params.templateIndex
    );
    
    this.currentSession = session;

    if (this.useUnifiedBackend && this.backendHealthSubject.value) {
      return this.processWithUnifiedBackend(params, session);
    } else {
      return this.processWithLegacyBackend(params, session);
    }
  }

  /**
   * Process using Unified Smart Backend v5.0
   */
  private async processWithUnifiedBackend(
    params: {
      promptText: string;
      msgUid: string;
      instructionId: string;
      templateCategory?: string;
      extractedFields?: Record<string, any>;
    },
    session: SimpleHawkSession
  ): Promise<SimpleHawkSession> {
    const startTime = Date.now();
    
    try {
      // Extract parameters from template fields and prompt
      const extractedParams = this.extractSmartParameters(params.promptText, params.extractedFields);
      
      // Build unified backend request
      const unifiedRequest: UnifiedBackendRequest = {
        user_prompt: params.promptText,
        template_category: params.templateCategory || this.detectTemplateCategory(params.promptText) || undefined,
        ...extractedParams
      };

      console.log(' Sending to Unified Backend:', {
        template_category: unifiedRequest.template_category,
        currency: unifiedRequest.currency,
        amount: unifiedRequest.amount
      });

      // Start streaming request
      await this.unifiedBackendService.processPromptStreaming(unifiedRequest);

      // Update session with unified backend flag
      await this.hawkAgentSimpleService.updateSession(params.msgUid, {
        metadata: {
          ...session.metadata,
          unified_backend: true,
          processing_start: new Date().toISOString(),
          request_params: unifiedRequest
        }
      });

      return session;
    } catch (error) {
      console.error(' Unified backend processing failed, falling back to legacy:', error);
      
      // Automatic fallback to legacy backend
      this.useUnifiedBackend = false;
      return this.processWithLegacyBackend(params, session);
    }
  }

  /**
   * Process using legacy Dify backend (existing logic)
   */
  private async processWithLegacyBackend(
    params: {
      promptText: string;
      msgUid: string;
      instructionId: string;
      templateCategory?: string;
    },
    session: SimpleHawkSession
  ): Promise<SimpleHawkSession> {
    console.log(' Processing with legacy Dify backend');
    
    // Update session with legacy flag
    await this.hawkAgentSimpleService.updateSession(params.msgUid, {
      metadata: {
        ...session.metadata,
        legacy_backend: true,
        processing_start: new Date().toISOString()
      }
    });

    // Emit legacy processing indicator
    this.streamingSubject.next({
      type: 'data',
      content: '[Processing with legacy backend...]',
      metadata: { backend_type: 'legacy' }
    });

    return session;
  }

  /**
   * Subscribe to unified backend streaming responses
   */
  private subscribeToUnifiedStreaming(): void {
    this.unifiedBackendService.getStreamingObservable().subscribe(chunk => {
      if (chunk.event === 'error') {
        this.streamingSubject.next({
          type: 'error',
          error: chunk.data?.error || 'Streaming error'
        });
      } else if (chunk.event === 'stream_complete') {
        this.streamingSubject.next({ type: 'complete' });
        this.completeCurrentSession();
      } else if (chunk.event === 'ping') {
        this.streamingSubject.next({ type: 'ping' });
      } else if (chunk.event === 'data' && chunk.data) {
        if (chunk.data.event === 'agent_message') {
          this.streamingSubject.next({
            type: 'data',
            content: chunk.data.answer || '',
            metadata: chunk.data
          });
        } else if (chunk.data.event === 'message_end') {
          this.performanceSubject.next({
            response_time_ms: chunk.data.metadata?.latency || 0,
            cache_hit_rate: 'N/A', // Will be updated from backend stats
            extraction_time_ms: 0, // Will be updated from analysis metadata
            total_records: 0,
            backend_type: 'unified'
          });
          this.streamingSubject.next({ type: 'complete' });
          this.completeCurrentSession(chunk.data.metadata);
        }
      }
    });
  }

  /**
   * Complete current session with performance data
   */
  private async completeCurrentSession(metadata?: any): Promise<void> {
    if (!this.currentSession) return;

    try {
      await this.hawkAgentSimpleService.updateSession(this.currentSession.msg_uid, {
        agent_status: 'completed',
        agent_response: {
          completion_time: new Date().toISOString(),
          backend_type: this.useUnifiedBackend ? 'unified' : 'legacy',
          metadata: metadata
        }
      });

      console.log(' Session completed:', this.currentSession.msg_uid);
    } catch (error) {
      console.error(' Failed to complete session:', error);
    }
  }

  /**
   * Check if Unified Backend is available
   */
  private async checkBackendAvailability(): Promise<void> {
    try {
      const isHealthy = await this.unifiedBackendService.checkBackendConnectivity();
      this.backendHealthSubject.next(isHealthy);
      
      if (isHealthy) {
        console.log(' Unified Backend is available');
        this.useUnifiedBackend = environment.unifiedBackend?.enabled !== false;
      } else {
        console.log(' Unified Backend unavailable, using legacy');
        this.useUnifiedBackend = false;
      }
    } catch (error) {
      console.error(' Backend health check failed:', error);
      this.backendHealthSubject.next(false);
      this.useUnifiedBackend = false;
    }
  }

  /**
   * Extract smart parameters from prompt text and template fields
   */
  private extractSmartParameters(promptText: string, extractedFields?: Record<string, any>): Partial<UnifiedBackendRequest> {
    const params: Partial<UnifiedBackendRequest> = {};

    // Use extracted fields from template preview component
    if (extractedFields) {
      if (extractedFields['currency']) params.currency = extractedFields['currency'];
      if (extractedFields['amount']) params.amount = parseFloat(extractedFields['amount']);
      if (extractedFields['date']) params.transaction_date = extractedFields['date'];
      if (extractedFields['nav_type']) params.nav_type = extractedFields['nav_type'];
      if (extractedFields['entity_scope']) params.entity_scope = extractedFields['entity_scope'];
      if (extractedFields['hedge_method']) params.hedge_method = extractedFields['hedge_method'];
    }

    // Smart extraction from prompt text as fallback - commented out until method is implemented
    // const smartExtraction = this.unifiedBackendService.extractPromptParameters(promptText);
    // if (!params.currency && smartExtraction.currency) params.currency = smartExtraction.currency;
    // if (!params.amount && smartExtraction.amount) params.amount = smartExtraction.amount;
    // if (!params.nav_type && smartExtraction.navType) params.nav_type = smartExtraction.navType;
    // if (!params.hedge_method && smartExtraction.hedgeMethod) params.hedge_method = smartExtraction.hedgeMethod;

    return params;
  }

  /**
   * Smart template category detection
   */
  private detectTemplateCategory(promptText: string): string | null {
    // Smart template category detection - simplified until backend method is implemented
    if (promptText.toLowerCase().includes('hedge')) return 'hedge_accounting';
    if (promptText.toLowerCase().includes('risk')) return 'risk_management';
    if (promptText.toLowerCase().includes('compliance')) return 'compliance';
    return 'analysis';
  }

  /**
   * Get current streaming response
   */
  getCurrentStreamingResponse(): UnifiedStreamingResponse | null {
    return this.streamingSubject.value;
  }

  /**
   * Get current performance metrics
   */
  getCurrentPerformanceMetrics(): BackendPerformanceMetrics | null {
    return this.performanceSubject.value;
  }

  /**
   * Check if unified backend is enabled and healthy
   */
  isUnifiedBackendActive(): boolean {
    return this.useUnifiedBackend && this.backendHealthSubject.value;
  }

  /**
   * Manually toggle backend preference (for testing)
   */
  toggleBackendPreference(): void {
    this.useUnifiedBackend = !this.useUnifiedBackend;
    console.log(' Backend preference toggled to:', this.useUnifiedBackend ? 'Unified' : 'Legacy');
  }

  /**
   * Get backend performance stats
   */
  async getPerformanceStats(): Promise<any> {
    if (!this.isUnifiedBackendActive()) {
      return { backend_type: 'legacy', stats: 'Legacy backend performance not tracked' };
    }

    try {
      const [systemStatus, cacheStats] = await Promise.all([
        this.unifiedBackendService.getSystemStatus().toPromise(),
        this.unifiedBackendService.getCacheStats().toPromise()
      ]);

      return {
        backend_type: 'unified',
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
    if (!this.isUnifiedBackendActive()) {
      console.warn(' Cache clearing only available with Unified Backend');
      return;
    }

    try {
      await this.unifiedBackendService.clearCacheForCurrency(currency).toPromise();
      console.log(` Cache cleared for ${currency}`);
    } catch (error) {
      console.error(' Failed to clear cache:', error);
      throw error;
    }
  }

  /**
   * Reset adapter state
   */
  resetState(): void {
    this.streamingSubject.next(null);
    this.performanceSubject.next(null);
    this.currentSession = null;
    this.unifiedBackendService.resetStreaming();
  }

  /**
   * Get backend status for UI display
   */
  getBackendStatus(): {
    type: 'unified' | 'legacy';
    healthy: boolean;
    url?: string;
    performance?: BackendPerformanceMetrics | null;
  } {
    return {
      type: this.useUnifiedBackend ? 'unified' : 'legacy',
      healthy: this.backendHealthSubject.value,
      url: this.useUnifiedBackend ? this.unifiedBackendService.getBackendUrl() : undefined,
      performance: this.performanceSubject.value
    };
  }
}