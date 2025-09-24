import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { HAWK_AGENTS, DEFAULT_AGENT } from '../../../core/config/app-config';

@Component({
  selector: 'app-hawk-agent-mode',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 min-h-full flex flex-col" style="height: 100vh;">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">Agent Mode</h2>
          <div class="text-xs text-gray-500">HAWK Agent - {{ getCurrentAgent().description }}</div>
        </div>
        <div class="flex items-center gap-4">
          <!-- Agent Selection Dropdown -->
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600 font-medium">Agent:</label>
            <select
              [(ngModel)]="selectedAgent"
              (ngModelChange)="onAgentChange($event)"
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
              <option *ngFor="let agent of getAgentOptions()" [value]="agent.key">
                {{ agent.name }}
              </option>
            </select>
          </div>

          <!-- Stage Badge -->
          <div class="flex items-center gap-1">
            <span *ngFor="let stage of getCurrentAgent().stages"
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  [ngClass]="getStageBadgeClass(stage)">
              Stage {{ stage }}
            </span>
          </div>

          <!-- Mode Toggle -->
          <div class="flex items-center gap-3">
            <span class="text-sm text-gray-400">Template Mode</span>
            <label class="inline-flex items-center cursor-pointer">
              <input type="checkbox" class="sr-only" [ngModel]="isAgentMode" (ngModelChange)="onToggle($event)">
              <div class="relative" role="switch" [attr.aria-checked]="isAgentMode">
                <div class="w-12 h-7 rounded-full transition-colors duration-200 shadow-inner ring-1" [ngClass]="isAgentMode ? 'bg-blue-600 ring-blue-600' : 'bg-gray-300 ring-gray-300'"></div>
                <div class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transform transition duration-200" [class.translate-x-5]="isAgentMode"></div>
              </div>
            </label>
            <span class="text-sm text-blue-700 font-medium">Agent Mode</span>
          </div>
        </div>
      </div>

      <!-- Agent Info Panel -->
      <div class="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full" [ngClass]="getAgentStatusClass()"></div>
            <div>
              <div class="text-sm font-medium text-gray-900">{{ getCurrentAgent().name }}</div>
              <div class="text-xs text-gray-500">{{ getCurrentAgent().scope.join(', ') }}</div>
            </div>
          </div>
          <div class="text-xs text-gray-400">
            API: {{ getCurrentAgent().apiKey.substring(0, 8) }}...
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 overflow-hidden flex-1 min-h-0" style="height: 75vh;">
        <iframe [src]="agentUrlSafe" class="w-full h-full" style="border:0; height: 100%;" allow="microphone; clipboard-read; clipboard-write"></iframe>
      </div>
    </div>
  `
})
export class AgentModeComponent {
  agentUrlSafe!: SafeResourceUrl;
  isAgentMode = true;
  selectedAgent: keyof typeof HAWK_AGENTS = DEFAULT_AGENT as keyof typeof HAWK_AGENTS;
  hawkAgents = HAWK_AGENTS;

  constructor(private sanitizer: DomSanitizer, private router: Router) {
    console.log('HAWK_AGENTS configuration:', this.hawkAgents);
    console.log('Available agent keys:', Object.keys(this.hawkAgents));
    this.updateAgentUrl();
  }

  onToggle(v: boolean) {
    this.isAgentMode = !!v;
    if (!this.isAgentMode) {
      this.router.navigate(['/hawk-agent/prompt-templates']);
    }
  }

  onAgentChange(agentKey: string) {
    this.selectedAgent = agentKey as keyof typeof HAWK_AGENTS;
    this.updateAgentUrl();
    console.log(`Switched to ${this.getCurrentAgent().name} with API key: ${this.getCurrentAgent().apiKey}`);
  }

  private updateAgentUrl() {
    const agent = this.hawkAgents[this.selectedAgent];
    this.agentUrlSafe = this.sanitizer.bypassSecurityTrustResourceUrl(agent.url);
  }

  getCurrentAgent() {
    return this.hawkAgents[this.selectedAgent];
  }

  getAgentOptions() {
    const options = Object.keys(this.hawkAgents).map(key => ({
      key,
      name: this.hawkAgents[key as keyof typeof HAWK_AGENTS].name
    }));
    console.log('Agent options for dropdown:', options);
    return options;
  }

  getStageBadgeClass(stage: string): string {
    const stageClasses: { [key: string]: string } = {
      '1A': 'bg-green-100 text-green-800 border border-green-200',
      '1B': 'bg-blue-100 text-blue-800 border border-blue-200',
      '2': 'bg-orange-100 text-orange-800 border border-orange-200',
      '3': 'bg-red-100 text-red-800 border border-red-200'
    };
    return stageClasses[stage] || 'bg-gray-100 text-gray-800 border border-gray-200';
  }

  getAgentStatusClass(): string {
    return this.selectedAgent === 'allocation'
      ? 'bg-green-400'
      : 'bg-orange-400';
  }
}
