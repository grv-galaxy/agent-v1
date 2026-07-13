import pytest
import time
from src.search_agent.breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_transitions():
    breaker = CircuitBreaker(failure_threshold=3, time_window_sec=600)
    engine = "duckduckgo"
    category = "news"
    all_engines = ["duckduckgo", "brave", "startpage"]
    
    # Initially healthy
    assert engine in breaker.get_eligible_engines(all_engines, category)
    
    # 1 failure
    breaker.record_failure(engine, category)
    assert engine in breaker.get_eligible_engines(all_engines, category)
    
    # 2 failures
    breaker.record_failure(engine, category)
    assert engine in breaker.get_eligible_engines(all_engines, category)
    
    # 3 failures -> trips to OPEN
    breaker.record_failure(engine, category)
    assert engine not in breaker.get_eligible_engines(all_engines, category)
    assert breaker.states[(engine, category)] == CircuitState.OPEN
    
    # Mark half-open (simulating the background task probe)
    breaker.mark_half_open(engine, category)
    assert engine in breaker.get_eligible_engines(all_engines, category)
    assert breaker.states[(engine, category)] == CircuitState.HALF_OPEN
    
    # Failure while HALF_OPEN trips immediately back to OPEN
    breaker.record_failure(engine, category)
    assert engine not in breaker.get_eligible_engines(all_engines, category)
    assert breaker.states[(engine, category)] == CircuitState.OPEN
    
    # Mark half-open again
    breaker.mark_half_open(engine, category)
    
    # Success while HALF_OPEN recovers fully to CLOSED
    breaker.record_success(engine, category)
    assert engine in breaker.get_eligible_engines(all_engines, category)
    assert breaker.states[(engine, category)] == CircuitState.CLOSED
    
def test_circuit_breaker_time_window():
    breaker = CircuitBreaker(failure_threshold=2, time_window_sec=0.1)
    
    # 1 failure
    breaker.record_failure("brave", "general")
    assert breaker.states.get(("brave", "general"), CircuitState.CLOSED) == CircuitState.CLOSED
    
    # Wait for time window to expire
    time.sleep(0.15)
    
    # 2nd failure (but the 1st one expired, so len(failures) should be 1)
    breaker.record_failure("brave", "general")
    assert breaker.states.get(("brave", "general"), CircuitState.CLOSED) == CircuitState.CLOSED
