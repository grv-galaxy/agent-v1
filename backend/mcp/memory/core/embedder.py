import os
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

class BGEONNXEmbedder:
    def __init__(self):
        # Locate the local model directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Up one level from core/ to memory/, then down into model/
        local_model_dir = os.path.abspath(os.path.join(current_dir, "..", "model"))
        
        # Point specifically to your downloaded quantized file structure
        model_path = os.path.join(local_model_dir, "model_quantized.onnx")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Quantized ONNX model file not found at: {model_path}\n"
                f"Please verify your folder name matches 'model' and contains 'model_quantized.onnx'"
            )

        print(f"Initializing local Quantized ONNX embedding session from: {local_model_dir}")
        self.tokenizer = AutoTokenizer.from_pretrained(local_model_dir)
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        # Tokenize the input texts locally
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np"
        )

        # Build execution input mapping for ONNX Runtime
        onnx_inputs = {
            "input_ids": encoded["input_ids"].astype(np.int64),
            "attention_mask": encoded["attention_mask"].astype(np.int64)
        }
        if "token_type_ids" in encoded:
            onnx_inputs["token_type_ids"] = encoded["token_type_ids"].astype(np.int64)

        # Run inference using the local quantized session
        outputs = self.session.run(None, onnx_inputs)
        
        # BAAI BGE models use CLS pooling (taking the first token representation index 0)
        last_hidden_state = outputs[0]
        embeddings = last_hidden_state[:, 0, :]

        # L2-Normalize for perfect cosine similarity matching
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-12, norms)  # Prevent division by zero
        return embeddings / norms

# Singleton instance placeholder for simple access
_instance = None

def encode_batch(texts: list[str]) -> np.ndarray:
    """Encodes a batch of sentences into normalized 384-dimensional embeddings."""
    global _instance
    if _instance is None:
        _instance = BGEONNXEmbedder()
    return _instance.encode_batch(texts)