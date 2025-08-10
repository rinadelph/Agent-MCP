# Agent-MCP/mcp_template/mcp_server_src/tools/registry.py
from typing import List, Dict, Any, Callable, Awaitable, Optional, Union
import mcp.types as mcp_types # Assuming this is the correct import for your mcp.types

# Import utility for JSON sanitization, as handle_tool uses it
from ..utils.json_utils import sanitize_json_input, get_sanitized_json_body
# Import the central logger
from ..core.config import logger

# Import ERP data integration tools
from .erp_data_import import import_erp_file, batch_import_erp_directory, get_import_status
from .erp_data_export import export_erp_data, export_predefined_report, batch_export_reports, get_available_reports

# Tool implementations will be imported here once they are created.
# For now, we'll define placeholders for the functions they will call.
# These will be replaced by actual imports from other tool modules.
# e.g., from .admin_tools import create_agent_tool_impl, view_status_tool_impl, ...
#       from .task_tools import assign_task_tool_impl, ...
#       from .rag_tools import ask_project_rag_tool_impl

# --- Tool Function Placeholders (to be replaced by actual imports) ---
# These represent the core logic of each tool, now separated from parsing/auth.
async def placeholder_tool_logic(*args, **kwargs) -> List[mcp_types.TextContent]:
    tool_name = kwargs.get('_tool_name', 'unknown_placeholder_tool')
    logger.warning(f"Placeholder logic called for tool: {tool_name} with args: {args}, kwargs: {kwargs}")
    return [mcp_types.TextContent(type="text", text=f"Placeholder response for {tool_name}. Not implemented in registry yet.")]

# This dictionary will map tool names to their implementation functions.
# It will be populated by importing and assigning the actual tool functions.
# Example:
# tool_implementations: Dict[str, Callable[..., Awaitable[List[mcp_types.TextContent]]]] = {
# "create_agent": create_agent_tool_impl, # from .admin_tools
# "view_status": view_status_tool_impl,   # from .admin_tools
# ... and so on for all tools
# }
# For now, it's empty and will be filled as we create the tool modules.
tool_implementations: Dict[str, Callable[..., Awaitable[List[mcp_types.TextContent]]]] = {}

# This list will hold the schema definitions for all tools.
# It will be populated by defining each tool's schema.
# Example entry:
# {
# "name": "create_agent",
# "description": "Create a new agent...",
# "inputSchema": { ... schema ... }
# }
tool_schemas: List[Dict[str, Any]] = []


# --- Core Tool Registry Functions ---

def register_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    implementation: Callable[..., Awaitable[List[mcp_types.TextContent]]]
):
    """
    Registers a tool's schema and its implementation.
    This function will be called by each tool module to register itself.
    """
    global tool_schemas, tool_implementations
    
    # Check for duplicate tool names
    if name in tool_implementations:
        logger.warning(f"Tool '{name}' is being re-registered. Overwriting previous definition.")

    tool_schemas.append({
        "name": name,
        "description": description,
        "inputSchema": input_schema
        # mcp.types.Tool in the original also had an outputSchema, which can be added if needed.
    })
    tool_implementations[name] = implementation
    logger.info(f"Registered tool: {name}")


async def list_available_tools() -> List[mcp_types.Tool]:
    """
    Returns a list of available tools with their schemas.
    This replaces the logic from `@app.list_tools()` in main.py (lines 1636-1858).
    It now reads from the `tool_schemas` list populated by `register_tool`.
    """
    # Convert the stored schema dictionaries to mcp_types.Tool objects
    # The original code directly returned a list of mcp_types.Tool.
    # We need to ensure the structure matches.
    
    # The `tool_schemas` list already contains dictionaries in the format
    # that can be directly used to instantiate `mcp_types.Tool` if the keys match.
    # Let's assume `mcp_types.Tool` can be constructed from a dictionary
    # with 'name', 'description', and 'inputSchema'.
    
    mcp_tool_list: List[mcp_types.Tool] = []
    for schema_dict in tool_schemas:
        try:
            # Assuming mcp_types.Tool can be initialized like this:
            # Tool(name="...", description="...", inputSchema={...})
            # If it requires specific keyword arguments, adjust accordingly.
            # The original `types.Tool` in main.py was directly instantiated.
            tool_instance = mcp_types.Tool(
                name=schema_dict["name"],
                description=schema_dict["description"],
                inputSchema=schema_dict["inputSchema"]
                # outputSchema=schema_dict.get("outputSchema") # If you add outputSchema
            )
            mcp_tool_list.append(tool_instance)
        except Exception as e:
            logger.error(f"Failed to create mcp_types.Tool instance for '{schema_dict.get('name', 'Unknown')}': {e}", exc_info=True)
            # Optionally, skip this tool or add a placeholder error tool.
            # For now, skipping problematic ones.

    return mcp_tool_list


