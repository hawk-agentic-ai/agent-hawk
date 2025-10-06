import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface HedgePromptRequest {
  prompt_type: 'utilization' | 'inception' | 'rollover' | 'termination' | 'amendment' | 'inquiry';
  currency: string;
  user_prompt: string;
  nav_type?: 'COI' | 'RE';
  entity_id?: string;
  order_id?: string;
  previous_order_id?: string;
}

export interface HedgeWorkflowResponse {
  prompt_type: string;
  currency: string;
  user_prompt: string;
  ai_processing: {
    status: 'success' | 'dify_error' | 'connection_error';
    ai_response?: string;
    error?: string;
    data_summary: Record<string, number>;
    total_records_sent?: number;
    conversation_id?: string;
    message_id?: string;
    processed_at?: string;
  };
  database_context: string;
  processing_approach: string;
}

export interface TemplateConfig {
  type: HedgePromptRequest['prompt_type'];
  label: string;
  description: string;
  icon: string;
  requiredFields: string[];
  samplePrompts: string[];
  color: string;
}

@Injectable({
  providedIn: 'root'
})
export class ComprehensiveHedgeService {
  
  private readonly API_BASE = 'https://3-238-163-106.nip.io/api/hedge-ai';
  
  // Template configurations for each instruction type
  readonly TEMPLATE_CONFIGS: TemplateConfig[] = [
    {
      type: 'utilization',
      label: 'Utilization (U)',
      description: 'Execute FX hedge utilization with AI-driven capacity analysis',
      icon: 'pi pi-chart-line',
      requiredFields: ['currency', 'user_prompt'],
      samplePrompts: [
        'Execute FX hedge utilization for EUR 10M exposure across all entities',
        'Process utilization instruction for JPY 500M against COI portfolio',
        'Hedge USD exposure of 25M for revenue protection with buffer analysis'
      ],
      color: 'blue'
    },
    {
      type: 'inception',
      label: 'Inception (I)',
      description: 'Start new hedge position with complete workflow automation',
      icon: 'pi pi-plus-circle',
      requiredFields: ['currency', 'nav_type', 'user_prompt'],
      samplePrompts: [
        'Start hedge inception for USD 25M COI exposure',
        'Initialize new hedge position for GBP 8M revenue protection',
        'Create inception instruction for CNY 100M subsidiary hedge'
      ],
      color: 'green'
    },
    {
      type: 'rollover',
      label: 'Rollover (R)',
      description: 'Extend hedge maturity with AI optimization',
      icon: 'pi pi-refresh',
      requiredFields: ['currency', 'user_prompt'],
      samplePrompts: [
        'Process rollover for existing EUR 12M hedge position',
        'Extend maturity for JPY 300M hedge to next quarter',
        'Rollover CNY hedge with updated terms and conditions'
      ],
      color: 'orange'
    },
    {
      type: 'termination',
      label: 'Termination (T)',
      description: 'Close hedge positions with P&L calculation',
      icon: 'pi pi-times-circle',
      requiredFields: ['currency', 'user_prompt'],
      samplePrompts: [
        'Process maturity settlement for USD 20M hedge expiring today',
        'Handle natural maturity for EUR 5M revenue hedge',
        'Execute termination closure for TWD 50M subsidiary hedge'
      ],
      color: 'red'
    },
    {
      type: 'amendment',
      label: 'Amendment (A)',
      description: 'Modify existing hedge instructions with validation',
      icon: 'pi pi-pencil',
      requiredFields: ['currency', 'order_id', 'previous_order_id', 'user_prompt'],
      samplePrompts: [
        'Amend order ORD-2025-011 previous ORD-2025-007 changing notional from 100M to 120M',
        'Process amendment ORD-2025-012 previous ORD-2025-008 update maturity date',
        'Execute amendment ORD-2025-013 previous ORD-2025-009 modify hedge method to NDF'
      ],
      color: 'purple'
    },
    {
      type: 'inquiry',
      label: 'Inquiry (Q)',
      description: 'Query system status and capacity information',
      icon: 'pi pi-search',
      requiredFields: ['user_prompt'],
      samplePrompts: [
        'Check status of hedge instruction MSG-I-2025-123456',
        'Query available EUR hedging capacity for entity ENT001',
        'Status inquiry for all pending orders for CNY currency'
      ],
      color: 'teal'
    }
  ];

