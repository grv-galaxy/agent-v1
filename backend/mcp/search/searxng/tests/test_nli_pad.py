import sys
import os

sys.path.append(os.getcwd())

from src.search_agent.citations import check_entailment

claim = "The current President of India is Droupadi Murmu, who has been in office since 25 July 2022."
snippet = "Junk word " * 600 + "Droupadi Murmu (born 20 June 1958) is an Indian politician and former teacher who is serving as the 15th and current President of India since 25 July 2022."

print("Entailment with padding:", check_entailment(claim, snippet))
