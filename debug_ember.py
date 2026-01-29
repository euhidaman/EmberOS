#!/usr/bin/env python3
"""
EmberOS Debug Script - Comprehensive system check
Run this to diagnose BitNet/Qwen server issues and daemon connectivity.
"""
import asyncio
import json
import sys
import aiohttp
import logging
import subprocess
import shutil
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Detect platform
IS_LINUX = sys.platform.startswith('linux')
IS_WINDOWS = sys.platform == 'win32'

def run_command(cmd, check=False):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if check and result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Command failed: {cmd}, error: {e}")
        return None

async def check_system_services():
    """Check if systemd services are running (Linux only)."""
    if not IS_LINUX:
        print("\n[SKIP] System service check (Windows)")
        return

    print("\n" + "="*60)
    print("CHECKING SYSTEM SERVICES")
    print("="*60)

    services = ["ember-llm", "emberd"]

    for service in services:
        print(f"\n{service}.service:")

        # Check if service exists
        status = run_command(f"systemctl --user status {service}")
        if status is None:
            print(f"  [X] Service not found or not installed")
            continue

        # Check if active
        is_active = run_command(f"systemctl --user is-active {service}")
        if is_active == "active":
            print(f"  [OK] Status: ACTIVE")
        else:
            print(f"  [X] Status: {is_active}")
            print(f"  [!] Try: systemctl --user start {service}")

        # Check if enabled
        is_enabled = run_command(f"systemctl --user is-enabled {service}")
        if is_enabled == "enabled":
            print(f"  [OK] Enabled: YES")
        else:
            print(f"  [!] Enabled: {is_enabled}")
            print(f"  [!] Try: systemctl --user enable {service}")

        # Get main PID
        pid = run_command(f"systemctl --user show -p MainPID --value {service}")
        if pid and pid != "0":
            print(f"  [OK] PID: {pid}")

async def check_ports():
    """Check which ports are listening."""
    print("\n" + "="*60)
    print("CHECKING LISTENING PORTS")
    print("="*60)

    ports = {
        "38080": "BitNet (text model)",
        "11434": "Qwen2.5-VL (vision model)"
    }

    if IS_LINUX:
        # Use ss command on Linux
        for port, name in ports.items():
            print(f"\nPort {port} ({name}):")
            result = run_command(f"ss -tlnp | grep :{port}")
            if result:
                print(f"  [OK] Listening")
                print(f"  {result}")
            else:
                print(f"  [X] NOT listening")
                print(f"  [!] Server may not be running on this port")
    elif IS_WINDOWS:
        # Use netstat on Windows
        for port, name in ports.items():
            print(f"\nPort {port} ({name}):")
            result = run_command(f"netstat -an | findstr :{port}")
            if result:
                print(f"  [OK] Listening")
                print(f"  {result}")
            else:
                print(f"  [X] NOT listening")
    else:
        print("  [!] Port check not supported on this platform")

async def check_binaries():
    """Check if required binaries are installed."""
    print("\n" + "="*60)
    print("CHECKING REQUIRED BINARIES")
    print("="*60)

    binaries = {
        "llama-server": "llama.cpp server (handles both models)",
        "python3": "Python interpreter",
    }

    for binary, description in binaries.items():
        print(f"\n{binary}:")
        path = shutil.which(binary)
        if path:
            print(f"  [OK] Found: {path}")
            # Try to get version
            if binary == "llama-server":
                version = run_command(f"{binary} --version")
                if version:
                    print(f"  Version: {version.split()[0] if version else 'unknown'}")
        else:
            print(f"  [X] NOT FOUND")
            print(f"  Description: {description}")
            if binary == "llama-server":
                print(f"  [!] Install: yay -S llama.cpp (Arch Linux)")

async def check_llm_manager_script():
    """Check the LLM manager script."""
    print("\n" + "="*60)
    print("CHECKING LLM MANAGER SCRIPT")
    print("="*60)

    script_path = Path("/usr/local/bin/ember-llm-manager")

    print(f"\nScript: {script_path}")
    if script_path.exists():
        print(f"  [OK] Exists")

        # Check if executable
        if script_path.stat().st_mode & 0o111:
            print(f"  [OK] Executable")
        else:
            print(f"  [X] Not executable")
            print(f"  [!] Run: sudo chmod +x {script_path}")

        # Show first 30 lines
        print(f"\nFirst 30 lines of script:")
        print("  " + "-"*56)
        try:
            with open(script_path, 'r') as f:
                for i, line in enumerate(f):
                    if i >= 30:
                        break
                    print(f"  {line.rstrip()}")
        except Exception as e:
            print(f"  [X] Cannot read: {e}")
        print("  " + "-"*56)
    else:
        print(f"  [X] NOT FOUND")
        print(f"  [!] Run: ./install.sh to install")

async def check_service_logs():
    """Check recent service logs (Linux only)."""
    if not IS_LINUX:
        return

    print("\n" + "="*60)
    print("CHECKING SERVICE LOGS (LAST 20 LINES)")
    print("="*60)

    services = {
        "ember-llm": "LLM Server Logs",
        "emberd": "Daemon Logs"
    }

    for service, title in services.items():
        print(f"\n{title} ({service}):")
        print("  " + "-"*56)
        logs = run_command(f"journalctl --user -u {service} -n 20 --no-pager")
        if logs:
            for line in logs.split('\n'):
                print(f"  {line}")
        else:
            print(f"  [!] No logs or service not running")
        print("  " + "-"*56)

