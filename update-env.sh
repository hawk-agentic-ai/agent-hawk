#!/bin/bash

echo "🔧 Updating .env file with real API keys..."

# Create .env file with actual values
cat > .env << 'EOF'
DIFY_API_KEY=app-KKtaMynVyn8tKbdV9VbbaeyR
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes
ENVIRONMENT=production
EOF

echo "✅ .env file updated with real API keys"
echo ""
echo "📄 .env contents (with masked keys):"
sed 's/=app-.*$/=app-***MASKED***/; s/=eyJ.*$/=eyJ***MASKED***/; s/=https:\/\/.*\.supabase\.co$/=https:\/\/***MASKED***.supabase.co/' .env

echo ""
echo "🔄 Restarting PM2 process..."
pm2 delete hedge-agent-api 2>/dev/null || echo "No existing process to delete"
pm2 start "uvicorn optimized_dify_endpoint:app --host 0.0.0.0 --port 8000 --workers 1" --name hedge-agent-api
pm2 save

echo ""
echo "⏱️ Waiting for startup..."
sleep 5

echo ""
echo "📊 PM2 Status:"
pm2 status

echo ""
echo "🧪 Testing backend connection:"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is responding!"
    echo "Health check response:"
    curl -s http://localhost:8000/health | head -5
else
    echo "❌ Backend still not responding"
    echo "📜 Recent logs:"
    pm2 logs hedge-agent-api --lines 5
fi

echo ""
echo "🌐 Testing external access:"
echo "Your frontend should now be available at: http://3.91.170.95"
echo "API endpoint: http://3.91.170.95/api"