async def dispatch_tool_call(
    tool_name: str,
    raw_arguments: Union[Dict[str, Any], List[Dict[str, Any]]] # Original accepted list or dict
) -> List[mcp_types.TextContent]:
    """
    Handles a tool call by dispatching to the appropriate implementation.
    This replaces the logic from `@app.call_tool()` in main.py (lines 1861-1931).
    """
    # Sanitize arguments input (main.py:1863-1877)
    sanitized_arguments: Any
    try:
        if isinstance(raw_arguments, list):
            # The original code had a recursive call to handle_tool for lists.
            # This is complex. A simpler approach is to define if tools accept lists of args
            # or if the client should make individual calls.
            # For 1-to-1 with original `handle_tool`'s list processing:
            # This implies that a single tool call message could contain a list of argument sets
            # for the *same* tool, and the server processes them sequentially, concatenating results.
            # This is an unusual pattern for tool calls.
            # Let's assume for now that a tool call is for one set of arguments.
            # If the list processing is essential, it needs careful thought on how it interacts
            # with individual tool function signatures.
            # The original code:
            # if isinstance(arguments, list):
            #     sanitized_args = []
            #     for arg in arguments:
            #         sanitized_args.append(sanitize_json_input(arg))
            #     results = []
            #     for arg in sanitized_args:
            #         res = await handle_tool(name, arg) # Recursive call
            #         results.extend(res)
            #     return results
            # This recursive structure is problematic for a clean dispatch.
            # For now, we will assume `raw_arguments` is a single dictionary for one tool call.
            # If list processing for a single tool name is needed, the tool implementation itself
            # should be designed to handle a list of argument sets.
            # The MCP protocol itself (mcp.types) might clarify if a "tool_call" message
            # can have a list of argument sets.
            # Given the structure of `call_mcp_tool` in the prompt (singular arguments),
            # it's more likely `raw_arguments` is a single Dict.
            if isinstance(raw_arguments, dict):
                sanitized_arguments = sanitize_json_input(raw_arguments)
            else: # If it's a list, and we are not supporting recursive calls here.
                logger.error(f"Received a list of arguments for tool '{tool_name}', but registry expects a single argument dictionary per call.")
                return [mcp_types.TextContent(type="text", text="Error: Server tool dispatcher expects a single argument set, not a list.")]

        elif not isinstance(raw_arguments, dict):
            # Try to sanitize and parse if not a dict (e.g., a JSON string from a raw request)
            sanitized_arguments = sanitize_json_input(raw_arguments)
            if not isinstance(sanitized_arguments, dict):
                # If after sanitization it's still not a dict, it's an invalid format.
                raise ValueError(f"Tool arguments for '{tool_name}' must be a dictionary after sanitization, got {type(sanitized_arguments)}")
        else: # It's already a dict
            sanitized_arguments = sanitize_json_input(raw_arguments) # Still sanitize it

    except ValueError as e:
        logger.error(f"Invalid input arguments for tool '{tool_name}': {e}")
        return [mcp_types.TextContent(type="text", text=f"Invalid input arguments: {str(e)}")]
    except Exception as e: # Catch any other sanitization errors
        logger.error(f"Error sanitizing arguments for tool '{tool_name}': {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error processing tool arguments: {str(e)}")]


    # Dispatch to the correct tool implementation (main.py:1879 onwards)
    if tool_name in tool_implementations:
        implementation_func = tool_implementations[tool_name]
        try:
            # The core logic of each tool (e.g., create_agent_tool_impl)
            # will now handle its own argument extraction (e.g., .get("token"))
            # and authentication/authorization if necessary.
            # This dispatch_tool_call function focuses on routing.
            # We pass the sanitized_arguments dictionary directly.
            # The original handle_tool had specific .get calls for each tool.
            # This will now be the responsibility of the individual tool_impl functions.
            # For example, create_agent_tool_impl(arguments: Dict) -> ...
            # inside create_agent_tool_impl: token = arguments.get("token"), agent_id = arguments.get("agent_id")
            
            # This is a key design decision:
            # Option A: Dispatcher unpacks args: `return await func(sanitized_args.get("token"), ...)` (like original)
            # Option B: Dispatcher passes dict: `return await func(sanitized_arguments)` (current choice)
            # Option B is more flexible if tool signatures vary widely or use **kwargs.
            # It makes individual tool functions responsible for their arg parsing.
            
            # For closer 1-to-1 with original's direct arg passing, we'd need a huge if/elif here.
            # Let's stick to Option B for better modularity, assuming tool_impl functions
            # are adapted to take a single dictionary of arguments.
            # If a strict 1-to-1 call signature is needed for each specific tool as in the original main.py,
            # then the `tool_implementations` would need to store lambdas or wrappers.
            # e.g. `lambda args: create_agent_tool_impl(args.get("token"), args.get("agent_id"), ...)`
            # This becomes cumbersome.
            # The most straightforward refactor is that tool_impl functions now take `(arguments: Dict[str, Any])`.

            # The original `handle_tool` in main.py (lines 1880-1931) had a large if/elif block.
            # This is now replaced by the `tool_implementations` dictionary lookup.
            # Each specific tool's logic (argument extraction, calling the core function)
            # will be in its own `*_tool.py` file, which registers its implementation.
            # The implementation function itself will handle argument extraction.
            
            # Example: if tool_name == "create_agent":
            #   return await create_agent_tool_impl(sanitized_arguments)
            # This is handled by the dict lookup now.

            return await implementation_func(sanitized_arguments)

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return [mcp_types.TextContent(type="text", text=f"Internal error executing tool '{tool_name}': {str(e)}")]
    else:
        logger.warning(f"Unknown tool called: {tool_name}")
        # Original main.py:1930 (raise ValueError(f"Unknown tool: {name}"))
        # Returning an error message is friendlier for an API.
        return [mcp_types.TextContent(type="text", text=f"Error: Unknown tool '{tool_name}'.")]

