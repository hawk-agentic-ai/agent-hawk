export const environment = {
  production: true,
  unifiedBackendUrl: 'https://13-222-100-183.nip.io/api/',
  supabaseUrl: '', // Removed for security - handled by backend
  supabaseAnonKey: '', // Removed for security - handled by backend
  difyApiKey: '', // Removed for security - handled by backend
  
  // Performance optimization settings
  unifiedBackend: {
    enabled: true,
    streamingEnabled: true,
    smartTemplateDetection: true,
    cacheEnabled: true
  }
};
