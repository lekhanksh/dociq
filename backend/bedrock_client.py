import boto3
import json
from typing import Dict, Any
from config import get_config

def get_bedrock_client():
    """Get Bedrock runtime client."""
    config = get_config()
    return boto3.client("bedrock-runtime", region_name=config["aws_region"])

def generate_response(context: str, question: str) -> str:
    """Generate response using Claude 3.5 Sonnet via Bedrock."""
    client = get_bedrock_client()
    config = get_config()
    
    prompt = f"""You are a helpful assistant that answers questions based on the provided context. 
Use only the information from the context to answer the question. If the context doesn't contain 
the answer, say "I don't have enough information to answer this question based on the provided documents."

Context:
{context}

Question: {question}

Provide a clear and concise answer:"""

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = client.invoke_model(
            modelId=config["bedrock_model_id"],
            contentType="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
    
    except Exception as e:
        raise Exception(f"Error generating response: {str(e)}")
