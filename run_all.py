import subprocess
import sys
import os
import time

def run_project():
    # Define paths
    root_dir = os.getcwd()
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("🚀 Starting project development environment...")

    try:
        # 1. Start the Backend
        # Using 'uv run' to execute main.py inside the backend directory
        print("📦 Starting Backend (uv run main.py)...")
        backend_process = subprocess.Popen(
            ["uv", "run", "main.py"],
            cwd=backend_dir
        )

        # Small delay to ensure backend initializes
        time.sleep(2)

        # 2. Start the Frontend
        # Executing 'npm run dev:desktop' inside the frontend directory
        print("🎨 Starting Frontend (npm run dev:desktop)...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev:desktop"],
            cwd=frontend_dir,
            shell=True # Required on some systems to resolve npm/npx
        )

        # Keep the script alive while processes are running
        backend_process.wait()
        frontend_process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Stopping all processes...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"\n❌ Error: Could not find required environment. {e}")
        print("Ensure 'uv' is installed and your directory structure is correct.")

if __name__ == "__main__":
    run_project()