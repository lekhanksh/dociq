# Real RAG backend with Bedrock + Vector Search
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import json
import uuid
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import PyPDF2
import docx

app = FastAPI(title="DocIQ RAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Bedrock client
bedrock_client = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# S3 client
s3_client = boto3.client('s3', 
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'your-company-documents')
BEDROCK_MODEL = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-4-6-sonnet-20250721')

# Load sentence transformer model
print("🤖 Loading sentence transformer model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!")

# Vector storage
document_chunks = []
chunk_embeddings = []
faiss_index = None

# Demo accounts
DEMO_ACCOUNTS = {
    "sarah@dociq.com": {"password": "demo123", "name": "Sarah Chen", "role": "uploader"},
    "viewer@dociq.com": {"password": "demo123", "name": "Alex Roy", "role": "viewer"},
    "admin@dociq.com": {"password": "demo123", "name": "Priya Mehta", "role": "admin"},
}

# Query request model
class QueryRequest(BaseModel):
    question: str

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        import io
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")
        return f"PDF file (could not extract text): {len(content)} bytes"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content"""
    try:
        import io
        docx_file = io.BytesIO(content)
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"❌ DOCX extraction failed: {e}")
        return f"DOCX file (could not extract text): {len(content)} bytes"

def query_bedrock(question: str, context: str) -> str:
    """Query AWS Bedrock for intelligent response"""
    try:
        prompt = f"""You are a helpful assistant that answers questions based on the provided context. 
Use only the information from the context to answer the question. If the context doesn't contain 
the answer, say "I don't have enough information to answer this question based on the provided documents."

Context:
{context}

Question: {question}

Answer:"""

        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body['content'][0]['text'].strip()
        
    except Exception as e:
        print(f"❌ Bedrock query failed: {e}")
        return f"I apologize, but I'm having trouble connecting to the AI service. Error: {str(e)}"

def create_faiss_index():
    """Create or update FAISS index"""
    global faiss_index
    if chunk_embeddings:
        embeddings_array = np.array(chunk_embeddings).astype('float32')
        dimension = embeddings_array.shape[1]
        faiss_index = faiss.IndexFlatL2(dimension)
        faiss_index.add(embeddings_array)
        print(f"✅ Created FAISS index with {len(chunk_embeddings)} chunks")

def search_similar_chunks(query: str, top_k: int = 5) -> List[Dict]:
    """Search for similar chunks using vector similarity"""
    if not faiss_index:
        return []
    
    query_embedding = embedder.encode([query])[0].astype('float32')
    distances, indices = faiss_index.search(np.array([query_embedding]), top_k)
    
    results = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx < len(document_chunks):
            chunk = document_chunks[idx]
            results.append({
                "text": chunk["text"],
                "filename": chunk["filename"],
                "department": chunk["department"],
                "similarity": 1 - dist[0],  # Convert distance to similarity
                "s3_url": chunk.get("s3_url", "")
            })
    
    return results

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dociq", "version": "1.0.0"}

@app.post("/auth/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    company_slug: str = Form(...)
):
    if email in DEMO_ACCOUNTS and password == "demo123":
        demo = DEMO_ACCOUNTS[email]
        token = f"demo_token_{uuid.uuid4().hex}"
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "sub": f"demo_{email}",
                "name": demo["name"],
                "email": email,
                "dept": "finance",
                "role": demo["role"],
                "company_id": "demo-company",
                "company_name": "Demo Company"
            }
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    authorization: str = Form(None)
):
    try:
        # Read file
        content = await file.read()
        
        # Upload to S3
        s3_key = f"documents/{uuid.uuid4()}/{file.filename}"
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type
            )
            s3_url = f"https://{BUCKET_NAME}.s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
            print(f"✅ Uploaded {file.filename} to S3")
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            s3_url = "local_storage"
        
        # Extract text based on file type
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif file.filename.lower().endswith('.docx'):
            text = extract_text_from_docx(content)
        else:
            try:
                text = content.decode('utf-8')
            except:
                text = f"Binary file: {file.filename} ({len(content)} bytes)"
        
        # Split into chunks
        chunk_size = 500
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i+chunk_size]
            if len(chunk_text.strip()) > 50:  # Skip very short chunks
                chunks.append({
                    "text": chunk_text.strip(),
                    "filename": file.filename,
                    "department": department,
                    "s3_url": s3_url,
                    "chunk_id": str(uuid.uuid4())
                })
        
        # Generate embeddings for chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = embedder.encode(chunk_texts)
        
        # Store chunks and embeddings
        document_chunks.extend(chunks)
        chunk_embeddings.extend(embeddings)
        
        # Update FAISS index
        create_faiss_index()
        
        print(f"✅ Processed {len(chunks)} chunks from {file.filename}")
        
        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "chunks_indexed": len(chunks),
            "department": department,
            "s3_url": s3_url,
            "total_chunks": len(document_chunks)
        }
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/query")
async def query_documents(
    query: QueryRequest,
    authorization: str = None
):
    try:
        question = query.question
        print(f"🔍 Searching for: {question}")
        
        # Search for relevant chunks
        similar_chunks = search_similar_chunks(question, top_k=5)
        
        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant information in your uploaded documents. Please upload more documents or try a different question.",
                "sources": []
            }
        
        # Prepare context for Bedrock
        context = "\n\n".join([f"From {chunk['filename']}:\n{chunk['text']}" for chunk in similar_chunks[:3]])
        
        # Get intelligent response from Bedrock
        answer = query_bedrock(question, context)
        
        return {
            "answer": answer,
            "sources": [
                {
                    "filename": chunk["filename"],
                    "s3_url": chunk.get("s3_url", ""),
                    "snippet": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    "similarity": round(chunk["similarity"], 3)
                }
                for chunk in similar_chunks[:3]
            ]
        }
        
    except Exception as e:
        print(f"❌ Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/collections/info")
async def get_collection_info():
    try:
        # Count documents by department
        dept_counts = {"hr": 0, "finance": 0, "legal": 0, "general": 0}
        unique_docs = set()
        
        for chunk in document_chunks:
            dept = chunk["department"]
            if dept in dept_counts:
                dept_counts[dept] += 1
            else:
                dept_counts["general"] += 1
            unique_docs.add(chunk["filename"])
        
        return dept_counts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting DocIQ RAG Backend...")
    print(f"📦 S3 Bucket: {BUCKET_NAME}")
    print(f"🤖 AI Model: {BEDROCK_MODEL}")
    print(f"🧠 Vector Index: FAISS")
    print(f"🌐 Backend: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
