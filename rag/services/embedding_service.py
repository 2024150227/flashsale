from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import torch

app = Flask(__name__)

MODEL_NAME = "mxbai-embed-large"
model = None

def initialize_model():
    global model
    print(f"正在加载模型: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    if torch.cuda.is_available():
        model = model.to("cuda")
        print("模型已加载到GPU")
    else:
        print("模型已加载到CPU")
    print("嵌入模型服务初始化完成")

@app.route("/api/embeddings", methods=["POST"])
def get_embeddings():
    data = request.get_json()
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    embedding = model.encode(prompt, convert_to_numpy=True).tolist()

    return jsonify({"embedding": embedding})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "model": MODEL_NAME})

if __name__ == "__main__":
    initialize_model()
    app.run(host="0.0.0.0", port=8002)
