import asyncio
import json
from emberos.cli.client import EmberClient

async def test():
    client = EmberClient()
    if await client.connect():
        print("Connected to daemon")
        
        # DEBUG: Introspect interface
        print("Interface members:")
        for member in dir(client.interface):
            if not member.startswith("_"):
                print(f"  - {member}")

        # Monitor signals
        done = asyncio.Event()
        
        def on_progress(update):
            print(f"Progress: {update.data.get('message')}")
            
        def on_completed(update):
            print(f"Completed: {update.data.get('response')}")
            done.set()
            
        def on_failed(update):
            print(f"Failed: {update.data.get('error')}")
            done.set()

        def on_confirmation(update):
            print(f"Confirmation required for task {update.task_id}: {update.data.get('message')}")
            print("Auto-confirming...")
            asyncio.create_task(client.confirm_action(update.task_id, True))

        client.on("progress", on_progress)
        client.on("completed", on_completed)
        client.on("failed", on_failed)
        client.on("confirmation", on_confirmation)
        
        print("Sending command: 'what time is it?'")
        result = await client.process_command("what time is it?")
        print(f"Result returned: {json.dumps(result, indent=2)}")
        
        try:
            await asyncio.wait_for(done.wait(), timeout=20)
        except asyncio.TimeoutError:
            print("Timed out waiting for response")
            
        await client.disconnect()
    else:
        print("Failed to connect to daemon")

if __name__ == "__main__":
    asyncio.run(test())
