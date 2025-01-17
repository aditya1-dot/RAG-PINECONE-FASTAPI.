from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict, Optional
import google.generativeai as genai
from pinecone import Pinecone
from PyPDF2 import PdfReader
import numpy as np
import os
from pydantic import BaseModel
import uuid
from transformers import AutoTokenizer, AutoModel
import torch
import asyncio
from datetime import datetime
import io
from fastapi import Form
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'pdf-embeddings')
MODEL_NAME = os.getenv('HF_MODEL_NAME', 'sentence-transformers/all-mpnet-base-v2')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
VECTOR_DIMENSION = int(os.getenv('VECTOR_DIMENSION', '768'))
TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '3'))

# Validate required environment variables
if not all([PINECONE_API_KEY, PINECONE_ENVIRONMENT, GEMINI_API_KEY]):
    raise ValueError("Missing required environment variables. Please check .env file.")

app = FastAPI()

# Initialize Hugging Face model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# Models for request/response
class QueryRequest(BaseModel):
    query: str
    email: str

class BatchUploadResponse(BaseModel):
    successful_files: List[str]
    failed_files: List[Dict[str, str]]
    total_chunks: int
    namespace: str

class NamespaceStats(BaseModel):
    total_vectors: int
    namespace: str
    dimension: int

def get_huggingface_embedding(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Hugging Face model"""
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs)
        attention_mask = inputs['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        
    return embeddings.numpy().tolist()

def extract_text_from_pdf(pdf_file) -> str:
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def create_chunks(text: str) -> list:
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1
        
        if current_size >= CHUNK_SIZE:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def get_or_create_index():
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=VECTOR_DIMENSION,
            metric="cosine"
        )
    return pc.Index(PINECONE_INDEX_NAME)

async def process_single_pdf(file: UploadFile, namespace: str, index) -> Dict:
    try:
        contents = await file.read()
        pdf_text = extract_text_from_pdf(io.BytesIO(contents))
        chunks = create_chunks(pdf_text)
        embeddings = get_huggingface_embedding(chunks)
        
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{uuid.uuid4()}"
            metadata = {
                "text": chunk,
                "chunk_index": i,
                "source": file.filename,
                "timestamp": datetime.now().isoformat()
            }
            vectors.append((vector_id, embedding, metadata))
        
        # Update to new upsert syntax
        index.upsert(vectors=[(id, vec, meta) for id, vec, meta in vectors], namespace=namespace)
        
        return {
            "success": True,
            "chunks": len(chunks),
            "filename": file.filename
        }
    except Exception as e:
        return {
            "success": False,
            "filename": file.filename,
            "error": str(e)
        }

@app.post("/batch-ingest")
async def batch_ingest_pdfs(
    files: List[UploadFile] = File(...),
    email: str = Form(...),  # Change this line
    background_tasks: BackgroundTasks = None
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    namespace = email.replace('@', '-').replace('.', '-')
    index = get_or_create_index()
    
    results = await asyncio.gather(*[
        process_single_pdf(file, namespace, index)
        for file in files
    ])
    
    successful_files = []
    failed_files = []
    total_chunks = 0
    
    for result in results:
        if result["success"]:
            successful_files.append(result["filename"])
            total_chunks += result["chunks"]
        else:
            failed_files.append({
                "filename": result["filename"],
                "error": result["error"]
            })
    
    return BatchUploadResponse(
        successful_files=successful_files,
        failed_files=failed_files,
        total_chunks=total_chunks,
        namespace=namespace
    )

@app.post("/query")
async def query_documents(query_request: QueryRequest):
    namespace = query_request.email.replace('@', '-').replace('.', '-')
    
    try:
        index = get_or_create_index()
        query_embedding = get_huggingface_embedding([query_request.query])[0]
        
        # Updated query syntax
        search_results = index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=TOP_K_RESULTS,
            include_metadata=True
        )
        
        context = "\n".join([match.metadata["text"] for match in search_results.matches])
        
        prompt = f"""
        Based on the following context, please answer the question.
        
        Context:
        {context}
        
        Question:
        {query_request.query}
        
        Please try to help the user if you don't get relevant context than provide the most relevant answer according to context and query.
        """
        
        response = gemini_model.generate_content(prompt)
        
        return {
            "answer": response.text,
            "context": context,
            "matches": len(search_results.matches)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/namespace/{email}/stats")
async def get_namespace_stats(email: str) -> NamespaceStats:
    namespace = email.replace('@', '-').replace('.', '-')
    index = get_or_create_index()
    
    stats = index.describe_index_stats()
    namespace_stats = stats.namespaces.get(namespace, {})
    
    return NamespaceStats(
        total_vectors=namespace_stats.get('vector_count', 0),
        namespace=namespace,
        dimension=VECTOR_DIMENSION
    )

@app.delete("/namespace/{email}")
async def delete_namespace(email: str):
    try:
        namespace = email.replace('@', '-').replace('.', '-')
        index = get_or_create_index()
        
        # Updated delete syntax
        index.delete(filter={}, namespace=namespace)
        
        return {"message": f"Successfully deleted namespace {namespace}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))