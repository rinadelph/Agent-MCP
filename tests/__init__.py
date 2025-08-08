# Agent-MCP Test Suite
"""
Test suite for the Agent-MCP system.
Provides unit tests, integration tests, and end-to-end tests.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    'database': {
        'file_name': 'test_mcp_state.db',
        'timeout': 5,
        'check_same_thread': False,
        'enable_foreign_keys': True
    },
    'openai': {
        'api_key': 'test-key',
        'embedding_model': 'text-embedding-3-small',
        'embedding_dimension': 1536,
        'chat_model': 'gpt-3.5-turbo',
        'max_tokens': 1000,
        'temperature': 0.1,
        'max_retries': 1,
        'timeout': 5
    },
    'agent': {
        'max_active_agents': 2,
        'agent_idle_timeout': 60,
        'auto_cleanup_enabled': True,
        'git_commit_interval': 300,
        'max_work_without_commit': 600
    },
    'rag': {
        'max_context_tokens': 1000,
        'chunk_size': 500,
        'overlap_size': 50,
        'max_results': 5,
        'similarity_threshold': 0.5,
        'auto_indexing_enabled': False
    },
    'server': {
        'host': 'localhost',
        'port': 8081,
        'debug': True,
        'log_level': 'DEBUG',
        'cors_enabled': True,
        'max_request_size': 1024 * 1024  # 1MB
    },
    'system': {
        'environment': 'testing',
        'project_dir': None,
        'data_dir': None,
        'log_dir': None,
        'temp_dir': None
    }
}

# Test utilities
def setup_test_environment():
    """Set up the test environment."""
    # Set test environment variables
    os.environ['ENVIRONMENT'] = 'testing'
    os.environ['OPENAI_API_KEY'] = 'test-key'
    os.environ['MCP_DEBUG'] = 'true'
    
    # Create test directories
    test_dir = Path(__file__).parent / 'test_data'
    test_dir.mkdir(exist_ok=True)
    
    # Set test project directory
    os.environ['MCP_PROJECT_DIR'] = str(test_dir)

def cleanup_test_environment():
    """Clean up the test environment."""
    # Remove test files
    test_dir = Path(__file__).parent / 'test_data'
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

def get_test_config():
    """Get test configuration."""
    return TEST_CONFIG.copy()
