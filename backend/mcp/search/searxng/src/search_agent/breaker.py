import time
from enum import Enum
from typing import Dict, List, Tuple
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"       # Healthy
    OPEN = "open"           # Failing, excluded
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, time_window_sec: float = 600.0):
        self.failure_threshold = failure_threshold
        self.time_window_sec = time_window_sec
        
        # (engine, category) -> list of failure timestamps
        self.failures: Dict[Tuple[str, str], List[float]] = {}
        
        # (engine, category) -> CircuitState
        self.states: Dict[Tuple[str, str], CircuitState] = {}
        
    def _clean_old_failures(self, engine: str, category: str, now: float):
        """Remove failure timestamps outside the rolling window."""
        key = (engine, category)
        if key in self.failures:
            self.failures[key] = [
                t for t in self.failures[key]
                if now - t <= self.time_window_sec
            ]

    def record_failure(self, engine: str, category: str):
        """Records a failure and trips the circuit if threshold is reached."""
        now = time.time()
        key = (engine, category)
        
        if key not in self.failures:
            self.failures[key] = []
        
        self.failures[key].append(now)
        self._clean_old_failures(engine, category, now)
        
        current_state = self.states.get(key, CircuitState.CLOSED)
        
        # If HALF_OPEN and we fail, trip back to OPEN immediately
        if current_state == CircuitState.HALF_OPEN:
            self.states[key] = CircuitState.OPEN
            print(f"[circuit-breaker] {engine}:{category} failed probe, tripping OPEN")
        # If CLOSED and we hit threshold, trip to OPEN
        elif current_state == CircuitState.CLOSED and len(self.failures[key]) >= self.failure_threshold:
            self.states[key] = CircuitState.OPEN
            print(f"[circuit-breaker] {engine}:{category} hit failure threshold, tripping OPEN")

    def record_success(self, engine: str, category: str):
        """Records a success, resetting failures and recovering if HALF_OPEN."""
        key = (engine, category)
        
        if key in self.failures:
            self.failures[key] = []
            
        current_state = self.states.get(key, CircuitState.CLOSED)
        if current_state == CircuitState.HALF_OPEN:
            self.states[key] = CircuitState.CLOSED
            print(f"[circuit-breaker] {engine}:{category} recovered, state is CLOSED")
        elif current_state == CircuitState.OPEN:
            # Should not technically happen unless forced, but if it does, close it
            self.states[key] = CircuitState.CLOSED

    def get_eligible_engines(self, all_engines: List[str], category: str) -> List[str]:
        """Returns engines that are not OPEN for the given category."""
        eligible = []
        for engine in all_engines:
            state = self.states.get((engine, category), CircuitState.CLOSED)
            if state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                eligible.append(engine)
        return eligible

    def mark_half_open(self, engine: str, category: str):
        """Used by the background worker to allow testing an OPEN engine."""
        key = (engine, category)
        if self.states.get(key) == CircuitState.OPEN:
            self.states[key] = CircuitState.HALF_OPEN
            
    def get_open_engines(self) -> List[Tuple[str, str]]:
        """Returns all (engine, category) tuples currently OPEN."""
        return [key for key, state in self.states.items() if state == CircuitState.OPEN]

# Global instance for the orchestrator to use
breaker = CircuitBreaker()
