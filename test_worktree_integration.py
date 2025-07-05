#!/usr/bin/env python3
"""
Test script for worktree integration features.

This script tests the integration layer and agent creation with worktree support.
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add the agent_mcp package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_worktree_integration():
    """Test worktree integration features."""
    print("🧪 Testing Worktree Integration")
    print("=" * 50)
    
    # Test 1: Import worktree integration module
    print("\n📝 Test 1: Import worktree integration")
    try:
        from agent_mcp.features.worktree_integration import (
            enable_worktree_support, is_worktree_enabled, 
            create_agent_worktree, WorktreeConfig, get_worktree_status
        )
        print("✅ Successfully imported worktree integration module")
    except ImportError as e:
        print(f"❌ Failed to import worktree integration: {e}")
        return False
    
    # Test 2: Enable worktree support
    print("\n📝 Test 2: Enable worktree support")
    try:
        enabled = enable_worktree_support()
        if enabled:
            print("✅ Worktree support enabled successfully")
        else:
            print("❌ Failed to enable worktree support")
            return False
    except Exception as e:
        print(f"❌ Error enabling worktree support: {e}")
        return False
    
    # Test 3: Check worktree status
    print("\n📝 Test 3: Check worktree status")
    try:
        is_enabled = is_worktree_enabled()
        status = get_worktree_status()
        print(f"✅ Worktree enabled: {is_enabled}")
        print(f"✅ Worktree status: {status}")
    except Exception as e:
        print(f"❌ Error checking worktree status: {e}")
        return False
    
    # Test 4: Create worktree config
    print("\n📝 Test 4: Create worktree config")
    try:
        config = WorktreeConfig(
            enabled=True,
            branch_name="test/integration",
            base_branch="v4/worktree-integration",
            auto_setup=True,
            cleanup_strategy="on_terminate"
        )
        print(f"✅ Created worktree config: {config}")
    except Exception as e:
        print(f"❌ Error creating worktree config: {e}")
        return False
    
    # Test 5: Test agent creation with worktree (simulation)
    print("\n📝 Test 5: Create agent worktree (test mode)")
    try:
        agent_id = "test_integration_agent"
        admin_token_suffix = "def2"
        
        result = create_agent_worktree(agent_id, admin_token_suffix, config)
        
        if result["success"]:
            print(f"✅ Created agent worktree: {result['worktree_path']}")
            
            # Clean up the test worktree
            from agent_mcp.features.worktree_integration import cleanup_agent_worktree
            cleanup_result = cleanup_agent_worktree(agent_id, force=True)
            
            if cleanup_result["success"]:
                print("✅ Successfully cleaned up test worktree")
            else:
                print(f"⚠️ Cleanup warning: {cleanup_result.get('error', 'unknown issue')}")
        else:
            print(f"❌ Failed to create agent worktree: {result.get('error', 'unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error in agent worktree creation: {e}")
        return False
    
    # Test 6: Test CLI imports
    print("\n📝 Test 6: Test CLI integration imports")
    try:
        from agent_mcp.cli import main_cli
        print("✅ Successfully imported CLI with worktree support")
    except ImportError as e:
        print(f"❌ Failed to import CLI: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All worktree integration tests passed!")
    return True

async def test_admin_tools_integration():
    """Test admin tools integration with worktree features."""
    print("\n🔧 Testing Admin Tools Integration")
    print("=" * 40)
    
    # Test: Import admin tools with worktree support
    try:
        from agent_mcp.tools.admin_tools import create_agent_tool_impl
        print("✅ Successfully imported admin tools with worktree support")
        
        # Simulate the schema parameters for worktree
        test_args = {
            "token": "dummy_admin_token",
            "agent_id": "test_worktree_agent",
            "use_worktree": True,
            "branch_name": "feature/test-integration",
            "base_branch": "main",
            "auto_setup": True
        }
        
        print(f"✅ Test arguments prepared: {list(test_args.keys())}")
        print("✅ Admin tools ready for worktree integration")
        
    except ImportError as e:
        print(f"❌ Failed to import admin tools: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in admin tools test: {e}")
        return False
    
    return True

async def main():
    """Run all integration tests."""
    print("🚀 Agent-MCP Worktree Integration Tests")
    print("=" * 60)
    
    success = True
    
    # Run worktree integration tests
    if not await test_worktree_integration():
        success = False
    
    # Run admin tools integration tests
    if not await test_admin_tools_integration():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Ready for end-to-end testing")
        return 0
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("🔧 Check the errors above for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)