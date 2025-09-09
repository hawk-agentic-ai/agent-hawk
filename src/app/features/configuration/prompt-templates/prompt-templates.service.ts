import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { getSupabase } from '../../../core/data/supabase.client';

export interface PromptTemplate {
  id?: string;
  name: string;
  family_type: string;
  template_category: string;
  description?: string;
  prompt_text: string;
  template_filters?: string;
  input_fields?: string[]; // JSON array of field names extracted from prompt_text
  status: 'active' | 'inactive';
  display_order?: number;
  usage_count?: number;
  created_at?: Date | string;
  updated_at?: Date | string;
  created_by?: string;
  updated_by?: string;
}

@Injectable({
  providedIn: 'root'
})
export class PromptTemplatesService {
  private templatesSubject = new BehaviorSubject<PromptTemplate[]>([]);
  public templates$ = this.templatesSubject.asObservable();

  constructor() {
    this.loadTemplates();
  }

  async loadTemplates(): Promise<void> {
    try {
      console.log(' Loading templates from Supabase...');
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('prompt_templates')
        .select('*')
        .eq('status', 'active')
        .order('display_order', { ascending: true });

      if (error) {
        console.error(' Supabase query error:', error);
        throw error;
      }

      console.log(` Loaded ${(data || []).length} templates from database`);
      if (data && data.length > 0) {
        console.log(' Sample template:', data[0]);
        console.log(' Available families:', [...new Set(data.map(t => t.family_type))]);
      }
      
      this.templatesSubject.next(data || []);
    } catch (error) {
      console.error(' Error loading prompt templates:', error);
      console.warn(' Loading fallback templates...');
      // Provide fallback templates when database is unavailable
      const fallbacks = this.getFallbackTemplates();
      console.log(` Using ${fallbacks.length} fallback templates`);
      this.templatesSubject.next(fallbacks);
    }
  }

  private getFallbackTemplates(): PromptTemplate[] {
    return [
      {
        id: 'fallback-1',
        name: 'Hedge Analysis Template',
        family_type: 'hedge_accounting',
        template_category: 'analysis',
        description: 'Basic hedge analysis template',
        prompt_text: 'Analyze {{hedge_type}} effectiveness for {{entity}} covering {{currency}} exposure of {{amount}}.',
        input_fields: ['hedge_type', 'entity', 'currency', 'amount'],
        status: 'active',
        display_order: 1
      },
      {
        id: 'fallback-2', 
        name: 'Risk Assessment Template',
        family_type: 'risk_management',
        template_category: 'assessment',
        description: 'Basic risk assessment template',
        prompt_text: 'Assess {{risk_type}} risk for {{portfolio}} with exposure {{amount}} in {{currency}}.',
        input_fields: ['risk_type', 'portfolio', 'amount', 'currency'],
        status: 'active',
        display_order: 2
      }
    ];
  }

  async addTemplate(template: Partial<PromptTemplate>): Promise<void> {
    try {
      const supabase = getSupabase();
      
      // Extract input fields from prompt text
      const inputFields = this.extractInputFields(template.prompt_text || '');
      
      const { error } = await supabase
        .from('prompt_templates')
        .insert([{
          ...template,
          input_fields: inputFields,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          created_by: 'current_user', // Replace with actual user
          updated_by: 'current_user'
        }]);

      if (error) throw error;
      await this.loadTemplates();
    } catch (error) {
      console.error('Error adding template:', error);
      throw error;
    }
  }

  async updateTemplate(id: string, template: Partial<PromptTemplate>): Promise<void> {
    try {
      const supabase = getSupabase();
      
      // Extract input fields from prompt text
      const inputFields = this.extractInputFields(template.prompt_text || '');
      
      const { error } = await supabase
        .from('prompt_templates')
        .update({
          ...template,
          input_fields: inputFields,
          updated_at: new Date().toISOString(),
          updated_by: 'current_user' // Replace with actual user
        })
        .eq('id', id);

      if (error) throw error;
      await this.loadTemplates();
    } catch (error) {
      console.error('Error updating template:', error);
      throw error;
    }
  }

  async deleteTemplate(id: string): Promise<void> {
    try {
      const supabase = getSupabase();
      const { error } = await supabase
        .from('prompt_templates')
        .delete()
        .eq('id', id);

      if (error) throw error;
      await this.loadTemplates();
    } catch (error) {
      console.error('Error deleting template:', error);
      throw error;
    }
  }

