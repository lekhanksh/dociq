# DocIQ - Deployment Guide

## 🚀 Complete Deployment Steps

This guide covers deploying DocIQ from local development to production on AWS.

---

## 📋 Prerequisites

### Required Tools
- AWS CLI configured with admin access
- Docker Desktop installed and running
- Terraform >= 1.0
- Node.js >= 18
- Python >= 3.11
- Git

### AWS Account Setup
1. Create AWS account (if needed)
2. Create IAM user with AdministratorAccess
3. Configure AWS CLI:
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

4. Request Bedrock model access:
   - Go to AWS Console → Bedrock → Model access
   - Request access to: Amazon Nova Pro (or Claude 3.5 Haiku)
   - Usually approved instantly

---

## 🏗️ Phase 1: Local Development Setup

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd dociq
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required `.env` variables:**
```bash
ENV=development
DATABASE_URL=sqlite:///./dociq.db
VECTOR_BACKEND=sqlite
JWT_SECRET=your-super-secret-key-minimum-32-characters-long
S3_BUCKET_NAME=your-company-documents
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

### 3. Create S3 Bucket
```bash
# Create bucket
aws s3 mb s3://your-company-documents --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-company-documents \
  --versioning-configuration Status=Enabled

# Add lifecycle policy (30-day Intelligent-Tiering)
cat > lifecycle.json <<EOF
{
  "Rules": [{
    "Id": "IntelligentTieringRule",
    "Status": "Enabled",
    "Transitions": [{
      "Days": 30,
      "StorageClass": "INTELLIGENT_TIERING"
    }]
  }]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket your-company-documents \
  --lifecycle-configuration file://lifecycle.json
```

### 4. Start Backend
```bash
cd backend
python app.py
# Backend running at http://localhost:8000
```

### 5. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Edit .env
nano .env
```

**Required `.env` variables:**
```bash
VITE_API_URL=http://localhost:8000
```

### 6. Start Frontend
```bash
cd frontend
npm run dev
# Frontend running at http://localhost:8080
```

### 7. Test Locally
- Open http://localhost:8080
- Login with: `admin@dociq.com` / `demo123` / `demo-company`
- Upload a test document
- Ask a question

---

## 🐳 Phase 2: Docker Build & Push to ECR

### 1. Create ECR Repository
```bash
aws ecr create-repository \
  --repository-name dociq-backend \
  --region us-east-1
```

**Output:**
```json
{
  "repository": {
    "repositoryUri": "028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend"
  }
}
```

### 2. Login to ECR
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  028975698487.dkr.ecr.us-east-1.amazonaws.com
```

### 3. Build Docker Image
```bash
cd backend

# Build for linux/amd64 (required for ECS Fargate)
docker build --platform linux/amd64 -t dociq-backend .

# Tag image
docker tag dociq-backend:latest \
  028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest
```

### 4. Push to ECR
```bash
docker push 028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest
```

---

## ☁️ Phase 3: Deploy Infrastructure with Terraform

### 1. Create Secrets Manager Secret
```bash
aws secretsmanager create-secret \
  --name dociq-staging-jwt-secret \
  --secret-string "dociq-staging-jwt-secret-32chars!!" \
  --region us-east-1
```

### 2. Initialize Terraform
```bash
cd infra/terraform

terraform init
```

### 3. Review Terraform Plan
```bash
terraform plan \
  -var="ecr_image_uri=028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest" \
  -var="jwt_secret=dociq-staging-jwt-secret-32chars!!" \
  -var="env=staging"
```

### 4. Deploy Infrastructure
```bash
terraform apply \
  -var="ecr_image_uri=028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest" \
  -var="jwt_secret=dociq-staging-jwt-secret-32chars!!" \
  -var="env=staging" \
  -auto-approve
```

**This creates:**
- VPC with public/private subnets (2 AZs)
- Application Load Balancer (public)
- ECS Fargate cluster + service
- Security groups
- VPC endpoints (S3, Bedrock, Secrets Manager, ECR, CloudWatch)
- IAM roles and policies
- CloudWatch log groups

**Deployment time:** ~10-15 minutes

### 5. Get ALB DNS Name
```bash
terraform output alb_dns_name
# Output: dociq-staging-alb-1174832729.us-east-1.elb.amazonaws.com
```

### 6. Test Backend
```bash
curl http://dociq-staging-alb-1174832729.us-east-1.elb.amazonaws.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "dociq",
  "version": "2.0.0",
  "features": {
    "bedrock": true,
    "vector_backend": "sqlite",
    "s3": true,
    "documents_indexed": 0
  }
}
```

---

## 🌐 Phase 4: Deploy Frontend

### Option A: Local Development (Current)
```bash
cd frontend

