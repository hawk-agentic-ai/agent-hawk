import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, Subject, from } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface UnifiedBackendRequest {
  user_prompt: string;
  template_category?: string;
  currency?: string;
  nav_type?: string;
  amount?: number;
  entity_scope?: string;
  transaction_date?: string;
  hedge_method?: string;
  // All other fields optional - no mandatory constraints
}

export interface UnifiedBackendResponse {
  success: boolean;
  streaming_url?: string;
  session_id?: string;
  analysis_metadata?: {
    intent: string;
    confidence: number;
    data_scope: string;
    tables_requested: number;
    tables_fetched: number;
    cache_hits: number;
    cache_misses: number;
    cache_hit_rate: string;
    extraction_time_ms: number;
    redis_available: boolean;
    total_records: number;
  };
  error?: string;
}

export interface SystemStatus {
  application: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  components: {
    supabase: {
      status: string;
      total_entities: number;
    };
    redis: {
      status: string;
      keys_count: number;
      memory_usage: string;
    };
    prompt_engine: {
      status: string;
    };
    data_extractor: {
      status: string;
      cache_stats: CacheStats;
    };
  };
}

export interface CacheStats {
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: string;
  redis_available: boolean;
  total_requests: number;
  avg_extraction_time_ms: number;
  optimization_target: string;
  redis_memory_usage?: string;
  redis_keys_count?: number;
}

export interface StreamingChunk {
  event: string;
  data: any;
  id?: string;
  raw?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UnifiedBackendService {
  private readonly BACKEND_URL = environment.unifiedBackendUrl;
  private streamingSubject = new Subject<StreamingChunk>();
  
  public streamingResponse$ = this.streamingSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Process prompt with the Unified Smart Backend
   * Supports all template categories without mandatory field constraints
   */
  processPrompt(request: UnifiedBackendRequest): Observable<any> {
    const url = `${this.BACKEND_URL}/hawk-agent/process-prompt`;
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });

    console.log(' Sending request to Unified Backend:', {
      url,
      request: {
        user_prompt: request.user_prompt,
        template_category: request.template_category,
        currency: request.currency,
        // Log key fields without exposing all data
      }
    });

