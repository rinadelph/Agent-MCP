"""
ERP Data Import Module - MCP Tools for Production-Ready Data Integration

This module provides MCP (Model Context Protocol) tools for importing eFab ERP data
into the textile ERP schema with comprehensive error handling, transaction management,
duplicate detection, and batch processing capabilities.

Features:
- MCP tools for Agent-MCP integration
- Batch import with progress tracking
- Transaction management and rollback
- Duplicate detection and handling
- Data mapping to textile_erp schema
- Comprehensive logging and error handling
- Memory-efficient processing for large datasets
- Data quality validation during import
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from ..core.config import logger
from ..db.connection import get_db_connection
from ..utils.erp_data_parser import ERPDataParser, ParsingConfig, ParseResult
from ..utils.erp_data_validator import ERPDataValidator, ValidationResult


@dataclass
class ImportResult:
    """Result of data import operation."""
    import_id: str
    file_path: str
    file_type: str
    total_records: int
    imported_records: int
    skipped_records: int
    error_records: int
    duplicate_records: int
    processing_time_seconds: float
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    success: bool


@dataclass
class ImportConfig:
    """Configuration for import operations."""
    batch_size: int = 1000
    max_workers: int = 4
    duplicate_strategy: str = 'skip'  # 'skip', 'update', 'error'
    validation_level: str = 'standard'  # 'minimal', 'standard', 'strict'
    transaction_size: int = 5000
    continue_on_error: bool = True
    create_backup: bool = True
    log_level: str = 'INFO'


class ERPDataImporter:
    """
    Production-ready ERP data importer with comprehensive error handling,
    transaction management, and MCP tool integration.
    """
    
    # Table mappings for different file types
    TABLE_MAPPINGS = {
        'inventory': 'fabric_inventory',
        'sales_orders': 'sales_orders',
        'yarn_demand': 'yarn_inventory',  # Custom mapping for yarn data
        'yarn_report': 'production_orders'  # Expected yarn reports to production planning
    }
    
    # Field mappings to database schema
    SCHEMA_MAPPINGS = {
        'fabric_inventory': {
            'style_number': 'fabric_type_id',
            'order_number': 'lot_number',
            'customer_name': 'supplier_id',  # Map to supplier lookup
            'roll_number': 'inventory_id',
            'vendor_roll_number': 'lot_number',
            'rack_location': 'location_bin',
            'quantity_yards': 'quantity_meters',
            'quantity_pounds': 'actual_weight_gsm',
            'received_date': 'received_date'
        },
        'sales_orders': {
            'order_status': 'status',
            'customer_service_rep': 'sales_rep_id',
            'unit_price': 'total_value',
            'quote_date': 'order_date',
            'quantity_ordered': 'total_pieces',
            'quantity_shipped': 'shipped_quantity',
            'purchase_order_number': 'order_number',
            'sold_to_customer': 'customer_id',
            'ship_date': 'promised_delivery_date'
        },
        'yarn_inventory': {
            'yarn_id': 'fabric_type_id',
            'supplier_name': 'supplier_id',
            'yarn_description': 'fabric_name',
            'color_code': 'color_code',
            'current_inventory': 'quantity_meters',
            'total_demand': 'reserved_meters'
        }
    }
    
    def __init__(self, config: Optional[ImportConfig] = None):
        """Initialize importer with configuration."""
        self.config = config or ImportConfig()
        self.logger = logger
        self.parser = ERPDataParser(ParsingConfig(
            strip_html=True,
            normalize_headers=True,
            validate_data=True
        ))
        self.validator = ERPDataValidator()
        
    def generate_import_id(self) -> str:
        """Generate unique import ID."""
        return f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def create_data_hash(self, data: Dict[str, Any]) -> str:
        """Create hash for duplicate detection."""
        # Create a consistent string representation for hashing
        sorted_items = sorted(data.items())
        data_string = json.dumps(sorted_items, sort_keys=True, default=str)
        return hashlib.md5(data_string.encode()).hexdigest()
    
    def map_data_to_schema(self, data: Dict[str, Any], file_type: str, table_name: str) -> Dict[str, Any]:
        """
        Map parsed data to database schema fields.
        
        Args:
            data: Parsed data dictionary
            file_type: Type of source file
            table_name: Target database table
            
        Returns:
            Dictionary mapped to database schema
        """
        schema_mapping = self.SCHEMA_MAPPINGS.get(table_name, {})
        mapped_data = {}
        
        for source_field, value in data.items():
            target_field = schema_mapping.get(source_field, source_field)
            
            # Handle special mappings
            if target_field == 'supplier_id' and isinstance(value, str):
                # Look up or create supplier ID
                supplier_id = self.get_or_create_supplier(value)
                mapped_data[target_field] = supplier_id
            elif target_field == 'customer_id' and isinstance(value, str):
                # Look up or create customer ID
                customer_id = self.get_or_create_customer(value)
                mapped_data[target_field] = customer_id
            elif target_field == 'fabric_type_id' and isinstance(value, str):
                # Look up or create fabric type ID
                fabric_type_id = self.get_or_create_fabric_type(value)
                mapped_data[target_field] = fabric_type_id
            else:
                mapped_data[target_field] = value
        
        # Add required fields with defaults
        mapped_data.setdefault('created_at', datetime.now().isoformat())
        mapped_data.setdefault('updated_at', datetime.now().isoformat())
        
        return mapped_data
    
    def get_or_create_supplier(self, supplier_name: str) -> str:
        """Get existing supplier ID or create new supplier."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clean supplier name
            clean_name = supplier_name.strip()[:100]  # Limit length
            
            # Check if supplier exists
            cursor.execute("SELECT supplier_id FROM suppliers WHERE company_name = ?", (clean_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new supplier
            supplier_id = f"SUP_{uuid.uuid4().hex[:8].upper()}"
            supplier_code = f"AUTO_{len(clean_name):03d}_{uuid.uuid4().hex[:4].upper()}"
            
            cursor.execute("""
                INSERT INTO suppliers (
                    supplier_id, supplier_code, company_name, supplier_type,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier_id, supplier_code, clean_name, 'FABRIC',
                'ACTIVE', datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            self.logger.debug(f"Created new supplier: {supplier_id} - {clean_name}")
            return supplier_id
            
        except Exception as e:
            self.logger.error(f"Error handling supplier '{supplier_name}': {e}")
            if conn:
                conn.rollback()
            # Return a default supplier ID
            return "SUP_UNKNOWN"
        finally:
            if conn:
                conn.close()
    
    def get_or_create_customer(self, customer_name: str) -> str:
        """Get existing customer ID or create new customer."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clean customer name
            clean_name = customer_name.strip()[:100]
            
            # Check if customer exists
            cursor.execute("SELECT customer_id FROM customers WHERE company_name = ?", (clean_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new customer
            customer_id = f"CUST_{uuid.uuid4().hex[:8].upper()}"
            customer_code = f"AUTO_{len(clean_name):03d}_{uuid.uuid4().hex[:4].upper()}"
            
            cursor.execute("""
                INSERT INTO customers (
                    customer_id, customer_code, company_name, customer_type,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, customer_code, clean_name, 'WHOLESALE',
                'ACTIVE', datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            self.logger.debug(f"Created new customer: {customer_id} - {clean_name}")
            return customer_id
            
        except Exception as e:
            self.logger.error(f"Error handling customer '{customer_name}': {e}")
            if conn:
                conn.rollback()
            # Return a default customer ID
            return "CUST_UNKNOWN"
        finally:
            if conn:
                conn.close()
    
    def get_or_create_fabric_type(self, fabric_info: str) -> str:
        """Get existing fabric type ID or create new fabric type."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clean fabric info
            clean_info = fabric_info.strip()[:100]
            
            # Check if fabric type exists
            cursor.execute("SELECT fabric_type_id FROM fabric_types WHERE fabric_name = ?", (clean_info,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new fabric type
            fabric_type_id = f"FAB_{uuid.uuid4().hex[:8].upper()}"
            
            cursor.execute("""
                INSERT INTO fabric_types (
                    fabric_type_id, fabric_name, fabric_category,
                    active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                fabric_type_id, clean_info, 'UNKNOWN',
                1, datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            self.logger.debug(f"Created new fabric type: {fabric_type_id} - {clean_info}")
            return fabric_type_id
            
        except Exception as e:
            self.logger.error(f"Error handling fabric type '{fabric_info}': {e}")
            if conn:
                conn.rollback()
            # Return a default fabric type ID
            return "FAB_UNKNOWN"
        finally:
            if conn:
                conn.close()
    
    def check_duplicate(self, data: Dict[str, Any], table_name: str) -> Optional[str]:
        """
        Check if record already exists based on key fields.
        
        Args:
            data: Data to check
            table_name: Target table name
            
        Returns:
            Existing record ID if duplicate found, None otherwise
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Define unique key fields for each table
            key_fields = {
                'fabric_inventory': ['inventory_id'],
                'sales_orders': ['order_number'],
                'yarn_inventory': ['fabric_type_id', 'supplier_id'],
                'production_orders': ['order_id']
            }
            
            table_keys = key_fields.get(table_name, [])
            if not table_keys:
                return None
            
            # Build WHERE clause
            conditions = []
            values = []
            
            for key_field in table_keys:
                if key_field in data and data[key_field] is not None:
                    conditions.append(f"{key_field} = ?")
                    values.append(data[key_field])
            
            if not conditions:
                return None
            
            where_clause = " AND ".join(conditions)
            
            # Check for existing record
            if table_name == 'fabric_inventory':
                cursor.execute(f"SELECT inventory_id FROM {table_name} WHERE {where_clause}", values)
            elif table_name == 'sales_orders':
                cursor.execute(f"SELECT order_id FROM {table_name} WHERE {where_clause}", values)
            else:
                cursor.execute(f"SELECT * FROM {table_name} WHERE {where_clause} LIMIT 1", values)
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            self.logger.error(f"Error checking duplicates in {table_name}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def insert_batch_data(self, batch_data: List[Dict[str, Any]], table_name: str) -> Tuple[int, int, List[str]]:
        """
        Insert batch of data into database with transaction management.
        
        Args:
            batch_data: List of data dictionaries
            table_name: Target table name
            
        Returns:
            Tuple of (inserted_count, skipped_count, errors)
        """
        conn = None
        inserted_count = 0
        skipped_count = 0
        errors = []
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            for record in batch_data:
                try:
                    # Check for duplicates
                    existing_id = self.check_duplicate(record, table_name)
                    
                    if existing_id:
                        if self.config.duplicate_strategy == 'skip':
                            skipped_count += 1
                            continue
                        elif self.config.duplicate_strategy == 'error':
                            errors.append(f"Duplicate record found: {existing_id}")
                            continue
                        elif self.config.duplicate_strategy == 'update':
                            # Perform update instead of insert
                            self.update_existing_record(cursor, record, table_name, existing_id)
                            inserted_count += 1
                            continue
                    
                    # Insert new record
                    self.insert_single_record(cursor, record, table_name)
                    inserted_count += 1
                    
                except Exception as e:
                    error_msg = f"Error inserting record: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
                    
                    if not self.config.continue_on_error:
                        raise
            
            # Commit transaction
            conn.commit()
            
        except Exception as e:
            error_msg = f"Batch insert failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return inserted_count, skipped_count, errors
    
    def insert_single_record(self, cursor: sqlite3.Cursor, data: Dict[str, Any], table_name: str) -> None:
        """Insert a single record into the database."""
        # Get column names from the table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Filter data to only include valid columns
        filtered_data = {k: v for k, v in data.items() if k in columns}
        
        if not filtered_data:
            raise ValueError("No valid columns found for insertion")
        
        # Build INSERT statement
        column_names = list(filtered_data.keys())
        placeholders = ['?' for _ in column_names]
        values = list(filtered_data.values())
        
        sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(sql, values)
    
    def update_existing_record(self, cursor: sqlite3.Cursor, data: Dict[str, Any], table_name: str, record_id: str) -> None:
        """Update existing record in the database."""
        # Get column names from the table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Filter data to only include valid columns (exclude ID columns)
        id_columns = ['inventory_id', 'order_id', 'fabric_type_id']
        filtered_data = {k: v for k, v in data.items() if k in columns and k not in id_columns}
        
        if not filtered_data:
            raise ValueError("No valid columns found for update")
        
        # Add updated timestamp
        filtered_data['updated_at'] = datetime.now().isoformat()
        
        # Build UPDATE statement
        set_clauses = [f"{k} = ?" for k in filtered_data.keys()]
        values = list(filtered_data.values())
        
        # Determine the primary key column
        primary_key = 'inventory_id' if table_name == 'fabric_inventory' else 'order_id'
        
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {primary_key} = ?"
        values.append(record_id)
        
        cursor.execute(sql, values)
    
    def import_file_data(self, file_path: Union[str, Path], file_type: Optional[str] = None) -> ImportResult:
        """
        Import data from a single file with comprehensive error handling.
        
        Args:
            file_path: Path to the file to import
            file_type: Override file type detection
            
        Returns:
            ImportResult with detailed operation results
        """
        start_time = time.time()
        import_id = self.generate_import_id()
        file_path = Path(file_path)
        
        self.logger.info(f"Starting import {import_id} for file: {file_path}")
        
        # Parse the file
        try:
            parse_result = self.parser.parse_file(file_path)
            
            if not parse_result.data:
                return ImportResult(
                    import_id=import_id,
                    file_path=str(file_path),
                    file_type=parse_result.metadata.get('file_type', 'unknown'),
                    total_records=0,
                    imported_records=0,
                    skipped_records=0,
                    error_records=0,
                    duplicate_records=0,
                    processing_time_seconds=time.time() - start_time,
                    errors=parse_result.errors or ["No data found in file"],
                    warnings=parse_result.warnings,
                    metadata=parse_result.metadata,
                    success=False
                )
                
        except Exception as e:
            error_msg = f"File parsing failed: {e}"
            self.logger.error(error_msg)
            return ImportResult(
                import_id=import_id,
                file_path=str(file_path),
                file_type=file_type or 'unknown',
                total_records=0,
                imported_records=0,
                skipped_records=0,
                error_records=1,
                duplicate_records=0,
                processing_time_seconds=time.time() - start_time,
                errors=[error_msg],
                warnings=[],
                metadata={},
                success=False
            )
        
        # Determine target table
        detected_file_type = file_type or parse_result.metadata.get('file_type', 'unknown')
        table_name = self.TABLE_MAPPINGS.get(detected_file_type)
        
        if not table_name:
            error_msg = f"Unknown file type: {detected_file_type}"
            self.logger.error(error_msg)
            return ImportResult(
                import_id=import_id,
                file_path=str(file_path),
                file_type=detected_file_type,
                total_records=len(parse_result.data),
                imported_records=0,
                skipped_records=0,
                error_records=len(parse_result.data),
                duplicate_records=0,
                processing_time_seconds=time.time() - start_time,
                errors=[error_msg],
                warnings=parse_result.warnings,
                metadata=parse_result.metadata,
                success=False
            )
        
        # Process data in batches
        total_records = len(parse_result.data)
        imported_records = 0
        skipped_records = 0
        error_records = 0
        duplicate_records = 0
        all_errors = list(parse_result.errors)
        all_warnings = list(parse_result.warnings)
        
        try:
            # Process data in batches
            for i in range(0, total_records, self.config.batch_size):
                batch = parse_result.data[i:i + self.config.batch_size]
                
                # Map data to schema
                mapped_batch = []
                for record in batch:
                    try:
                        mapped_record = self.map_data_to_schema(record, detected_file_type, table_name)
                        
                        # Validate mapped data
                        if self.config.validation_level != 'minimal':
                            validation_result = self.validator.validate_record(mapped_record, table_name)
                            if not validation_result.is_valid:
                                if self.config.validation_level == 'strict':
                                    error_records += 1
                                    all_errors.extend(validation_result.errors)
                                    continue
                                else:
                                    all_warnings.extend(validation_result.warnings)
                        
                        mapped_batch.append(mapped_record)
                        
                    except Exception as e:
                        error_msg = f"Data mapping failed for record: {e}"
                        all_errors.append(error_msg)
                        error_records += 1
                        
                        if not self.config.continue_on_error:
                            raise
                
                # Insert batch
                if mapped_batch:
                    batch_inserted, batch_skipped, batch_errors = self.insert_batch_data(
                        mapped_batch, table_name
                    )
                    
                    imported_records += batch_inserted
                    skipped_records += batch_skipped
                    all_errors.extend(batch_errors)
                
                # Log progress
                if i > 0 and i % 5000 == 0:
                    self.logger.info(f"Import progress: {i}/{total_records} records processed")
        
        except Exception as e:
            error_msg = f"Import operation failed: {e}"
            self.logger.error(error_msg)
            all_errors.append(error_msg)
        
        processing_time = time.time() - start_time
        success = error_records == 0 and len(all_errors) == 0
        
        self.logger.info(f"Import {import_id} completed: {imported_records}/{total_records} records imported in {processing_time:.2f}s")
        
        return ImportResult(
            import_id=import_id,
            file_path=str(file_path),
            file_type=detected_file_type,
            total_records=total_records,
            imported_records=imported_records,
            skipped_records=skipped_records,
            error_records=error_records,
            duplicate_records=duplicate_records,  # This would need to be calculated during processing
            processing_time_seconds=processing_time,
            errors=all_errors,
            warnings=all_warnings,
            metadata={
                **parse_result.metadata,
                'import_config': asdict(self.config),
                'target_table': table_name
            },
            success=success
        )
    
    def batch_import_directory(self, directory_path: Union[str, Path], file_pattern: str = "*") -> Dict[str, ImportResult]:
        """
        Import all matching files in a directory with parallel processing.
        
        Args:
            directory_path: Path to directory containing files
            file_pattern: Glob pattern for file matching
            
        Returns:
            Dictionary mapping file paths to ImportResult objects
        """
        directory_path = Path(directory_path)
        results = {}
        
        if not directory_path.exists():
            self.logger.error(f"Directory not found: {directory_path}")
            return results
        
        # Find files to import
        matching_files = list(directory_path.glob(file_pattern))
        supported_extensions = {'.csv', '.xlsx', '.xls', '.xlsm'}
        
        files_to_import = [
            f for f in matching_files 
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        self.logger.info(f"Starting batch import of {len(files_to_import)} files from {directory_path}")
        
        # Process files with thread pool
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all jobs
            future_to_file = {
                executor.submit(self.import_file_data, file_path): file_path 
                for file_path in files_to_import
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results[str(file_path)] = result
                    
                    if result.success:
                        self.logger.info(f"Successfully imported {file_path}: {result.imported_records} records")
                    else:
                        self.logger.warning(f"Import failed for {file_path}: {len(result.errors)} errors")
                        
                except Exception as e:
                    error_msg = f"Import failed for {file_path}: {e}"
                    self.logger.error(error_msg)
                    results[str(file_path)] = ImportResult(
                        import_id=self.generate_import_id(),
                        file_path=str(file_path),
                        file_type='unknown',
                        total_records=0,
                        imported_records=0,
                        skipped_records=0,
                        error_records=1,
                        duplicate_records=0,
                        processing_time_seconds=0,
                        errors=[error_msg],
                        warnings=[],
                        metadata={},
                        success=False
                    )
        
        # Log summary
        total_files = len(results)
        successful_files = sum(1 for r in results.values() if r.success)
        total_imported = sum(r.imported_records for r in results.values())
        
        self.logger.info(f"Batch import completed: {successful_files}/{total_files} files successful, {total_imported} total records imported")
        
        return results


# MCP Tool Functions for Agent-MCP Integration

def import_erp_file(file_path: str, file_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    MCP tool to import a single ERP data file.
    
    Args:
        file_path: Path to the file to import
        file_type: Optional file type override
        config: Import configuration dictionary
        
    Returns:
        Import result as dictionary
    """
    try:
        # Create importer with config
        import_config = ImportConfig(**(config or {}))
        importer = ERPDataImporter(import_config)
        
        # Import file
        result = importer.import_file_data(file_path, file_type)
        
        return {
            'success': result.success,
            'import_id': result.import_id,
            'file_path': result.file_path,
            'file_type': result.file_type,
            'total_records': result.total_records,
            'imported_records': result.imported_records,
            'skipped_records': result.skipped_records,
            'error_records': result.error_records,
            'processing_time_seconds': result.processing_time_seconds,
            'errors': result.errors[:10],  # Limit errors for MCP response
            'warnings': result.warnings[:10],  # Limit warnings for MCP response
            'metadata': result.metadata
        }
        
    except Exception as e:
        logger.error(f"MCP import_erp_file failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'import_id': None,
            'total_records': 0,
            'imported_records': 0
        }


def batch_import_erp_directory(directory_path: str, file_pattern: str = "*", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    MCP tool to batch import all ERP files in a directory.
    
    Args:
        directory_path: Path to directory containing files
        file_pattern: Glob pattern for file matching
        config: Import configuration dictionary
        
    Returns:
        Batch import results as dictionary
    """
    try:
        # Create importer with config
        import_config = ImportConfig(**(config or {}))
        importer = ERPDataImporter(import_config)
        
        # Import directory
        results = importer.batch_import_directory(directory_path, file_pattern)
        
        # Summarize results
        total_files = len(results)
        successful_files = sum(1 for r in results.values() if r.success)
        total_records = sum(r.total_records for r in results.values())
        imported_records = sum(r.imported_records for r in results.values())
        
        # Get sample errors/warnings
        all_errors = []
        all_warnings = []
        for result in results.values():
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return {
            'success': successful_files > 0,
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': total_files - successful_files,
            'total_records': total_records,
            'imported_records': imported_records,
            'processing_summary': {
                file_path: {
                    'success': result.success,
                    'imported': result.imported_records,
                    'errors': len(result.errors)
                }
                for file_path, result in results.items()
            },
            'sample_errors': all_errors[:20],
            'sample_warnings': all_warnings[:20]
        }
        
    except Exception as e:
        logger.error(f"MCP batch_import_erp_directory failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_files': 0,
            'successful_files': 0,
            'imported_records': 0
        }


def get_import_status(import_id: Optional[str] = None) -> Dict[str, Any]:
    """
    MCP tool to get import operation status and statistics.
    
    Args:
        import_id: Specific import ID to check (None for general stats)
        
    Returns:
        Import status information
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if import_id:
            # Get specific import status (would need import tracking table)
            return {
                'success': True,
                'import_id': import_id,
                'status': 'completed',  # Would come from tracking table
                'message': 'Import status tracking not yet implemented'
            }
        else:
            # Get general database statistics
            stats = {}
            
            # Check main textile ERP tables
            tables_to_check = ['fabric_inventory', 'sales_orders', 'suppliers', 'customers', 'fabric_types']
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except sqlite3.OperationalError:
                    stats[table] = 'Table not found'
            
            return {
                'success': True,
                'database_statistics': stats,
                'timestamp': datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"MCP get_import_status failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        if conn:
            conn.close()


# Example usage and testing
if __name__ == "__main__":
    # Test the importer
    config = ImportConfig(
        batch_size=500,
        duplicate_strategy='skip',
        validation_level='standard',
        continue_on_error=True
    )
    
    importer = ERPDataImporter(config)
    
    # Test importing a sample file
    sample_file = "/mnt/c/Users/psytz/TMUX Final/Tmux-Orchestrator/ERP Data/eFab_Inventory_F01_20250726.csv"
    
    if Path(sample_file).exists():
        result = importer.import_file_data(sample_file)
        
        print(f"Import Results:")
        print(f"  Success: {result.success}")
        print(f"  Import ID: {result.import_id}")
        print(f"  Total records: {result.total_records}")
        print(f"  Imported records: {result.imported_records}")
        print(f"  Processing time: {result.processing_time_seconds:.2f}s")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
    else:
        print("Sample file not found for testing")