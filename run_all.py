import subprocess
import sys
import os
import time

def run_project():
    root_dir = os.getcwd()
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    mcp_memory_dir = os.path.join(root_dir, "backend", "mcp", "memory")

    print("🚀 Starting project development environment...")

    processes = []  # list of (name, Popen) in START order

    # On Windows, give each child its own process group so we can
    # reliably kill it (and any children it spawns) as a whole tree.
    popen_kwargs = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        # 1. MCP Memory Server first — backend depends on it being up
        print("🧠 Starting MCP Memory Server (uv run server.py)...")
        mcp_process = subprocess.Popen(
            ["uv", "run", "server.py"],
            cwd=mcp_memory_dir,
            **popen_kwargs
        )
        processes.append(("MCP Memory Server", mcp_process))
        time.sleep(2)  # let it bind its SSE port before backend connects

        # 2. Backend
        print("📦 Starting Backend (uv run main.py)...")
        backend_process = subprocess.Popen(
            ["uv", "run", "main.py"],
            cwd=backend_dir,
            **popen_kwargs
        )
        processes.append(("Backend", backend_process))
        time.sleep(2)

        # 3. Frontend
        print("🎨 Starting Frontend (npm run dev:desktop)...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev:desktop"],
            cwd=frontend_dir,
            shell=True,
            **popen_kwargs
        )
        processes.append(("Frontend", frontend_process))

        print("\n✅ All services launched, each in its own process. Press Ctrl+C to stop everything.\n")

        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"\n⚠️ {name} exited on its own (code {ret}). Shutting everything down...")
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping all processes...")
    except FileNotFoundError as e:
        print(f"\n❌ Error: Could not find required environment. {e}")
        print("Ensure 'uv' and 'npm' are installed and your directory structure is correct.")
    finally:
        shutdown_all(processes)
        sys.exit(0)


def shutdown_all(processes: list[tuple[str, subprocess.Popen]]) -> None:
    """
    Shuts everything down in REVERSE start order (Frontend -> Backend -> MCP),
    so the Backend's own shutdown hook (final memory sync) gets a chance to
    run and reach the MCP server before the MCP server itself goes down.
    """
    for name, proc in reversed(processes):
        if proc.poll() is not None:
            continue  # already exited
        print(f"   → Stopping {name}...")
        _kill_process_tree(name, proc)

    # Give backend's shutdown hook (async sync call) a moment to actually
    # complete before we potentially kill MCP's process below.
    time.sleep(3)

    for name, proc in reversed(processes):
        if proc.poll() is None:
            print(f"   → Force killing remaining tree: {name}...")
            _kill_process_tree(name, proc, force=True)


def _kill_process_tree(name: str, proc: subprocess.Popen, force: bool = False) -> None:
    """
    Kills a process AND any children it spawned (uvicorn reloader ->
    server process, npm -> vite/electron, etc). Plain proc.terminate()
    only kills the direct child, leaving orphans behind on Windows.
    """
    try:
        if sys.platform == "win32":
            flag = "/F" if force else ""
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T"] + ([flag] if flag else []),
                capture_output=True
            )
        else:
            proc.terminate()
            if force:
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
    except Exception as e:
        print(f"     (cleanup warning for {name}: {e})")


if __name__ == "__main__":
    run_project()