  async incrementUsageCount(id: string): Promise<void> {
    try {
      const supabase = getSupabase();
      const { error } = await supabase.rpc('increment_template_usage', {
        template_id: id
      });

      if (error) throw error;
      await this.loadTemplates();
    } catch (error) {
      console.error('Error incrementing usage count:', error);
    }
  }

  async getTemplatesByFamilyType(familyType: string): Promise<PromptTemplate[]> {
    try {
      console.log(` Loading templates for family: ${familyType}`);
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('prompt_templates')
        .select('*')
        .eq('family_type', familyType)
        .eq('status', 'active')
        .order('display_order', { ascending: true });

      if (error) {
        console.error(' Templates by family query error:', error);
        throw error;
      }
      
      console.log(` Found ${(data || []).length} templates for family ${familyType}`);
      return data || [];
    } catch (error) {
      console.error(' Error getting templates by family type:', error);
      return [];
    }
  }

  async searchTemplates(query: string, familyType?: string): Promise<PromptTemplate[]> {
    try {
      const supabase = getSupabase();
      let queryBuilder = supabase
        .from('prompt_templates')
        .select('*')
        .eq('status', 'active');

      if (familyType) {
        queryBuilder = queryBuilder.eq('family_type', familyType);
      }

      if (query) {
        queryBuilder = queryBuilder.or(`name.ilike.%${query}%,description.ilike.%${query}%,template_filters.ilike.%${query}%`);
      }

      const { data, error } = await queryBuilder.order('display_order', { ascending: true });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Error searching templates:', error);
      return [];
    }
  }

  private extractInputFields(promptText: string): string[] {
    // Extract inner contents for both {{ ... }} and [ ... ] preserving user text
    const fields: string[] = [];
    const seen = new Set<string>(); // track uniqueness by lowercased, collapsed whitespace
    let match: RegExpExecArray | null;

    const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ');

    // Match any content between double braces
    const braceRe = /\{\{([^}]+)\}\}/g;
    while ((match = braceRe.exec(promptText)) !== null) {
      const rawInner = (match[1] || '').trim();
      // For {{ var | filter }} keep the variable name before the first pipe for UX clarity
      const base = rawInner.split('|')[0].trim();
      const key = norm(base);
      if (key && !seen.has(key)) { seen.add(key); fields.push(base); }
    }

