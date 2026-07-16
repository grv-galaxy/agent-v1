import re
import os
import json
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# Load NLI Model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
NLI_MODEL_DIR = os.path.join(BASE_DIR, "..", "..", "memory", "nli-deberta-v3-small")

nli_session = None
nli_tokenizer = None
entailment_idx = 1 # Fallback default

def init_nli():
    global nli_session, nli_tokenizer, entailment_idx
    if nli_session is not None:
        return
        
    try:
        model_path = os.path.join(NLI_MODEL_DIR, "onnx", "model_quantized.onnx")
        if not os.path.exists(model_path):
            model_path = os.path.join(NLI_MODEL_DIR, "onnx", "model.onnx")
        if not os.path.exists(model_path):
            model_path = os.path.join(NLI_MODEL_DIR, "model_quantized.onnx")
        if not os.path.exists(model_path):
            model_path = os.path.join(NLI_MODEL_DIR, "model.onnx")
            
        nli_session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        nli_tokenizer = Tokenizer.from_file(os.path.join(NLI_MODEL_DIR, "tokenizer.json"))
        nli_tokenizer.enable_truncation(max_length=512)
        nli_tokenizer.enable_padding(direction='right', pad_id=0, pad_type_id=0, pad_token='[PAD]')
        
        # Determine entailment index from config
        config_path = os.path.join(NLI_MODEL_DIR, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                for k, v in config.get("id2label", {}).items():
                    if "entail" in v.lower():
                        entailment_idx = int(k)
                        break
    except Exception as e:
        print(f"Failed to load NLI model: {e}")

def check_entailment(claim: str, snippet: str) -> bool:
    """Checks if snippet entails claim using NLI ONNX model."""
    if not claim.strip() or not snippet.strip():
        return False
        
    init_nli()
    if not nli_session or not nli_tokenizer:
        return False
        
    # NLI pairs are usually (premise, hypothesis). So (snippet, claim).
    encoded = nli_tokenizer.encode(snippet, claim)
    
    input_ids = np.array([encoded.ids], dtype=np.int64)
    attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
    
    inputs = {
        'input_ids': input_ids,
        'attention_mask': attention_mask
    }
    
    expected_inputs = [i.name for i in nli_session.get_inputs()]
    if 'token_type_ids' in expected_inputs:
        inputs['token_type_ids'] = np.array([encoded.type_ids], dtype=np.int64)
        
    try:
        outputs = nli_session.run(None, inputs)
        logits = outputs[0][0] # shape (3,)
        
        # If the highest probability class is entailment, return True
        return bool(np.argmax(logits) == entailment_idx)
    except Exception as e:
        print(f"NLI inference error: {e}")
        return False

def verify_citations(synthesized_text: str, top_results: list[dict]) -> list[dict]:
    """
    Parses a synthesized answer for inline citations (e.g. `[1]`), extracts the 
    preceding sentence/claim, and verifies it against the corresponding result snippet
    using an NLI model.
    """
    verifications = []
    
    segments = re.finditer(r'(.*?)(?:\[(\d+)\])', synthesized_text, re.DOTALL)
    
    for match in segments:
        claim_text = match.group(1).strip()
        sentences = re.split(r'(?<!\b\d)[.?!]\s+', claim_text)
        last_sentence = sentences[-1].strip() if sentences else claim_text
        
        # If the last sentence is a fragment (e.g., less than 5 words), 
        # the NLI model will struggle. Use the full claim block instead.
        if len(last_sentence.split()) < 5:
            last_sentence = claim_text
        
        try:
            cit_num = int(match.group(2))
            
            if 1 <= cit_num <= len(top_results):
                snippet = top_results[cit_num - 1].get('content', '')
                passed = check_entailment(last_sentence, snippet)
            else:
                passed = False
                
            verifications.append({
                "citation_number": cit_num,
                "passed": passed
            })
            
        except ValueError:
            continue
            
    return verifications
