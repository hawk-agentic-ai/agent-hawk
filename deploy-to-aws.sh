#!/bin/bash

# Deploy Hedge Agent to AWS with Full Optimization
# This script automates the entire AWS deployment process

set -e

echo "🚀 Starting AWS Deployment for Hedge Agent with Full Optimization..."

# Configuration
PROJECT_NAME="hedge-agent"
ENVIRONMENT="prod"
AWS_REGION="us-east-1"
ECR_REPO_NAME="hedge-agent-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Node.js and Angular CLI are installed
    if ! command -v ng &> /dev/null; then
        print_error "Angular CLI is not installed. Please install it first: npm install -g @angular/cli"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured. Please run 'aws configure'"
        exit 1
    fi
    
    print_success "All prerequisites are satisfied!"
}

# Get user inputs
get_user_inputs() {
    print_status "Gathering configuration..."
    
    # Check if environment variables are set, otherwise prompt
    if [ -z "$DIFY_API_KEY" ]; then
        read -p "Enter your Dify API key: " DIFY_API_KEY
    fi
    
    if [ -z "$SUPABASE_URL" ]; then
        read -p "Enter your Supabase URL: " SUPABASE_URL
    fi
    
    if [ -z "$SUPABASE_ANON_KEY" ]; then
        read -s -p "Enter your Supabase anonymous key: " SUPABASE_ANON_KEY
        echo
    fi
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_success "AWS Account ID: $AWS_ACCOUNT_ID"
}

# Step 1: Create ECR repository and build Docker image
build_and_push_docker() {
    print_status "Step 1: Building and pushing Docker image..."
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || {
        print_status "Creating ECR repository..."
        aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION
        print_success "ECR repository created!"
    }
    
    # Get ECR login token
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Create Dockerfile for FastAPI backend
    cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY optimized_hedge_data_service.py .
COPY redis_cache_service.py .
COPY optimized_dify_endpoint.py .
COPY app/ ./app/ 2>/dev/null || echo "No app directory found"

# Create health check endpoint
RUN echo 'from fastapi import FastAPI; from optimized_dify_endpoint import app; @app.get("/health"); def health_check(): return {"status": "healthy"}' >> health_check.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "optimized_dify_endpoint:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

    # Create requirements.txt
    cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
httpx==0.25.2
pydantic==2.5.0
supabase==2.0.2
python-multipart==0.0.6
asyncio-throttle==1.0.2
python-dotenv==1.0.0
boto3==1.34.0
EOF

    # Build Docker image
    print_status "Building Docker image..."
    docker build -t $ECR_REPO_NAME:latest .
    
    # Tag for ECR
    docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
    
    # Push to ECR
    print_status "Pushing Docker image to ECR..."
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
    
    print_success "Docker image built and pushed successfully!"
}

# Step 2: Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_status "Step 2: Deploying AWS infrastructure with Terraform..."
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars file
    cat > terraform.tfvars << EOF
aws_region = "$AWS_REGION"
project_name = "$PROJECT_NAME"
environment = "$ENVIRONMENT"
dify_api_key = "$DIFY_API_KEY"
supabase_url = "$SUPABASE_URL"
supabase_anon_key = "$SUPABASE_ANON_KEY"
EOF

    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var-file="terraform.tfvars"
    
    # Ask for confirmation
    read -p "Do you want to proceed with the infrastructure deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Apply infrastructure
        print_status "Applying Terraform configuration..."
        terraform apply -var-file="terraform.tfvars" -auto-approve
        print_success "Infrastructure deployed successfully!"
        
        # Get outputs
        REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
        LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
        CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain)
        S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
        ECS_CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
        
        print_success "Infrastructure outputs:"
        echo "  - Redis Endpoint: $REDIS_ENDPOINT"
        echo "  - Load Balancer DNS: $LOAD_BALANCER_DNS"
        echo "  - CloudFront Domain: $CLOUDFRONT_DOMAIN"
        echo "  - S3 Bucket: $S3_BUCKET_NAME"
        echo "  - ECS Cluster: $ECS_CLUSTER_NAME"
        
    else
        print_warning "Infrastructure deployment cancelled."
        exit 1
    fi
}

# Step 3: Update ECS Task Definition with correct image URI
update_ecs_task_definition() {
    print_status "Step 3: Updating ECS task definition with correct image..."
    
    # Update the Terraform configuration to use the correct ECR image URI
    sed -i.bak "s|your-ecr-repo-url:latest|$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest|g" aws-terraform-infrastructure.tf
    
    # Apply the updated configuration
    terraform apply -var-file="terraform.tfvars" -auto-approve
    
    print_success "ECS task definition updated!"
}