# Update .env to point to AWS backend
echo "VITE_API_URL=http://dociq-staging-alb-1174832729.us-east-1.elb.amazonaws.com" > .env

# Start dev server
npm run dev
# Access at http://localhost:8080
```

### Option B: Deploy to S3 + CloudFront (Production)

#### 1. Build Frontend
```bash
cd frontend
npm run build
# Creates frontend/dist/ folder
```

#### 2. Create S3 Bucket for Frontend
```bash
aws s3 mb s3://dociq-frontend-prod --region us-east-1

# Enable static website hosting
aws s3 website s3://dociq-frontend-prod \
  --index-document index.html \
  --error-document index.html
```

#### 3. Upload Build
```bash
cd frontend
aws s3 sync dist/ s3://dociq-frontend-prod --delete
```

#### 4. Create CloudFront Distribution
```bash
# Create distribution (via AWS Console or Terraform)
# Point origin to S3 bucket
# Enable HTTPS with ACM certificate
# Set default root object: index.html
```

#### 5. Update Frontend .env
```bash
# In frontend/.env (before building)
VITE_API_URL=https://api.dociq.yourcompany.com
```

---

## 🔒 Phase 5: Production Hardening

### 1. Make ALB Internal (Private)
```bash
cd infra/terraform

# Edit ecs.tf
# Change: internal = false → internal = true

terraform apply -auto-approve
```

### 2. Add WAF to ALB
```bash
# Create WAF Web ACL
aws wafv2 create-web-acl \
  --name dociq-waf \
  --scope REGIONAL \
  --region us-east-1 \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <waf-arn> \
  --resource-arn <alb-arn>
```

### 3. Enable HTTPS on ALB
```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name dociq.yourcompany.com \
  --validation-method DNS \
  --region us-east-1

# Add HTTPS listener to ALB (via Terraform or Console)
# Redirect HTTP → HTTPS
```

### 4. Upgrade to RDS Aurora
```bash
# Create RDS Aurora PostgreSQL cluster
aws rds create-db-cluster \
  --db-cluster-identifier dociq-prod \
  --engine aurora-postgresql \
  --engine-version 16.1 \
  --master-username dociq \
  --master-user-password <strong-password> \
  --db-subnet-group-name dociq-db-subnet \
  --vpc-security-group-ids sg-xxx

# Create instance
aws rds create-db-instance \
  --db-instance-identifier dociq-prod-instance-1 \
  --db-instance-class db.t4g.micro \
  --engine aurora-postgresql \
  --db-cluster-identifier dociq-prod

# Install pgvector extension
psql -h <rds-endpoint> -U dociq -d postgres
CREATE EXTENSION vector;
```

### 5. Update Backend Environment Variables
```bash
# Update ECS task definition with new env vars
DATABASE_URL=postgresql://dociq:<password>@<rds-endpoint>:5432/dociq
VECTOR_BACKEND=pgvector
```

### 6. Switch to Fargate Spot (70% discount)
```bash
# Edit infra/terraform/ecs.tf
# Add capacity_provider_strategy:
capacity_provider_strategy {
  capacity_provider = "FARGATE_SPOT"
  weight           = 100
}

terraform apply -auto-approve
```

---

## 📊 Phase 6: Monitoring & Alerts

### 1. Create CloudWatch Dashboard
```bash
aws cloudwatch put-dashboard \
  --dashboard-name dociq-prod \
  --dashboard-body file://dashboard.json
```

### 2. Create Alarms
```bash
# CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name dociq-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions <sns-topic-arn>

# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name dociq-high-errors \
  --alarm-description "Alert when error rate > 1%" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>
```

### 3. Enable CloudTrail (Audit Logs)
```bash
aws cloudtrail create-trail \
  --name dociq-audit \
  --s3-bucket-name dociq-cloudtrail-logs

