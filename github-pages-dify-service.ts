import { Injectable } from '@angular/core';
import { Observable, from } from 'rxjs';
import { map, catchError, tap } from 'rxjs/operators';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ClientSideOptimizationService, OptimizedContextData, ClientOptimizationMetrics } from './client-side-optimization.service';

export interface GitHubPagesDifyResponse {
  success: boolean;
  response: any;
  metrics: ClientOptimizationMetrics;
  optimization_applied: boolean;
  context_reduction: number;
  cache_used: boolean;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class GitHubPagesDifyService {
  private readonly DIFY_API_URL = 'https://api.dify.ai/v1/chat-messages';
  private readonly DIFY_API_KEY = 'app-sF86KavXxF9u2HwQx5JpM4TK'; // Move to environment

  constructor(
    private http: HttpClient,
    private clientOptimizer: ClientSideOptimizationService
  ) {}

  /**
   * Send optimized Dify request that works with GitHub Pages
   */
  sendOptimizedDifyRequest(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposureCurrency: string;
    hedgeMethod?: string;
    navType?: string;
    currencyType?: string;
    useOptimization?: boolean;
  }): Observable<GitHubPagesDifyResponse> {
    
    const startTime = Date.now();
    const useOptimization = params.useOptimization !== false;
    
    console.log(' GitHub Pages optimized Dify request:', {
      ...params,
      optimization: useOptimization ? 'enabled' : 'disabled'
    });

    if (useOptimization) {
      // Use client-side optimization
      return from(this.sendWithClientOptimization(params, startTime));
    } else {
      // Use legacy direct Dify call
      return this.sendDirectDifyRequest(params, startTime);
    }
  }

  /**
   * Send request with client-side optimization
   */
  private async sendWithClientOptimization(
    params: any,
    startTime: number
  ): Promise<GitHubPagesDifyResponse> {
    
    try {
      // Step 1: Fetch and prepare optimized context
      const contextResult = await this.clientOptimizer.fetchOptimizedHedgeData(
        params.exposureCurrency,
        params.query,
        {
          hedgeMethod: params.hedgeMethod,
          navType: params.navType,
          currencyType: params.currencyType,
          useCache: true
        }
      );

      console.log(' Context optimization metrics:', contextResult.metrics);

      // Step 2: Prepare Dify payload with optimized context
      const difyPayload = {
        inputs: {
          hedge_context: JSON.stringify(contextResult.contextData, null, 2),
          msg_uid: params.msgUid,
          instruction_id: params.instructionId,
          optimization_metadata: JSON.stringify({
            optimization_applied: true,
            client_side: true,
            context_source: contextResult.metrics.cache_used ? 'cache' : 'fresh',
            data_reduction_percent: contextResult.metrics.data_reduction_percent,
            github_pages_compatible: true
          })
        },
        query: params.query,
        response_mode: 'blocking',
        conversation_id: '',
        user: `hedge_user_${params.msgUid}`,
        files: []
      };

      // Step 3: Send to Dify
      const difyStart = Date.now();
      const difyResponse = await this.callDifyAPI(difyPayload);
      const difyTime = Date.now() - difyStart;

      // Step 4: Calculate final metrics
      const totalTime = Date.now() - startTime;
      const finalMetrics: ClientOptimizationMetrics = {
        ...contextResult.metrics,
        total_time_ms: totalTime,
        dify_response_time_ms: difyTime
      };

      console.log(' GitHub Pages optimization complete:', {
        totalTime: `${totalTime}ms`,
        contextTime: `${contextResult.metrics.context_prep_time_ms}ms`,
        difyTime: `${difyTime}ms`,
        dataReduction: `${contextResult.metrics.data_reduction_percent.toFixed(1)}%`,
        cacheUsed: contextResult.metrics.cache_used
      });

      return {
        success: true,
        response: difyResponse,
        metrics: finalMetrics,
        optimization_applied: true,
        context_reduction: contextResult.metrics.data_reduction_percent,
        cache_used: contextResult.metrics.cache_used
      };

    } catch (error) {
      console.error(' Client optimization failed, falling back to direct call:', error);
      
      // Fallback to direct Dify call
      return this.sendDirectDifyRequest(params, startTime).toPromise() as Promise<GitHubPagesDifyResponse>;
    }
  }

