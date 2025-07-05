#!/usr/bin/env python3
"""
Basic test script for worktree utilities.

This script tests the core worktree functionality before integrating
with the main agent system.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the agent_mcp package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from agent_mcp.utils.worktree_utils import (
    is_git_repository,
    validate_worktree_requirements,
    create_git_worktree,
    list_git_worktrees,
    cleanup_git_worktree,
    detect_project_setup_commands,
    generate_worktree_path,
    generate_branch_name,
    get_current_branch
)


def test_basic_validation():
    """Test basic validation functions."""
    print("🔍 Testing basic validation...")
    
    # Test Git repository detection
    is_repo = is_git_repository()
    print(f"  ✓ Is Git repository: {is_repo}")
    
    if not is_repo:
        print("  ❌ Not in a Git repository - cannot test worktree operations")
        return False
    
    # Test worktree requirements
    validation = validate_worktree_requirements()
    print(f"  ✓ Worktree validation: {validation}")
    
    if not validation["valid"]:
        print(f"  ❌ Worktree requirements not met: {validation['issues']}")
        return False
    
    # Test current branch
    current_branch = get_current_branch()
    print(f"  ✓ Current branch: {current_branch}")
    
    return True


def test_path_generation():
    """Test path and branch name generation."""
    print("🏗️  Testing path generation...")
    
    # Test worktree path generation
    agent_id = "test_agent"
    token_suffix = "def2"
    worktree_path = generate_worktree_path(agent_id, token_suffix)
    print(f"  ✓ Generated worktree path: {worktree_path}")
    
    # Test branch name generation
    branch_name = generate_branch_name(agent_id)
    print(f"  ✓ Generated branch name: {branch_name}")
    
    custom_branch = generate_branch_name(agent_id, "feature/custom")
    print(f"  ✓ Custom branch name: {custom_branch}")
    
    return True


def test_worktree_operations():
    """Test worktree creation, listing, and cleanup."""
    print("⚙️  Testing worktree operations...")
    
    # Create a temporary directory for testing
    test_dir = os.path.join(tempfile.gettempdir(), "agent_mcp_worktree_test")
    
    try:
        # Clean up any existing test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        # Test worktree creation
        print(f"  🔨 Creating test worktree at: {test_dir}")
        create_result = create_git_worktree(
            path=test_dir,
            branch="test/worktree-utils",
            base_branch=get_current_branch() or "main"
        )
        
        print(f"  ✓ Create result: {create_result}")
        
        if not create_result["success"]:
            print(f"  ❌ Failed to create worktree: {create_result['error']}")
            return False
        
        # Verify the worktree was created
        if not os.path.exists(test_dir):
            print(f"  ❌ Worktree directory was not created: {test_dir}")
            return False
        
        print(f"  ✅ Worktree created successfully")
        
        # Test worktree listing
        print("  📋 Listing worktrees...")
        worktrees = list_git_worktrees()
        print(f"  ✓ Found {len(worktrees)} worktrees")
        
        # Find our test worktree
        test_worktree = None
        for wt in worktrees:
            if test_dir in wt["path"]:
                test_worktree = wt
                break
        
        if not test_worktree:
            print("  ❌ Test worktree not found in listing")
            return False
        
        print(f"  ✅ Test worktree found: {test_worktree}")
        
        # Test setup command detection
        print("  🔍 Detecting setup commands...")
        setup_commands = detect_project_setup_commands(test_dir)
        print(f"  ✓ Detected commands: {setup_commands}")
        
        # Test worktree cleanup
        print("  🧹 Cleaning up test worktree...")
        cleanup_result = cleanup_git_worktree(test_dir)
        print(f"  ✓ Cleanup result: {cleanup_result}")
        
        if not cleanup_result["success"]:
            print(f"  ❌ Failed to cleanup worktree: {cleanup_result['error']}")
            return False
        
        # Verify cleanup
        if os.path.exists(test_dir):
            print(f"  ❌ Worktree directory still exists after cleanup: {test_dir}")
            return False
        
        print(f"  ✅ Worktree cleaned up successfully")
        
        return True
        
    except Exception as e:
        print(f"  💥 Exception during worktree operations: {e}")
        return False
    finally:
        # Emergency cleanup
        if os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
            except Exception:
                print(f"  ⚠️  Manual cleanup required: {test_dir}")


def test_project_detection():
    """Test project type detection."""
    print("🔎 Testing project type detection...")
    
    current_dir = os.getcwd()
    setup_commands = detect_project_setup_commands(current_dir)
    print(f"  ✓ Current project setup commands: {setup_commands}")
    
    return True


def main():
    """Run all tests."""
    print("🚀 Testing Agent-MCP Worktree Utilities")
    print("=" * 50)
    
    tests = [
        ("Basic Validation", test_basic_validation),
        ("Path Generation", test_path_generation),
        ("Project Detection", test_project_detection),
        ("Worktree Operations", test_worktree_operations),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 {test_name}")
        print("-" * 30)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Worktree utilities are working correctly.")
        return 0
    else:
        print("🚨 Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())