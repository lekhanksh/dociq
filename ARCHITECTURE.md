# DocIQ - System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────┐
│   Browser   │
│  (React)    │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│     ALB     │────▶│ ECS Fargate  │────▶│  RDS Aurora  │
│   + WAF     │     │  (Backend)   │     │  PostgreSQL  │
└─────────────┘     └──────┬───────┘     │  + pgvector  │
                           │              └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌─────▼─────┐
   │   S3    │      │   Bedrock   │    │  Pinecone │
   │ (Docs)  │      │ (Nova Pro)  │    │ (Vectors) │
   └─────────┘      └─────────────┘    └───────────┘
```

---

## 📦 Component Architecture

### 1. Frontend Layer

**Technology**: React 18 + TypeScript + Vite

**Components**:
- `AppLayout.tsx` - Main layout with sidebar
- `Login.tsx` - Authentication page
- `Upload.tsx` - Document upload interface
- `Chat.tsx` - Query interface with citations
- `ChatMessage.tsx` - Message display with expandable citations
- `ProtectedRoute.tsx` - Route guards based on roles

**State Management**:
- TanStack Query for API calls
- React Context for auth state
- Local storage for JWT tokens

**Key Features**:
- JWT-based authentication
- Role-based UI rendering
- Drag-and-drop file upload
- Real-time chat interface
- Expandable citation sources
- Responsive design (mobile-friendly)

---

### 2. Backend Layer

**Technology**: FastAPI + Python 3.11

**Architecture Layers**:

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│  • POST /auth/login - JWT authentication                │
│  • POST /upload - Document upload & processing          │
│  • POST /query - RAG query with AI                      │
│  • GET /collections/info - Document stats               │
│  • DELETE /documents/{id} - Admin-only deletion         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Authentication & Authorization              │
│  • JWT token validation (jose)                          │
│  • Role-based access control (RBAC)                     │
│  • Department-level isolation                           │
│  • Rate limiting (100 req/min per user)                 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Document Processing Pipeline                │
│  1. File validation (type, size)                        │
│  2. Text extraction (PyPDF2, python-docx)               │
│  3. Text chunking (500 chars, 50 overlap)               │
│  4. Vector embedding (384 dimensions)                   │
│  5. Storage (pgvector/Pinecone + S3)                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  RAG Pipeline                            │
│  1. Query embedding                                      │
│  2. Vector similarity search (top 5-15 chunks)          │
│  3. Filter by company_id + department                   │
│  4. Context assembly (multi-doc aware)                  │
│  5. Bedrock API call (Amazon Nova Pro)                  │
│  6. Response with citations                             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Data Access Layer                       │
│  • SQLAlchemy ORM                                        │
│  • Connection pooling                                    │
│  • Transaction management                                │
│  • Query optimization                                    │
└──────────────────────────────────────────────────────────┘
```

---

### 3. Data Layer

#### A. PostgreSQL + pgvector (Production)

**Schema**:

