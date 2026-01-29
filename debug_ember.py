#!/usr/bin/env python3
"""
EmberOS Debug Script - Comprehensive system check
"""
import asyncio
import json
import sys
import aiohttp
import logging
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
                        print(f"  ✓ Health: {health}")
                    else:
                        print(f"  ✗ Health check failed: {resp.status}")
            except Exception as e:
                print(f"  ✗ Health check error: {e}")
                continue
            
            # Check models endpoint
            try:
                async with session.get(f"{url}/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        models = await resp.json()
                        print(f"  ✓ Models: {json.dumps(models, indent=4)}")
                    else:
                        print(f"  ✗ Models check failed: {resp.status}")
            except Exception as e:
                print(f"  ✗ Models check error: {e}")
            
            # Try a simple completion
            print(f"  Testing completion...")
            try:
                payload = {
                    "model": "default",
                    "prompt": "Hello",
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "stream": False
                }
                async with session.post(
                    f"{url}/v1/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"  ✓ Completion successful:")
                        print(f"    Response: {result.get('choices', [{}])[0].get('text', 'N/A')}")
                    else:
                        error_text = await resp.text()
                        print(f"  ✗ Completion failed: {resp.status}")
                        print(f"    Error: {error_text}")
            except Exception as e:
                print(f"  ✗ Completion error: {e}")

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
            print("✓ Connected to daemon successfully")
            
            # Check interface
            print("\nAvailable D-Bus interface methods:")
            for member in dir(client.interface):
                if not member.startswith("_"):
                    print(f"  - {member}")
            
            await client.disconnect()
            return True
        else:
            print("✗ Failed to connect to daemon")
            print("\nTroubleshooting:")
            print("  1. Is emberd service running?")
            print("     Check: systemctl --user status emberd")
            print("  2. Is D-Bus session available?")
            print("     Check: echo $DBUS_SESSION_BUS_ADDRESS")
            return False
            
    except ImportError as e:
        print(f"✗ Cannot import EmberClient: {e}")
        print("  EmberOS may not be installed correctly")
        return False
    except Exception as e:
        print(f"✗ Error checking daemon: {e}")
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
            print("✗ Cannot connect to daemon")
            return
        
        print("✓ Connected to daemon")
        
        # Setup signal handlers
        responses = []
        done = asyncio.Event()
        
        def on_progress(update):
            msg = f"Progress: {update.data.get('message', 'N/A')}"
            print(f"  📊 {msg}")
            responses.append(("progress", msg))
            
        def on_completed(update):
            msg = update.data.get('response', 'N/A')
            print(f"  ✓ Completed: {msg}")
            responses.append(("completed", msg))
            done.set()
            
        def on_failed(update):
            error = update.data.get('error', 'Unknown error')
            print(f"  ✗ Failed: {error}")
            responses.append(("failed", error))
            done.set()
        
        def on_confirmation(update):
            msg = update.data.get('message', 'N/A')
            print(f"  ❓ Confirmation required: {msg}")
            responses.append(("confirmation", msg))
            # Auto-confirm
            asyncio.create_task(client.confirm_action(update.task_id, True))
        
        client.on("progress", on_progress)
        client.on("completed", on_completed)
        client.on("failed", on_failed)
        client.on("confirmation", on_confirmation)
        
        # Test simple command
        test_command = "What is 2+2?"
        print(f"\n📤 Sending command: '{test_command}'")
        
        result = await client.process_command(test_command)
        print(f"\n📥 Immediate result: {json.dumps(result, indent=2)}")
        
        # Wait for completion
        print("\n⏳ Waiting for completion (timeout: 30s)...")
        try:
            await asyncio.wait_for(done.wait(), timeout=30)
            print("\n✓ Workflow completed!")
        except asyncio.TimeoutError:
            print("\n✗ TIMEOUT: No completion signal received")
            print("\nThis usually means:")
            print("  1. LLM server not responding")
            print("  2. Planner failing to generate valid JSON")
            print("  3. Orchestrator hanging")
        
        print("\n" + "-"*60)
        print("SIGNAL HISTORY:")
        for i, (signal_type, msg) in enumerate(responses, 1):
            print(f"  {i}. [{signal_type}] {msg}")
        
        if not responses:
            print("  ⚠️  NO SIGNALS RECEIVED - Daemon may not be processing")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"\n✗ Error during workflow test: {e}")
        import traceback
        traceback.print_exc()

async def check_model_files():
    """Check if model files exist"""
    print("\n" + "="*60)
    print("CHECKING MODEL FILES")
    print("="*60)
    
    model_paths = [
        ("BitNet", "/usr/local/share/ember/models/bitnet/ggml-model-i2_s.gguf"),
        ("BitNet (alt)", Path.home() / "Desktop/BitNet/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf"),
        ("Qwen2.5-VL", "/usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf"),
    ]
    
    for name, path in model_paths:
        path = Path(path)
        print(f"\n{name}:")
        print(f"  Path: {path}")
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Exists ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ NOT FOUND")

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
        print(f"✗ Error loading config: {e}")

async def main():
    """Run all diagnostic checks"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "EMBEROS DEBUG UTILITY" + " "*22 + "║")
    print("╚" + "="*58 + "╝")
    
    # Run checks
    await check_model_files()
    await check_llm_servers()
    await check_llm_orchestrator_logs()
    daemon_ok = await check_daemon()
    
    if daemon_ok:
        await test_full_workflow()
    else:
        print("\n⚠️  Skipping workflow test (daemon not available)")
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)
    print("\nIf issues persist, check:")
    print("  • journalctl --user -u emberd -n 100 --no-pager")
    print("  • journalctl --user -u ember-llm -n 100 --no-pager")
    print("  • ~/.local/share/ember/logs/")
    print()

if __name__ == "__main__":
    asyncio.run(main())

