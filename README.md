# DocIQ - Secure Multi-Tenant RAG Chatbot

A production-ready, secure RAG (Retrieval Augmented Generation) chatbot that enables companies to upload confidential documents and query them using AI - with enterprise-grade security, multi-tenant isolation, and zero data leakage.

## 🚀 Features

- **Multi-tenant isolation** - Company-level data segregation
- **Role-based access control** - Admin, Uploader, Viewer roles
- **Department-level security** - HR can't see Finance docs
- **AWS Bedrock integration** - Amazon Nova Pro for AI inference
- **Vector search** - pgvector for semantic search
- **Audit logging** - Full compliance trail
- **Production-ready** - Deployed on AWS with Terraform

## 🏗️ Architecture

- **Frontend**: React 18 + TypeScript + Vite + shadcn/ui
- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL + pgvector (production) / SQLite (demo)
- **AI**: AWS Bedrock (Amazon Nova Pro)
- **Storage**: Amazon S3
- **Infrastructure**: AWS ECS Fargate, ALB, VPC, RDS Aurora

## 📋 Prerequisites

- Node.js >= 18
- Python >= 3.11
- AWS Account with Bedrock access
- Docker (for deployment)

## 🔧 Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials and settings

# Run the backend
python app.py
```

### Frontend

```bash
cd frontend
npm install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your backend URL

# Run the frontend
npm run dev
```

## 🌐 Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete deployment instructions.

### Quick Deploy to Vercel (Frontend)

```bash
cd frontend
npm run build
npx vercel --prod
```

### Deploy to AWS (Backend)

```bash
cd infra/terraform
terraform init
terraform apply
```

## 🔐 Security

- All secrets stored in AWS Secrets Manager
- VPC isolation with private subnets
- No public internet access for backend
- Encrypted at rest (AES-256) and in transit (TLS 1.3)
- Multi-tenant data isolation
- HIPAA, SOC 2, PCI-DSS compliant architecture

## 📊 Cost

- **Demo**: ~$35/month (testing only)
- **Small Team (1-50 users)**: ~$71/month
- **Medium Company (50-500 users)**: ~$235/month
- **Enterprise (500-5000 users)**: ~$1,547/month

## 📖 Documentation

- [Product Brief](PRODUCT_BRIEF.md)
- [Architecture](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Interactive Diagrams](DIAGRAMS_README.md)

## 🧪 Demo Accounts

- Admin: `admin@dociq.com` / `demo123` / `demo-company`
- Uploader: `sarah@dociq.com` / `demo123` / `demo-company`
- Viewer: `viewer@dociq.com` / `demo123` / `demo-company`

## 📝 License

MIT

## ⚠️ Important Notes

- Never commit `.env` files or database files
- Always use environment variables for secrets
- Keep AWS credentials secure
- Review security groups before deploying to production
