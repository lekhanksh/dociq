"""
DocIQ Production-Ready RAG Backend
Private & Secure Company Chatbot with AWS Bedrock + Vector Search
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import boto3
import json
import uuid
import os
import time
from typing import List, Dict, Any, Optional
import PyPDF2
import docx
import io
from functools import wraps
from dotenv import load_dotenv
from vector_store import InMemoryVectorStore, SQLiteVectorStore, PgVectorStore, PineconeVectorStore

load_dotenv()

# ========== CONFIGURATION ==========
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
REQUEST_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
REQUEST_LIMIT_PER_WINDOW = int(os.getenv("RATE_LIMIT_REQUESTS_PER_WINDOW", "100"))

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-company-documents")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dociq.db")
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "memory").lower()
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:3000,http://127.0.0.1:8080").split(",") if origin.strip()]
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "./logs/audit.log")

# ========== AWS CLIENTS ==========
try:
    bedrock_client = boto3.client(
        'bedrock-runtime',
        region_name=AWS_REGION
    )
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    print("✅ AWS clients initialized")
except Exception as e:
    print(f"⚠️ AWS clients not available: {e}")
    bedrock_client = None
    s3_client = None

SQLITE_VECTOR_PATH = os.getenv("SQLITE_VECTOR_PATH", "./dociq_vectors.db")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")

# ========== VECTOR STORE ==========
# Priority: pinecone → pgvector (prod) → SQLite (local dev) → in-memory (fallback)
if VECTOR_BACKEND == "pinecone":
    if not PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY is required when VECTOR_BACKEND=pinecone")
    try:
        vector_store = PineconeVectorStore(PINECONE_API_KEY)
        print("✅ Using Pinecone vector backend")
    except Exception as e:
        print(f"⚠️ Pinecone failed, falling back to SQLite: {e}")
        vector_store = SQLiteVectorStore(SQLITE_VECTOR_PATH)
elif VECTOR_BACKEND == "pgvector" and DATABASE_URL.startswith("postgresql"):
    try:
        vector_store = PgVectorStore(DATABASE_URL)
        print("✅ Using pgvector backend")
    except Exception as e:
        print(f"⚠️ pgvector failed, falling back to SQLite: {e}")
        vector_store = SQLiteVectorStore(SQLITE_VECTOR_PATH)
elif VECTOR_BACKEND == "memory":
    vector_store = InMemoryVectorStore()
    print("✅ Using in-memory vector backend (data lost on restart)")
else:
    # Default for local dev: SQLite — persists across restarts, no extra services
    vector_store = SQLiteVectorStore(SQLITE_VECTOR_PATH)
    print(f"✅ Using SQLite vector backend (persistent): {SQLITE_VECTOR_PATH}")

# In-memory activity registry for local/stat endpoints
document_store: List[Dict[str, Any]] = []

def _sync_document_store_from_vector_store():
    """Populate document_store from the persistent vector store on startup."""
    try:
        # Pull all chunks (no filter) and rebuild document_store
        all_chunks = vector_store.search_chunks(query="the", top_k=10000)
        document_store.extend(all_chunks)
        unique = len({c.get("file_id") for c in all_chunks})
        if unique:
            print(f"✅ Restored {unique} documents ({len(all_chunks)} chunks) from persistent store")
    except Exception as e:
        print(f"⚠️ Could not restore document_store: {e}")

_sync_document_store_from_vector_store()

# ========== DATABASE ==========
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ========== DATABASE MODELS ==========
class CompanyDB(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserDB(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    department = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, uploader, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentDB(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False)
    uploaded_by = Column(String)
    filename = Column(String, nullable=False)
    department = Column(String, nullable=False)
    s3_key = Column(String)
    file_size = Column(Integer)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

class QueryLogDB(Base):
    __tablename__ = "query_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False)
    user_id = Column(String)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    sources = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"⚠️ Database bootstrap issue: {e}")

# ========== PYDANTIC MODELS ==========
class LoginRequest(BaseModel):
    email: str
    password: str
    company_slug: str

class QueryRequest(BaseModel):
    question: str
    department: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

# ========== DEMO DATA ==========
DEMO_COMPANIES = {
    "demo-company": {"id": "demo-company-001", "name": "Demo Company"}
}

DEMO_USERS = {
    "sarah@dociq.com": {
        "password": "demo123",
        "name": "Sarah Chen",
        "role": "uploader",
        "dept": "finance",
        "company_id": "demo-company-001"
    },
    "viewer@dociq.com": {
        "password": "demo123",
        "name": "Alex Roy",
        "role": "viewer",
        "dept": "hr",
        "company_id": "demo-company-001"
    },
    "admin@dociq.com": {
        "password": "demo123",
        "name": "Priya Mehta",
        "role": "admin",
        "dept": "general",
        "company_id": "demo-company-001"
    }
}

# ========== FASTAPI APP ==========
app = FastAPI(
    title="DocIQ RAG API",
    version="2.0.0",
    description="Private & Secure Company RAG Chatbot"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limit_state: Dict[str, List[float]] = {}

# ========== DATABASE DEPENDENCY ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== AUTHENTICATION ==========
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def enforce_rate_limit(actor_key: str, endpoint: str):
    now = time.time()
    key = f"{actor_key}:{endpoint}"
    timestamps = rate_limit_state.get(key, [])
    valid_timestamps = [ts for ts in timestamps if now - ts <= REQUEST_WINDOW_SECONDS]
    if len(valid_timestamps) >= REQUEST_LIMIT_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    valid_timestamps.append(now)
    rate_limit_state[key] = valid_timestamps


def log_audit_event(action: str, current_user: Dict[str, Any], details: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        payload = {
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "user": current_user.get("email"),
            "company_id": current_user.get("company_id"),
            "role": current_user.get("role"),
            "details": details,
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to write audit log: {e}")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    client_ip = request.client.host if request.client else "unknown"
    if not credentials or not credentials.credentials:
        log_audit_event("unauthorized", {"email": "anonymous", "company_id": "unknown", "role": "none"}, {
            "endpoint": str(request.url.path), "ip": client_ip, "reason": "missing_token"
        })
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        # Check demo tokens
        if token.startswith("demo_token_"):
            return {"role": "admin", "company_id": "demo-company-001", "email": "admin@dociq.com"}
        log_audit_event("unauthorized", {"email": "anonymous", "company_id": "unknown", "role": "none"}, {
            "endpoint": str(request.url.path), "ip": client_ip, "reason": "invalid_token"
        })
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload

def require_role(required_roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: dict = Depends(get_current_user), **kwargs):
            if current_user.get("role") not in required_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# ========== DOCUMENT PROCESSING ==========
def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF"""
    try:
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip() or "[PDF: Text extraction limited]"
    except Exception as e:
        return f"[PDF Extraction Error: {str(e)}]"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX"""
    try:
        docx_file = io.BytesIO(content)
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return text.strip() or "[DOCX: Text extraction limited]"
    except Exception as e:
        return f"[DOCX Extraction Error: {str(e)}]"

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks

def search_similar_chunks(query: str, top_k: int = 5, department: Optional[str] = None) -> List[Dict]:
    """Search for similar chunks using configured vector backend."""
    # For complex queries that might need multiple documents, increase top_k
    if any(keyword in query.lower() for keyword in ['total', 'calculate', 'sum', 'all', 'across', 'combined', 'overall']):
        top_k = min(top_k * 3, 15)  # Get more chunks for aggregation queries
    
    return vector_store.search_chunks(query=query, top_k=top_k, department=department)

# ========== BEDROCK AI ==========
def query_bedrock_with_context(question: str, context_chunks: List[Dict]) -> str:
    """Query AWS Bedrock with Amazon Nova Pro for RAG"""
    if not bedrock_client:
        print("❌ Bedrock client not initialized")
        return "[AI Service Unavailable: AWS Bedrock not configured]"

    # Prepare context - group by document for better multi-doc reasoning
    docs_context = {}
    for chunk in context_chunks[:10]:  # Increased from 3 to 10 for multi-doc queries
        doc_name = chunk['filename']
        if doc_name not in docs_context:
            docs_context[doc_name] = {
                'department': chunk['department'],
                'chunks': []
            }
        docs_context[doc_name]['chunks'].append(chunk['text'][:1000])
    
    # Format context with clear document separation
    context_parts = []
    for doc_name, doc_data in docs_context.items():
        doc_text = "\n".join(doc_data['chunks'])
        context_parts.append(
            f"=== DOCUMENT: {doc_name} (Department: {doc_data['department']}) ===\n{doc_text}\n"
        )
    
    context_text = "\n".join(context_parts)

    system_text = """You are DocIQ, a secure company document assistant specialized in financial analysis and multi-document reasoning. 