    return this.http.post(url, request, { 
      headers,
      observe: 'response',
      responseType: 'text' // Handle streaming text response
    }).pipe(
      tap(response => {
        console.log(' Unified Backend Response received:', {
          status: response.status,
          headers: response.headers.keys(),
          bodyPreview: response.body?.substring(0, 200) + '...'
        });
      }),
      catchError(error => {
        console.error(' Unified Backend Error:', error);
        throw error;
      })
    );
  }

  /**
   * Process prompt with streaming response handling
   * Uses native Fetch API for better streaming support
   */
  async processPromptStreaming(request: UnifiedBackendRequest): Promise<void> {
    const url = `${this.BACKEND_URL}/hawk-agent/process-prompt`;
    
    console.log(' Starting streaming request to Unified Backend:', {
      user_prompt: request.user_prompt,
      template_category: request.template_category,
      currency: request.currency
    });

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body reader available');
      }

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log(' Streaming complete');
          this.streamingSubject.next({ event: 'stream_complete', data: null });
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.trim()) {
            try {
              // Parse Server-Sent Events format
              if (line.startsWith('data: ')) {
                const data = line.substring(6);
                
                if (data === 'event: ping') {
                  // Handle ping events
                  this.streamingSubject.next({ event: 'ping', data: null });
                  continue;
                }

                // Try to parse JSON data
                let parsedData;
                try {
                  parsedData = JSON.parse(data);
                } catch {
                  // If not JSON, treat as plain text
                  parsedData = { text: data };
                }

                console.log(' Streaming chunk:', parsedData);
                this.streamingSubject.next({ 
                  event: 'data', 
                  data: parsedData,
                  raw: line
                });
              }
            } catch (parseError) {
              console.warn(' Failed to parse streaming chunk:', line, parseError);
              this.streamingSubject.next({ 
                event: 'raw_data', 
                data: line,
                raw: line
              });
            }
          }
        }
      }
    } catch (error) {
      console.error(' Streaming request failed:', error);
      this.streamingSubject.next({ 
        event: 'error', 
        data: { error: error instanceof Error ? error.message : 'Unknown error' }
      });
      throw error;
    }
  }

  /**
   * Get system health status
   */
  getHealthStatus(): Observable<{ status: string; version: string; timestamp: string; components: any; cache_stats: any }> {
    const url = `${this.BACKEND_URL}/health`;
    return this.http.get<any>(url).pipe(
      tap(response => {
        console.log(' Health Status:', response);
      }),
      catchError(error => {
        console.error(' Health check failed:', error);
        throw error;
      })
    );
  }

  /**
   * Get detailed system status
   */
  getSystemStatus(): Observable<SystemStatus> {
    const url = `${this.BACKEND_URL}/system/status`;
    return this.http.get<SystemStatus>(url).pipe(
      tap(response => {
        console.log(' System Status:', {
          version: response.version,
          components: Object.keys(response.components),
          cache_hit_rate: response.components.data_extractor.cache_stats.cache_hit_rate
        });
      }),
      catchError(error => {
        console.error(' System status failed:', error);
        throw error;
      })
    );
  }

  /**
   * Get cache performance statistics
   */
  getCacheStats(): Observable<CacheStats> {
    const url = `${this.BACKEND_URL}/cache/stats`;
    return this.http.get<CacheStats>(url).pipe(
      tap(response => {
        console.log(' Cache Stats:', {
          hit_rate: response.cache_hit_rate,
          total_requests: response.total_requests,
          avg_time: response.avg_extraction_time_ms + 'ms',
          redis_available: response.redis_available
        });
      }),
      catchError(error => {
        console.error(' Cache stats failed:', error);
        throw error;
      })
    );
  }

  /**
   * Clear cache for specific currency
   */
  clearCacheForCurrency(currency: string): Observable<{ message: string; keys_cleared: number; timestamp: string }> {
    const url = `${this.BACKEND_URL}/cache/clear/${currency.toUpperCase()}`;
    return this.http.post<any>(url, {}).pipe(
      tap(response => {
        console.log(` Cache cleared for ${currency}:`, response);
      }),
      catchError(error => {
        console.error(` Cache clear failed for ${currency}:`, error);
        throw error;
      })
    );
  }

  /**
   * Test prompt analysis capabilities
   */
  testPromptAnalysis(prompt: string, category?: string): Observable<any> {
    const url = `${this.BACKEND_URL}/prompt-analysis/test`;
    const params = new URLSearchParams();
    params.set('prompt', prompt);
    if (category) params.set('category', category);
    
    return this.http.get<any>(`${url}?${params.toString()}`).pipe(
      tap(response => {
        console.log(' Prompt Analysis:', response);
      }),
      catchError(error => {
        console.error(' Prompt analysis failed:', error);
        throw error;
      })
    );
  }

  /**
   * Smart template detection based on user input
   * Helps frontend auto-select appropriate template category
   */
  detectTemplateCategory(userPrompt: string): string | null {
    const prompt = userPrompt.toLowerCase();

    // Hedge instructions patterns (I-U-R-T-A-Q)
    if (prompt.match(/\b(start|begin|create|initiate|inception)\b.*\b(hedge|hedging)\b/) ||
        prompt.match(/\b(new|fresh)\b.*\b(position|hedge)\b/)) {
      return 'hedge_accounting'; // Inception
    }
    
    if (prompt.match(/\b(update|modify|change|adjust|amend)\b.*\b(hedge|position)\b/) ||
        prompt.match(/\b(increase|decrease|resize)\b.*\b(hedge|position)\b/)) {
      return 'hedge_accounting'; // Update
    }
    
    if (prompt.match(/\b(remove|delete|close|terminate|end)\b.*\b(hedge|position)\b/) ||
        prompt.match(/\b(unwind|exit)\b.*\b(hedge|position)\b/)) {
      return 'hedge_accounting'; // Removal
    }
    
    if (prompt.match(/\b(transfer|move|migrate)\b.*\b(hedge|position)\b/) ||
        prompt.match(/\bfrom\b.*\bto\b.*\b(hedge|position|entity)\b/)) {
      return 'hedge_accounting'; // Transfer
    }
    
    if (prompt.match(/\b(adjust|tune|calibrate|fine-tune)\b.*\b(hedge|position)\b/) ||
        prompt.match(/\b(parameter|setting|ratio)\b.*\b(hedge|position)\b/)) {
      return 'hedge_accounting'; // Adjustment
    }
    
    if (prompt.match(/\b(check|query|status|capacity|current|what)\b.*\b(hedge|position)\b/) ||
        prompt.match(/\b(how much|available|remaining)\b.*\b(hedge|capacity)\b/)) {
      return 'hedge_accounting'; // Query
    }

    // Risk analysis patterns
    if (prompt.match(/\b(risk|var|value at risk|exposure|volatility)\b/) ||
        prompt.match(/\b(risk analysis|risk assessment|risk report)\b/)) {
      return 'risk_analysis';
    }

    // Compliance patterns
    if (prompt.match(/\b(compliance|regulatory|regulation|audit|rule)\b/) ||
        prompt.match(/\b(violation|breach|threshold|limit)\b/)) {
      return 'compliance';
    }

    // Performance monitoring patterns
    if (prompt.match(/\b(performance|monitoring|report|analytics|metrics)\b/) ||
        prompt.match(/\b(dashboard|kpi|benchmark|trend)\b/)) {
      return 'performance';
    }

    // General monitoring patterns
    if (prompt.match(/\b(monitor|alert|exception|notification|status)\b/) ||
        prompt.match(/\b(system|health|activity|log)\b/)) {
      return 'monitoring';
    }

    return null; // Let backend handle general queries
  }

  /**
   * Enhanced request builder with smart defaults
   */
  buildSmartRequest(
    userPrompt: string, 
    overrides: Partial<UnifiedBackendRequest> = {}
  ): UnifiedBackendRequest {
    const detectedCategory = this.detectTemplateCategory(userPrompt);
    
    const smartRequest: UnifiedBackendRequest = {
      user_prompt: userPrompt,
      template_category: detectedCategory || undefined,
      ...overrides
    };

    console.log(' Smart request built:', {
      detected_category: detectedCategory,
      user_prompt_preview: userPrompt.substring(0, 50) + '...',
      final_category: smartRequest.template_category
    });

    return smartRequest;
  }

  /**
   * Complete workflow: Build request + Process with streaming
   */
  async processSmartPrompt(
    userPrompt: string,
    templateOverrides: Partial<UnifiedBackendRequest> = {}
  ): Promise<void> {
    const smartRequest = this.buildSmartRequest(userPrompt, templateOverrides);
    return this.processPromptStreaming(smartRequest);
  }

  /**
   * Get streaming subject for components to subscribe to
   */
  getStreamingObservable(): Observable<StreamingChunk> {
    return this.streamingResponse$;
  }

  /**
   * Reset streaming state (call before new requests)
   */
  resetStreaming(): void {
    console.log(' Resetting streaming state');
  }

  /**
   * Check if backend is accessible
   */
  async checkBackendConnectivity(): Promise<boolean> {
    try {
      const response = await fetch(`${this.BACKEND_URL}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });
      return response.ok;
    } catch (error) {
      console.error(' Backend connectivity check failed:', error);
      return false;
    }
  }

  /**
   * Get backend URL for reference
   */
  getBackendUrl(): string {
    return this.BACKEND_URL;
  }
}
