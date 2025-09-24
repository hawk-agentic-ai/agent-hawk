// HAWK Agent Configuration
export const HAWK_AGENTS = {
  allocation: {
    name: 'HAWK Allocation Agent',
    description: 'Stage 1A: Pre‑utilization check & feasibility assessment',
    url: 'https://udify.app/chat/uPrwnPv2TV6UKQ9X',
    apiKey: 'app-MHztrttE0Ty6jOqykQrp6rL2',
    stages: ['1A'],
    scope: ['utilization', 'feasibility', 'capacity']
  },
  booking: {
    name: 'HAWK Booking Agent',
    description: 'Stage 1B/2/3: Booking, execution & GL posting',
    url: 'https://udify.app/chat/jAkq2aHd4HTx5BxS',
    apiKey: 'app-cxzVbRQUUDofTjx1nDfajpRX',
    stages: ['1B', '2', '3'],
    scope: ['booking', 'murex', 'gl_posting', 'trade_execution']
  },
  analytics: {
    name: 'HAWK Analytics Agent',
    description: 'Analytics & reporting: effectiveness, exposure, trends',
    url: 'https://udify.app/chat/SE9xbNvBsPQkZGua',
    apiKey: 'app-KKtaMynVyn8tKbdV9VbbaeyR',
    stages: ['cross'],
    scope: ['analytics', 'reporting', 'effectiveness']
  },
  config: {
    name: 'HAWK Configuration Agent',
    description: 'Configuration & setup (thresholds, buffers, mappings)',
    url: 'https://udify.app/chat/REPLACE_CONFIG_CHAT_ID',
    apiKey: 'app-x1QM74ZNV2mLqfH0jArH0tjn',
    stages: ['config'],
    scope: ['configuration', 'setup']
  }
};

// Default agent (Allocation Agent)
export const DEFAULT_AGENT = 'allocation';

// Legacy export for backward compatibility
export const AGENT_IFRAME_URL = HAWK_AGENTS[DEFAULT_AGENT].url;
export const RESOLVED_AGENT_IFRAME_URL = AGENT_IFRAME_URL;

// Derived origin used for postMessage targetOrigin safety if needed
export const AGENT_IFRAME_ORIGIN = (() => {
  try {
    return new URL(AGENT_IFRAME_URL).origin;
  } catch {
    return '*';
  }
})();
