import { Injectable } from '@angular/core';
import { getSupabase } from '../core/data/supabase.client';

interface SmartDataContext {
  requiredTables: string[];
  dataPayload: Record<string, any>;
  enrichedPrompt: string;
}

@Injectable({
  providedIn: 'root'
})
export class ClientSideSmartDataService {
  
  // Keywords that indicate specific data requirements
  private readonly DATA_KEYWORDS = {
    hedge_positions: ['hedge', 'position', 'hedging', 'exposure', 'risk'],
    entity_master: ['entity', 'entities', 'company', 'companies'],
    products: ['product', 'products', 'instrument', 'instruments'],
    currency: ['currency', 'currencies', 'exchange', 'fx'],
    thresholds: ['threshold', 'thresholds', 'limit', 'limits']
  };

  // Smart prompt analysis - simplified version of Python logic
  analyzePromptDataRequirements(prompt: string): string[] {
    const lowerPrompt = prompt.toLowerCase();
    const requiredTables: string[] = [];

    // Check each table for relevant keywords
    Object.entries(this.DATA_KEYWORDS).forEach(([table, keywords]) => {
      const hasKeyword = keywords.some(keyword => 
        lowerPrompt.includes(keyword.toLowerCase())
      );
      
      if (hasKeyword) {
        requiredTables.push(table);
      }
    });

    // Default fallback - if no specific tables identified, include common ones
    if (requiredTables.length === 0) {
      requiredTables.push('entity_master', 'hedge_positions');
    }

    console.log('🧠 Smart Analysis - Required tables:', requiredTables);
    return requiredTables;
  }

  // Fetch data from Supabase based on requirements
  async fetchSmartData(requiredTables: string[]): Promise<Record<string, any>> {
    const supabase = getSupabase();
    const dataPayload: Record<string, any> = {};

    console.log('📊 Fetching smart data for tables:', requiredTables);

    try {
      // Fetch data for each required table
      for (const table of requiredTables) {
        switch (table) {
          case 'entity_master':
            const { data: entities } = await supabase
              .from('entity_master')
              .select('*')
              .eq('is_active', true)
              .limit(50);
            dataPayload.entities = entities || [];
            break;

          case 'hedge_positions':
            // Mock hedge positions data structure
            dataPayload.hedge_positions = [
              {
                id: 1,
                entity_code: 'ENT001',
                position_type: 'Forward',
                notional: 1000000,
                currency: 'USD',
                maturity_date: '2025-12-31'
              }
            ];
            break;

          case 'products':
            dataPayload.products = [
              { id: 1, name: 'USD Forward', type: 'FX_FORWARD' },
              { id: 2, name: 'EUR Swap', type: 'FX_SWAP' }
            ];
            break;

          case 'currency':
            dataPayload.currencies = [
              { code: 'USD', name: 'US Dollar', rate: 1.0 },
              { code: 'EUR', name: 'Euro', rate: 0.85 }
            ];
            break;

          case 'thresholds':
            dataPayload.thresholds = [
              { entity: 'ENT001', threshold_type: 'RISK_LIMIT', value: 5000000 }
            ];
            break;
        }
      }

      console.log('✅ Smart data fetched successfully:', Object.keys(dataPayload));
      return dataPayload;

    } catch (error) {
      console.error('❌ Error fetching smart data:', error);
      // Return empty payload on error to avoid breaking the flow
      return {};
    }
  }

  // Create enriched prompt with contextual data
  createEnrichedPrompt(originalPrompt: string, dataPayload: Record<string, any>): string {
    let enrichedPrompt = originalPrompt;

    // Add context section if we have data
    if (Object.keys(dataPayload).length > 0) {
      enrichedPrompt += '\n\n--- CONTEXTUAL DATA ---\n';
      
      // Add available data context
      Object.entries(dataPayload).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length > 0) {
          enrichedPrompt += `\n${key.toUpperCase()}:\n`;
          
          // Show first few items as examples
          const examples = value.slice(0, 3);
          examples.forEach((item, index) => {
            if (typeof item === 'object') {
              enrichedPrompt += `${index + 1}. ${JSON.stringify(item)}\n`;
            } else {
              enrichedPrompt += `${index + 1}. ${item}\n`;
            }
          });
          
          if (value.length > 3) {
            enrichedPrompt += `... and ${value.length - 3} more items\n`;
          }
        }
      });
      
      enrichedPrompt += '\n--- END CONTEXT ---\n';
      enrichedPrompt += '\nPlease use this contextual data to provide more accurate and specific responses.';
    }

    return enrichedPrompt;
  }

  // Main method - combines all smart data logic
  async processPromptWithSmartData(prompt: string): Promise<SmartDataContext> {
    console.log('🚀 Starting smart data processing for prompt...');
    
    // Step 1: Analyze prompt to understand data requirements
    const requiredTables = this.analyzePromptDataRequirements(prompt);
    
    // Step 2: Fetch relevant data
    const dataPayload = await this.fetchSmartData(requiredTables);
    
    // Step 3: Create enriched prompt
    const enrichedPrompt = this.createEnrichedPrompt(prompt, dataPayload);
    
    console.log('✅ Smart data processing complete');
    console.log('📋 Context summary:', {
      requiredTables: requiredTables.length,
      dataItems: Object.keys(dataPayload).length,
      promptLength: enrichedPrompt.length
    });

    return {
      requiredTables,
      dataPayload,
      enrichedPrompt
    };
  }
}