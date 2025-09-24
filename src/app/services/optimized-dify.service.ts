import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, tap, map } from 'rxjs';
import { BackendApiService } from './backend-api.service';

export interface DifyOptimizationMetrics {
  total_time_ms: number;
  context_prep_time_ms: number;
  dify_response_time_ms: number;
  context_source: 'cache' | 'fresh';
  context_size_chars?: number;
  cache_hit_rate_percent?: number;
}

export interface DifyOptimizedResponse {
  success: boolean;
  dify_response?: any;
  context_metadata: any;
  performance_metrics: DifyOptimizationMetrics;
  error?: string;
}

export interface DifyPerformanceStats {
  service_performance: {
    total_requests: number;
    cache_hits: number;
    avg_context_prep_time: number;
    avg_dify_response_time: number;
    cache_hit_rate_percent: number;
  };
  cache_health: {
    total_keys: number;
    memory_used_human: string;
    key_distribution: Record<string, number>;
  };
  timestamp: string;
}

@Injectable({
  providedIn: 'root'
})
export class OptimizedDifyService {
  private performanceMetricsSubject = new BehaviorSubject<DifyOptimizationMetrics | null>(null);
  private performanceStatsSubject = new BehaviorSubject<DifyPerformanceStats | null>(null);
  
  public performanceMetrics$ = this.performanceMetricsSubject.asObservable();
  public performanceStats$ = this.performanceStatsSubject.asObservable();

  constructor(private backendApiService: BackendApiService) {
    // Load performance stats on service initialization
    this.loadPerformanceStats();
  }

