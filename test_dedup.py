import numpy as np
import sys
import os

sys.path.append(os.path.abspath('backend'))

from mcp.memory.core.deduplicator import dedup_batch, CandidateTriple
from mcp.memory.core.vector_store import EmbeddingCache
from mcp.memory.core import deduplicator

class MockConn:
    def execute(self, *args):
        class MockCur:
            def fetchall(self): return []
        return MockCur()

class MockStorage:
    @staticmethod
    def get_by_ids(conn, ids):
        return {}

deduplicator.storage = MockStorage()

class MockCache(EmbeddingCache):
    def __init__(self):
        self.ids = []
        self._subjects = np.array([], dtype='<U200')
        self.matrix_normed = np.empty((0, 384), dtype=np.float32)

    def top_matches(self, vec, k=1, subject=None):
        return []

def mock_embed(texts):
    return np.random.rand(len(texts), 384).astype(np.float32)

cache = MockCache()
candidates = [
    CandidateTriple(subject="foo", relation="bar", object="baz"),
    CandidateTriple(subject="foo", relation="bar", object="qux"),
]
res = dedup_batch(MockConn(), cache, candidates, mock_embed)
for r in res.results:
    print(r.candidate.object, r.outcome)
