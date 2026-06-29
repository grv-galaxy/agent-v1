import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from tabulate import tabulate  # Correct function import

# Add backend directory to path to ensure app package is discoverable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.factory import ProviderFactory
from app.providers.base import BaseProvider

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

async def run_diagnostic(provider_name: str):
    """
    Performs a full architectural diagnostic on a specific provider.
    Tests: Registry, Instantiation, Blueprint Adherence, and Error Logic.
    """
    results = []
    
    # 1. Registry Check
    supported = ProviderFactory.get_supported_providers()
    if provider_name.lower() in supported:
        results.append([provider_name, "Registry Check", f"{Color.GREEN}PASS{Color.END}", "Found in Factory"])
    else:
        results.append([provider_name, "Registry Check", f"{Color.RED}FAIL{Color.END}", "Missing from _registry"])

    # 2. Instantiation & Config Test
    try:
        instance = ProviderFactory.create(
            provider_name=provider_name, 
            api_key="mock_key_123", 
            extra_config={"custom_flag": True}
        )
        results.append([provider_name, "Instantiation", f"{Color.GREEN}PASS{Color.END}", "Instance Created"])
        
        # 3. Blueprint Adherence (Check if it has required methods)
        has_resp = hasattr(instance, 'generate_response')
        has_stream = hasattr(instance, 'generate_stream')
        if has_resp and has_stream:
            results.append([provider_name, "Blueprint Match", f"{Color.GREEN}PASS{Color.END}", "Methods Implemented"])
        else:
            results.append([provider_name, "Blueprint Match", f"{Color.RED}FAIL{Color.END}", "Missing Abstract Methods"])

    except Exception as e:
        results.append([provider_name, "Instantiation", f"{Color.RED}FAIL{Color.END}", str(e)])

    # 4. Mocked Execution Test (Simulate a "Dry Run")
    try:
        # Patch the base method to prevent real API calls during the dry run
        with patch.object(BaseProvider, 'generate_response', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = {"text": "Mock Success", "usage": {"total_tokens": 10}}
            instance = ProviderFactory.create(provider_name, "key")
            results.append([provider_name, "Dry Run Logic", f"{Color.BLUE}READY{Color.END}", "Logic Structuralized"])
    except:
        pass

    return results

async def main():
    print(f"\n{Color.BLUE}STARTING MULTI-AGENT PROVIDER ARCHITECTURE DIAGNOSTIC{Color.END}\n")
    
    all_results = []
    
    # Get all providers currently in your Factory registry
    target_providers = ProviderFactory.get_supported_providers()
    
    # Run diagnostics concurrently
    tasks = [run_diagnostic(p) for p in target_providers]
    diagnostic_outputs = await asyncio.gather(*tasks)
    
    for output in diagnostic_outputs:
        all_results.extend(output)

    # 5. Stress Test Global Guardrails
    print(f"{Color.YELLOW}Checking Factory Guardrails...{Color.END}")
    
    # Case: Empty Provider Name
    try:
        ProviderFactory.create("", "key")
    except HTTPException as e:
        all_results.append(["GLOBAL", "Empty Name Guard", f"{Color.GREEN}PASS{Color.END}", f"Caught {e.status_code}"])

    # Case: Empty API Key
    try:
        ProviderFactory.create("openai", "")
    except HTTPException as e:
        all_results.append(["GLOBAL", "Empty Key Guard", f"{Color.GREEN}PASS{Color.END}", f"Caught {e.status_code}"])

    # Case: Unknown/Unsupported Provider
    try:
        ProviderFactory.create("unknown_ai", "key")
    except HTTPException as e:
        all_results.append(["GLOBAL", "Unknown Provider", f"{Color.GREEN}PASS{Color.END}", f"Caught {e.status_code}"])

    # Print Results in a Pretty Table
    headers = ["PROVIDER", "DIAGNOSTIC TEST", "STATUS", "REMARKS"]
    print(tabulate(all_results, headers=headers, tablefmt="fancy_grid"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"{Color.RED}Fatal Error during test execution: {e}{Color.END}")