  /**
   * Send optimized query to Dify with context pre-loading
   */
  sendOptimizedQuery(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposure_currency: string;
    hedge_method?: string;
    nav_type?: string;
    currency_type?: string;
    use_cache?: boolean;
    max_context_size?: number;
    include_historical?: boolean;
  }): Observable<DifyOptimizedResponse> {
    const startTime = Date.now();
    
    return this.backendApiService.sendToDifyOptimized(params).pipe(
      tap((response: DifyOptimizedResponse) => {
        // Update performance metrics
        if (response.success && response.performance_metrics) {
          this.performanceMetricsSubject.next(response.performance_metrics);
        }
        
        // Log performance improvement
        console.log(' Optimized Dify Response:', {
          success: response.success,
          contextSource: response.performance_metrics?.context_source,
          totalTime: response.performance_metrics?.total_time_ms,
          contextPrepTime: response.performance_metrics?.context_prep_time_ms,
          difyResponseTime: response.performance_metrics?.dify_response_time_ms
        });
      }),
      catchError(error => {
        console.error('Optimized Dify query failed:', error);
        throw error;
      })
    );
  }

  /**
   * Stream optimized query to Dify with context pre-loading
   */
  streamOptimizedQuery(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposure_currency: string;
    hedge_method?: string;
    nav_type?: string;
    currency_type?: string;
    use_cache?: boolean;
    max_context_size?: number;
    include_historical?: boolean;
  }): Observable<any> {
    return this.backendApiService.streamDifyResponseOptimized(params).pipe(
      tap(response => {
        console.log(' Streaming optimized Dify response:', response);
      }),
      catchError(error => {
        console.error('Optimized Dify streaming failed:', error);
        throw error;
      })
    );
  }

  /**
   * Load and track performance statistics
   */
  loadPerformanceStats(): void {
    this.backendApiService.getDifyPerformanceStats().pipe(
      tap((stats: DifyPerformanceStats) => {
        this.performanceStatsSubject.next(stats);
        console.log(' Dify Performance Stats:', {
          totalRequests: stats.service_performance.total_requests,
          cacheHitRate: stats.service_performance.cache_hit_rate_percent,
          avgResponseTime: stats.service_performance.avg_dify_response_time,
          avgContextPrepTime: stats.service_performance.avg_context_prep_time,
          cacheMemory: stats.cache_health.memory_used_human
        });
      }),
      catchError(error => {
        console.error('Failed to load performance stats:', error);
        throw error;
      })
    ).subscribe();
  }

  /**
   * Invalidate cache for specific currency
   */
  invalidateCurrencyCache(currency: string): Observable<any> {
    return this.backendApiService.invalidateCurrencyCache(currency).pipe(
      tap(response => {
        console.log(` Cache invalidated for ${currency}:`, response);
        // Reload performance stats after cache invalidation
        this.loadPerformanceStats();
      }),
      catchError(error => {
        console.error(`Cache invalidation failed for ${currency}:`, error);
        throw error;
      })
    );
  }

  /**
   * Compare performance between optimized and legacy calls
   */
  performanceComparison(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposure_currency: string;
    hedge_method?: string;
    nav_type?: string;
    currency_type?: string;
  }): Observable<{
    optimized: DifyOptimizedResponse;
    legacy: any;
    improvement: {
      time_saved_ms: number;
      time_saved_percent: number;
      cache_benefit: boolean;
    };
  }> {
    const legacyStartTime = Date.now();
    const legacyParams = {
      query: params.query,
      msgUid: params.msgUid + '_legacy',
      instructionId: params.instructionId,
      amount: 0,
      currency: params.exposure_currency,
      date: new Date().toISOString()
    };

    const optimizedStartTime = Date.now();
    const optimizedParams = {
      ...params,
      use_cache: true
    };

    // Run both calls and compare
    const legacyCall = this.backendApiService.sendToDify(legacyParams).pipe(
      map(response => ({
        response,
        duration: Date.now() - legacyStartTime
      }))
    );

    const optimizedCall = this.sendOptimizedQuery(optimizedParams);

    return new Observable(observer => {
      Promise.all([
        legacyCall.toPromise(),
        optimizedCall.toPromise()
      ]).then(([legacyResult, optimizedResult]) => {
        const timeSaved = legacyResult!.duration - (optimizedResult!.performance_metrics.total_time_ms || 0);
        const timeSavedPercent = (timeSaved / legacyResult!.duration) * 100;

        observer.next({
          optimized: optimizedResult!,
          legacy: legacyResult!.response,
          improvement: {
            time_saved_ms: timeSaved,
            time_saved_percent: Math.round(timeSavedPercent * 100) / 100,
            cache_benefit: optimizedResult!.performance_metrics.context_source === 'cache'
          }
        });
        observer.complete();
      }).catch(error => {
        observer.error(error);
      });
    });
  }

  /**
   * Get current performance metrics
   */
  getCurrentMetrics(): DifyOptimizationMetrics | null {
    return this.performanceMetricsSubject.value;
  }

  /**
   * Get current performance stats
   */
  getCurrentStats(): DifyPerformanceStats | null {
    return this.performanceStatsSubject.value;
  }

  /**
   * Detect optimal settings based on query characteristics
   */
  getOptimalSettings(query: string): {
    max_context_size: number;
    include_historical: boolean;
    use_cache: boolean;
    estimated_complexity: 'minimal' | 'focused' | 'comprehensive';
  } {
    const queryLower = query.toLowerCase();
    
    // Detect query complexity
    const complexityIndicators = {
      comprehensive: ['comprehensive', 'detailed', 'full', 'complete', 'all', 'analysis', 'report'],
      minimal: ['current', 'status', 'quick', 'simple', 'brief'],
      historical: ['history', 'past', 'previous', 'trend', 'over time']
    };

    let complexity: 'minimal' | 'focused' | 'comprehensive' = 'focused';
    
    if (complexityIndicators.comprehensive.some(word => queryLower.includes(word))) {
      complexity = 'comprehensive';
    } else if (complexityIndicators.minimal.some(word => queryLower.includes(word))) {
      complexity = 'minimal';
    }

    const includeHistorical = complexityIndicators.historical.some(word => queryLower.includes(word));

    return {
      max_context_size: complexity === 'comprehensive' ? 75000 : 
                       complexity === 'focused' ? 50000 : 25000,
      include_historical: includeHistorical,
      use_cache: false, // Disabled - Dify handles caching internally
      estimated_complexity: complexity
    };
  }

  /**
   * Smart query optimization based on prompt analysis
   */
  smartOptimizedQuery(params: {
    query: string;
    msgUid: string;
    instructionId: string;
    exposure_currency: string;
    hedge_method?: string;
    nav_type?: string;
    currency_type?: string;
  }): Observable<DifyOptimizedResponse> {
    // Get optimal settings based on query
    const optimalSettings = this.getOptimalSettings(params.query);
    
    console.log(' Smart optimization settings:', optimalSettings);

    // Merge with optimal settings
    const optimizedParams = {
      ...params,
      ...optimalSettings
    };

    return this.sendOptimizedQuery(optimizedParams);
  }
}