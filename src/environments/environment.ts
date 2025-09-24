export const environment = {
  production: false,
  // For local dev you can set this to 'http://localhost:8004' or keep '/api' if using a proxy
  apiUrl: '/api', // HTTPS API endpoint (dev proxy or nginx)
  unifiedBackendUrl: '/api', // Unified backend base
  supabaseUrl: '', // Remove from client
  supabaseAnonKey: '', // Remove from client
  difyApiKey: '', // Remove from client - move to backend
  
  // Performance optimization settings
  unifiedBackend: {
    enabled: true,
    streamingEnabled: true,
    smartTemplateDetection: true,
    cacheEnabled: true
  }
};