# The actual tool schemas and implementations will be populated by calls to `register_tool`
# from each of the specific tool modules (e.g., admin_tools.py, task_tools.py, etc.)
# when those modules are imported by the application (e.g., in mcp_server_src/tools/__init__.py).


# --- ERP Data Integration Tool Implementations ---

async def import_erp_file_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for importing ERP data files."""
    try:
        file_path = arguments.get("file_path")
        file_type = arguments.get("file_type")
        config = arguments.get("config", {})
        
        if not file_path:
            return [mcp_types.TextContent(type="text", text="Error: file_path is required")]
        
        # Call the import function
        result = import_erp_file(file_path, file_type, config)
        
        if result['success']:
            response = f"✅ ERP File Import Successful\n\n"
            response += f"Import ID: {result['import_id']}\n"
            response += f"File: {result['file_path']}\n"
            response += f"Type: {result['file_type']}\n"
            response += f"Records Imported: {result['imported_records']}/{result['total_records']}\n"
            response += f"Processing Time: {result['processing_time_seconds']:.2f}s\n"
            
            if result['skipped_records'] > 0:
                response += f"Skipped Records: {result['skipped_records']}\n"
            
            if result['errors']:
                response += f"\nErrors ({len(result['errors'])}):\n"
                for error in result['errors'][:3]:  # Show first 3 errors
                    response += f"  - {error}\n"
                if len(result['errors']) > 3:
                    response += f"  ... and {len(result['errors']) - 3} more\n"
        else:
            response = f"❌ ERP File Import Failed\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in import_erp_file_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


async def batch_import_erp_directory_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for batch importing ERP directory."""
    try:
        directory_path = arguments.get("directory_path")
        file_pattern = arguments.get("file_pattern", "*")
        config = arguments.get("config", {})
        
        if not directory_path:
            return [mcp_types.TextContent(type="text", text="Error: directory_path is required")]
        
        # Call the batch import function
        result = batch_import_erp_directory(directory_path, file_pattern, config)
        
        if result['success']:
            response = f"✅ ERP Batch Import Successful\n\n"
            response += f"Total Files: {result['total_files']}\n"
            response += f"Successful Files: {result['successful_files']}\n"
            response += f"Failed Files: {result['failed_files']}\n"
            response += f"Total Records Imported: {result['imported_records']}\n"
            
            if result['processing_summary']:
                response += f"\nFile Processing Summary:\n"
                for file_path, summary in result['processing_summary'].items():
                    filename = file_path.split('/')[-1]
                    status = "✅" if summary['success'] else "❌"
                    response += f"  {status} {filename}: {summary['imported']} records"
                    if summary['errors'] > 0:
                        response += f" ({summary['errors']} errors)"
                    response += "\n"
        else:
            response = f"❌ ERP Batch Import Failed\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in batch_import_erp_directory_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


