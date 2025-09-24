import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-pt-results',
  standalone: true,
  imports: [CommonModule, FormsModule],
  styles: [`
    .streaming-table {
      animation: slideIn 0.3s ease-out;
    }
    
    .animate-fadeIn {
      animation: fadeIn 0.5s ease-in forwards;
      opacity: 0;
    }
    
    @keyframes slideIn {
      from {
        transform: translateY(-10px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }
    
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateX(-5px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
    
    /* Enhanced table styling for better readability during streaming */
    .streaming-table tbody tr {
      border-left: 3px solid transparent;
      transition: border-color 0.3s ease;
    }
    
    .streaming-table tbody tr:hover {
      border-left-color: #3b82f6;
      background-color: #f8fafc;
    }
    
    /* Highlight new rows as they appear */
    .streaming-table tbody tr.animate-fadeIn {
      border-left-color: #10b981;
    }
  `],
  template: `
    <div class="flex flex-col h-full">
      <div class="px-2 py-1 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-900">Results</h3>
        <button 
          class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded border border-gray-300 flex items-center gap-1 transition-colors"
          (click)="copyResults()"
          [disabled]="!responseText || responseText.trim() === ''"
          title="Copy results to clipboard">
          <i class="pi pi-copy text-xs"></i>
          <span>Copy</span>
        </button>
      </div>
      <div class="flex-1 overflow-auto">
        <div class="p-2">
          <div class="text-gray-800 leading-relaxed text-base font-sans w-full prose prose-base max-w-none"
               style="word-break: break-word; overflow-wrap: anywhere; max-width: 100%; font-family: inherit; font-size: 16px; line-height: 1.6;"
               [innerHTML]="getFormattedResponse()"></div>

          <div *ngIf="streaming" class="flex items-center gap-2 mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span class="text-sm text-blue-700 font-medium">Receiving response...</span>
            <div class="flex gap-1 ml-2">
              <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></div>
              <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.2s"></div>
              <div class="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style="animation-delay: 0.4s"></div>
            </div>
          </div>
        </div>

        <!-- Metadata now included in main response above, no separate section needed -->
      </div>

      <div class="px-2 py-2 border-t border-gray-100 flex flex-wrap gap-2">
        <button class="btn btn-secondary" (click)="export.emit()"><i class="pi pi-download"></i><span>Export Report</span></button>
        <button class="btn btn-secondary" (click)="ticket.emit()"><i class="pi pi-ticket"></i><span>Create Ticket</span></button>
        <button class="btn btn-secondary" (click)="schedule.emit()"><i class="pi pi-calendar"></i><span>Schedule Review</span></button>
        <button class="btn btn-secondary" (click)="share.emit()"><i class="pi pi-share-alt"></i><span>Share</span></button>
      </div>

      <!-- Rating & Completion, similar to legacy UI -->
      <div class="px-2 py-3 border-t border-gray-100">
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h4 class="text-sm font-medium text-gray-900 mb-2">Rate this response</h4>
            <p class="text-xs text-gray-600 mb-3">Help improve template accuracy by rating the quality of this result</p>
            <div class="flex items-center gap-2">
              <div class="flex items-center gap-1">
                <button *ngFor="let star of [1,2,3,4,5]; let i = index"
                        (click)="rate.emit(star)"
                        class="text-lg transition-colors duration-200"
                        [class]="star <= rating ? 'text-yellow-400 hover:text-yellow-500' : 'text-gray-300 hover:text-yellow-300'">
                  <i class="pi pi-star-fill"></i>
                </button>
              </div>
              <div class="flex items-center gap-2 ml-4">
                <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                        [class]="rating >= 4 ? 'bg-green-100 text-green-700 border-green-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-green-50'"
                        (click)="rate.emit(5)">
                  <i class="pi pi-check-circle mr-1"></i>
                  Correct
                </button>
                <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                        [class]="rating <= 2 ? 'bg-red-100 text-red-700 border-red-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-red-50'"
                        (click)="rate.emit(1)">
                  <i class="pi pi-times-circle mr-1"></i>
                  Incorrect
                </button>
              </div>
              <div class="flex items-center gap-2 ml-4 border-l border-gray-300 pl-4">
                <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                        [class]="completion === 'complete' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-blue-50'"
                        (click)="setCompletion.emit('complete')">
                  <i class="pi pi-check mr-1"></i>
                  Complete
                </button>
                <button class="px-3 py-1 text-xs rounded-full border transition-colors"
                        [class]="completion === 'incomplete' ? 'bg-orange-100 text-orange-700 border-orange-300' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-orange-50'"
                        (click)="setCompletion.emit('incomplete')">
                  <i class="pi pi-exclamation-triangle mr-1"></i>
                  Incomplete
                </button>
              </div>
            </div>
            <!-- Feedback input -->
            <div class="mt-4">
              <label class="block text-xs font-medium text-gray-600 mb-1">Reason / Feedback (optional)</label>
              <textarea rows="4" class="filter-input w-full" [ngModel]="feedback" (ngModelChange)="feedbackChange.emit($event)" placeholder="Describe why the response was correct/incorrect, or any notes for improvement..."></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class TemplateResultsComponent {
  @Input() responseText = '';
  @Input() streaming = false;
  @Input() rating = 0;
  @Input() completion: 'complete'|'incomplete'|null = null;
  @Input() feedback = '';
  @Output() export = new EventEmitter<void>();
  @Output() ticket = new EventEmitter<void>();
  @Output() schedule = new EventEmitter<void>();
  @Output() share = new EventEmitter<void>();
  @Output() rate = new EventEmitter<number>();
  @Output() setCompletion = new EventEmitter<'complete'|'incomplete'>();
  @Output() feedbackChange = new EventEmitter<string>();

  constructor(private sanitizer: DomSanitizer) {}

  private getCleanResponse(): string {
    if (!this.responseText) return '';
    const parts = this.responseText.split('\n\n---\n');
    return parts[0] || this.responseText;
  }

  getFormattedResponse(): SafeHtml {
    if (!this.responseText) return this.sanitizer.bypassSecurityTrustHtml('');
    
    // Use the entire response instead of splitting it
    let fullResponse = this.responseText;
    
    // First, clean up any remaining JSON artifacts that might have leaked through
    fullResponse = fullResponse
      .replace(/data:\s*\{[^}]*"event"[^}]*\}/g, '') // Remove any JSON objects
      .replace(/\{[^}]*"conversation_id"[^}]*\}/g, '') // Remove conversation data
      .replace(/\\\\/g, '') // Remove escaped backslashes
      .replace(/\\n/g, '\n') // Convert literal \n to actual newlines
      .replace(/\\/g, '') // Remove remaining escape characters
      .trim();
    
    // ENHANCED: Process tables first, then apply other formatting
    let formattedText = this.convertTablesToHtml(fullResponse);
    
    // Apply other formatting (but avoid double-processing table content)
    // Split by table blocks to avoid applying formatting inside tables
    const parts = formattedText.split(/(<table[^>]*>.*?<\/table>)/gs);
    
    formattedText = parts.map((part, index) => {
      // Don't format content inside table tags (odd indices after split)
      if (index % 2 === 1 && part.includes('<table')) {
        return part; // Return table HTML as-is
      }
      
      // Apply formatting to non-table content
      return part
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold text
        .replace(/^([🔥⚡✅📊🔍💡⚠️🚀📈📉💰🎯🔧⭐])\s*(.*$)/gm, '<div class="mb-2"><strong class="text-blue-600">$1</strong> $2</div>') // Emoji sections
        .replace(/^\*\s+(.*$)/gm, '<div class="ml-4">• $1</div>') // Bullet points  
        .replace(/^(\d+\.\s+)(.*$)/gm, '<div class="ml-4 mb-1"><strong>$1</strong>$2</div>') // Numbered lists
        .replace(/---\n/g, '<hr class="my-4 border-gray-300">') // Convert separator to visual line
        .replace(/\n/g, '<br>'); // Convert newlines to breaks
    }).join('');
    
    return this.sanitizer.bypassSecurityTrustHtml(formattedText);
  }

  getResponseMetadata(): string {
    if (!this.responseText) return '';
    const parts = this.responseText.split('\n\n---\n');
    if (parts.length > 1) return parts[1].trim();
    return '';
  }

  private convertTablesToHtml(text: string): string {
    // First, clean up streaming artifacts and JSON data
    let cleanText = this.cleanStreamingData(text);
    
    // Use multiple parsing strategies for different table formats
    let result = this.parseJsonEmbeddedTables(cleanText);
    result = this.parseMarkdownTables(result);
    result = this.parseStructuredData(result);
    result = this.parseSpaceSeparatedTables(result);
    
    return result;
  }

  private parseJsonEmbeddedTables(text: string): string {
    // Look for JSON data that might contain table-like information
    return text.replace(/\{[^}]*\"[^"]*\":\s*\[[^\]]*\][^}]*\}/g, (match) => {
      try {
        const jsonData = JSON.parse(match);
        
        // Check if this looks like tabular data
        const arrays = Object.values(jsonData).filter(value => Array.isArray(value));
        if (arrays.length > 0) {
          const tableData = arrays[0] as any[];
          if (tableData.length > 0 && typeof tableData[0] === 'object') {
            return this.buildJsonTable(tableData);
          }
        }
        
        // Check for key-value pairs that could be a table
        const entries = Object.entries(jsonData);
        if (entries.length >= 2) {
          return this.buildKeyValueTable(entries.map(([key, value]) => `${key}: ${value}`));
        }
      } catch (e) {
        // Not valid JSON, return as-is
      }
      return match;
    });
  }

  private buildJsonTable(data: any[]): string {
    if (data.length === 0) return '';
    
    const firstItem = data[0];
    const headers = Object.keys(firstItem);
    
    let html = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
    
    // Headers
    html += '<thead class="bg-gray-50"><tr>';
    headers.forEach(header => {
      html += `<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">${this.escapeHtml(header)}</th>`;
    });
    html += '</tr></thead>';
    
    // Data rows
    html += '<tbody class="bg-white divide-y divide-gray-200">';
    data.forEach(item => {
      html += '<tr class="hover:bg-gray-50">';
      headers.forEach(header => {
        const value = item[header] || '';
        html += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${this.escapeHtml(String(value))}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    
    return html;
  }

  private cleanStreamingData(text: string): string {
    return text
      // Remove JSON streaming artifacts
      .replace(/data:\s*data:\s*\{[^}]*\}/g, '')
      .replace(/data:\s*\{[^}]*\}/g, '')
      .replace(/\{"event"[^}]*\}/g, '')
      .replace(/\{[^}]*"conversation_id"[^}]*\}/g, '')
      // Clean up escaped content
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '')
      // Remove empty data lines
      .replace(/^data:\s*$/gm, '')
      .replace(/^\s*data:\s*$/gm, '')
      // Clean multiple consecutive newlines
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  private parseMarkdownTables(text: string): string {
    const lines = text.split('\n');
    let result = '';
    let currentTable: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Check if this is a markdown table row
      if (line.startsWith('|') && line.endsWith('|') && line.split('|').length >= 3) {
        currentTable.push(line);
        
        // Check next line to see if table continues
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
        const isNextTableRow = nextLine.startsWith('|') && nextLine.endsWith('|');
        const isNextSeparator = /^\|[\s\-:]+\|$/.test(nextLine);
        
        // If next line is separator, skip it
        if (isNextSeparator) {
          i++;
          continue;
        }
        
        // If table ends, process it
        if (!isNextTableRow || i === lines.length - 1) {
          if (currentTable.length > 0) {
            result += this.buildMarkdownTableHtml(currentTable) + '\n';
            currentTable = [];
          }
        }
      } else {
        // Not a table row, add regular content
        if (currentTable.length > 0) {
          result += this.buildMarkdownTableHtml(currentTable) + '\n';
          currentTable = [];
        }
        result += line + '\n';
      }
    }
    
    return result;
  }

  private parseStructuredData(text: string): string {
    // Look for structured data patterns like "Entity: VALUE  Currency: VALUE"
    return text.replace(/^(\w+):\s*([^\n]+?)(\s{2,}(\w+):\s*([^\n]+?))*$/gm, (match) => {
      const pairs = match.match(/(\w+):\s*([^\s]+)/g);
      if (pairs && pairs.length >= 2) {
        return this.buildKeyValueTable(pairs);
      }
      return match;
    });
  }

  private parseSpaceSeparatedTables(text: string): string {
    const lines = text.split('\n');
    let result = '';
    let potentialTable: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (this.looksLikeTableData(line)) {
        potentialTable.push(line);
        
        // Look ahead to see if we have more table-like data
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
        if (!this.looksLikeTableData(nextLine) || i === lines.length - 1) {
          // Process accumulated table data
          if (potentialTable.length >= 2) {
            result += this.buildSpaceSeparatedTable(potentialTable) + '\n';
          } else {
            // Not enough rows for a table, add as regular content
            result += potentialTable.join('\n') + '\n';
          }
          potentialTable = [];
        }
      } else {
        // Process any accumulated table first
        if (potentialTable.length >= 2) {
          result += this.buildSpaceSeparatedTable(potentialTable) + '\n';
        } else if (potentialTable.length > 0) {
          result += potentialTable.join('\n') + '\n';
        }
        potentialTable = [];
        result += line + '\n';
      }
    }
    
    return result;
  }

  private looksLikeTableData(line: string): boolean {
    if (!line || line.length < 10) return false;
    
    // Check for multiple space-separated values
    const parts = line.split(/\s{2,}/).filter(p => p.trim().length > 0);
    if (parts.length < 2) return false;
    
    // Look for patterns that suggest tabular data
    const hasNumbers = parts.some(part => /\d/.test(part));
    const hasConsistentFormat = parts.length >= 3;
    const hasKeywords = /entity|currency|amount|rate|position|nav|allocation/i.test(line);
    
    return (hasNumbers && hasConsistentFormat) || hasKeywords;
  }

  private buildMarkdownTableHtml(tableRows: string[]): string {
    if (tableRows.length === 0) return '';
    
    let html = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
    
    // First row as header
    const headerRow = tableRows[0];
    const headerCells = headerRow.split('|').slice(1, -1).map(cell => cell.trim());
    
    html += '<thead class="bg-gray-50"><tr>';
    headerCells.forEach(cell => {
      html += `<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">${this.escapeHtml(cell)}</th>`;
    });
    html += '</tr></thead>';
    
    // Data rows
    html += '<tbody class="bg-white divide-y divide-gray-200">';
    for (let i = 1; i < tableRows.length; i++) {
      const row = tableRows[i];
      const cells = row.split('|').slice(1, -1).map(cell => cell.trim());
      
      html += '<tr class="hover:bg-gray-50">';
      cells.forEach(cell => {
        html += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${this.escapeHtml(cell)}</td>`;
      });
      html += '</tr>';
    }
    html += '</tbody></table>';
    
    return html;
  }

  private buildKeyValueTable(pairs: string[]): string {
    let html = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
    html += '<tbody class="bg-white divide-y divide-gray-200">';
    
    pairs.forEach(pair => {
      const [key, value] = pair.split(':').map(s => s.trim());
      html += '<tr class="hover:bg-gray-50">';
      html += `<td class="px-4 py-3 text-sm font-medium text-gray-500 border-b border-gray-100">${this.escapeHtml(key)}</td>`;
      html += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${this.escapeHtml(value)}</td>`;
      html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
  }

  private buildSpaceSeparatedTable(rows: string[]): string {
    if (rows.length < 2) return rows.join('\n');
    
    // Analyze column structure
    const columnData = this.analyzeColumns(rows);
    if (columnData.length < 2) return rows.join('\n');
    
    let html = '<table class="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg overflow-hidden my-4">';
    
    // Use first row as header if it looks like one
    const firstRowIsHeader = this.isLikelyHeader(rows[0]);
    
    if (firstRowIsHeader) {
      const headerParts = this.splitIntoColumns(rows[0], columnData);
      html += '<thead class="bg-gray-50"><tr>';
      headerParts.forEach(cell => {
        html += `<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">${this.escapeHtml(cell)}</th>`;
      });
      html += '</tr></thead>';
    }
    
    html += '<tbody class="bg-white divide-y divide-gray-200">';
    const dataRows = firstRowIsHeader ? rows.slice(1) : rows;
    
    dataRows.forEach(row => {
      const cells = this.splitIntoColumns(row, columnData);
      html += '<tr class="hover:bg-gray-50">';
      cells.forEach(cell => {
        html += `<td class="px-4 py-3 text-sm text-gray-900 border-b border-gray-100">${this.escapeHtml(cell)}</td>`;
      });
      html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
  }

  private analyzeColumns(rows: string[]): number[] {
    // Find consistent column boundaries across all rows
    const positions = new Set<number>();
    
    rows.forEach(row => {
      let pos = 0;
      while (pos < row.length) {
        const match = row.slice(pos).match(/\s{2,}/);
        if (match && match.index !== undefined) {
          positions.add(pos + match.index);
          pos += match.index + match[0].length;
        } else {
          break;
        }
      }
    });
    
    return Array.from(positions).sort((a, b) => a - b);
  }

  private splitIntoColumns(row: string, positions: number[]): string[] {
    const columns = [];
    let start = 0;
    
    for (const pos of positions) {
      if (pos > start) {
        columns.push(row.slice(start, pos).trim());
        start = pos;
      }
    }
    
    // Add the last column
    if (start < row.length) {
      columns.push(row.slice(start).trim());
    }
    
    return columns.filter(col => col.length > 0);
  }

  private isLikelyHeader(row: string): boolean {
    // Headers typically contain descriptive words, not just numbers/data
    const words = row.toLowerCase();
    const headerKeywords = ['entity', 'currency', 'amount', 'rate', 'position', 'nav', 'allocation', 'id', 'name', 'type', 'status'];
    return headerKeywords.some(keyword => words.includes(keyword));
  }


  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  copyResults(): void {
    if (!this.responseText || this.responseText.trim() === '') {
      return;
    }

    // Clean the response text for copying - remove HTML and format nicely
    let cleanText = this.responseText
      .replace(/data:\s*\{[^}]*"event"[^}]*\}/g, '') // Remove JSON objects
      .replace(/\{[^}]*"conversation_id"[^}]*\}/g, '') // Remove conversation data
      .replace(/\\\\/g, '') // Remove escaped backslashes
      .replace(/\\n/g, '\n') // Convert literal \n to actual newlines
      .replace(/\\/g, '') // Remove remaining escape characters
      .replace(/\*\*(.*?)\*\*/g, '$1') // Remove markdown bold formatting
      .trim();

    // Copy to clipboard
    navigator.clipboard.writeText(cleanText).then(() => {
      // Show success feedback (optional - could add a toast notification)
      console.log('Results copied to clipboard');
      
      // Visual feedback - temporarily change button text
      const button = document.querySelector('[title="Copy results to clipboard"]') as HTMLButtonElement;
      if (button) {
        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="pi pi-check text-xs"></i><span>Copied!</span>';
        button.classList.add('bg-green-100', 'text-green-700', 'border-green-300');
        button.classList.remove('bg-gray-100', 'text-gray-700', 'border-gray-300');
        
        setTimeout(() => {
          button.innerHTML = originalContent;
          button.classList.remove('bg-green-100', 'text-green-700', 'border-green-300');
          button.classList.add('bg-gray-100', 'text-gray-700', 'border-gray-300');
        }, 2000);
      }
    }).catch(err => {
      console.error('Failed to copy to clipboard:', err);
      
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = cleanText;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        console.log('Results copied to clipboard (fallback method)');
      } catch (err) {
        console.error('Fallback copy failed:', err);
      }
      
      document.body.removeChild(textArea);
    });
  }
}
