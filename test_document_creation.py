#!/usr/bin/env python3
"""
Quick test script to verify document creation flow.
Run this to see detailed logs of what's happening.
"""
import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from emberos.daemon.planner import AgentPlanner
from emberos.daemon.llm_orchestrator import LLMOrchestrator
from emberos.tools.registry import ToolRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_document_creation():
    """Test the document creation flow."""
    print("\n" + "="*60)
    print("Testing Document Creation Flow")
    print("="*60 + "\n")

    # Initialize components
    tool_registry = ToolRegistry()
    llm = LLMOrchestrator()
    planner = AgentPlanner(llm, tool_registry)

    # Simulate the conversation
    print("Step 1: User requests document creation")
    print("User: 'create txt document about types of machine learning'\n")

    plan1 = await planner.create_plan(
        "create txt document about types of machine learning",
        context={"working_directory": "/home/user"}
    )

    print(f"Plan reasoning: {plan1.reasoning}")
    print(f"Confirmation message: {plan1.confirmation_message}")
    print(f"Requires confirmation: {plan1.requires_confirmation}\n")

    if plan1.confirmation_message == "DOCUMENT_CREATION_PROMPT":
        print("✓ Correctly set to prompt for filename/location\n")

        # Synthesize response (should ask for filename/location)
        response1 = await planner.synthesize_response(
            "create txt document about types of machine learning",
            plan1,
            []
        )
        print(f"Agent response:\n{response1}\n")

        # Step 2: User provides filename and location
        print("Step 2: User provides filename and location")
        print("User: 'machine_learning.txt in Downloads'\n")

        plan2 = await planner.create_plan(
            "machine_learning.txt in Downloads",
            context={"working_directory": "/home/user"}
        )

        print(f"Plan reasoning: {plan2.reasoning}")
        print(f"Confirmation message: {plan2.confirmation_message[:50]}..." if plan2.confirmation_message else "None")

        if plan2.confirmation_message and plan2.confirmation_message.startswith("GENERATE_DOCUMENT"):
            print("✓ Correctly set to generate document\n")

            # Synthesize response (should generate and save file)
            response2 = await planner.synthesize_response(
                "machine_learning.txt in Downloads",
                plan2,
                []
            )
            print(f"Agent response:\n{response2}\n")

            if "Created" in response2 or "created" in response2:
                print("✓ Document creation successful!")
            else:
                print("✗ Document creation may have failed")
        else:
            print("✗ Failed to create GENERATE_DOCUMENT plan")
    else:
        print("✗ Failed to set DOCUMENT_CREATION_PROMPT")

    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_document_creation())