  constructor(private http: HttpClient) {}

  /**
   * Execute hedge workflow using comprehensive AI backend
   */
  executeHedgeWorkflow(request: HedgePromptRequest): Observable<HedgeWorkflowResponse> {
    const endpoint = `${this.API_BASE}/${request.prompt_type}`;
    
    return this.http.post<HedgeWorkflowResponse>(endpoint, request).pipe(
      catchError(error => {
        console.error(`${request.prompt_type} workflow failed:`, error);
        return of({
          prompt_type: request.prompt_type,
          currency: request.currency,
          user_prompt: request.user_prompt,
          ai_processing: {
            status: 'connection_error',
            error: `Failed to connect to comprehensive hedge backend: ${error.message}`,
            data_summary: {}
          },
          database_context: 'Connection failed',
          processing_approach: 'Backend unavailable'
        } as HedgeWorkflowResponse);
      })
    );
  }

  /**
   * Get template configuration for specific instruction type
   */
  getTemplateConfig(type: HedgePromptRequest['prompt_type']): TemplateConfig | undefined {
    return this.TEMPLATE_CONFIGS.find(config => config.type === type);
  }

  /**
   * Get all available template configurations
   */
  getAllTemplateConfigs(): TemplateConfig[] {
    return this.TEMPLATE_CONFIGS;
  }

  /**
   * Validate request based on template requirements
   */
  validateRequest(request: HedgePromptRequest): { valid: boolean; errors: string[] } {
    const config = this.getTemplateConfig(request.prompt_type);
    const errors: string[] = [];

    if (!config) {
      return { valid: false, errors: ['Invalid prompt type'] };
    }

    // Check required fields
    config.requiredFields.forEach(field => {
      if (!request[field as keyof HedgePromptRequest]) {
        errors.push(`${field} is required for ${config.label}`);
      }
    });

    // Specific validations
    if (request.prompt_type === 'inception' && !request.nav_type) {
      errors.push('NAV Type (COI/RE) is required for Inception instructions');
    }

    if (request.prompt_type === 'amendment') {
      if (!request.order_id || !request.previous_order_id) {
        errors.push('Both order_id and previous_order_id are required for Amendment instructions');
      }
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Get system status from comprehensive backend
   */
  getSystemStatus(): Observable<any> {
    return this.http.get(`${this.API_BASE.replace('/hedge-ai', '')}/hedge-ai/system-status`).pipe(
      catchError(error => {
        console.error('System status check failed:', error);
        return of({
          version: 'unknown',
          system: 'Comprehensive Hedge Data Extraction System',
          status: 'connection_error',
          error: error.message
        });
      })
    );
  }

  /**
   * Build prompt suggestion based on template and user input
   */
  buildPromptSuggestion(templateType: HedgePromptRequest['prompt_type'], currency?: string, amount?: string): string {
    const config = this.getTemplateConfig(templateType);
    if (!config || !config.samplePrompts.length) return '';

    let suggestion = config.samplePrompts[0];
    
    // Customize with user inputs
    if (currency) {
      suggestion = suggestion.replace(/(EUR|USD|JPY|GBP|CNY|TWD)/g, currency);
    }
    
    if (amount) {
      suggestion = suggestion.replace(/(\d+M|\d+\.\d+M)/g, amount);
    }

    return suggestion;
  }

  /**
   * Extract key metrics from AI response
   */
  extractMetricsFromResponse(response: HedgeWorkflowResponse): Record<string, any> {
    const metrics: Record<string, any> = {};

    // Extract data summary
    if (response.ai_processing.data_summary) {
      const totalRecords = Object.values(response.ai_processing.data_summary).reduce((sum, count) => sum + count, 0);
      metrics.total_records_processed = totalRecords;
      metrics.tables_accessed = Object.keys(response.ai_processing.data_summary).length;
      metrics.largest_table = Object.entries(response.ai_processing.data_summary)
        .sort(([,a], [,b]) => b - a)[0]?.[0] || 'none';
    }

    // Extract processing info
    metrics.processing_approach = response.processing_approach;
    metrics.database_context = response.database_context;
    metrics.ai_status = response.ai_processing.status;

    if (response.ai_processing.processed_at) {
      metrics.processing_timestamp = response.ai_processing.processed_at;
    }

    return metrics;
  }
}