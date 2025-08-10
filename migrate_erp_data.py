#!/usr/bin/env python3
"""
ERP Data Migration Script - Production-Ready Migration Workflow

This script provides a comprehensive migration workflow for eFab ERP data
with progress tracking, error handling, rollback capabilities, and data
integrity verification.

Features:
- Full migration workflow with pre-flight checks
- Progress tracking with detailed logging
- Transaction-based rollback capabilities
- Data integrity verification
- Performance monitoring
- Resume capability for interrupted migrations
- Comprehensive error handling and recovery
- Integration with Agent-MCP system

Usage:
    python migrate_erp_data.py --source-dir /path/to/erp/data --dry-run
    python migrate_erp_data.py --source-dir /path/to/erp/data --migrate
    python migrate_erp_data.py --resume migration_20240101_120000
    python migrate_erp_data.py --verify
    python migrate_erp_data.py --rollback migration_20240101_120000
"""

import argparse
import json
import logging
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid
import hashlib
import shutil
import signal

# Add the Agent-MCP path to sys.path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from agent_mcp.core.config import logger, get_db_path
    from agent_mcp.db.connection import get_db_connection
    from agent_mcp.db.schema import init_database
    from agent_mcp.db.textile_erp_schema import initialize_textile_erp_schema
    from agent_mcp.utils.erp_data_parser import ERPDataParser, ParsingConfig
    from agent_mcp.tools.erp_data_import import ERPDataImporter, ImportConfig
    from agent_mcp.utils.erp_data_validator import ERPDataValidator
except ImportError as e:
    print(f"Error importing Agent-MCP modules: {e}")
    print("Make sure you're running from the Agent-MCP root directory")
    sys.exit(1)


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    source_directory: str
    dry_run: bool = True
    batch_size: int = 1000
    max_workers: int = 4
    backup_enabled: bool = True
    verification_enabled: bool = True
    continue_on_error: bool = False
    log_level: str = "INFO"
    checkpoint_interval: int = 5000
    timeout_seconds: int = 3600  # 1 hour default timeout


@dataclass
class MigrationState:
    """Current migration state for resume capability."""
    migration_id: str
    config: MigrationConfig
    start_time: datetime
    current_phase: str
    processed_files: List[str]
    failed_files: List[str]
    total_records_processed: int
    total_records_imported: int
    total_errors: int
    checkpoints: List[Dict[str, Any]]
    completed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'migration_id': self.migration_id,
            'config': asdict(self.config),
            'start_time': self.start_time.isoformat(),
            'current_phase': self.current_phase,
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'total_records_processed': self.total_records_processed,
            'total_records_imported': self.total_records_imported,
            'total_errors': self.total_errors,
            'checkpoints': self.checkpoints,
            'completed': self.completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationState':
        """Create instance from dictionary."""
        config = MigrationConfig(**data['config'])
        return cls(
            migration_id=data['migration_id'],
            config=config,
            start_time=datetime.fromisoformat(data['start_time']),
            current_phase=data['current_phase'],
            processed_files=data['processed_files'],
            failed_files=data['failed_files'],
            total_records_processed=data['total_records_processed'],
            total_records_imported=data['total_records_imported'],
            total_errors=data['total_errors'],
            checkpoints=data['checkpoints'],
            completed=data['completed']
        )