async def export_erp_data_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for exporting ERP data."""
    try:
        query = arguments.get("query")
        output_path = arguments.get("output_path")
        format = arguments.get("format", "csv")
        config = arguments.get("config", {})
        parameters = arguments.get("parameters", [])
        
        if not query or not output_path:
            return [mcp_types.TextContent(type="text", text="Error: query and output_path are required")]
        
        # Call the export function
        result = export_erp_data(query, output_path, format, config, parameters)
        
        if result['success']:
            response = f"✅ ERP Data Export Successful\n\n"
            response += f"Export ID: {result['export_id']}\n"
            response += f"File: {result['file_path']}\n"
            response += f"Format: {result['format']}\n"
            response += f"Records Exported: {result['total_rows']}\n"
            response += f"File Size: {result['file_size_bytes']:,} bytes\n"
            response += f"Processing Time: {result['processing_time_seconds']:.2f}s\n"
            
            if result['warnings']:
                response += f"\nWarnings:\n"
                for warning in result['warnings'][:3]:
                    response += f"  - {warning}\n"
        else:
            response = f"❌ ERP Data Export Failed\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in export_erp_data_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


async def export_predefined_report_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for exporting predefined reports."""
    try:
        report_name = arguments.get("report_name")
        output_path = arguments.get("output_path")
        format = arguments.get("format", "csv")
        config = arguments.get("config", {})
        parameters = arguments.get("parameters", {})
        
        if not report_name or not output_path:
            return [mcp_types.TextContent(type="text", text="Error: report_name and output_path are required")]
        
        # Call the export function
        result = export_predefined_report(report_name, output_path, format, config, parameters)
        
        if result['success']:
            response = f"✅ ERP Report Export Successful\n\n"
            response += f"Report: {report_name}\n"
            response += f"Export ID: {result['export_id']}\n"
            response += f"File: {result['file_path']}\n"
            response += f"Format: {result['format']}\n"
            response += f"Records Exported: {result['total_rows']}\n"
            response += f"File Size: {result['file_size_bytes']:,} bytes\n"
            response += f"Processing Time: {result['processing_time_seconds']:.2f}s\n"
        else:
            response = f"❌ ERP Report Export Failed\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
            if 'available_reports' in result:
                response += f"\nAvailable Reports:\n"
                for report in result['available_reports']:
                    response += f"  - {report}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in export_predefined_report_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


