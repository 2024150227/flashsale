from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__)

MODEL_NAME = "google/gemma-3-4b-it"
tokenizer = None
model = None

def initialize_model():
    global tokenizer, model
    print(f"正在加载模型: {MODEL_NAME}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )

    print("生成模型服务初始化完成")

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = data.get("prompt", "")
    model_name = data.get("model", "gemma3:4b")
    stream = data.get("stream", False)

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return jsonify({"response": response})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "model": MODEL_NAME})

if __name__ == "__main__":
    initialize_model()
    app.run(host="0.0.0.0", port=8003)
