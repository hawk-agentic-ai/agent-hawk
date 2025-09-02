import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class BackendApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Secure Dify API calls through backend
  sendToDify(data: {
    query: string;
    msgUid: string;
    instructionId: string;
    amount?: number;
    currency?: string;
    date?: string;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/dify/chat`, data);
  }

  streamDifyResponse(data: {
    query: string;
    msgUid: string;
    instructionId: string;
    amount?: number;
    currency?: string;
    date?: string;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/dify/stream`, data);
  }

  // Optimized Dify API calls with context pre-loading
  sendToDifyOptimized(data: {
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
    const optimizedData = {
      query: data.query,
      msgUid: data.msgUid,
      instructionId: data.instructionId,
      exposure_currency: data.exposure_currency,
      hedge_method: data.hedge_method || 'COH',
      nav_type: data.nav_type,
      currency_type: data.currency_type,
      use_cache: data.use_cache !== false, // Default to true
      max_context_size: data.max_context_size || 50000,
      include_historical: data.include_historical || false
    };
    return this.http.post(`${this.apiUrl}/dify/chat-optimized`, optimizedData);
  }

  streamDifyResponseOptimized(data: {
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
    const optimizedData = {
      query: data.query,
      msgUid: data.msgUid,
      instructionId: data.instructionId,
      exposure_currency: data.exposure_currency,
      hedge_method: data.hedge_method || 'COH',
      nav_type: data.nav_type,
      currency_type: data.currency_type,
      use_cache: data.use_cache !== false,
      max_context_size: data.max_context_size || 50000,
      include_historical: data.include_historical || false
    };
    return this.http.post(`${this.apiUrl}/dify/stream-optimized`, optimizedData);
  }

  // Get Dify performance statistics
  getDifyPerformanceStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/dify/performance-stats`);
  }

  // Invalidate cache for specific currency
  invalidateCurrencyCache(currency: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/cache/invalidate/${currency}`, {});
  }

  // Secure Supabase operations through backend
  getTemplates(): Observable<any> {
    return this.http.get(`${this.apiUrl}/templates`);
  }

  createTemplate(template: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/templates`, template);
  }

  updateTemplate(id: string, template: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/templates/${id}`, template);
  }

  deleteTemplate(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/templates/${id}`);
  }

  // Other secure database operations
  getCurrencies(): Observable<any> {
    return this.http.get(`${this.apiUrl}/currencies`);
  }

  getEntities(): Observable<any> {
    return this.http.get(`${this.apiUrl}/entities`);
  }
}