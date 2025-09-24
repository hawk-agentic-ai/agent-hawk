FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements_fixed_new.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY unified_smart_backend.py .
COPY prompt_intelligence_engine.py .
COPY smart_data_extractor.py .
COPY hedge_management_cache_config.py .
COPY payloads.py .

# Environment variables with defaults
ENV SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
ENV SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes
ENV DIFY_API_KEY=app-sF86KavXxF9u2HwQx5JpM4TK
ENV REDIS_URL=redis://localhost:6379/0

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8004/health || exit 1

# Start the unified smart backend
CMD ["python", "unified_smart_backend.py"]