    // Match any content between square brackets
    const bracketRe = /\[([^\]]+)\]/g;
    while ((match = bracketRe.exec(promptText)) !== null) {
      const rawInner = (match[1] || '').trim();
      const key = norm(rawInner);
      if (key && !seen.has(key)) { seen.add(key); fields.push(rawInner); }
    }

    // Post-filter to remove likely unwanted items (sentences, URLs, pipes, overly long tokens)
    const cleaned = fields.filter((s) => {
      const t = (s || '').trim();
      if (!t) return false;
      if (t.length > 80) return false;
      if (t.includes('\n')) return false;
      if (t.includes('|') || t.includes('<') || t.includes('>') || t.startsWith('http')) return false;
      // Too many words likely indicates a sentence rather than a field
      const words = t.split(/\s+/).filter(Boolean);
      if (words.length > 6) return false;
      // Exclude purely non-alpha tokens
      if (!/[a-zA-Z]/.test(t)) return false;
      return true;
    });
    return cleaned;
  }

  // Helper method to get input fields for a template
  getInputFields(promptText: string): string[] {
    return this.extractInputFields(promptText);
  }

  // Helper method to extract field names from database input_fields format
  extractFieldNamesFromTemplate(template: PromptTemplate): string[] {
    const fields: string[] = [];
    
    // First try to get from stored input_fields (database format)
    if (template.input_fields && Array.isArray(template.input_fields)) {
      template.input_fields.forEach((field: any) => {
        if (typeof field === 'string') {
          // Already a string, use as is
          fields.push(field.trim());
        } else if (field && typeof field === 'object' && field.name) {
          // Object format: {name: 'field_name', type: 'string', ...}
          fields.push(field.name.trim());
        }
      });
    }
    
    // Also extract from prompt text to catch any missed fields
    const extractedFields = this.extractInputFields(template.prompt_text || '');
    
    // Enhanced deduplication - case-insensitive and whitespace-aware
    const seen = new Set<string>();
    const allFields: string[] = [];
    
    [...fields, ...extractedFields].forEach(field => {
      const normalized = field.toLowerCase().trim().replace(/\s+/g, ' ');
      if (!seen.has(normalized) && field.trim()) {
        seen.add(normalized);
        allFields.push(field.trim());
      }
    });
    
    // Log only if there are issues or for debugging
    if (fields.length + extractedFields.length !== allFields.length) {
      console.log(`Field extraction for "${template.name}": Found ${allFields.length} unique fields from ${fields.length + extractedFields.length} total`);
    }
    
    return allFields;
  }

  // Helper method to replace placeholders with actual values
  fillTemplate(promptText: string, values: { [key: string]: string }): string {
    const escapeReg = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    let filledText = promptText;
    const map = values || {};
    for (const k of Object.keys(map)) {
      const v = map[k] ?? `{{${k}}}`;
      const variants = Array.from(new Set([
        String(k),
        String(k).trim(),
        String(k).replace(/\s+/g, '_'),
        String(k).replace(/_/g, ' '),
      ]));
      for (const variant of variants) {
        const ek = escapeReg(variant);
        const braceRe = new RegExp(`\\{\\{\\s*${ek}(?:[^}]*)\\}\\}`, 'gi');
        const bracketRe = new RegExp(`\\[\\s*${ek}\\s*\\]`, 'gi');
        filledText = filledText.replace(braceRe, v).replace(bracketRe, v);
      }
    }
    return filledText;
  }

  // Get unique family types from database
  async getUniqueFamilyTypes(): Promise<{label: string, value: string}[]> {
    try {
      console.log(' Loading family types from Supabase...');
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('prompt_templates')
        .select('family_type')
        .eq('status', 'active');

      if (error) {
        console.error(' Family types query error:', error);
        throw error;
      }
      
      const uniqueTypes = [...new Set((data || []).map(t => t.family_type))];
      console.log(' Found family types:', uniqueTypes);
      
      const result = uniqueTypes.map(type => ({
        label: this.formatFamilyLabel(type),
        value: type
      }));
      
      console.log(' Formatted families:', result);
      return result;
    } catch (error) {
      console.error(' Error getting unique family types:', error);
      // Return fallback families
      return [
        { label: 'Hedge Accounting', value: 'hedge_accounting' },
        { label: 'Risk Management', value: 'risk_management' }
      ];
    }
  }

  // Get unique template categories for a specific family type
  async getTemplateCategoriesByFamily(familyType: string): Promise<{label: string, value: string}[]> {
    try {
      console.log(` Loading categories for family: ${familyType}`);
      const supabase = getSupabase();
      const { data, error } = await supabase
        .from('prompt_templates')
        .select('template_category')
        .eq('family_type', familyType)
        .eq('status', 'active');

      if (error) {
        console.error(' Categories query error:', error);
        throw error;
      }
      
      const uniqueCategories = [...new Set((data || []).map(t => t.template_category))];
      console.log(` Found categories for ${familyType}:`, uniqueCategories);
      
      const result = uniqueCategories.map(category => ({
        label: this.formatCategoryLabel(category),
        value: category
      }));
      
      console.log(' Formatted categories:', result);
      return result;
    } catch (error) {
      console.error(' Error getting template categories:', error);
      return [];
    }
  }

  private formatFamilyLabel(family: string): string {
    const map: Record<string, string> = {
      'hedge_accounting': 'Hedge Accounting',
      'risk_management': 'Risk Management', 
      'compliance': 'Compliance',
      'reporting': 'Reporting',
      'analysis': 'Analysis',
      'operations': 'Operations',
      'Instructions & Processing': 'Instructions & Processing',
      'Risk & Compliance': 'Risk & Compliance',
      'Analysis & Reporting': 'Analysis & Reporting',
      'Problem Resolution': 'Problem Resolution',
      'Configuration & Setup': 'Configuration & Setup',
      'Monitoring & Status': 'Monitoring & Status'
    };
    return map[family] || this.formatCategoryLabel(family);
  }

  private formatCategoryLabel(category: string): string {
    return category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }
}