async def get_available_reports_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for getting available reports."""
    try:
        result = get_available_reports()
        
        if result['success']:
            response = f"📊 Available ERP Reports ({result['total_reports']})\n\n"
            
            for report_name, info in result['reports'].items():
                response += f"**{report_name}**\n"
                response += f"  Description: {info['description']}\n"
                response += f"  Query Preview: {info['query_preview']}\n\n"
        else:
            response = f"❌ Failed to get available reports\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in get_available_reports_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


async def get_import_status_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """MCP tool implementation for getting import status."""
    try:
        import_id = arguments.get("import_id")
        
        result = get_import_status(import_id)
        
        if result['success']:
            if import_id:
                response = f"📊 Import Status: {import_id}\n\n"
                response += f"Status: {result.get('status', 'Unknown')}\n"
                response += f"Message: {result.get('message', 'No additional information')}\n"
            else:
                response = f"📊 Database Statistics\n\n"
                stats = result.get('database_statistics', {})
                
                for table_name, count in stats.items():
                    response += f"{table_name}: {count}\n"
                
                response += f"\nTimestamp: {result.get('timestamp', 'Unknown')}\n"
        else:
            response = f"❌ Failed to get import status\n\n"
            response += f"Error: {result.get('error', 'Unknown error')}\n"
            
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in get_import_status_impl: {e}")
        return [mcp_types.TextContent(type="text", text=f"Internal error: {str(e)}")]


# --- ERP Tool Registration ---

def register_erp_tools():
    """Register all ERP data integration tools."""
    
    # Import ERP File Tool
    register_tool(
        name="import_erp_file",
        description="Import data from a single ERP file (CSV, Excel) with HTML cleaning and validation",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the ERP data file to import"
                },
                "file_type": {
                    "type": "string",
                    "description": "Optional file type override (inventory, sales_orders, yarn_demand, etc.)",
                    "enum": ["inventory", "sales_orders", "yarn_demand", "yarn_report", "auto"]
                },
                "config": {
                    "type": "object",
                    "description": "Import configuration options",
                    "properties": {
                        "batch_size": {"type": "integer", "default": 1000},
                        "duplicate_strategy": {"type": "string", "enum": ["skip", "update", "error"], "default": "skip"},
                        "validation_level": {"type": "string", "enum": ["minimal", "standard", "strict"], "default": "standard"},
                        "continue_on_error": {"type": "boolean", "default": False}
                    }
                }
            },
            "required": ["file_path"]
        },
        implementation=import_erp_file_impl
    )
    
    # Batch Import Directory Tool
    register_tool(
        name="batch_import_erp_directory",
        description="Import all ERP files from a directory with parallel processing",
        input_schema={
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to directory containing ERP data files"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for file matching (default: '*')",
                    "default": "*"
                },
                "config": {
                    "type": "object",
                    "description": "Import configuration options",
                    "properties": {
                        "batch_size": {"type": "integer", "default": 1000},
                        "max_workers": {"type": "integer", "default": 4},
                        "duplicate_strategy": {"type": "string", "enum": ["skip", "update", "error"], "default": "skip"},
                        "continue_on_error": {"type": "boolean", "default": True}
                    }
                }
            },
            "required": ["directory_path"]
        },
        implementation=batch_import_erp_directory_impl
    )
    
    # Export ERP Data Tool
    register_tool(
        name="export_erp_data",
        description="Export ERP data using custom SQL query to various formats (CSV, Excel, JSON, PDF)",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute for data export"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for exported data"
                },
                "format": {
                    "type": "string",
                    "description": "Export format",
                    "enum": ["csv", "excel", "xlsx", "json", "pdf"],
                    "default": "csv"
                },
                "config": {
                    "type": "object",
                    "description": "Export configuration options",
                    "properties": {
                        "include_headers": {"type": "boolean", "default": True},
                        "max_rows": {"type": "integer", "description": "Maximum rows to export"},
                        "compression": {"type": "string", "enum": ["zip", "gzip"], "description": "File compression"},
                        "include_metadata": {"type": "boolean", "default": True}
                    }
                },
                "parameters": {
                    "type": "array",
                    "description": "Query parameters for parameterized queries",
                    "items": {"type": "string"}
                }
            },
            "required": ["query", "output_path"]
        },
        implementation=export_erp_data_impl
    )
    
    # Export Predefined Report Tool
    register_tool(
        name="export_predefined_report",
        description="Export predefined ERP reports (inventory_summary, sales_orders_active, etc.)",
        input_schema={
            "type": "object",
            "properties": {
                "report_name": {
                    "type": "string",
                    "description": "Name of predefined report",
                    "enum": [
                        "inventory_summary", "sales_orders_active", "production_orders_current",
                        "quality_metrics_weekly", "supplier_performance", "machine_utilization"
                    ]
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for exported report"
                },
                "format": {
                    "type": "string",
                    "description": "Export format",
                    "enum": ["csv", "excel", "xlsx", "json", "pdf"],
                    "default": "csv"
                },
                "config": {
                    "type": "object",
                    "description": "Export configuration options"
                },
                "parameters": {
                    "type": "object",
                    "description": "Report parameters as key-value pairs"
                }
            },
            "required": ["report_name", "output_path"]
        },
        implementation=export_predefined_report_impl
    )
    
    # Get Available Reports Tool
    register_tool(
        name="get_available_reports",
        description="Get list of available predefined ERP reports with descriptions",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        },
        implementation=get_available_reports_impl
    )
    
    # Get Import Status Tool
    register_tool(
        name="get_import_status",
        description="Get import operation status or database statistics",
        input_schema={
            "type": "object",
            "properties": {
                "import_id": {
                    "type": "string",
                    "description": "Optional import ID to check status (omit for general database stats)"
                }
            }
        },
        implementation=get_import_status_impl
    )
    
    logger.info("Registered 6 ERP data integration tools")


# Auto-register ERP tools when module is imported
register_erp_tools()