Your capabilities:
1. Analyze and synthesize information across MULTIPLE documents
2. Perform calculations when numerical data is provided (revenue, expenses, totals, etc.)
3. Cross-reference information from different sources
4. Identify patterns and trends across documents
5. Provide detailed, accurate answers with proper citations

Critical rules:
1. Use ONLY information from the provided documents - never make up data
2. When calculating totals or aggregations:
   - List each value found with its source document
   - Show your calculation step-by-step
   - Clearly state if any documents are missing data
3. If documents contain conflicting information, mention both values and their sources
4. If the answer requires information not in the documents, explicitly state what's missing
5. Always cite specific documents when referencing data
6. For financial queries, be precise with numbers and units (currency, percentages, etc.)

Format for multi-document answers:
- Start with the direct answer
- Show calculation breakdown if applicable
- List sources used with specific values from each
- Note any limitations or missing information"""

    user_text = f"""DOCUMENTS:
{context_text}

QUESTION: {question}

Answer based ONLY on the documents above:"""

    try:
        print(f"🤖 Calling Bedrock model: {BEDROCK_MODEL}")
        
        # Claude models use different API format
        if "claude" in BEDROCK_MODEL or "anthropic" in BEDROCK_MODEL:
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "system": system_text,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_text
                        }
                    ]
                })
            )
        else:
            # Nova models format
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "system": [{"text": system_text}],
                    "messages": [
                        {"role": "user", "content": [{"text": user_text}]}
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 2000,
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                })
            )

        response_body = json.loads(response['body'].read().decode('utf-8'))
        print(f"✅ Bedrock response received")

        # Parse response based on model type
        if "claude" in BEDROCK_MODEL or "anthropic" in BEDROCK_MODEL:
            # Claude response format
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text'].strip()
        else:
            # Nova Pro response format
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message']['content']
                if content and len(content) > 0:
                    return content[0]['text'].strip()
            elif 'content' in response_body:
                return response_body['content'][0]['text'].strip()
        
        return str(response_body)

    except Exception as e:
        print(f"❌ Bedrock error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {str(e)}")

# ========== API ENDPOINTS ==========
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dociq",
        "version": "2.0.0",
        "features": {
            "bedrock": bedrock_client is not None,
            "vector_backend": VECTOR_BACKEND,
            "s3": s3_client is not None,
            "documents_indexed": vector_store.stats().get("documents_indexed", 0)
        }
    }

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    email = request.email
    password = request.password
    company_slug = request.company_slug

    enforce_rate_limit(request.email.lower(), "login")
    # Check demo accounts
    if email in DEMO_USERS and password == DEMO_USERS[email]["password"]:
        demo = DEMO_USERS[email]
        token_data = {
            "sub": f"demo_{email}",
            "email": email,
            "name": demo["name"],
            "role": demo["role"],
            "dept": demo["dept"],
            "company_id": demo["company_id"],
            "company_name": DEMO_COMPANIES.get(company_slug, {}).get("name", "Demo Company")
        }
        token = create_access_token(token_data)

        user_payload = {
            "id": token_data["sub"],
            "email": token_data["email"],
            "full_name": token_data["name"],
            "department": token_data["dept"],
            "role": token_data["role"],
            "company_name": token_data["company_name"],
        }

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_payload
        }

    raise HTTPException(status_code=401, detail="Invalid email, password, or company slug")


@app.post("/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    token_data = {
        "sub": current_user.get("sub"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "role": current_user.get("role"),
        "dept": current_user.get("dept"),
        "company_id": current_user.get("company_id"),
        "company_name": current_user.get("company_name", "Demo Company"),
    }
    new_token = create_access_token(token_data, timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES))
    return {"access_token": new_token, "token_type": "bearer"}

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.get("sub"),
        "email": current_user.get("email"),
        "full_name": current_user.get("name"),
        "department": current_user.get("dept"),
        "role": current_user.get("role"),
        "company_name": current_user.get("company_name", "Demo Company"),
    }

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process document"""

    # Check permissions
    if current_user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot upload documents")
    enforce_rate_limit(current_user.get("email", "unknown"), "upload")

    # Validate file type (Req 3.3)
    filename_lower = file.filename.lower() if file.filename else ""
    ext = os.path.splitext(filename_lower)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Read and validate file size (Req 3.2)
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size // 1024} KB). Maximum allowed size is 10 MB."
        )

    # Generate unique S3 key
    file_id = str(uuid.uuid4())
    s3_key = f"companies/{current_user.get('company_id', 'demo')}/documents/{file_id}/{file.filename}"

    # Upload to S3
    s3_url = None
    if s3_client:
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
                Metadata={
                    "company_id": current_user.get("company_id", "demo"),
                    "uploaded_by": current_user.get("email", "unknown"),
                    "department": department,
                    "original_filename": file.filename
                }
            )
            s3_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            print(f"✅ Uploaded to S3: {file.filename}")
        except Exception as e:
            print(f"⚠️ S3 upload failed: {e}")

    # Extract text based on file type (Req 3.5 — raise 422 on extraction failure)
    try:
        if ext == ".pdf":
            text = extract_text_from_pdf(content)
            if text.startswith("[PDF Extraction Error"):
                raise ValueError(text)
        elif ext in (".docx", ".doc"):
            text = extract_text_from_docx(content)
            if text.startswith("[DOCX Extraction Error"):
                raise ValueError(text)
        else:  # .txt / .md
            text = content.decode("utf-8", errors="ignore")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Text extraction failed: {exc}")

    # Split into chunks
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    chunk_texts = [c for c in chunks if len(c.strip()) > 10]

    if not chunk_texts:
        raise HTTPException(status_code=422, detail="No extractable text found in the document.")

    vector_chunks = []
    upload_timestamp = datetime.utcnow().isoformat()
    for i, txt in enumerate(chunk_texts):
        vector_chunks.append({
            "chunk_id": f"{file_id}_{i}",
            "text": txt,
            "filename": file.filename,
            "department": department,
            "company_id": current_user.get("company_id", "demo"),
            "s3_key": s3_key,
            "s3_url": s3_url,
            "file_id": file_id,
            "chunk_index": i,
            "uploaded_at": upload_timestamp,
        })

    vector_store.upsert_chunks(vector_chunks)
    document_store.extend(vector_chunks)
    log_audit_event(
        "uploaded",
        current_user,
        {"file_id": file_id, "filename": file.filename, "department": department, "chunks": len(vector_chunks)},
    )

    return {
        "message": "Document uploaded and indexed successfully",
        "filename": file.filename,
        "chunks_indexed": len(vector_chunks),
        "file_size": file_size,
        "department": department,
        "s3_url": s3_url,
        "document_id": file_id
    }