```sql
-- Companies table (multi-tenant isolation)
CREATE TABLE companies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users table (authentication + RBAC)
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR REFERENCES companies(id),
    email VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR,
    department VARCHAR NOT NULL,  -- hr, finance, legal, general
    role VARCHAR NOT NULL,         -- admin, uploader, viewer
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, email)
);

-- Documents table (metadata)
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR REFERENCES companies(id),
    uploaded_by VARCHAR REFERENCES users(id),
    filename VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    s3_key VARCHAR,
    file_size INTEGER,
    chunk_count INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Query logs table (audit trail)
CREATE TABLE query_logs (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR REFERENCES companies(id),
    user_id VARCHAR REFERENCES users(id),
    question TEXT NOT NULL,
    answer TEXT,
    sources JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Embeddings table (vector search with pgvector)
CREATE TABLE embeddings (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR REFERENCES documents(id),
    chunk_index INTEGER,
    chunk_text TEXT,
    embedding VECTOR(384),  -- pgvector extension
    metadata JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast vector search
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### B. S3 (Document Storage)

**Structure**:
```
s3://your-company-documents/
├── companies/
│   ├── demo-company-001/
│   │   ├── documents/
│   │   │   ├── {file_id_1}/
│   │   │   │   └── policy.pdf
│   │   │   ├── {file_id_2}/
│   │   │   │   └── report.docx
```

**Features**:
- Versioning enabled (recover deleted files)
- Lifecycle policy: 30 days → Intelligent-Tiering
- Server-side encryption (AES-256)
- Metadata: company_id, uploaded_by, department

#### C. Vector Store Options

**Option 1: pgvector (Current)**
- Embedded in PostgreSQL
- Good for <1M vectors
- 50-100ms latency
- Lower cost ($12/month for RDS)
- ACID transactions with metadata

**Option 2: Pinecone (Alternative)**
- Managed vector database
- Scales to billions of vectors
- <30ms latency
- Free tier: 100K vectors
- Paid: $70/month (unlimited)

---

### 4. AI Layer

**AWS Bedrock - Amazon Nova Pro**

**Model**: `amazon.nova-pro-v1:0`

**Configuration**:
```python
{
    "system": "You are DocIQ, a secure company document assistant...",
    "messages": [
        {"role": "user", "content": "DOCUMENTS:\n{context}\n\nQUESTION: {question}"}
    ],
    "inferenceConfig": {
        "max_new_tokens": 2000,
        "temperature": 0.3,  # Factual, not creative
        "top_p": 0.9
    }
}
```

**Features**:
- Multi-document reasoning
- Calculation support (totals, averages)
- Source citation
- No data retention (privacy)
- Cost: ~$0.02 per query

**Alternative Models**:
- Claude 3.5 Haiku: 5x cheaper, good quality
- Claude 3.5 Sonnet: Best quality, 12x more expensive

---

### 5. Infrastructure Layer (AWS)

#### A. Networking (VPC)

```
VPC: 10.0.0.0/16
├── Availability Zone: us-east-1a
│   ├── Public Subnet: 10.0.1.0/24
│   │   └── ALB (part 1)
│   └── Private Subnet: 10.0.101.0/24
│       └── ECS Fargate Task #1
│
├── Availability Zone: us-east-1b
│   ├── Public Subnet: 10.0.2.0/24
│   │   └── ALB (part 2)
│   └── Private Subnet: 10.0.102.0/24
│       └── ECS Fargate Task #2 (auto-scaled)
│
├── Internet Gateway
│   └── Public subnets only
│
├── VPC Endpoints (PrivateLink)
│   ├── S3 (Gateway) - No internet needed
│   ├── Bedrock (Interface) - Private connection
│   ├── Secrets Manager (Interface)
│   ├── ECR (Interface) - Pull Docker images
│   └── CloudWatch Logs (Interface)
│
└── Security Groups
    ├── sg-alb: 0.0.0.0/0:443 → ECS:8000
    ├── sg-backend: ALB only → All out
    └── sg-rds: ECS only:5432
```

#### B. Compute (ECS Fargate)

**Cluster**: `dociq-staging-cluster`

**Service**: `backend-service`
- Desired count: 2 (production) / 1 (demo)
- Min: 2, Max: 10
- Auto-scaling target: CPU 70%
- Deployment: Rolling update
- Health check grace period: 60s

**Task Definition**:
- CPU: 1024 (1 vCPU)
- Memory: 2048 (2 GB)
- Image: ECR (dociq-backend:latest)
- Port: 8000
- Platform: linux/amd64
- Pricing: Fargate Spot (70% discount)

**Environment Variables**:
```bash
ENV=production
DATABASE_URL=postgresql://...
VECTOR_BACKEND=pgvector
JWT_SECRET=<from-secrets-manager>
S3_BUCKET_NAME=your-company-documents
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

#### C. Load Balancer (ALB)

**Configuration**:
- Type: Application Load Balancer
- Scheme: internet-facing (demo) / internal (production)
- Subnets: Public subnets (us-east-1a, us-east-1b)
- Listener: HTTPS:443 → Target Group
- Health check: GET /health every 30s
- SSL: ACM certificate (free)

**Target Group**:
- Protocol: HTTP
- Port: 8000
- Health check path: /health
- Healthy threshold: 2 consecutive successes
- Unhealthy threshold: 3 consecutive failures
- Timeout: 5 seconds
- Interval: 30 seconds

---

## 🔄 Data Flow Diagrams

### Upload Flow