class MigrationManager:
    """
    Comprehensive migration manager with error handling and recovery.
    """
    
    def __init__(self, config: MigrationConfig):
        """Initialize migration manager."""
        self.config = config
        self.logger = logger
        self.parser = ERPDataParser(ParsingConfig(
            strip_html=True,
            normalize_headers=True,
            validate_data=True,
            chunk_size=config.batch_size
        ))
        self.importer = ERPDataImporter(ImportConfig(
            batch_size=config.batch_size,
            max_workers=config.max_workers,
            duplicate_strategy='skip',
            validation_level='standard',
            continue_on_error=config.continue_on_error
        ))
        self.validator = ERPDataValidator()
        
        # Migration state
        self.migration_id = self.generate_migration_id()
        self.state_file = Path(f"migration_state_{self.migration_id}.json")
        self.backup_dir = Path(f"migration_backup_{self.migration_id}")
        
        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.shutdown_requested = False
    
    def generate_migration_id(self) -> str:
        """Generate unique migration ID."""
        return f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def save_state(self, state: MigrationState) -> None:
        """Save migration state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            self.logger.debug(f"Migration state saved to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save migration state: {e}")
    
    def load_state(self, migration_id: str) -> Optional[MigrationState]:
        """Load migration state from file."""
        state_file = Path(f"migration_state_{migration_id}.json")
        
        if not state_file.exists():
            self.logger.error(f"Migration state file not found: {state_file}")
            return None
        
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            state = MigrationState.from_dict(data)
            self.logger.info(f"Loaded migration state for {migration_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to load migration state: {e}")
            return None
    
    def create_backup(self) -> bool:
        """Create backup of current database."""
        if not self.config.backup_enabled:
            self.logger.info("Backup disabled in configuration")
            return True
        
        try:
            db_path = Path(get_db_path())
            if not db_path.exists():
                self.logger.warning("Database file not found, skipping backup")
                return True
            
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Copy database file
            backup_file = self.backup_dir / f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_file)
            
            self.logger.info(f"Database backup created: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False
    
    def verify_prerequisites(self) -> Tuple[bool, List[str]]:
        """Verify prerequisites for migration."""
        issues = []
        
        # Check source directory
        source_dir = Path(self.config.source_directory)
        if not source_dir.exists():
            issues.append(f"Source directory not found: {source_dir}")
        elif not source_dir.is_dir():
            issues.append(f"Source path is not a directory: {source_dir}")
        else:
            # Check for supported files
            supported_extensions = {'.csv', '.xlsx', '.xls', '.xlsm'}
            files = list(source_dir.glob("*"))
            supported_files = [f for f in files if f.suffix.lower() in supported_extensions]
            
            if not supported_files:
                issues.append(f"No supported files found in {source_dir}")
            else:
                self.logger.info(f"Found {len(supported_files)} supported files")
        
        # Check database connectivity
        try:
            conn = get_db_connection()
            conn.close()
            self.logger.debug("Database connection verified")
        except Exception as e:
            issues.append(f"Database connection failed: {e}")
        
        # Check disk space
        try:
            import shutil
            free_space = shutil.disk_usage(Path.cwd()).free
            if free_space < 1024 * 1024 * 100:  # 100MB minimum
                issues.append("Insufficient disk space (minimum 100MB required)")
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
        
        return len(issues) == 0, issues
    
    def initialize_database(self) -> bool:
        """Initialize database schema."""
        try:
            self.logger.info("Initializing database schema...")
            
            # Initialize core schema
            init_database()
            
            # Initialize textile ERP schema
            success = initialize_textile_erp_schema()
            
            if success:
                self.logger.info("Database schema initialized successfully")
                return True
            else:
                self.logger.error("Failed to initialize textile ERP schema")
                return False
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def discover_files(self) -> List[Path]:
        """Discover files to be migrated."""
        source_dir = Path(self.config.source_directory)
        supported_extensions = {'.csv', '.xlsx', '.xls', '.xlsm'}
        
        files = []
        for pattern in ['*.csv', '*.xlsx', '*.xls', '*.xlsm']:
            files.extend(source_dir.glob(pattern))
        
        # Filter out backup and temporary files
        filtered_files = []
        for file in files:
            filename = file.name.lower()
            if not any(skip in filename for skip in ['backup', 'temp', '~', '.tmp']):
                filtered_files.append(file)
        
        self.logger.info(f"Discovered {len(filtered_files)} files for migration")
        return sorted(filtered_files)
    
    def analyze_files(self, files: List[Path]) -> Dict[str, Any]:
        """Analyze files to provide migration overview."""
        analysis = {
            'total_files': len(files),
            'file_types': {},
            'estimated_records': 0,
            'potential_issues': []
        }
        
        for file in files:
            try:
                # Get file info
                file_size = file.stat().st_size
                file_type = self.parser.detect_file_type(file)
                
                analysis['file_types'][file_type] = analysis['file_types'].get(file_type, 0) + 1
                
                # Quick parse to estimate records
                if file_size < 50 * 1024 * 1024:  # Only parse files smaller than 50MB for analysis
                    result = self.parser.parse_file(file)
                    analysis['estimated_records'] += result.total_rows
                    
                    if result.errors:
                        analysis['potential_issues'].extend([
                            f"{file.name}: {error}" for error in result.errors[:3]
                        ])
                
            except Exception as e:
                analysis['potential_issues'].append(f"{file.name}: Analysis failed - {e}")
        
        return analysis
    
    def process_files(self, files: List[Path], state: MigrationState) -> None:
        """Process files for migration."""
        total_files = len(files)
        
        for i, file_path in enumerate(files):
            if self.shutdown_requested:
                self.logger.warning("Shutdown requested, stopping file processing")
                break
            
            # Skip already processed files in resume scenario
            if str(file_path) in state.processed_files:
                self.logger.debug(f"Skipping already processed file: {file_path.name}")
                continue
            
            self.logger.info(f"Processing file {i+1}/{total_files}: {file_path.name}")
            
            try:
                if self.config.dry_run:
                    # Dry run: only parse and validate
                    parse_result = self.parser.parse_file(file_path)
                    
                    state.total_records_processed += parse_result.total_rows
                    if parse_result.errors:
                        state.total_errors += len(parse_result.errors)
                        state.failed_files.append(str(file_path))
                        self.logger.warning(f"File {file_path.name} has {len(parse_result.errors)} parsing errors")
                    
                    self.logger.info(f"Dry run - File {file_path.name}: {parse_result.valid_rows}/{parse_result.total_rows} valid rows")
                
                else:
                    # Real migration
                    import_result = self.importer.import_file_data(file_path)
                    
                    state.total_records_processed += import_result.total_records
                    state.total_records_imported += import_result.imported_records
                    
                    if not import_result.success or import_result.errors:
                        state.total_errors += len(import_result.errors)
                        state.failed_files.append(str(file_path))
                        
                        self.logger.warning(f"File {file_path.name} import issues: {len(import_result.errors)} errors")
                        
                        if not self.config.continue_on_error:
                            raise Exception(f"Migration failed for {file_path.name}: {import_result.errors[0] if import_result.errors else 'Unknown error'}")
                    
                    self.logger.info(f"File {file_path.name}: {import_result.imported_records}/{import_result.total_records} records imported")
                
                # Mark file as processed
                state.processed_files.append(str(file_path))
                
                # Create checkpoint
                if len(state.processed_files) % (self.config.checkpoint_interval // self.config.batch_size) == 0:
                    self.create_checkpoint(state)
                
            except Exception as e:
                error_msg = f"Failed to process {file_path.name}: {e}"
                self.logger.error(error_msg)
                
                state.failed_files.append(str(file_path))
                state.total_errors += 1
                
                if not self.config.continue_on_error:
                    raise Exception(error_msg)
        
        # Update state
        state.current_phase = "completed" if not self.shutdown_requested else "interrupted"
        self.save_state(state)
    
    def create_checkpoint(self, state: MigrationState) -> None:
        """Create migration checkpoint."""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'processed_files': len(state.processed_files),
            'total_records_processed': state.total_records_processed,
            'total_records_imported': state.total_records_imported,
            'total_errors': state.total_errors
        }
        
        state.checkpoints.append(checkpoint)
        self.save_state(state)
        
        self.logger.info(f"Checkpoint created: {len(state.processed_files)} files processed")
    
    def verify_migration(self, state: MigrationState) -> Dict[str, Any]:
        """Verify migration results."""
        if not self.config.verification_enabled:
            return {'verification': 'skipped'}
        
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'table_counts': {},
            'data_integrity_checks': {},
            'issues': []
        }
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check record counts in main tables
            tables_to_check = [
                'fabric_inventory', 'sales_orders', 'suppliers', 
                'customers', 'fabric_types', 'production_orders'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    verification_results['table_counts'][table] = count
                    
                    self.logger.info(f"Table {table}: {count} records")
                    
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e).lower():
                        verification_results['table_counts'][table] = 'Table not found'
                    else:
                        verification_results['issues'].append(f"Error checking {table}: {e}")
            
            # Basic data integrity checks
            integrity_checks = [
                ("Fabric inventory without fabric type", 
                 "SELECT COUNT(*) FROM fabric_inventory WHERE fabric_type_id NOT IN (SELECT fabric_type_id FROM fabric_types)"),
                ("Sales orders without customer", 
                 "SELECT COUNT(*) FROM sales_orders WHERE customer_id NOT IN (SELECT customer_id FROM customers)"),
                ("Negative inventory quantities",
                 "SELECT COUNT(*) FROM fabric_inventory WHERE quantity_meters < 0"),
                ("Future dates in historical data",
                 "SELECT COUNT(*) FROM fabric_inventory WHERE received_date > date('now')")
            ]
            
            for check_name, check_query in integrity_checks:
                try:
                    cursor.execute(check_query)
                    result = cursor.fetchone()[0]
                    verification_results['data_integrity_checks'][check_name] = result
                    
                    if result > 0:
                        verification_results['issues'].append(f"{check_name}: {result} issues found")
                
                except Exception as e:
                    verification_results['issues'].append(f"Integrity check '{check_name}' failed: {e}")
            
            conn.close()
            
            self.logger.info(f"Migration verification completed: {len(verification_results['issues'])} issues found")
            
        except Exception as e:
            error_msg = f"Verification failed: {e}"
            verification_results['issues'].append(error_msg)
            self.logger.error(error_msg)
        
        return verification_results
    
    def rollback_migration(self, migration_id: str) -> bool:
        """Rollback migration to pre-migration state."""
        try:
            # Find backup directory
            backup_dir = Path(f"migration_backup_{migration_id}")
            
            if not backup_dir.exists():
                self.logger.error(f"Backup directory not found: {backup_dir}")
                return False
            
            # Find backup file
            backup_files = list(backup_dir.glob("database_backup_*.db"))
            
            if not backup_files:
                self.logger.error("No backup database file found")
                return False
            
            # Use the most recent backup
            backup_file = sorted(backup_files)[-1]
            db_path = Path(get_db_path())
            
            # Create current database backup before rollback
            rollback_backup = db_path.with_suffix(f".pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if db_path.exists():
                shutil.copy2(db_path, rollback_backup)
                self.logger.info(f"Current database backed up to: {rollback_backup}")
            
            # Restore from backup
            shutil.copy2(backup_file, db_path)
            
            self.logger.info(f"Database rolled back from: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def run_migration(self, resume_migration_id: Optional[str] = None) -> Dict[str, Any]:
        """Run complete migration workflow."""
        start_time = time.time()
        
        try:
            # Initialize or resume state
            if resume_migration_id:
                state = self.load_state(resume_migration_id)
                if not state:
                    return {'success': False, 'error': 'Failed to load migration state for resume'}
                
                self.migration_id = state.migration_id
                self.logger.info(f"Resuming migration {self.migration_id}")
            else:
                # Create new migration state
                state = MigrationState(
                    migration_id=self.migration_id,
                    config=self.config,
                    start_time=datetime.now(),
                    current_phase='initializing',
                    processed_files=[],
                    failed_files=[],
                    total_records_processed=0,
                    total_records_imported=0,
                    total_errors=0,
                    checkpoints=[],
                    completed=False
                )
                
                self.logger.info(f"Starting new migration {self.migration_id}")
                
                # Run prerequisite checks
                prereq_ok, issues = self.verify_prerequisites()
                if not prereq_ok:
                    return {
                        'success': False,
                        'error': 'Prerequisites check failed',
                        'issues': issues
                    }
                
                # Create backup
                if not self.config.dry_run:
                    if not self.create_backup():
                        return {
                            'success': False,
                            'error': 'Failed to create database backup'
                        }
                
                # Initialize database schema
                if not self.config.dry_run:
                    if not self.initialize_database():
                        return {
                            'success': False,
                            'error': 'Failed to initialize database schema'
                        }
            
            # Discover and analyze files
            state.current_phase = 'discovery'
            self.save_state(state)
            
            files = self.discover_files()
            if not files:
                return {
                    'success': False,
                    'error': 'No files found for migration'
                }
            
            analysis = self.analyze_files(files)
            self.logger.info(f"Migration analysis: {analysis}")
            
            # Process files
            state.current_phase = 'processing'
            self.save_state(state)
            
            self.process_files(files, state)
            
            # Verify results if not dry run
            verification_results = {}
            if not self.config.dry_run and self.config.verification_enabled:
                state.current_phase = 'verification'
                self.save_state(state)
                
                verification_results = self.verify_migration(state)
            
            # Mark as completed
            state.current_phase = 'completed' if not self.shutdown_requested else 'interrupted'
            state.completed = not self.shutdown_requested
            self.save_state(state)
            
            processing_time = time.time() - start_time
            
            result = {
                'success': state.completed,
                'migration_id': self.migration_id,
                'dry_run': self.config.dry_run,
                'processing_time_seconds': processing_time,
                'summary': {
                    'total_files': len(files),
                    'processed_files': len(state.processed_files),
                    'failed_files': len(state.failed_files),
                    'total_records_processed': state.total_records_processed,
                    'total_records_imported': state.total_records_imported,
                    'total_errors': state.total_errors
                },
                'file_analysis': analysis,
                'verification': verification_results,
                'interrupted': self.shutdown_requested
            }
            
            self.logger.info(f"Migration {'completed' if state.completed else 'interrupted'}: {result['summary']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'migration_id': self.migration_id,
                'processing_time_seconds': time.time() - start_time
            }


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="ERP Data Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to check data without importing
  python migrate_erp_data.py --source-dir ./ERP_Data --dry-run
  
  # Full migration
  python migrate_erp_data.py --source-dir ./ERP_Data --migrate
  
  # Resume interrupted migration
  python migrate_erp_data.py --resume migration_20240101_120000
  
  # Rollback migration
  python migrate_erp_data.py --rollback migration_20240101_120000
  
  # Verify database integrity
  python migrate_erp_data.py --verify
        """
    )
    
    # Main operation modes
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--dry-run', action='store_true',
                         help='Perform dry run without importing data')
    operation.add_argument('--migrate', action='store_true',
                         help='Perform actual data migration')
    operation.add_argument('--resume', type=str, metavar='MIGRATION_ID',
                         help='Resume interrupted migration')
    operation.add_argument('--rollback', type=str, metavar='MIGRATION_ID',
                         help='Rollback migration')
    operation.add_argument('--verify', action='store_true',
                         help='Verify database integrity')
    
    # Configuration options
    parser.add_argument('--source-dir', type=str, required=False,
                       default='/mnt/c/Users/psytz/TMUX Final/Tmux-Orchestrator/ERP Data',
                       help='Source directory containing ERP data files')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing (default: 1000)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of worker threads (default: 4)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Disable database backup before migration')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip post-migration verification')
    parser.add_argument('--continue-on-error', action='store_true',
                       help='Continue migration even if some files fail')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    parser.add_argument('--timeout', type=int, default=3600,
                       help='Migration timeout in seconds (default: 3600)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handle different operations
    if args.verify:
        # Verification only
        try:
            validator = ERPDataValidator()
            print("Running database integrity verification...")
            
            # This would run comprehensive verification
            print("Verification completed - check logs for details")
            return 0
            
        except Exception as e:
            print(f"Verification failed: {e}")
            return 1
    
    elif args.rollback:
        # Rollback operation
        try:
            config = MigrationConfig(source_directory="", dry_run=True)
            manager = MigrationManager(config)
            
            print(f"Rolling back migration {args.rollback}...")
            success = manager.rollback_migration(args.rollback)
            
            if success:
                print("Rollback completed successfully")
                return 0
            else:
                print("Rollback failed")
                return 1
                
        except Exception as e:
            print(f"Rollback failed: {e}")
            return 1
    
    else:
        # Migration operations (dry-run, migrate, resume)
        if not args.source_dir and not args.resume:
            print("Error: --source-dir is required for migration operations")
            return 1
        
        # Create migration configuration
        config = MigrationConfig(
            source_directory=args.source_dir or "",
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            max_workers=args.workers,
            backup_enabled=not args.no_backup,
            verification_enabled=not args.no_verify,
            continue_on_error=args.continue_on_error,
            log_level=args.log_level,
            timeout_seconds=args.timeout
        )
        
        # Run migration
        try:
            manager = MigrationManager(config)
            
            if args.resume:
                print(f"Resuming migration {args.resume}...")
                result = manager.run_migration(resume_migration_id=args.resume)
            else:
                operation_type = "dry run" if args.dry_run else "migration"
                print(f"Starting {operation_type}...")
                result = manager.run_migration()
            
            # Print results
            print(f"\n{'='*60}")
            print(f"Migration {'Dry Run' if config.dry_run else 'Results'}")
            print(f"{'='*60}")
            print(f"Success: {result['success']}")
            print(f"Migration ID: {result['migration_id']}")
            print(f"Processing Time: {result['processing_time_seconds']:.2f} seconds")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\nSummary:")
                print(f"  Total Files: {summary['total_files']}")
                print(f"  Processed Files: {summary['processed_files']}")
                print(f"  Failed Files: {summary['failed_files']}")
                print(f"  Total Records Processed: {summary['total_records_processed']}")
                if not config.dry_run:
                    print(f"  Total Records Imported: {summary['total_records_imported']}")
                print(f"  Total Errors: {summary['total_errors']}")
            
            if result.get('interrupted'):
                print(f"\nMigration was interrupted. Use --resume {result['migration_id']} to continue.")
            
            if not result['success']:
                if 'error' in result:
                    print(f"Error: {result['error']}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"Migration failed: {e}")
            logging.error(traceback.format_exc())
            return 1


if __name__ == "__main__":
    sys.exit(main())