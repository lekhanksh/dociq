import fitz  # PyMuPDF
from docx import Document
from typing import List, Dict
import uuid

def parse_pdf(file_path: str) -> List[Dict]:
    """Parse PDF file and return chunks with page numbers."""
    chunks = []
    doc = fitz.open(file_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        # Simple chunking by paragraphs
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:  # Skip very short chunks
                chunks.append({
                    "text": para,
                    "page": page_num + 1
                })
    
    doc.close()
    return chunks

def parse_docx(file_path: str) -> List[Dict]:
    """Parse DOCX file and return chunks."""
    chunks = []
    doc = Document(file_path)
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if len(text) > 50:  # Skip very short chunks
            chunks.append({
                "text": text,
                "page": None  # DOCX doesn't have page numbers in the same way
            })
    
    return chunks

def parse_txt(file_path: str) -> List[Dict]:
    """Parse TXT file and return chunks."""
    chunks = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple chunking by paragraphs
    paragraphs = content.split('\n\n')
    for para in paragraphs:
        para = para.strip()
        if len(para) > 50:  # Skip very short chunks
            chunks.append({
                "text": para,
                "page": None
            })
    
    return chunks

def parse_file(file_path: str, file_type: str) -> List[Dict]:
    """Main parser function that routes to appropriate parser."""
    if file_type.lower() == 'pdf':
        return parse_pdf(file_path)
    elif file_type.lower() == 'docx':
        return parse_docx(file_path)
    elif file_type.lower() == 'txt':
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
