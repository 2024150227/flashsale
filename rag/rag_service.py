from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import chromadb
import re
import os
import json
from typing import List, AsyncGenerator

app = FastAPI(title="RAG客服系统")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# 优化：设置更合理的超时时间
EMBEDDING_TIMEOUT = 15
GENERATION_TIMEOUT = 60

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    relevant_docs: List[str]

class Document:
    def __init__(self, content: str, metadata: dict = None):
        self.content = content
        self.metadata = metadata or {}

def parse_knowledge_base(file_path: str = "knowledge_base.md") -> List[Document]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"知识库文件 {file_path} 未找到")
        return []

    documents = []
    sections = re.split(r'### Q\d+:', content)

    for i, section in enumerate(sections[1:], 1):
        lines = section.strip().split('\n', 1)
        if len(lines) == 2:
            question = lines[0].strip()
            answer = lines[1].strip()
            doc_content = f"问题：{question}\n答案：{answer}"
            documents.append(Document(doc_content, {"id": i}))

    return documents

def get_embedding(text: str) -> List[float]:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=EMBEDDING_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except requests.exceptions.Timeout:
        print("Ollama嵌入调用超时")
        return []
    except Exception as e:
        print(f"Ollama嵌入调用失败: {e}")
        return []

def generate_response_stream(prompt: str) -> AsyncGenerator[str, None]:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": True},
            timeout=GENERATION_TIMEOUT,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if 'response' in data:
                        yield data['response']
                    if data.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue
    except requests.exceptions.Timeout:
        yield "\n\n抱歉，请求超时，请稍后再试。"
    except Exception as e:
        print(f"Ollama流式生成失败: {e}")
        yield "\n\n抱歉，我现在无法回答您的问题，请稍后再试。"

def generate_response(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=GENERATION_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.Timeout:
        return "抱歉，请求超时，请稍后再试。"
    except Exception as e:
        print(f"Ollama生成调用失败: {e}")
        return "抱歉，我现在无法回答您的问题，请稍后再试。"

def initialize_vector_store():
    client = chromadb.PersistentClient(path="./chroma_db")

    collection_name = "knowledge_base"

    try:
        collection = client.get_collection(name=collection_name)
        print(f"找到已存在的集合: {collection_name}")
    except:
        print("创建新的向量集合")
        collection = client.create_collection(name=collection_name)

        documents = parse_knowledge_base()
        print(f"解析到 {len(documents)} 条知识库文档")

        for doc in documents:
            embedding = get_embedding(doc.content)
            if embedding:
                collection.add(
                    embeddings=[embedding],
                    documents=[doc.content],
                    metadatas=[doc.metadata],
                    ids=[str(doc.metadata["id"])]
                )

        print("向量数据库初始化完成")

    return collection

vector_collection = None

@app.on_event("startup")
async def startup_event():
    global vector_collection
    print(f"正在初始化RAG服务...")
    vector_collection = initialize_vector_store()
    print("RAG服务启动完成")

@app.get("/")
async def root():
    return {"message": "RAG客服系统运行中", "status": "ok"}

@app.post("/chat", response_model=QuestionResponse)
async def chat(request: QuestionRequest):
    if not vector_collection:
        raise HTTPException(status_code=500, detail="向量数据库未初始化")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    query_embedding = get_embedding(question)
    if not query_embedding:
        raise HTTPException(status_code=500, detail="嵌入模型调用失败")

    results = vector_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    relevant_docs = results["documents"][0] if results["documents"] else []

    context = "\n\n".join([f"参考信息{i+1}：{doc}" for i, doc in enumerate(relevant_docs)])

    prompt = f"""你是一个专业的客服助手。请根据以下参考信息回答用户的问题。

参考信息：
{context}

用户问题：{question}

请用简洁、友好的语气回答，如果参考信息中没有相关内容，请礼貌地告知用户。"""

    answer = generate_response(prompt)

    return QuestionResponse(
        answer=answer,
        relevant_docs=relevant_docs
    )

@app.post("/chat/stream")
async def chat_stream(request: QuestionRequest):
    if not vector_collection:
        raise HTTPException(status_code=500, detail="向量数据库未初始化")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    query_embedding = get_embedding(question)
    if not query_embedding:
        raise HTTPException(status_code=500, detail="嵌入模型调用失败")

    results = vector_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    relevant_docs = results["documents"][0] if results["documents"] else []
    context = "\n\n".join([f"参考信息{i+1}：{doc}" for i, doc in enumerate(relevant_docs)])

    prompt = f"""你是一个专业的客服助手。请根据以下参考信息回答用户的问题。

参考信息：
{context}

用户问题：{question}

请用简洁、友好的语气回答，如果参考信息中没有相关内容，请礼貌地告知用户。"""

    async def generate():
        async for chunk in generate_response_stream(prompt):
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "vector_store": "initialized" if vector_collection else "not_initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