```
1. User selects PDF file (frontend)
   ↓
2. POST /upload (multipart/form-data)
   ↓
3. Backend validates:
   • File type (.pdf, .docx, .txt only)
   • File size (< 10MB)
   • User has uploader/admin role
   ↓
4. Extract text:
   • PDF: PyPDF2.PdfReader
   • DOCX: python-docx.Document
   • TXT: decode UTF-8
   ↓
5. Chunk text:
   • Size: 500 characters
   • Overlap: 50 characters
   • Result: ~40 chunks for 10-page PDF
   ↓
6. Generate embeddings:
   • Model: sentence-transformers (384d)
   • Store in pgvector with metadata
   ↓
7. Upload original to S3:
   • Key: companies/{company_id}/documents/{file_id}/{filename}
   • Metadata: company_id, uploaded_by, department
   ↓
8. Save metadata to PostgreSQL:
   • documents table
   • Return document_id
   ↓
9. Return success (200 OK)
   Time: 5-10 seconds
```

### Query Flow

```
1. User asks: "What's the total revenue?"
   ↓
2. POST /query {"question": "..."}
   ↓
3. Backend detects complex query:
   • Keywords: total, calculate, sum, all, across
   • Increase top_k from 5 to 15
   ↓
4. Generate query embedding (384d)
   ↓
5. Vector similarity search (pgvector):
   • SELECT * FROM embeddings
   • WHERE company_id = ?
   • ORDER BY embedding <=> query_vector
   • LIMIT 15
   ↓
6. Filter by department:
   • If user is admin: all departments
   • Else: user's department only
   ↓
7. Group chunks by document:
   • Q1_Report.pdf: [chunk1, chunk2, ...]
   • Q2_Report.pdf: [chunk3, chunk4, ...]
   ↓
8. Build context:
   === DOCUMENT: Q1_Report.pdf ===
   Revenue: $1.2M
   === DOCUMENT: Q2_Report.pdf ===
   Revenue: $1.5M
   ↓
9. Send to Bedrock:
   • System prompt: "You can calculate across documents"
   • User prompt: Context + Question
   • Temperature: 0.3 (factual)
   ↓
10. Bedrock returns answer:
    "Total revenue: $2.7M
     Breakdown:
     - Q1: $1.2M (Q1_Report.pdf)
     - Q2: $1.5M (Q2_Report.pdf)"
   ↓
11. Log to audit trail:
    • query_logs table
    • Include: user, question, answer, sources
   ↓
12. Return response with citations (200 OK)
    Time: 2-3 seconds
```

---

## 🔐 Security Architecture

### 1. Authentication Flow

```
1. User enters email + password + company_slug
   ↓
2. Backend validates:
   • Company exists (by slug)
   • User exists (by email + company_id)
   • Password matches (bcrypt verify)
   ↓
3. Generate JWT token:
   • Payload: {sub, email, role, dept, company_id}
   • Secret: From AWS Secrets Manager
   • Expiry: 24 hours
   ↓
4. Return token + user info
   ↓
5. Frontend stores token:
   • localStorage: "auth_token"
   • Include in all API requests: Authorization: Bearer <token>
   ↓
6. Backend validates token on each request:
   • Decode JWT
   • Verify signature
   • Check expiry
   • Extract user info
   ↓
7. Check permissions:
   • RBAC: admin/uploader/viewer
   • Department isolation
   • Rate limiting
```

### 2. Multi-Tenant Isolation

**Database Level**:
```sql
-- Every query MUST filter by company_id
SELECT * FROM documents WHERE company_id = ? AND department = ?;

-- Row-level security (RLS) as backup
CREATE POLICY company_isolation ON documents
  USING (company_id = current_setting('app.current_company_id'));
```

**Application Level**:
```python
# Extract company_id from JWT token
current_user = get_current_user(token)
company_id = current_user["company_id"]

# Filter all queries
documents = db.query(Document).filter(
    Document.company_id == company_id
).all()
```

**Storage Level**:
```
# S3 prefix per company
s3://bucket/companies/{company_id}/documents/
```

### 3. Network Security

**Layers**:
1. **WAF** (Web Application Firewall)
   - SQL injection protection
   - XSS protection
   - Rate limiting (100 req/min per IP)
   - Geo-blocking (optional)

2. **ALB** (Application Load Balancer)
   - SSL/TLS termination
   - Security group: 0.0.0.0/0:443 only
   - Health checks

3. **VPC** (Virtual Private Cloud)
   - Private subnets for ECS tasks
   - No internet gateway for private subnets
   - VPC endpoints for AWS services

4. **Security Groups** (Stateful firewall)
   - sg-alb: Inbound 443 from internet, Outbound 8000 to ECS
   - sg-backend: Inbound 8000 from ALB only, Outbound all
   - sg-rds: Inbound 5432 from ECS only