async def check_llm_servers():
    """Check if LLM servers are responding"""
    print("\n" + "="*60)
    print("CHECKING LLM SERVERS")
    print("="*60)

    servers = [
        ("BitNet (text)", "http://127.0.0.1:38080"),
        ("Qwen2.5-VL (vision)", "http://127.0.0.1:11434"),
    ]

    async with aiohttp.ClientSession() as session:
        for name, url in servers:
            print(f"\n{name}: {url}")

            # Check health endpoint
            try:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        health = await resp.json()
                        print(f"  [OK] Health: {health}")
                    else:
                        print(f"  [X] Health check failed: {resp.status}")
                        print(f"  [!] Server is running but not healthy")
                        continue
            except aiohttp.ClientConnectorError:
                print(f"  [X] Connection refused - Server NOT running")
                print(f"  [!] Check: systemctl --user status ember-llm")
                print(f"  [!] Start: systemctl --user start ember-llm")
                continue
            except asyncio.TimeoutError:
                print(f"  [X] Connection timeout - Server not responding")
                continue
            except Exception as e:
                print(f"  [X] Health check error: {type(e).__name__}: {e}")
                continue

            # Check models endpoint
            try:
                async with session.get(f"{url}/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        models = await resp.json()
                        print(f"  [OK] Models endpoint responsive")
                        if models.get('data'):
                            print(f"       Model: {models['data'][0].get('id', 'unknown')}")
                    else:
                        print(f"  [X] Models check failed: {resp.status}")
            except Exception as e:
                print(f"  [!] Models endpoint error: {type(e).__name__}")

            # Try llama.cpp completion endpoint
            print(f"  Testing /completion endpoint...")
            try:
                payload = {
                    "prompt": "Hello, my name is",
                    "n_predict": 10,
                    "temperature": 0.1,
                    "stream": False
                }
                async with session.post(
                    f"{url}/completion",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result.get('content', '')
                        tokens = result.get('tokens_predicted', 0)
                        print(f"  [OK] Completion successful")
                        print(f"       Response: {content[:100]}")
                        print(f"       Tokens: {tokens}")
                    else:
                        error_text = await resp.text()
                        print(f"  [X] Completion failed: {resp.status}")
                        print(f"       Error: {error_text[:200]}")
            except asyncio.TimeoutError:
                print(f"  [X] Completion timeout (30s)")
                print(f"  [!] Model may be loading or stuck")
            except Exception as e:
                print(f"  [X] Completion error: {type(e).__name__}: {e}")

async def check_daemon():
    """Check if EmberOS daemon is running and accessible"""
    print("\n" + "="*60)
    print("CHECKING EMBEROS DAEMON")
    print("="*60)

    try:
        from emberos.cli.client import EmberClient

        client = EmberClient()
        print("\nAttempting to connect to daemon...")

        if await client.connect():
            print("[OK] Connected to daemon successfully")

            # Check interface
            print("\nAvailable D-Bus interface methods:")
            for member in dir(client.interface):
                if not member.startswith("_"):
                    print(f"  - {member}")

            await client.disconnect()
            return True
        else:
            print("[X] Failed to connect to daemon")
            print("\nTroubleshooting:")
            print("  1. Is emberd service running?")
            print("     Check: systemctl --user status emberd")
            print("  2. Is D-Bus session available?")
            print("     Check: echo $DBUS_SESSION_BUS_ADDRESS")
            print("  3. Try restarting: systemctl --user restart emberd")
            return False

    except ImportError as e:
        print(f"[X] Cannot import EmberClient: {e}")
        print("  EmberOS may not be installed correctly")
        print("  Run: pip install -e . (in EmberOS directory)")
        return False
    except Exception as e:
        print(f"[X] Error checking daemon: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_workflow():
    """Test a complete workflow through the daemon"""
    print("\n" + "="*60)
    print("TESTING FULL WORKFLOW")
    print("="*60)

    try:
        from emberos.cli.client import EmberClient

        client = EmberClient()
        if not await client.connect():
            print("[X] Cannot connect to daemon")
            return

        print("[OK] Connected to daemon")

        # Setup signal handlers
        responses = []
        done = asyncio.Event()

        def on_progress(update):
            msg = f"Progress: {update.data.get('message', 'N/A')}"
            print(f"  [PROGRESS] {msg}")
            responses.append(("progress", msg))

        def on_completed(update):
            msg = update.data.get('response', 'N/A')
            print(f"  [COMPLETED] {msg}")
            responses.append(("completed", msg))
            done.set()

        def on_failed(update):
            error = update.data.get('error', 'Unknown error')
            print(f"  [FAILED] {error}")
            responses.append(("failed", error))
            done.set()

        def on_confirmation(update):
            msg = update.data.get('message', 'N/A')
            print(f"  [CONFIRMATION] {msg}")
            responses.append(("confirmation", msg))
            # Auto-confirm
            asyncio.create_task(client.confirm_action(update.task_id, True))

        client.on("progress", on_progress)
        client.on("completed", on_completed)
        client.on("failed", on_failed)
        client.on("confirmation", on_confirmation)

        # Test simple command
        test_command = "What is 2+2?"
        print(f"\n[SEND] Command: '{test_command}'")

        result = await client.process_command(test_command)
        print(f"\n[RECV] Immediate result:")
        print(f"  {json.dumps(result, indent=2)}")

        # Wait for completion
        print(f"\n[WAIT] Waiting for completion (timeout: 30s)...")
        try:
            await asyncio.wait_for(done.wait(), timeout=30)
            print("\n[OK] Workflow completed!")
        except asyncio.TimeoutError:
            print("\n[X] TIMEOUT: No completion signal received")
            print("\n    This usually means:")
            print("    1. LLM server not responding")
            print("    2. Planner failing to generate valid JSON")
            print("    3. Orchestrator hanging")
            print("\n    Check logs: journalctl --user -u emberd -f")

        print("\n" + "-"*60)
        print("SIGNAL HISTORY:")
        if responses:
            for i, (signal_type, msg) in enumerate(responses, 1):
                print(f"  {i}. [{signal_type.upper()}] {msg}")
        else:
            print("  [!] NO SIGNALS RECEIVED - Daemon may not be processing")
            print("      Check: journalctl --user -u emberd -n 50 --no-pager")

        await client.disconnect()

    except Exception as e:
        print(f"\n[X] Error during workflow test: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def check_model_files():
    """Check if model files exist"""
    print("\n" + "="*60)
    print("CHECKING MODEL FILES")
    print("="*60)

    model_paths = [
        ("BitNet", "/usr/local/share/ember/models/bitnet/ggml-model-i2_s.gguf"),
        ("BitNet (alt)", str(Path.home() / "Desktop/BitNet/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf")),
        ("Qwen2.5-VL", "/usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf"),
    ]

    for name, path in model_paths:
        path = Path(path)
        print(f"\n{name}:")
        print(f"  Path: {path}")
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  [OK] Exists ({size_mb:.1f} MB)")
        else:
            print(f"  [X] NOT FOUND")
            if "bitnet" in str(path).lower():
                print(f"  [!] Download: Run ./install.sh to download BitNet model")

async def check_llm_orchestrator_logs():
    """Check LLM orchestrator configuration"""
    print("\n" + "="*60)
    print("CHECKING LLM ORCHESTRATOR CONFIG")
    print("="*60)

    try:
        from emberos.daemon.llm_orchestrator import LLMOrchestrator
        from emberos.core.config import EmberConfig

        config = EmberConfig.load()
        print(f"\nLLM Configuration:")
        print(f"  Server URL: {config.llm.server_url}")
        print(f"  Model: {config.llm.default_model}")
        print(f"  Timeout: {config.llm.timeout}s")
        print(f"  Temperature: {config.llm.temperature}")

    except Exception as e:
        print(f"[X] Error loading config: {type(e).__name__}: {e}")

async def main():
    """Run all diagnostic checks"""
    print("\n")
    print("=" + "="*58 + "=")
    print("|" + " "*15 + "EMBEROS DEBUG UTILITY" + " "*22 + "|")
    print("=" + "="*58 + "=")

    # Run checks in order
    await check_system_services()
    await check_ports()
    await check_binaries()
    await check_model_files()
    await check_llm_manager_script()
    await check_llm_servers()
    await check_llm_orchestrator_logs()
    daemon_ok = await check_daemon()

    if daemon_ok:
        await test_full_workflow()
    else:
        print("\n[!] Skipping workflow test (daemon not available)")

    # Show service logs at the end
    await check_service_logs()

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)

    print("\n=== SUMMARY ===")
    print("\nIf you see issues above:")
    print("\n1. BitNet server not running (port 38080):")
    print("   - Check: journalctl --user -u ember-llm -n 50 --no-pager | grep -i bitnet")
    print("   - Model file: ls -lh /usr/local/share/ember/models/bitnet/")
    print("   - Restart: systemctl --user restart ember-llm")
    print("\n2. Qwen server not running (port 11434):")
    print("   - Check: journalctl --user -u ember-llm -n 50 --no-pager | grep -i qwen")
    print("   - Model file: ls -lh /usr/local/share/ember/models/qwen*")
    print("   - Restart: systemctl --user restart ember-llm")
    print("\n3. Daemon not connecting:")
    print("   - Check: journalctl --user -u emberd -n 50 --no-pager")
    print("   - Restart: systemctl --user restart emberd")
    print("   - D-Bus: echo $DBUS_SESSION_BUS_ADDRESS")
    print("\n4. No response from commands:")
    print("   - Watch logs: journalctl --user -u emberd -f")
    print("   - Look for [ORCHESTRATOR], [PLANNER], [DBUS] tags")
    print("\n5. Reinstall:")
    print("   - cd ~/EmberOS && git pull && ./install.sh")
    print()

if __name__ == "__main__":
    asyncio.run(main())

