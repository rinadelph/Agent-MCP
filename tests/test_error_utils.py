# Tests for error handling utilities
"""
Unit tests for the error handling utilities module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from agent_mcp.utils.error_utils import (
    AgentMCPError,
    AuthenticationError,
    DatabaseError,
    OpenAIError,
    ToolExecutionError,
    ValidationError,
    handle_tool_errors,
    validate_required_fields,
    validate_field_types,
    retry_on_failure,
    log_operation,
    format_error_response,
    create_error_content
)
import mcp.types as mcp_types

class TestErrorTypes:
    """Test error type hierarchy."""
    
    def test_error_inheritance(self):
        """Test that all error types inherit from AgentMCPError."""
        assert issubclass(AuthenticationError, AgentMCPError)
        assert issubclass(DatabaseError, AgentMCPError)
        assert issubclass(OpenAIError, AgentMCPError)
        assert issubclass(ToolExecutionError, AgentMCPError)
        assert issubclass(ValidationError, AgentMCPError)

class TestValidationFunctions:
    """Test validation utility functions."""
    
    def test_validate_required_fields_success(self):
        """Test successful validation of required fields."""
        arguments = {'field1': 'value1', 'field2': 'value2'}
        required_fields = ['field1', 'field2']
        
        # Should not raise an exception
        validate_required_fields(arguments, required_fields)
    
    def test_validate_required_fields_missing(self):
        """Test validation failure when required fields are missing."""
        arguments = {'field1': 'value1'}
        required_fields = ['field1', 'field2']
        
        with pytest.raises(ValidationError, match="Missing required fields: field2"):
            validate_required_fields(arguments, required_fields)
    
    def test_validate_required_fields_none_value(self):
        """Test validation failure when required field has None value."""
        arguments = {'field1': 'value1', 'field2': None}
        required_fields = ['field1', 'field2']
        
        with pytest.raises(ValidationError, match="Missing required fields: field2"):
            validate_required_fields(arguments, required_fields)
    
    def test_validate_field_types_success(self):
        """Test successful validation of field types."""
        arguments = {'field1': 'string', 'field2': 42, 'field3': True}
        field_types = {
            'field1': str,
            'field2': int,
            'field3': bool
        }
        
        # Should not raise an exception
        validate_field_types(arguments, field_types)
    
    def test_validate_field_types_wrong_type(self):
        """Test validation failure when field has wrong type."""
        arguments = {'field1': 'string', 'field2': 'not_an_int'}
        field_types = {
            'field1': str,
            'field2': int
        }
        
        with pytest.raises(ValidationError, match="Field 'field2' must be of type int"):
            validate_field_types(arguments, field_types)
    
    def test_validate_field_types_optional_field(self):
        """Test validation when optional field is not present."""
        arguments = {'field1': 'string'}
        field_types = {
            'field1': str,
            'field2': int  # Not in arguments, should be ignored
        }
        
        # Should not raise an exception
        validate_field_types(arguments, field_types)

class TestHandleToolErrors:
    """Test the handle_tool_errors decorator."""
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_success(self):
        """Test successful tool execution."""
        @handle_tool_errors
        async def test_tool(arguments):
            return [mcp_types.TextContent(type="text", text="Success")]
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert result[0].text == "Success"
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_authentication_error(self):
        """Test handling of AuthenticationError."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise AuthenticationError("Invalid token")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "Authentication error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_validation_error(self):
        """Test handling of ValidationError."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise ValidationError("Invalid input")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "Validation error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_database_error(self):
        """Test handling of DatabaseError."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise DatabaseError("Connection failed")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "Database error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_openai_error(self):
        """Test handling of OpenAIError."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise OpenAIError("API rate limit")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "OpenAI API error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_tool_execution_error(self):
        """Test handling of ToolExecutionError."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise ToolExecutionError("Tool failed")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "Tool execution error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_tool_errors_unexpected_error(self):
        """Test handling of unexpected errors."""
        @handle_tool_errors
        async def test_tool(arguments):
            raise ValueError("Unexpected error")
        
        result = await test_tool({'test': 'value'})
        assert len(result) == 1
        assert "Unexpected error" in result[0].text

class TestRetryOnFailure:
    """Test the retry_on_failure decorator."""
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_success_first_try(self):
        """Test successful execution on first try."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "Success"
        
        result = await test_function()
        assert result == "Success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_success_after_retries(self):
        """Test successful execution after some retries."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "Success"
        
        result = await test_function()
        assert result == "Success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_max_retries_exceeded(self):
        """Test failure after max retries exceeded."""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError, match="Persistent failure"):
            await test_function()
        
        assert call_count == 3  # Initial try + 2 retries

class TestLogOperation:
    """Test the log_operation decorator."""
    
    @pytest.mark.asyncio
    async def test_log_operation_success(self):
        """Test successful operation logging."""
        @log_operation("test_operation")
        async def test_function():
            return "Success"
        
        result = await test_function()
        assert result == "Success"
    
    @pytest.mark.asyncio
    async def test_log_operation_failure(self):
        """Test operation logging on failure."""
        @log_operation("test_operation")
        async def test_function():
            raise ValueError("Operation failed")
        
        with pytest.raises(ValueError, match="Operation failed"):
            await test_function()

class TestErrorFormatting:
    """Test error formatting functions."""
    
    def test_format_error_response_authentication(self):
        """Test formatting of AuthenticationError."""
        error = AuthenticationError("Invalid token")
        result = format_error_response(error)
        assert "Authentication failed" in result
    
    def test_format_error_response_validation(self):
        """Test formatting of ValidationError."""
        error = ValidationError("Invalid input")
        result = format_error_response(error)
        assert "Invalid input" in result
    
    def test_format_error_response_database(self):
        """Test formatting of DatabaseError."""
        error = DatabaseError("Connection failed")
        result = format_error_response(error)
        assert "Database error" in result
    
    def test_format_error_response_openai(self):
        """Test formatting of OpenAIError."""
        error = OpenAIError("Rate limit exceeded")
        result = format_error_response(error)
        assert "OpenAI API error" in result
    
    def test_format_error_response_tool_execution(self):
        """Test formatting of ToolExecutionError."""
        error = ToolExecutionError("Tool failed")
        result = format_error_response(error)
        assert "Tool execution error" in result
    
    def test_format_error_response_unexpected(self):
        """Test formatting of unexpected errors."""
        error = ValueError("Unexpected error")
        result = format_error_response(error)
        assert "Unexpected error" in result
    
    def test_create_error_content(self):
        """Test creation of error content for MCP."""
        error = ValidationError("Invalid input")
        result = create_error_content(error)
        
        assert len(result) == 1
        assert isinstance(result[0], mcp_types.TextContent)
        assert result[0].type == "text"
        assert "Invalid input" in result[0].text
