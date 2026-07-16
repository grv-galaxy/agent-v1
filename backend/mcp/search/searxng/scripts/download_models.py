from huggingface_hub import snapshot_download
import os

target_dir = r"C:\Users\kumar\Documents\agent-v1\backend\mcp\memory\cross-encoder-ms-marco-MiniLM-L-6-v2"
os.makedirs(target_dir, exist_ok=True)

print("Downloading cross-encoder ONNX weights and tokenizer...")

# Xenova repos provide pre-exported ONNX weights (model.onnx, model_quantized.onnx)
# We use allow_patterns to specifically exclude PyTorch/Safetensors bins and grab ONLY the ONNX files and tokenizer configs.
snapshot_download(
    repo_id="Xenova/ms-marco-MiniLM-L-6-v2",
    local_dir=target_dir,
    allow_patterns=[
        "*.onnx",
        "tokenizer.json",
        "tokenizer_config.json",
        "config.json",
        "special_tokens_map.json",
        "vocab.txt"
    ],
    local_dir_use_symlinks=False
)

print("Download complete. Models located at:", target_dir)