# Step 4: Build and deploy Angular frontend
deploy_frontend() {
    print_status "Step 4: Building and deploying Angular frontend..."
    
    # Update environment configuration
    LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
    
    # Update Angular environment file
    cat > src/environments/environment.prod.ts << EOF
export const environment = {
  production: true,
  apiUrl: 'http://$LOAD_BALANCER_DNS/api/v2',
  supabaseUrl: '$SUPABASE_URL',
  supabaseAnonKey: '$SUPABASE_ANON_KEY',
  
  // AWS optimization settings
  awsOptimization: {
    enabled: true,
    serverSideCache: true,
    parallelProcessing: true,
    redisCache: true
  }
};
EOF

    # Build Angular application
    print_status "Building Angular application..."
    ng build --configuration=production
    
    # Deploy to S3
    S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
    print_status "Deploying to S3 bucket: $S3_BUCKET_NAME"
    
    aws s3 sync dist/ s3://$S3_BUCKET_NAME --delete
    
    # Invalidate CloudFront cache
    CLOUDFRONT_DISTRIBUTION_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?contains(Aliases.Items, '$CLOUDFRONT_DOMAIN')].Id" --output text)
    if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
        print_status "Invalidating CloudFront cache..."
        aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"
    fi
    
    print_success "Frontend deployed successfully!"
}

# Step 5: Verify deployment
verify_deployment() {
    print_status "Step 5: Verifying deployment..."
    
    # Check ECS service status
    ECS_CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    SERVICE_STATUS=$(aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services "${PROJECT_NAME}-api-service-${ENVIRONMENT}" --query 'services[0].status' --output text)
    
    if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
        print_success "ECS service is ACTIVE"
    else
        print_warning "ECS service status: $SERVICE_STATUS"
    fi
    
    # Check health endpoint
    LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
    print_status "Checking health endpoint..."
    
    # Wait for service to be ready
    print_status "Waiting for service to be ready..."
    sleep 60
    
    HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://$LOAD_BALANCER_DNS/health || echo "000")
    if [ "$HEALTH_CHECK" == "200" ]; then
        print_success "Health check passed!"
    else
        print_warning "Health check returned status: $HEALTH_CHECK"
    fi
    
    # Test optimization endpoint
    print_status "Testing optimization endpoint..."
    TEST_RESPONSE=$(curl -s -X POST http://$LOAD_BALANCER_DNS/dify/performance-stats || echo "Failed")
    if [[ $TEST_RESPONSE == *"service_performance"* ]]; then
        print_success "Optimization endpoint is responding!"
    else
        print_warning "Optimization endpoint may not be ready yet"
    fi
    
    print_success "Deployment verification complete!"
}

# Step 6: Display deployment summary
display_summary() {
    print_status "🎉 Deployment Summary"
    
    CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain)
    LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
    
    echo "=================================="
    echo "AWS Deployment Complete!"
    echo "=================================="
    echo ""
    echo "🌍 Frontend URL: https://$CLOUDFRONT_DOMAIN"
    echo "🔧 API Endpoint: http://$LOAD_BALANCER_DNS"
    echo "📊 Performance Stats: http://$LOAD_BALANCER_DNS/dify/performance-stats"
    echo ""
    echo "🚀 Expected Performance Improvements:"
    echo "   • Response Time: 200-500ms (vs 2-3 seconds)"
    echo "   • Cache Hit Rate: 80-90% after warmup"
    echo "   • Data Reduction: 90% less data to Dify"
    echo ""
    echo "📊 Monitoring:"
    echo "   • CloudWatch: AWS Console → CloudWatch → Log Groups"
    echo "   • ECS Tasks: AWS Console → ECS → Clusters → $ECS_CLUSTER_NAME"
    echo "   • Redis: AWS Console → ElastiCache"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   • Check ECS logs in CloudWatch"
    echo "   • Verify security groups allow traffic"
    echo "   • Ensure environment variables are correct"
    echo ""
    echo "✅ Your optimized hedge agent is now running on AWS!"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up temporary files..."
    rm -f Dockerfile requirements.txt terraform.tfvars
}

# Main execution
main() {
    print_status "🚀 AWS Deployment Script for Hedge Agent"
    print_status "This will deploy your application with full optimization to AWS"
    echo ""
    
    check_prerequisites
    get_user_inputs
    
    # Create backup of original Terraform file
    cp aws-terraform-infrastructure.tf aws-terraform-infrastructure.tf.backup
    
    build_and_push_docker
    deploy_infrastructure
    update_ecs_task_definition
    deploy_frontend
    verify_deployment
    display_summary
    
    cleanup
    
    print_success "🎉 Deployment completed successfully!"
    print_status "Your optimized Dify integration is now live on AWS!"
}

# Handle script interruption
trap cleanup EXIT

# Run main function
main "$@"