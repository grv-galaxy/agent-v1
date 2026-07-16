from huggingface_hub import snapshot_download
import os

target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "memory", "nli-deberta-v3-small"))
os.makedirs(target_dir, exist_ok=True)

print(f"Downloading Xenova/nli-deberta-v3-small to {target_dir}...")
snapshot_download(
    repo_id="Xenova/nli-deberta-v3-small", 
    local_dir=target_dir,
    allow_patterns=["*onnx/model_quantized.onnx", "*onnx/model.onnx", "*.json", "*.txt"]
)
print("Done!")
