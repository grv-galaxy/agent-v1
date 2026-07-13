import re

def get_ngrams(text: str, n: int = 2) -> set:
    """Helper function to convert text into a set of word n-grams for overlap comparison."""
    # Strip punctuation and lower
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < n:
        return set(words)
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))

def check_overlap(claim: str, snippet: str, threshold: float = 0.15) -> bool:
    """
    Checks if a claim is reasonably grounded in a snippet using n-gram overlap.
    For v1, we use a simple and fast string overlap rather than an ML entailment model.
    """
    if not claim.strip() or not snippet.strip():
        return False
        
    claim_ngrams = get_ngrams(claim, n=2)
    snippet_ngrams = get_ngrams(snippet, n=2)
    
    if not claim_ngrams:
        return True # If the claim is too short to form an n-gram, default pass
        
    # How many of the claim's n-grams are found in the snippet?
    overlap = len(claim_ngrams.intersection(snippet_ngrams))
    ratio = overlap / len(claim_ngrams)
    
    return ratio >= threshold

def verify_citations(synthesized_text: str, top_results: list[dict]) -> list[dict]:
    """
    Parses a synthesized answer for inline citations (e.g. `[1]`), extracts the 
    preceding sentence/claim, and verifies it against the corresponding result snippet.
    """
    verifications = []
    
    # Regex to find citations and the text immediately preceding them.
    # Matches a sequence of words/punctuation ending with [number].
    # Split the text by citations first to isolate the claims.
    
    # Split text into segments ending with [num]
    segments = re.finditer(r'(.*?)(?:\[(\d+)\])', synthesized_text, re.DOTALL)
    
    for match in segments:
        claim_text = match.group(1).strip()
        
        # We only want the sentence immediately preceding the citation.
        # Split by typical sentence boundaries (. ? !)
        sentences = re.split(r'[.?!]\s+', claim_text)
        last_sentence = sentences[-1] if sentences else claim_text
        
        try:
            cit_num = int(match.group(2))
            
            # 1-based index to 0-based index
            if 1 <= cit_num <= len(top_results):
                snippet = top_results[cit_num - 1].get('content', '')
                passed = check_overlap(last_sentence, snippet)
            else:
                passed = False # Citation points to a non-existent source
                
            verifications.append({
                "citation_number": cit_num,
                "passed": passed
            })
            
        except ValueError:
            continue
            
    return verifications