---

## 📊 Performance Architecture

### 1. Caching Strategy

**Current** (No caching):
- Every query hits Bedrock ($0.02 cost)
- Every vector search hits database

**Future** (With Redis):
```
Query → Check Redis cache
  ├─ Hit: Return cached answer (0ms, $0)
  └─ Miss: RAG pipeline → Cache result → Return
```

**Cache Key**: `hash(company_id + question)`
**TTL**: 1 hour (answers may change as docs are added)

### 2. Database Optimization

**Connection Pooling**:
```python
# SQLAlchemy pool
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # Max 10 connections
    max_overflow=20,     # Up to 30 total
    pool_timeout=30,     # Wait 30s for connection
    pool_recycle=3600    # Recycle after 1 hour
)
```

**Indexes**:
```sql
-- Vector search (pgvector)
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- Metadata queries
CREATE INDEX ON documents (company_id, department);
CREATE INDEX ON query_logs (company_id, created_at);
CREATE INDEX ON users (company_id, email);
```

### 3. Auto-Scaling

**ECS Service**:
```
Target: CPU 70%
Min: 2 tasks
Max: 10 tasks

Scale up: Add 1 task when CPU > 70% for 2 minutes
Scale down: Remove 1 task when CPU < 50% for 5 minutes
```

**RDS Aurora**:
```
Min ACU: 0.5 (0.5 vCPU, 1 GB RAM)
Max ACU: 2 (2 vCPU, 4 GB RAM)

Auto-scales based on:
- CPU utilization
- Connection count
- Database load
```

---

## 💰 Cost Architecture

### Current (Demo): ~$100/month

| Service | Cost | Optimization |
|---------|------|--------------|
| ECS Fargate (1 task, on-demand) | $30 | Use Spot (-70%) |
| ALB | $20 | Keep |
| VPC Endpoints (5) | $37 | Remove 3 (-$22) |
| S3 | $1 | Keep |
| Bedrock | $10 | Use Haiku (-50%) |
| CloudWatch | $3 | Keep |
| Other | $1 | Keep |

### Optimized (Production): ~$50/month

| Service | Cost | Change |
|---------|------|--------|
| ECS Fargate Spot (2 tasks) | $9 | -70% discount |
| ALB | $16 | Slight decrease |
| VPC Endpoints (2: S3 + Bedrock) | $15 | Removed 3 |
| RDS t4g.micro | $12 | Added |
| S3 | $1 | Same |
| Bedrock (Haiku) | $5 | Cheaper model |
| CloudWatch | $0.50 | Reduced logs |
| CloudFront | $1 | Added |
| Other | $1 | Same |

---

## 🔮 Future Architecture

### Phase 1: Caching Layer
```
Frontend → CloudFront → ALB → ECS → Redis → PostgreSQL
                                  ↓
                              Bedrock
```
- Add Redis for query caching
- 80% cache hit rate = 80% cost savings on Bedrock

### Phase 2: Multi-Region
```
Route 53 (Geo-routing)
├─ us-east-1 (Primary)
│  └─ Full stack
└─ eu-west-1 (Secondary)
   └─ Full stack
```
- Active-active deployment
- Cross-region RDS replication
- S3 cross-region replication

### Phase 3: Microservices
```
API Gateway
├─ Auth Service (Lambda)
├─ Upload Service (ECS)
├─ Query Service (ECS)
└─ Admin Service (Lambda)
```
- Separate services for better scaling
- Independent deployment
- Service mesh (AWS App Mesh)

---

## 📈 Monitoring Architecture

### CloudWatch Dashboards

**1. Application Metrics**
- Request count (per minute)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Query latency (vector search + Bedrock)

**2. Infrastructure Metrics**
- ECS CPU/Memory utilization
- ALB target health
- RDS connections/CPU
- S3 request count

**3. Business Metrics**
- Documents uploaded (per day)
- Queries executed (per day)
- Active users (per day)
- Cost per query

### Alarms

**Critical** (PagerDuty):
- Error rate > 5%
- All ECS tasks unhealthy
- RDS CPU > 90%
- ALB 5xx > 10/min

**Warning** (Email):
- Error rate > 1%
- ECS CPU > 80%
- RDS connections > 80%
- Query latency > 5s

---

**Architecture complete! This document covers all layers from frontend to infrastructure.**