@app.post("/query", response_model=QueryResponse)
async def query_documents(
    query: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Query documents using RAG (Retrieval Augmented Generation)"""
    
    try:
        question = query.question
        enforce_rate_limit(current_user.get("email", "unknown"), "query")
        department = query.department or current_user.get("dept")
        company_id = current_user.get("company_id", "demo")
        
        print(f"🔍 Query: '{question}' | Dept: {department} | Company: {company_id}")
        
        # Determine if this is a complex multi-document query
        is_complex_query = any(keyword in question.lower() for keyword in [
            'total', 'calculate', 'sum', 'all', 'across', 'combined', 'overall',
            'compare', 'difference', 'between', 'each', 'revenue', 'profit', 'expense'
        ])
        
        top_k = 15 if is_complex_query else 5
        
        # Step 1: Retrieve relevant chunks
        relevant_chunks = search_similar_chunks(
            question,
            top_k=top_k,
            department=department if current_user.get("role") != "admin" else None
        )
        
        # Filter by company (simple check for demo)
        relevant_chunks = [
            chunk for chunk in relevant_chunks 
            if chunk.get("company_id", company_id) == company_id or company_id == "demo-company-001"
        ]
        
        print(f"📚 Found {len(relevant_chunks)} relevant chunks")
        
        # Step 2: Generate AI response
        if relevant_chunks:
            try:
                answer = query_bedrock_with_context(question, relevant_chunks)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"AI service unavailable: {str(e)}")
        else:
            answer = """I couldn't find any relevant information in the uploaded documents for your question.

This could be because:
• No documents have been uploaded yet
• The question doesn't match the content of uploaded documents
• The relevant documents are in a different department

Please try:
• Uploading relevant documents first
• Rephrasing your question
• Checking documents in other departments"""

        # Step 3: Format response with more sources for complex queries
        max_sources = 10 if is_complex_query else 3
        sources = [
            {
                "filename": chunk["filename"],
                "department": chunk["department"],
                "s3_url": chunk.get("s3_url", ""),
                "snippet": chunk["text"][:300] + "..." if len(chunk["text"]) > 300 else chunk["text"],
                "similarity": round(chunk["similarity"], 3)
            }
            for chunk in relevant_chunks[:max_sources]
        ]

        # Audit log the query (Req 8.1)
        log_audit_event("query", current_user, {
            "question": question,
            "chunks_retrieved": len(relevant_chunks),
            "department": department,
        })

        return QueryResponse(answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/collections/info")
async def get_collection_info(current_user: dict = Depends(get_current_user)):
    """Get document collection statistics"""
    
    company_id = current_user.get("company_id", "demo")
    user_dept = current_user.get("dept", "general")
    is_admin = current_user.get("role") == "admin"
    
    # Filter documents by company and department
    filtered_docs = []
    for chunk in document_store:
        if chunk.get("company_id", "demo") == company_id or company_id == "demo-company-001":
            if is_admin or chunk["department"] == user_dept:
                filtered_docs.append(chunk)
    
    # Count by department
    dept_counts = {"hr": 0, "finance": 0, "legal": 0, "general": 0}
    unique_files = set()
    
    for chunk in filtered_docs:
        dept = chunk["department"]
        if dept in dept_counts:
            dept_counts[dept] += 1
        else:
            dept_counts["general"] += 1
        unique_files.add(chunk["filename"])
    
    return {
        "hr": dept_counts["hr"],
        "finance": dept_counts["finance"],
        "legal": dept_counts["legal"],
        "general": dept_counts["general"],
        "total_files": len(unique_files),
        "total_chunks": len(filtered_docs),
        "recent_uploads": list(unique_files)[:5]
    }

@app.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all documents for the current user's company"""
    
    company_id = current_user.get("company_id", "demo")
    user_dept = current_user.get("dept", "general")
    is_admin = current_user.get("role") == "admin"
    
    # Get unique documents from document_store
    docs_map = {}
    for chunk in document_store:
        if chunk.get("company_id", "demo") == company_id or company_id == "demo-company-001":
            # Filter by department unless admin
            if not is_admin and chunk["department"] != user_dept:
                continue
                
            file_id = chunk.get("file_id")
            if file_id not in docs_map:
                docs_map[file_id] = {
                    "id": file_id,
                    "filename": chunk["filename"],
                    "department": chunk["department"],
                    "s3_url": chunk.get("s3_url", ""),
                    "chunks": 0,
                    "uploaded_at": chunk.get("uploaded_at", datetime.utcnow().isoformat()),
                    "status": "active"
                }
            docs_map[file_id]["chunks"] += 1
    
    return {"documents": list(docs_map.values())}

@app.get("/admin/stats")
async def admin_stats(current_user: dict = Depends(get_current_user)):
    """Admin dashboard: users, document counts, usage stats"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    company_id = current_user.get("company_id", "demo")

    # Document stats
    docs_map: Dict[str, Any] = {}
    dept_counts: Dict[str, int] = {}
    for chunk in document_store:
        if chunk.get("company_id", "demo") != company_id and company_id != "demo-company-001":
            continue
        fid = chunk.get("file_id")
        if fid and fid not in docs_map:
            docs_map[fid] = {
                "id": fid,
                "filename": chunk["filename"],
                "department": chunk["department"],
                "uploaded_at": chunk.get("uploaded_at", ""),
            }
        dept = chunk.get("department", "general")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    # User list from demo accounts
    users = [
        {
            "email": email,
            "name": info["name"],
            "role": info["role"],
            "department": info["dept"],
        }
        for email, info in DEMO_USERS.items()
    ]

    vs_stats = vector_store.stats()

    return {
        "users": users,
        "total_users": len(users),
        "total_documents": len(docs_map),
        "total_chunks": vs_stats.get("total_chunks", 0),
        "documents_by_department": dept_counts,
        "recent_documents": sorted(
            list(docs_map.values()),
            key=lambda d: d.get("uploaded_at", ""),
            reverse=True,
        )[:10],
    }



@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document and its chunks (admin only — Req 5.2/5.3)"""

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete documents")

    removed_count = vector_store.delete_document(document_id)
    document_store[:] = [chunk for chunk in document_store if chunk.get("file_id") != document_id]
    log_audit_event("deleted", current_user, {"document_id": document_id, "removed_chunks": removed_count})

    return {"message": "Document deleted successfully", "removed_chunks": removed_count}

# ========== STARTUP ==========
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting DocIQ Production RAG Backend...")
    print(f"📦 S3 Bucket: {BUCKET_NAME}")
    print(f"🤖 Bedrock Model: {BEDROCK_MODEL}")
    print(f"🧠 Vector Engine: {VECTOR_BACKEND}")
    print(f"🔐 JWT Authentication: Enabled")
    print(f"🏢 Multi-tenant: Enabled")
    print(f"🌐 API: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
