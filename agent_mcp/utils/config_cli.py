#!/usr/bin/env python3
"""
Configuration Management CLI Tool
Provides commands to validate, export, import, and manage configuration settings.
"""

import argparse
import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.config import ConfigurationManager, ConfigError, config_manager


def validate_config(config_file: Optional[Path] = None) -> bool:
    """Validate configuration and return True if valid."""
    try:
        if config_file:
            # Create a new manager with the specified file
            manager = ConfigurationManager(config_file)
        else:
            manager = config_manager
        
        # Validate environment variables
        missing_vars = manager.validate_environment_variables()
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        # Configuration is already validated during loading
        print("✅ Configuration validation passed")
        return True
        
    except ConfigError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return False


def export_config(output_file: Path, format_type: str = "json") -> bool:
    """Export current configuration to a file."""
    try:
        config_data = config_manager.to_dict()
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            if format_type.lower() == "yaml":
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_data, f, indent=2)
        
        print(f"✅ Configuration exported to {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting configuration: {e}")
        return False


def import_config(input_file: Path) -> bool:
    """Import configuration from a file."""
    try:
        if not input_file.exists():
            print(f"❌ Configuration file not found: {input_file}")
            return False
        
        # Create a new manager with the input file
        manager = ConfigurationManager(input_file)
        
        # Save to the current config file if it exists
        if config_manager.config_file:
            manager.save_to_file(config_manager.config_file)
            print(f"✅ Configuration imported and saved to {config_manager.config_file}")
        else:
            print("✅ Configuration imported (no default config file to save to)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error importing configuration: {e}")
        return False


def show_config(section: Optional[str] = None) -> bool:
    """Show current configuration."""
    try:
        config_data = config_manager.to_dict()
        
        if section:
            if section not in config_data:
                print(f"❌ Configuration section '{section}' not found")
                return False
            config_data = {section: config_data[section]}
        
        print(json.dumps(config_data, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Error showing configuration: {e}")
        return False


def set_config_value(key: str, value: str) -> bool:
    """Set a configuration value."""
    try:
        # Parse the key path (e.g., "openai.api_key")
        parts = key.split('.')
        if len(parts) != 2:
            print("❌ Invalid key format. Use 'section.key' (e.g., 'openai.api_key')")
            return False
        
        section, key_name = parts
        
        # Get the section object
        section_obj = getattr(config_manager, section, None)
        if section_obj is None:
            print(f"❌ Configuration section '{section}' not found")
            return False
        
        # Convert value to appropriate type
        current_value = getattr(section_obj, key_name, None)
        if current_value is not None:
            if isinstance(current_value, bool):
                converted_value = value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(current_value, int):
                converted_value = int(value)
            elif isinstance(current_value, float):
                converted_value = float(value)
            else:
                converted_value = value
        else:
            # Try to guess the type
            if value.lower() in ('true', 'false'):
                converted_value = value.lower() == 'true'
            elif value.isdigit():
                converted_value = int(value)
            elif value.replace('.', '').isdigit():
                converted_value = float(value)
            else:
                converted_value = value
        
        # Set the value
        setattr(section_obj, key_name, converted_value)
        
        # Save to file if config file exists
        if config_manager.config_file:
            config_manager.save_to_file()
        
        print(f"✅ Set {key} = {converted_value}")
        return True
        
    except Exception as e:
        print(f"❌ Error setting configuration value: {e}")
        return False


def create_default_config(output_file: Path, format_type: str = "json") -> bool:
    """Create a default configuration file."""
    try:
        # Create a new manager with default values
        manager = ConfigurationManager()
        
        # Save to the specified file
        manager.save_to_file(output_file)
        
        print(f"✅ Default configuration created at {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating default configuration: {e}")
        return False


def check_environment() -> bool:
    """Check environment variables and configuration."""
    try:
        print("🔍 Checking environment variables...")
        
        # Check required environment variables
        missing_vars = config_manager.validate_environment_variables()
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        else:
            print("✅ All required environment variables are set")
        
        # Check optional but important variables
        optional_vars = {
            "MCP_PROJECT_DIR": "Project directory",
            "OPENAI_API_KEY": "OpenAI API key",
            "ENVIRONMENT": "Environment type",
            "LOG_LEVEL": "Log level"
        }
        
        print("\n📋 Environment variable status:")
        for var, description in optional_vars.items():
            value = config_manager.openai.api_key if var == "OPENAI_API_KEY" else os.getenv(var)
            if value:
                # Mask sensitive values
                if var == "OPENAI_API_KEY":
                    display_value = f"{value[:8]}..." if len(value) > 8 else "***"
                else:
                    display_value = value
                print(f"  ✅ {var}: {display_value}")
            else:
                print(f"  ⚠️  {var}: Not set ({description})")
        
        return len(missing_vars) == 0
        
    except Exception as e:
        print(f"❌ Error checking environment: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent-MCP Configuration Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate                    # Validate current configuration
  %(prog)s export config.json         # Export configuration to JSON
  %(prog)s export config.yaml --yaml  # Export configuration to YAML
  %(prog)s import config.json         # Import configuration from JSON
  %(prog)s show                       # Show all configuration
  %(prog)s show openai                # Show OpenAI configuration section
  %(prog)s set openai.temperature 0.7 # Set OpenAI temperature
  %(prog)s create-default config.json # Create default configuration
  %(prog)s check-env                  # Check environment variables
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--config', type=Path, help='Configuration file to validate')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('output_file', type=Path, help='Output file path')
    export_parser.add_argument('--yaml', action='store_true', help='Export as YAML instead of JSON')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration')
    import_parser.add_argument('input_file', type=Path, help='Input file path')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show configuration')
    show_parser.add_argument('section', nargs='?', help='Configuration section to show')
    
    # Set command
    set_parser = subparsers.add_parser('set', help='Set configuration value')
    set_parser.add_argument('key', help='Configuration key (e.g., openai.api_key)')
    set_parser.add_argument('value', help='Configuration value')
    
    # Create default command
    create_parser = subparsers.add_parser('create-default', help='Create default configuration')
    create_parser.add_argument('output_file', type=Path, help='Output file path')
    create_parser.add_argument('--yaml', action='store_true', help='Create as YAML instead of JSON')
    
    # Check environment command
    subparsers.add_parser('check-env', help='Check environment variables')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    success = False
    
    try:
        if args.command == 'validate':
            success = validate_config(args.config)
        
        elif args.command == 'export':
            format_type = "yaml" if args.yaml else "json"
            success = export_config(args.output_file, format_type)
        
        elif args.command == 'import':
            success = import_config(args.input_file)
        
        elif args.command == 'show':
            success = show_config(args.section)
        
        elif args.command == 'set':
            success = set_config_value(args.key, args.value)
        
        elif args.command == 'create-default':
            format_type = "yaml" if args.yaml else "json"
            success = create_default_config(args.output_file, format_type)
        
        elif args.command == 'check-env':
            success = check_environment()
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
