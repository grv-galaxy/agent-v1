import os
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# Define paths relative to this file (src/search_agent/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # This gets us to searxng/
BI_ENCODER_PATH = os.path.join(BASE_DIR, "..", "..", "memory", "model")
CROSS_ENCODER_PATH = os.path.join(BASE_DIR, "..", "..", "memory", "cross-encoder-ms-marco-MiniLM-L-6-v2")

class ONNXRanker:
    def __init__(self, bi_encoder_dir: str, cross_encoder_dir: str):
        """
        Loads the bi-encoder and cross-encoder models into ONNXRuntime sessions
        and configures their respective tokenizers.
        """
        # --- Bi-Encoder Setup ---
        bi_model_path = os.path.join(bi_encoder_dir, "model_q4.onnx")
        if not os.path.exists(bi_model_path):
            bi_model_path = os.path.join(bi_encoder_dir, "model_quantized.onnx")
        
        self.bi_session = ort.InferenceSession(bi_model_path, providers=['CPUExecutionProvider'])
        self.bi_tokenizer = Tokenizer.from_file(os.path.join(bi_encoder_dir, "tokenizer.json"))
        # Truncate inputs and pad appropriately for batches
        self.bi_tokenizer.enable_truncation(max_length=256)
        self.bi_tokenizer.enable_padding(direction='right', pad_id=0, pad_type_id=0, pad_token='[PAD]')
        
        # --- Cross-Encoder Setup ---
        cross_model_path = os.path.join(cross_encoder_dir, "onnx", "model_quantized.onnx")
        if not os.path.exists(cross_model_path):
            cross_model_path = os.path.join(cross_encoder_dir, "onnx", "model.onnx")
        if not os.path.exists(cross_model_path):
            # Fallback if downloaded flat
            cross_model_path = os.path.join(cross_encoder_dir, "model_quantized.onnx")
            
        self.cross_session = ort.InferenceSession(cross_model_path, providers=['CPUExecutionProvider'])
        self.cross_tokenizer = Tokenizer.from_file(os.path.join(cross_encoder_dir, "tokenizer.json"))
        # Truncate at 512 for cross-encoder pair sequences
        self.cross_tokenizer.enable_truncation(max_length=512)
        self.cross_tokenizer.enable_padding(direction='right', pad_id=0, pad_type_id=0, pad_token='[PAD]')

    def _mean_pooling(self, token_embeddings, attention_mask):
        """Standard mean pooling over token embeddings where attention_mask is 1."""
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        return sum_embeddings / sum_mask

    def bi_encoder_rank(self, query: str, results: list[dict]) -> list[dict]:
        """
        First pass: O(N) cosine similarity ranking over all results.
        Returns the full list sorted by bi-encoder score descending.
        """
        if not results:
            return []
            
        # Combine title and content for better contextual embedding
        texts = [f"{res.get('title', '')} {res.get('content', '')}".strip() for res in results]
        
        # Batch encode query + all texts
        all_texts = [query] + texts
        encoded = self.bi_tokenizer.encode_batch(all_texts)
        
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        
        inputs = {
            'input_ids': input_ids,
            'attention_mask': attention_mask
        }
        
        expected_inputs = [i.name for i in self.bi_session.get_inputs()]
        if 'token_type_ids' in expected_inputs:
            inputs['token_type_ids'] = np.array([e.type_ids for e in encoded], dtype=np.int64)
            
        # Run ONNX inference
        outputs = self.bi_session.run(None, inputs)
        token_embeddings = outputs[0]
        
        # Mean pool to get sentence embeddings
        pooled = self._mean_pooling(token_embeddings, attention_mask)
        
        # L2 normalize
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / np.clip(norms, a_min=1e-9, a_max=None)
        
        query_emb = normalized[0]
        docs_embs = normalized[1:]
        
        # Calculate cosine similarities
        scores = np.dot(docs_embs, query_emb)
        
        # Attach scores and sort
        scored_results = []
        for res, score in zip(results, scores):
            res_copy = dict(res)
            res_copy['_bi_score'] = float(score)
            scored_results.append(res_copy)
            
        scored_results.sort(key=lambda x: x['_bi_score'], reverse=True)
        return scored_results

    def cross_encoder_rerank(self, query: str, top_results: list[dict]) -> list[dict]:
        """
        Second pass: Slow but highly accurate relevance scoring over a truncated list (usually top 8).
        Returns the list sorted by cross-encoder score descending.
        """
        if not top_results:
            return []
            
        # Truncate to top 8 max
        candidates = top_results[:8]
        
        texts = [f"{res.get('title', '')} {res.get('content', '')}".strip() for res in candidates]
        
        # tokenizers.encode_batch accepts tuples for pairs
        pairs = [(query, text) for text in texts]
        encoded = self.cross_tokenizer.encode_batch(pairs)
        
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        
        inputs = {
            'input_ids': input_ids,
            'attention_mask': attention_mask
        }
        
        expected_inputs = [i.name for i in self.cross_session.get_inputs()]
        if 'token_type_ids' in expected_inputs:
            inputs['token_type_ids'] = np.array([e.type_ids for e in encoded], dtype=np.int64)
            
        # Run ONNX inference
        outputs = self.cross_session.run(None, inputs)
        logits = outputs[0]
        
        # Cross encoder yields a single logit per pair [batch_size, 1]
        scores = logits.flatten()
        
        scored_results = []
        for res, score in zip(candidates, scores):
            res_copy = dict(res)
            res_copy['_cross_score'] = float(score)
            scored_results.append(res_copy)
            
        scored_results.sort(key=lambda x: x['_cross_score'], reverse=True)
        return scored_results

    def rank_results(self, query: str, results: list[dict], top_k: int = 3) -> list[dict]:
        """Convenience method combining both passes and yielding final top_k."""
        if not results:
            return []
            
        bi_ranked = self.bi_encoder_rank(query, results)
        cross_ranked = self.cross_encoder_rerank(query, bi_ranked)
        
        return cross_ranked[:top_k]
