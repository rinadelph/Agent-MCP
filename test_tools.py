#!/usr/bin/env python3
"""Test script to inspect MCP tool schemas without running the server."""

import os
import sys
from pathlib import Path

# Add the agent_mcp package to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Mock the OPENAI_API_KEY so imports work
os.environ["OPENAI_API_KEY"] = "mock_key_for_testing"
os.environ["MCP_PROJECT_DIR"] = str(Path(__file__).parent)

try:
    # Import the tools package to trigger registration
    import agent_mcp.tools
    from agent_mcp.tools.registry import tool_schemas, tool_implementations
    
    print("=== MCP TOOLS ANALYSIS ===\n")
    print(f"Total tools registered: {len(tool_schemas)}")
    print(f"Tool names: {list(tool_implementations.keys())}\n")
    
    # Find and inspect bulk_update_project_context specifically
    bulk_tool = None
    for tool in tool_schemas:
        if tool["name"] == "bulk_update_project_context":
            bulk_tool = tool
            break
    
    if bulk_tool:
        print("=== BULK_UPDATE_PROJECT_CONTEXT TOOL SCHEMA ===")
        print(f"Name: {bulk_tool['name']}")
        print(f"Description: {bulk_tool['description']}")
        
        schema = bulk_tool["inputSchema"]
        print("\nInput Schema:")
        print(f"  Type: {schema.get('type', 'MISSING')}")
        print(f"  Required: {schema.get('required', 'MISSING')}")
        
        if "properties" in schema:
            print("  Properties:")
            for prop_name, prop_def in schema["properties"].items():
                print(f"    {prop_name}:")
                print(f"      Type: {prop_def.get('type', 'MISSING')}")
                print(f"      Description: {prop_def.get('description', 'MISSING')}")
                
                if prop_name == "updates" and "items" in prop_def:
                    print("      Items:")
                    items = prop_def["items"]
                    if "properties" in items:
                        for item_prop, item_def in items["properties"].items():
                            print(f"        {item_prop}:")
                            print(f"          Type: {item_def.get('type', 'MISSING')}")
                            if "anyOf" in item_def:
                                print(f"          AnyOf: {item_def['anyOf']}")
                            print(f"          Description: {item_def.get('description', 'MISSING')}")
    else:
        print("ERROR: bulk_update_project_context tool not found!")
        
except Exception as e:
    print(f"Error during tool analysis: {e}")
    import traceback
    traceback.print_exc()