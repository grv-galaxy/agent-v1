"""
creation_of_database.py
-----------------------
Utility script to manually initialize or verify the complete LTM SQLite database.
Combines metadata schema from storage.py and vector schema from vector_store.py.

Target Destination: agent-v1/backend/data/ltm_memory.db
"""

import sys
from pathlib import Path

# Import both storage sub-modules directly since they are at the same level
import storage
import vector_store

# Define the target database filename
DB_FILENAME = "ltm_memory.db"

def get_target_db_path() -> Path:
    """
    Safely finds the true absolute 'backend/data' directory by scanning
    upwards for the 'backend' folder root in the script's path tree.
    """
    current_file = Path(__file__).resolve()
    
    # Search upwards through parent directories until we hit 'backend'
    backend_dir = None
    for parent in current_file.parents:
        if parent.name == "backend":
            backend_dir = parent
            break
            
    # Fallback safety if 'backend' isn't explicitly found in ancestry names
    if backend_dir is None:
        backend_dir = current_file.parent.parent.parent 

    # Explicitly target backend/data/
    target_data_dir = backend_dir / "data"
    
    # Create the directory safely if it doesn't exist yet
    target_data_dir.mkdir(parents=True, exist_ok=True)
    
    return target_data_dir / DB_FILENAME

def initialize_database():
    """
    Triggers the initialization of the SQLite database, applying table schemas,
    indexes, and loading the vector extension cleanly inside backend/data/.
    """
    db_path = get_target_db_path()
    print(f"[*] Initializing complete LTM database at: {db_path.resolve()}")

    try:
        # Step 1: Initialize metadata layer via storage.py
        # This handles the connection setup, turns on WAL mode, and builds the 'triples' schema.
        conn = storage.connect(db_path)
        print("[+] Metadata layer connected and initialized.")

        # Step 2: Initialize vector layer via vector_store.py
        # This loads sqlite-vec and attempts to set up a virtual vec0 table or fallback BLOB table.
        has_native_vec = vector_store.init_vector_table(conn)
        
        # Step 3: Verification Pass
        cursor = conn.cursor()
        
        # Check if triples table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='triples';")
        triples_exists = cursor.fetchone()
        
        # Check if embeddings table/virtual table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE name='embeddings';")
        embeddings_exists = cursor.fetchone()

        print("\n=== SYSTEM VERIFICATION ===")
        print(f"[+] Target Destination: backend/data/{db_path.name}")
        
        # Print Triples status
        if triples_exists:
            print("[+] Status: 'triples' table (Metadata) is READY.")
        else:
            print("[-] Error: 'triples' table was NOT found.")
            
        # Print Embeddings status
        if embeddings_exists:
            storage_type = "Native Virtual Table (vec0)" if has_native_vec else "Fallback Table (BLOB)"
            print(f"[+] Status: 'embeddings' table (Vectors) is READY using: {storage_type}.")
        else:
            print("[-] Error: 'embeddings' table was NOT found.")

        # Print Active Journal Mode
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()
        print(f"[+] Performance: Active Journal Mode is {dict(mode)['journal_mode'].upper()}.")
        print("===========================\n")
            
        # Clean up the connection safely
        conn.close()
        print("[*] Database connection closed safely.")

    except ImportError as e:
        print(f"[-] Error: Module import failed ({str(e)}). Ensure this script sits next to storage.py and vector_store.py.")
    except Exception as e:
        print(f"[-] Database initialization failed: {str(e)}")

if __name__ == "__main__":
    initialize_database()