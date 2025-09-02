import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, from, of, forkJoin } from 'rxjs';
import { map, catchError, tap, switchMap } from 'rxjs/operators';
import { getSupabase } from '../core/data/supabase.client';

export interface ClientOptimizationMetrics {
  total_time_ms: number;
  data_fetch_time_ms: number;
  context_prep_time_ms: number;
  dify_response_time_ms: number;
  data_reduction_percent: number;
  cache_used: boolean;
}

export interface OptimizedContextData {
  entities: any[];
  positions: any[];
  recent_allocations: any[];
  hedge_instruments: any[];
  currency_rates: any[];
  prompt_analysis: {
    currencies: string[];
    entities: string[];
    hedge_methods: string[];
    nav_types: string[];
    complexity: 'minimal' | 'focused' | 'comprehensive';
    requires_recent_data: boolean;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ClientSideOptimizationService {
  private supabase = getSupabase();
  private cache = new Map<string, { data: any; expiry: number }>();
  private performanceMetricsSubject = new BehaviorSubject<ClientOptimizationMetrics | null>(null);
  
  public performanceMetrics$ = this.performanceMetricsSubject.asObservable();

  // Cache TTL in milliseconds
  private readonly CACHE_TTL = {
    static_config: 4 * 60 * 60 * 1000,      // 4 hours
    currency_rates: 24 * 60 * 60 * 1000,     // 24 hours
    entity_positions: 2 * 60 * 60 * 1000,    // 2 hours
    hedge_data: 30 * 60 * 1000,              // 30 minutes
    prompt_context: 15 * 60 * 1000           // 15 minutes
  };

  constructor() {
    // Clean expired cache every 10 minutes
    setInterval(() => this.cleanExpiredCache(), 10 * 60 * 1000);
  }

  /**
   * Optimized data fetching with client-side caching and parallel queries
   */
  async fetchOptimizedHedgeData(
    exposureCurrency: string,
    promptText: string,
    options: {
      hedgeMethod?: string;
      navType?: string;
      currencyType?: string;
      useCache?: boolean;
    } = {}
  ): Promise<{ contextData: OptimizedContextData; metrics: ClientOptimizationMetrics }> {
    
    const startTime = Date.now();
    const useCache = options.useCache !== false;
    
    // Step 1: Analyze prompt requirements
    const promptAnalysis = this.analyzePromptRequirements(promptText);
    console.log('🧠 Prompt Analysis:', promptAnalysis);

    // Step 2: Check cache first
    const cacheKey = this.generateCacheKey('prompt_context', {
      currency: exposureCurrency,
      prompt: this.hashString(promptText),
      options: options
    });

    if (useCache) {
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        console.log('💾 Cache hit for optimized data');
        return {
          contextData: cached,
          metrics: {
            total_time_ms: Date.now() - startTime,
            data_fetch_time_ms: 0,
            context_prep_time_ms: 5,
            dify_response_time_ms: 0,
            data_reduction_percent: 0,
            cache_used: true
          }
        };
      }
    }

    // Step 3: Fetch data in parallel batches
    const dataFetchStart = Date.now();
    
    try {
      // Batch 1: Core data (parallel)
      const coreDataPromises = [
        this.fetchEntities(exposureCurrency, options.currencyType, promptAnalysis),
        this.fetchPositions(exposureCurrency, options.navType, promptAnalysis),
        this.fetchCurrencyConfig(exposureCurrency)
      ];

      const [entities, positions, currencyConfig] = await Promise.all(coreDataPromises);

      // Extract entity IDs for subsequent queries
      const entityIds = this.extractEntityIds(entities, positions);
      
      // Batch 2: Detail data (parallel, limited by prompt analysis)
      const detailDataPromises = [
        this.fetchAllocations(exposureCurrency, entityIds, promptAnalysis),
        this.fetchHedgeInstruments(exposureCurrency, options, promptAnalysis),
        this.fetchCurrencyRates(exposureCurrency, promptAnalysis)
      ];

      // Only fetch recent data if needed
      if (promptAnalysis.requires_recent_data) {
        detailDataPromises.push(
          this.fetchRecentHedgeEvents(entityIds, promptAnalysis),
          this.fetchRecentInstructions(exposureCurrency, promptAnalysis)
        );
      }

      const detailResults = await Promise.all(detailDataPromises);
      
      const dataFetchTime = Date.now() - dataFetchStart;
      
      // Step 4: Structure optimized context
      const contextPrepStart = Date.now();
      
      const originalDataSize = this.estimateDataSize(entities, positions, detailResults);
      const contextData = this.structureOptimizedContext({
        entities,
        positions,
        allocations: detailResults[0] || [],
        hedge_instruments: detailResults[1] || [],
        currency_rates: detailResults[2] || [],
        recent_hedge_events: detailResults[3] || [],
        recent_instructions: detailResults[4] || [],
        currency_config: currencyConfig
      }, promptAnalysis);
      
      const optimizedDataSize = this.estimateDataSize([contextData]);
      const dataReduction = ((originalDataSize - optimizedDataSize) / originalDataSize) * 100;
      
      const contextPrepTime = Date.now() - contextPrepStart;
      
      // Step 5: Cache the result
      if (useCache) {
        this.setCache(cacheKey, contextData, this.CACHE_TTL.prompt_context);
      }

      const totalTime = Date.now() - startTime;
      
      const metrics: ClientOptimizationMetrics = {
        total_time_ms: totalTime,
        data_fetch_time_ms: dataFetchTime,
        context_prep_time_ms: contextPrepTime,
        dify_response_time_ms: 0,
        data_reduction_percent: Math.max(0, dataReduction),
        cache_used: false
      };

      this.performanceMetricsSubject.next(metrics);
      
      console.log('⚡ Client-side optimization metrics:', metrics);

      return { contextData, metrics };

    } catch (error) {
      console.error('❌ Client-side optimization failed:', error);
      throw error;
    }
  }

  /**
   * Analyze prompt to determine data requirements
   */
  private analyzePromptRequirements(promptText: string): OptimizedContextData['prompt_analysis'] {
    const text = promptText.toLowerCase();
    
    // Extract currencies
    const currencyPattern = /\b(usd|eur|gbp|jpy|sgd|aud|chf|cad|hkd|cny|inr|krw|thb|myr|php|twd|nzd)\b/gi;
    const currencies = [...new Set((promptText.match(currencyPattern) || []).map(c => c.toUpperCase()))];
    
    // Extract entities (basic patterns)
    const entityPattern = /\b[A-Z]{2,6}\d{2,4}\b/g;
    const entities = [...new Set(promptText.match(entityPattern) || [])];
    
    // Extract hedge methods
    const hedgeMethods: string[] = [];
    if (/cash flow hedge|coh/i.test(text)) hedgeMethods.push('COH');
    if (/fair value hedge|mtm/i.test(text)) hedgeMethods.push('MTM');
    if (/net investment hedge|nih/i.test(text)) hedgeMethods.push('NIH');
    
    // Extract NAV types
    const navTypes: string[] = [];
    if (/\bcoi\b|core operating/i.test(text)) navTypes.push('COI');
    if (/\bre\b|real estate/i.test(text)) navTypes.push('RE');
    
    // Determine complexity
    let complexity: 'minimal' | 'focused' | 'comprehensive' = 'focused';
    
    const comprehensiveKeywords = ['comprehensive', 'detailed', 'full', 'complete', 'all', 'analysis', 'report'];
    const minimalKeywords = ['current', 'status', 'quick', 'simple', 'brief'];
    
    if (comprehensiveKeywords.some(word => text.includes(word))) {
      complexity = 'comprehensive';
    } else if (minimalKeywords.some(word => text.includes(word))) {
      complexity = 'minimal';
    }
    
    // Check if recent data is needed
    const requiresRecentData = /recent|latest|current|today|this week|this month/i.test(text);
    
    return {
      currencies,
      entities,
      hedge_methods: hedgeMethods,
      nav_types: navTypes,
      complexity,
      requires_recent_data: requiresRecentData
    };
  }

  /**
   * Fetch entities with optimization
   */
  private async fetchEntities(exposureCurrency: string, currencyType?: string, analysis?: any): Promise<any[]> {
    const cacheKey = this.generateCacheKey('entities', { currency: exposureCurrency, type: currencyType });
    
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    let query = this.supabase
      .from('entity_master')
      .select('*, currency_configuration(currency_type)')
      .eq('currency_code', exposureCurrency);

    if (currencyType) {
      query = query.eq('currency_configuration.currency_type', currencyType);
    }

    // Limit based on complexity
    const limit = analysis?.complexity === 'minimal' ? 5 : 
                 analysis?.complexity === 'comprehensive' ? 50 : 20;
    
    query = query.limit(limit);

    const { data, error } = await query;
    if (error) throw error;

    this.setCache(cacheKey, data || [], this.CACHE_TTL.entity_positions);
    return data || [];
  }

  /**
   * Fetch positions with optimization
   */
  private async fetchPositions(exposureCurrency: string, navType?: string, analysis?: any): Promise<any[]> {
    const cacheKey = this.generateCacheKey('positions', { currency: exposureCurrency, nav: navType });
    
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    let query = this.supabase
      .from('position_nav_master')
      .select('*')
      .eq('currency_code', exposureCurrency);

    if (navType) {
      query = query.eq('nav_type', navType);
    } else if (analysis?.nav_types?.length) {
      query = query.in('nav_type', analysis.nav_types);
    }

    const { data, error } = await query;
    if (error) throw error;

    this.setCache(cacheKey, data || [], this.CACHE_TTL.entity_positions);
    return data || [];
  }

  /**
   * Fetch allocations with smart limiting
   */
  private async fetchAllocations(exposureCurrency: string, entityIds: string[], analysis: any): Promise<any[]> {
    const limit = analysis.complexity === 'minimal' ? 10 :
                 analysis.complexity === 'comprehensive' ? 50 : 25;

    let query = this.supabase
      .from('allocation_engine')
      .select('*')
      .eq('currency_code', exposureCurrency)
      .order('created_date', { ascending: false })
      .limit(limit);

    // Filter by recent data if needed
    if (analysis.requires_recent_data) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - 30); // Last 30 days
      query = query.gte('created_date', cutoffDate.toISOString());
    }

