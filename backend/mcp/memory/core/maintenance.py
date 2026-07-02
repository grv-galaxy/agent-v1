"""
maintenance.py
--------------
Periodic relation maintenance and alias-clustering job (ltm_doc.md §13).
Finds distinct relation terms with highly similar semantic embeddings and 
collapses/merges them under a single canonical name.
"""

from __future__ import annotations

import numpy as np
from . import storage
from . import vector_store

def maintain_relation_aliases(
    conn,
    embed_fn,
    similarity_threshold: float = 0.85
) -> int:
    """
    Scans all active distinct relations in the database, clusters them by 
    embedding similarity, and collapses duplicates into a canonical form.
    Returns the total number of rows updated.
    """
    cursor = conn.cursor()
    
    # 1. Fetch all distinct relations currently active in the triples store
    cursor.execute("SELECT DISTINCT relation FROM triples WHERE status = 'active'")
    relations = [row[0] for row in cursor.fetchall() if row[0]]
    
    if len(relations) < 2:
        return 0  # Not enough relations to cluster or merge

    # 2. Embed each unique relation name to evaluate similarity matrix
    rel_embeddings = embed_fn(relations)
    if hasattr(rel_embeddings, "ndim") and rel_embeddings.ndim == 1:
        rel_embeddings = np.expand_dims(rel_embeddings, axis=0)
        
    # Normalize vectors for accurate cosine similarity matrix product
    norms = np.linalg.norm(rel_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-9
    normed_embeddings = rel_embeddings / norms

    # Compute a full similarity grid: shape (len(relations), len(relations))
    sim_matrix = np.dot(normed_embeddings, normed_embeddings.T)

    merges_to_apply: dict[str, str] = {}  # source_relation -> canonical_target
    visited = set()

    # 3. Identify clusters passing the threshold
    for i in range(len(relations)):
        if i in visited:
            continue
            
        canonical = relations[i]
        cluster_indices = []
        
        for j in range(i + 1, len(relations)):
            if j not in visited and sim_matrix[i, j] >= similarity_threshold:
                cluster_indices.append(j)
                
        # If matches are found, the lexicographically first name is picked as canonical
        if cluster_indices:
            visited.add(i)
            all_cluster_names = [relations[idx] for idx in cluster_indices] + [canonical]
            all_cluster_names.sort()  # Deterministic sorting
            target_canonical = all_cluster_names[0]
            
            for idx in cluster_indices:
                visited.add(idx)
                if relations[idx] != target_canonical:
                    merges_to_apply[relations[idx]] = target_canonical
            if canonical != target_canonical:
                merges_to_apply[canonical] = target_canonical

    if not merges_to_apply:
        return 0

    # 4. Perform structural updates in a single transactional bulk step
    total_updated = 0
    with storage.transaction(conn):
        for source, target in merges_to_apply.items():
            cursor.execute(
                "UPDATE triples SET relation = ? WHERE relation = ? AND status = 'active'",
                (target, source)
            )
            total_updated += cursor.rowcount

    return total_updated