export const environment = {
  production: true,
  apiUrl: 'http://3.91.170.95/api',
  supabaseUrl: 'https://ladviaautlfvpxuadqrb.supabase.co',
  supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes',
  
  // AWS Free Tier optimization settings
  freeTierOptimization: {
    enabled: true,
    serverSideCache: true,
    parallelProcessing: true,
    redisCache: true,
    limitConcurrentRequests: true,
    maxConcurrentRequests: 10
  }
};