    const { data, error } = await query;
    if (error) throw error;

    return data || [];
  }

  /**
   * Fetch hedge instruments with filtering
   */
  private async fetchHedgeInstruments(exposureCurrency: string, options: any, analysis: any): Promise<any[]> {
    const cacheKey = this.generateCacheKey('hedge_instruments', { 
      currency: exposureCurrency, 
      method: options.hedgeMethod,
      nav: options.navType 
    });
    
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    let query = this.supabase
      .from('hedge_instruments')
      .select('*')
      .eq('active_flag', 'Y');

    // Filter by currency
    const pair1 = `${exposureCurrency}SGD`;
    const pair2 = `SGD${exposureCurrency}`;
    query = query.or(`base_currency.eq.${exposureCurrency},quote_currency.eq.${exposureCurrency},currency_pair.in.(${pair1},${pair2})`);

    // Apply method and NAV type filters
    if (options.hedgeMethod) {
      query = query.in('accounting_method_supported', ['Both', options.hedgeMethod]);
    }
    
    if (options.navType) {
      query = query.in('nav_type_applicable', ['Both', options.navType]);
    }

    const { data, error } = await query;
    if (error) throw error;

    this.setCache(cacheKey, data || [], this.CACHE_TTL.static_config);
    return data || [];
  }

  /**
   * Fetch currency rates with caching
   */
  private async fetchCurrencyRates(exposureCurrency: string, analysis: any): Promise<any[]> {
    const cacheKey = this.generateCacheKey('currency_rates', { 
      currency: exposureCurrency,
      date: new Date().toDateString()
    });
    
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    const { data, error } = await this.supabase
      .from('currency_rates')
      .select('*')
      .or(`currency_pair.eq.${exposureCurrency}SGD,currency_pair.eq.SGD${exposureCurrency}`)
      .order('effective_date', { ascending: false })
      .limit(10);

    if (error) throw error;

    this.setCache(cacheKey, data || [], this.CACHE_TTL.currency_rates);
    return data || [];
  }

  /**
   * Fetch currency configuration
   */
  private async fetchCurrencyConfig(exposureCurrency: string): Promise<any[]> {
    const cacheKey = this.generateCacheKey('currency_config', { currency: exposureCurrency });
    
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    const { data, error } = await this.supabase
      .from('currency_configuration')
      .select('*')
      .or(`currency_code.eq.${exposureCurrency},proxy_currency.eq.${exposureCurrency}`);

    if (error) throw error;

    this.setCache(cacheKey, data || [], this.CACHE_TTL.static_config);
    return data || [];
  }

  /**
   * Fetch recent hedge events (only if needed)
   */
  private async fetchRecentHedgeEvents(entityIds: string[], analysis: any): Promise<any[]> {
    if (!entityIds.length) return [];

    const { data, error } = await this.supabase
      .from('hedge_business_events')
      .select('*')
      .in('entity_id', entityIds.slice(0, 20)) // Limit entity scope
      .order('trade_date', { ascending: false })
      .limit(15);

    if (error) throw error;
    return data || [];
  }

  /**
   * Fetch recent instructions (only if needed)
   */
  private async fetchRecentInstructions(exposureCurrency: string, analysis: any): Promise<any[]> {
    const { data, error } = await this.supabase
      .from('hedge_instructions')
      .select('*')
      .eq('exposure_currency', exposureCurrency)
      .order('instruction_date', { ascending: false })
      .limit(10);

    if (error) throw error;
    return data || [];
  }

  /**
   * Structure optimized context based on prompt analysis
   */
  private structureOptimizedContext(rawData: any, analysis: OptimizedContextData['prompt_analysis']): OptimizedContextData {
    return {
      entities: this.limitArray(rawData.entities, analysis.complexity === 'minimal' ? 3 : 10),
      positions: this.limitArray(rawData.positions, analysis.complexity === 'minimal' ? 5 : 15),
      recent_allocations: this.limitArray(rawData.allocations, analysis.complexity === 'minimal' ? 5 : 10),
      hedge_instruments: this.limitArray(rawData.hedge_instruments, 10),
      currency_rates: this.limitArray(rawData.currency_rates, 5),
      prompt_analysis: analysis
    };
  }

  /**
   * Cache management methods
   */
  private generateCacheKey(type: string, params: any): string {
    const paramStr = Object.keys(params)
      .sort()
      .map(key => `${key}:${params[key]}`)
      .join('|');
    return `${type}:${this.hashString(paramStr)}`;
  }

  private hashString(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16);
  }

  private getFromCache(key: string): any | null {
    const cached = this.cache.get(key);
    if (cached && cached.expiry > Date.now()) {
      return cached.data;
    }
    this.cache.delete(key);
    return null;
  }

  private setCache(key: string, data: any, ttl: number): void {
    this.cache.set(key, {
      data,
      expiry: Date.now() + ttl
    });
  }

  private cleanExpiredCache(): void {
    const now = Date.now();
    for (const [key, cached] of this.cache.entries()) {
      if (cached.expiry <= now) {
        this.cache.delete(key);
      }
    }
  }

  // Utility methods
  private extractEntityIds(entities: any[], positions: any[]): string[] {
    const ids = new Set<string>();
    entities.forEach(e => e.entity_id && ids.add(e.entity_id));
    positions.forEach(p => p.entity_id && ids.add(p.entity_id));
    return Array.from(ids);
  }

  private limitArray(arr: any[], limit: number): any[] {
    return arr.slice(0, limit);
  }

  private estimateDataSize(data: any): number {
    return JSON.stringify(data).length;
  }

  /**
   * Get current performance metrics
   */
  getCurrentMetrics(): ClientOptimizationMetrics | null {
    return this.performanceMetricsSubject.value;
  }

  /**
   * Clear all cache
   */
  clearCache(): void {
    this.cache.clear();
    console.log('🗑️ Client cache cleared');
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { totalKeys: number; cacheSize: number; hitRate: number } {
    return {
      totalKeys: this.cache.size,
      cacheSize: JSON.stringify([...this.cache.values()]).length,
      hitRate: 0 // Would need to track hits/misses to calculate
    };
  }
}