  /**
   * Direct Dify API call (legacy/fallback)
   */
  private sendDirectDifyRequest(
    params: any,
    startTime: number
  ): Observable<GitHubPagesDifyResponse> {
    
    const enhancedQuery = `[MSG_UID: ${params.msgUid}] [INSTRUCTION_ID: ${params.instructionId}] ${params.query}`;
    
    const payload = {
      conversation_id: '',
      inputs: {
        msg_uid: params.msgUid,
        instruction_id: params.instructionId
      },
      query: enhancedQuery,
      user: 'test-user',
      response_mode: 'blocking',
      files: []
    };

    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.DIFY_API_KEY}`,
      'Content-Type': 'application/json'
    });

    const difyStart = Date.now();

    return this.http.post(this.DIFY_API_URL, payload, { headers }).pipe(
      map((response: any) => {
        const totalTime = Date.now() - startTime;
        const difyTime = Date.now() - difyStart;
        
        console.log(' Direct Dify call completed:', {
          totalTime: `${totalTime}ms`,
          difyTime: `${difyTime}ms`,
          optimization: 'none'
        });

        return {
          success: true,
          response: response,
          metrics: {
            total_time_ms: totalTime,
            data_fetch_time_ms: 0,
            context_prep_time_ms: 0,
            dify_response_time_ms: difyTime,
            data_reduction_percent: 0,
            cache_used: false
          },
          optimization_applied: false,
          context_reduction: 0,
          cache_used: false
        };
      }),
      catchError(error => {
        console.error(' Direct Dify call failed:', error);
        throw error;
      })
    );
  }

  /**
   * Streaming Dify request with optimization (for GitHub Pages)
   */
  sendOptimizedStreamingRequest(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposureCurrency: string;
    hedgeMethod?: string;
    navType?: string;
    currencyType?: string;
    useOptimization?: boolean;
  }): Observable<any> {
    
    const useOptimization = params.useOptimization !== false;
    
    if (useOptimization) {
      return from(this.streamWithClientOptimization(params));
    } else {
      return this.streamDirectDifyRequest(params);
    }
  }

  /**
   * Streaming with client-side optimization
   */
  private async streamWithClientOptimization(params: any): Promise<Observable<any>> {
    try {
      // Fetch optimized context first
      const contextResult = await this.clientOptimizer.fetchOptimizedHedgeData(
        params.exposureCurrency,
        params.query,
        {
          hedgeMethod: params.hedgeMethod,
          navType: params.navType,
          currencyType: params.currencyType,
          useCache: true
        }
      );

      console.log(' Streaming with optimized context:', contextResult.metrics);

      // Create streaming payload with optimized context
      const payload = {
        inputs: {
          hedge_context: JSON.stringify(contextResult.contextData, null, 2),
          msg_uid: params.msgUid,
          instruction_id: params.instructionId
        },
        query: params.query,
        response_mode: 'streaming',
        conversation_id: '',
        user: `hedge_user_${params.msgUid}`,
        files: []
      };

      return this.streamDifyAPI(payload);

    } catch (error) {
      console.error(' Streaming optimization failed, using direct stream:', error);
      return this.streamDirectDifyRequest(params);
    }
  }

  /**
   * Direct streaming Dify request
   */
  private streamDirectDifyRequest(params: any): Observable<any> {
    const enhancedQuery = `[MSG_UID: ${params.msgUid}] [INSTRUCTION_ID: ${params.instructionId}] ${params.query}`;
    
    const payload = {
      conversation_id: '',
      inputs: {
        msg_uid: params.msgUid,
        instruction_id: params.instructionId
      },
      query: enhancedQuery,
      user: 'test-user',
      response_mode: 'streaming',
      files: []
    };

    return this.streamDifyAPI(payload);
  }

  /**
   * Call Dify API with fetch (GitHub Pages compatible)
   */
  private async callDifyAPI(payload: any): Promise<any> {
    const response = await fetch(this.DIFY_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.DIFY_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Dify API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Stream Dify API responses (GitHub Pages compatible)
   */
  private streamDifyAPI(payload: any): Observable<any> {
    return new Observable(observer => {
      fetch(this.DIFY_API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.DIFY_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      }).then(async response => {
        if (!response.ok) {
          throw new Error(`Dify API error: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            observer.next(chunk);
          }
          observer.complete();
        } catch (error) {
          observer.error(error);
        } finally {
          reader.releaseLock();
        }

      }).catch(error => {
        observer.error(error);
      });
    });
  }

  /**
   * Performance comparison between optimized and direct calls
   */
  async performanceComparison(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposureCurrency: string;
    hedgeMethod?: string;
    navType?: string;
  }): Promise<{
    optimized: GitHubPagesDifyResponse;
    direct: GitHubPagesDifyResponse;
    improvement: {
      time_saved_ms: number;
      time_saved_percent: number;
      data_reduction_percent: number;
      cache_benefit: boolean;
    };
  }> {
    
    console.log(' Running performance comparison...');

    // Run both in parallel for fair comparison
    const [optimizedResult, directResult] = await Promise.all([
      this.sendOptimizedDifyRequest({ ...params, useOptimization: true }).toPromise(),
      this.sendOptimizedDifyRequest({ ...params, msgUid: params.msgUid + '_direct', useOptimization: false }).toPromise()
    ]);

    const timeSaved = directResult!.metrics.total_time_ms - optimizedResult!.metrics.total_time_ms;
    const timeSavedPercent = (timeSaved / directResult!.metrics.total_time_ms) * 100;

    const improvement = {
      time_saved_ms: Math.max(0, timeSaved),
      time_saved_percent: Math.max(0, timeSavedPercent),
      data_reduction_percent: optimizedResult!.context_reduction,
      cache_benefit: optimizedResult!.cache_used
    };

    console.log(' Performance comparison results:', improvement);

    return {
      optimized: optimizedResult!,
      direct: directResult!,
      improvement
    };
  }

  /**
   * Get client optimization statistics
   */
  getOptimizationStats(): any {
    return this.clientOptimizer.getCacheStats();
  }

  /**
   * Clear client cache
   */
  clearCache(): void {
    this.clientOptimizer.clearCache();
  }
}