aws cloudtrail start-logging --name dociq-audit
```

---

## 🔄 Phase 7: CI/CD Setup (Optional)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | \
          docker login --username AWS --password-stdin \
          028975698487.dkr.ecr.us-east-1.amazonaws.com
      
      - name: Build and push Docker image
        run: |
          cd backend
          docker build --platform linux/amd64 -t dociq-backend .
          docker tag dociq-backend:latest \
            028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest
          docker push 028975698487.dkr.ecr.us-east-1.amazonaws.com/dociq-backend:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster dociq-staging-cluster \
            --service backend-service \
            --force-new-deployment
```

---

## 🧪 Testing Checklist

### After Each Deployment

- [ ] Backend health check returns 200
- [ ] Frontend loads without errors
- [ ] Can login with demo accounts
- [ ] Can upload PDF document
- [ ] Can query documents and get answers
- [ ] Citations are clickable and expandable
- [ ] Admin can delete documents
- [ ] Viewer cannot upload (403 error)
- [ ] Rate limiting works (429 after 100 requests)
- [ ] Audit logs are being written
- [ ] CloudWatch logs are appearing
- [ ] ECS tasks are healthy
- [ ] ALB target group shows healthy targets

---

## 🐛 Troubleshooting

### Backend Not Starting
```bash
# Check ECS task logs
aws logs tail /ecs/dociq-staging --follow

# Check task status
aws ecs describe-tasks \
  --cluster dociq-staging-cluster \
  --tasks <task-id>
```

### ALB Returns 503
```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# Common causes:
# - ECS task not passing health checks
# - Security group blocking ALB → ECS traffic
# - Backend not listening on port 8000
```

### Can't Access Bedrock
```bash
# Check VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.bedrock-runtime"

# Check IAM permissions
aws iam get-role-policy \
  --role-name ecs-task-role \
  --policy-name bedrock-access
```

### Database Connection Fails
```bash
# Check security group
aws ec2 describe-security-groups --group-ids <sg-id>

# Test connection from ECS task
aws ecs execute-command \
  --cluster dociq-staging-cluster \
  --task <task-id> \
  --command "psql -h <rds-endpoint> -U dociq -d postgres"
```

---

## 💰 Cost Optimization Tips

1. **Use Fargate Spot**: 70% discount, rare interruptions
2. **Remove unnecessary VPC endpoints**: Keep only S3 + Bedrock
3. **Use Claude Haiku**: 5x cheaper than Sonnet
4. **Enable S3 Intelligent-Tiering**: Automatic cost optimization
5. **Set ECS auto-scaling**: Scale down during off-hours
6. **Use RDS t4g.micro**: ARM-based, 20% cheaper
7. **Enable CloudWatch log retention**: Delete old logs after 7 days

---

## 📈 Scaling Guide

### Vertical Scaling (More Resources)
```bash
# Increase ECS task size
# Edit task definition:
cpu: 2048 (2 vCPU)
memory: 4096 (4 GB)

# Upgrade RDS instance
aws rds modify-db-instance \
  --db-instance-identifier dociq-prod-instance-1 \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

### Horizontal Scaling (More Tasks)
```bash
# Update ECS service
aws ecs update-service \
  --cluster dociq-staging-cluster \
  --service backend-service \
  --desired-count 3

# Configure auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/dociq-staging-cluster/backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/dociq-staging-cluster/backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization}"
```

---

## 🔐 Security Best Practices

1. **Rotate secrets regularly** (JWT secret, DB password)
2. **Enable MFA** on AWS root account
3. **Use IAM roles** instead of access keys
4. **Enable CloudTrail** for audit logs
5. **Review security groups** monthly
6. **Enable GuardDuty** for threat detection
7. **Use AWS Config** for compliance monitoring
8. **Enable S3 bucket encryption** (already done)
9. **Use VPC Flow Logs** for network monitoring
10. **Regular security audits** with AWS Trusted Advisor

---

## 📞 Support

For issues or questions:
1. Check CloudWatch logs first
2. Review this deployment guide
3. Check AWS service health dashboard
4. Review Terraform state for infrastructure issues

---

**Deployment complete! 🎉**
