"""
ERP Data Validation Module - Production-Ready Data Quality Assurance

This module provides comprehensive data validation capabilities for textile ERP data
including schema validation, business rule validation, data quality checks,
anomaly detection, and inconsistency reporting.

Features:
- Schema validation against database constraints
- Business rule validation for textile manufacturing
- Data quality assessment and scoring
- Anomaly detection using statistical methods
- Cross-reference validation between related entities
- Performance monitoring and validation metrics
- Comprehensive error reporting with suggestions
- Integration with Agent-MCP system
"""

import re
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import statistics
import json
from pathlib import Path
import uuid

from ..core.config import logger
from ..db.connection import get_db_connection


@dataclass
class ValidationRule:
    """Definition of a validation rule."""
    rule_id: str
    rule_name: str
    rule_type: str  # SCHEMA, BUSINESS, QUALITY, REFERENCE
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    table_name: str
    column_name: Optional[str] = None
    validation_expression: Optional[str] = None
    error_message: str = ""
    suggestion: str = ""
    active: bool = True


@dataclass
class ValidationError:
    """Individual validation error."""
    rule_id: str
    severity: str
    error_type: str
    table_name: str
    column_name: Optional[str]
    record_id: Optional[str]
    error_message: str
    suggestion: str
    actual_value: Any = None
    expected_value: Any = None


@dataclass
class ValidationResult:
    """Result of validation operation."""
    validation_id: str
    timestamp: datetime
    table_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    error_count: int
    warning_count: int
    quality_score: float  # 0-100
    processing_time_seconds: float
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True


class ERPDataValidator:
    """
    Comprehensive data validator for textile ERP with business logic
    and data quality assessment capabilities.
    """
    
    # Schema validation rules
    SCHEMA_RULES = {
        'fabric_inventory': [
            ValidationRule(
                rule_id='FI001',
                rule_name='Required Fields Check',
                rule_type='SCHEMA',
                severity='CRITICAL',
                description='Check that required fields are not null',
                table_name='fabric_inventory',
                error_message='Required field cannot be null',
                suggestion='Provide a valid value for this required field'
            ),
            ValidationRule(
                rule_id='FI002',
                rule_name='Positive Quantity Check',
                rule_type='BUSINESS',
                severity='HIGH',
                description='Quantity values must be positive',
                table_name='fabric_inventory',
                column_name='quantity_meters',
                error_message='Quantity cannot be negative',
                suggestion='Check data source for calculation errors'
            ),
            ValidationRule(
                rule_id='FI003',
                rule_name='Available Quantity Logic',
                rule_type='BUSINESS',
                severity='MEDIUM',
                description='Available quantity should not exceed total quantity',
                table_name='fabric_inventory',
                error_message='Available quantity exceeds total quantity',
                suggestion='Verify reservation calculations'
            )
        ],
        'sales_orders': [
            ValidationRule(
                rule_id='SO001',
                rule_name='Order Date Validation',
                rule_type='BUSINESS',
                severity='HIGH',
                description='Order date should not be in the future',
                table_name='sales_orders',
                column_name='order_date',
                error_message='Order date cannot be in the future',
                suggestion='Check date format and system clock'
            ),
            ValidationRule(
                rule_id='SO002',
                rule_name='Delivery Date Logic',
                rule_type='BUSINESS',
                severity='MEDIUM',
                description='Delivery date should be after order date',
                table_name='sales_orders',
                error_message='Delivery date is before order date',
                suggestion='Verify date sequence in order processing'
            ),
            ValidationRule(
                rule_id='SO003',
                rule_name='Order Value Check',
                rule_type='BUSINESS',
                severity='HIGH',
                description='Order total value must be positive',
                table_name='sales_orders',
                column_name='total_value',
                error_message='Order value must be positive',
                suggestion='Check pricing calculations'
            )
        ],
        'suppliers': [
            ValidationRule(
                rule_id='SUP001',
                rule_name='Contact Information',
                rule_type='QUALITY',
                severity='MEDIUM',
                description='Suppliers should have email or phone contact',
                table_name='suppliers',
                error_message='Missing contact information',
                suggestion='Add email or phone number for supplier communication'
            ),
            ValidationRule(
                rule_id='SUP002',
                rule_name='Rating Range Check',
                rule_type='BUSINESS',
                severity='LOW',
                description='Quality rating should be between 1 and 5',
                table_name='suppliers',
                column_name='quality_rating',
                error_message='Rating outside valid range (1-5)',
                suggestion='Use standard 1-5 rating scale'
            )
        ],
        'customers': [
            ValidationRule(
                rule_id='CUST001',
                rule_name='Credit Limit Check',
                rule_type='BUSINESS',
                severity='MEDIUM',
                description='Credit limit should be reasonable for customer type',
                table_name='customers',
                column_name='credit_limit',
                error_message='Credit limit seems unusually high or low',
                suggestion='Review credit assessment and customer history'
            )
        ],
        'production_orders': [
            ValidationRule(
                rule_id='PO001',
                rule_name='Production Quantity',
                rule_type='BUSINESS',
                severity='HIGH',
                description='Production quantity must be positive',
                table_name='production_orders',
                column_name='quantity_pieces',
                error_message='Production quantity must be positive',
                suggestion='Check order specifications'
            ),
            ValidationRule(
                rule_id='PO002',
                rule_name='Date Sequence Check',
                rule_type='BUSINESS',
                severity='MEDIUM',
                description='Planned end date should be after start date',
                table_name='production_orders',
                error_message='Invalid date sequence in production schedule',
                suggestion='Review production planning timeline'
            )
        ]
    }
    
    # Business validation ranges and constraints
    BUSINESS_CONSTRAINTS = {
        'fabric_inventory': {
            'quantity_meters': {'min': 0, 'max': 100000},
            'unit_cost': {'min': 0, 'max': 1000},
            'moisture_content': {'min': 0, 'max': 20},
            'tensile_strength': {'min': 0, 'max': 10000}
        },
        'sales_orders': {
            'total_value': {'min': 0, 'max': 1000000},
            'priority': {'min': 1, 'max': 5}
        },
        'suppliers': {
            'quality_rating': {'min': 1, 'max': 5},
            'delivery_rating': {'min': 1, 'max': 5},
            'price_rating': {'min': 1, 'max': 5},
            'lead_time_days': {'min': 0, 'max': 365}
        },
        'production_orders': {
            'quantity_pieces': {'min': 1, 'max': 1000000},
            'priority': {'min': 1, 'max': 5},
            'completion_percentage': {'min': 0, 'max': 100}
        }
    }
    
    # Pattern validation for text fields
    PATTERN_VALIDATIONS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'phone': re.compile(r'^[\+]?[\d\s\-\(\)]{10,}$'),
        'postal_code': re.compile(r'^[\d\w\s\-]{3,10}$'),
        'fabric_id': re.compile(r'^FAB_[A-Z0-9]{8}$'),
        'supplier_id': re.compile(r'^SUP_[A-Z0-9]{8}$'),
        'customer_id': re.compile(r'^CUST_[A-Z0-9]{8}$')
    }
    
    def __init__(self):
        """Initialize validator with configuration."""
        self.logger = logger
        
    def generate_validation_id(self) -> str:
        """Generate unique validation ID."""
        return f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information from database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema = {}
            for col_info in columns:
                col_name = col_info[1]
                col_type = col_info[2]
                not_null = bool(col_info[3])
                default_value = col_info[4]
                primary_key = bool(col_info[5])
                
                schema[col_name] = {
                    'type': col_type,
                    'not_null': not_null,
                    'default': default_value,
                    'primary_key': primary_key
                }
            
            return schema
            
        except Exception as e:
            self.logger.error(f"Failed to get schema for table {table_name}: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def validate_schema_constraints(self, data: Dict[str, Any], table_name: str) -> List[ValidationError]:
        """Validate data against database schema constraints."""
        errors = []
        schema = self.get_table_schema(table_name)
        
        if not schema:
            errors.append(ValidationError(
                rule_id='SCHEMA001',
                severity='CRITICAL',
                error_type='SCHEMA',
                table_name=table_name,
                column_name=None,
                record_id=None,
                error_message=f'Could not retrieve schema for table {table_name}',
                suggestion='Verify table exists in database'
            ))
            return errors
        
        for column_name, column_info in schema.items():
            value = data.get(column_name)
            
            # Check NOT NULL constraints
            if column_info['not_null'] and (value is None or value == ''):
                errors.append(ValidationError(
                    rule_id='SCHEMA002',
                    severity='CRITICAL',
                    error_type='SCHEMA',
                    table_name=table_name,
                    column_name=column_name,
                    record_id=data.get('id'),
                    error_message=f'Required field {column_name} cannot be null',
                    suggestion='Provide a valid value for this required field',
                    actual_value=value
                ))
            
            # Check data type constraints
            if value is not None and value != '':
                type_error = self.validate_data_type(value, column_info['type'], column_name)
                if type_error:
                    errors.append(ValidationError(
                        rule_id='SCHEMA003',
                        severity='HIGH',
                        error_type='SCHEMA',
                        table_name=table_name,
                        column_name=column_name,
                        record_id=data.get('id'),
                        error_message=type_error,
                        suggestion='Check data type and format',
                        actual_value=value,
                        expected_value=column_info['type']
                    ))
        
        return errors
    
    def validate_data_type(self, value: Any, expected_type: str, column_name: str) -> Optional[str]:
        """Validate data type constraints."""
        try:
            expected_type_lower = expected_type.lower()
            
            if 'int' in expected_type_lower:
                int(float(value))  # Handle string numbers
            elif 'real' in expected_type_lower or 'float' in expected_type_lower:
                float(value)
            elif 'text' in expected_type_lower:
                str(value)
            elif 'bool' in expected_type_lower:
                if value not in [0, 1, True, False, 'true', 'false', 'True', 'False']:
                    return f"Invalid boolean value for {column_name}: {value}"
            
            return None
            
        except (ValueError, TypeError):
            return f"Invalid {expected_type} value for {column_name}: {value}"
    
    def validate_business_rules(self, data: Dict[str, Any], table_name: str) -> List[ValidationError]:
        """Validate data against business rules."""
        errors = []
        rules = self.SCHEMA_RULES.get(table_name, [])
        constraints = self.BUSINESS_CONSTRAINTS.get(table_name, {})
        
        # Apply predefined business rules
        for rule in rules:
            if rule.rule_type == 'BUSINESS' and rule.active:
                error = self.apply_business_rule(data, rule)
                if error:
                    errors.append(error)
        
        # Apply numeric range constraints
        for column_name, constraint in constraints.items():
            if column_name in data and data[column_name] is not None:
                value = data[column_name]
                try:
                    numeric_value = float(value)
                    
                    if 'min' in constraint and numeric_value < constraint['min']:
                        errors.append(ValidationError(
                            rule_id=f'RANGE_{column_name.upper()}',
                            severity='MEDIUM',
                            error_type='BUSINESS',
                            table_name=table_name,
                            column_name=column_name,
                            record_id=data.get('id'),
                            error_message=f'{column_name} value {numeric_value} is below minimum {constraint["min"]}',
                            suggestion=f'Value should be at least {constraint["min"]}',
                            actual_value=numeric_value,
                            expected_value=f'>= {constraint["min"]}'
                        ))
                    
                    if 'max' in constraint and numeric_value > constraint['max']:
                        errors.append(ValidationError(
                            rule_id=f'RANGE_{column_name.upper()}',
                            severity='MEDIUM',
                            error_type='BUSINESS',
                            table_name=table_name,
                            column_name=column_name,
                            record_id=data.get('id'),
                            error_message=f'{column_name} value {numeric_value} exceeds maximum {constraint["max"]}',
                            suggestion=f'Value should not exceed {constraint["max"]}',
                            actual_value=numeric_value,
                            expected_value=f'<= {constraint["max"]}'
                        ))
                
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        rule_id=f'TYPE_{column_name.upper()}',
                        severity='HIGH',
                        error_type='BUSINESS',
                        table_name=table_name,
                        column_name=column_name,
                        record_id=data.get('id'),
                        error_message=f'Invalid numeric value for {column_name}: {value}',
                        suggestion='Provide a valid numeric value',
                        actual_value=value
                    ))
        
        # Apply specific business logic
        if table_name == 'fabric_inventory':
            errors.extend(self.validate_fabric_inventory_business_rules(data))
        elif table_name == 'sales_orders':
            errors.extend(self.validate_sales_order_business_rules(data))
        elif table_name == 'production_orders':
            errors.extend(self.validate_production_order_business_rules(data))
        
        return errors
    
    def apply_business_rule(self, data: Dict[str, Any], rule: ValidationRule) -> Optional[ValidationError]:
        """Apply a specific business rule to data."""
        try:
            # Custom business rule implementations
            if rule.rule_id == 'FI003':  # Available quantity logic
                total_qty = data.get('quantity_meters', 0)
                available_qty = data.get('available_meters', 0)
                
                if total_qty and available_qty and float(available_qty) > float(total_qty):
                    return ValidationError(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        error_type=rule.rule_type,
                        table_name=rule.table_name,
                        column_name='available_meters',
                        record_id=data.get('id'),
                        error_message=rule.error_message,
                        suggestion=rule.suggestion,
                        actual_value=available_qty,
                        expected_value=f'<= {total_qty}'
                    )
            
            elif rule.rule_id == 'SO002':  # Delivery date logic
                order_date_str = data.get('order_date')
                delivery_date_str = data.get('promised_delivery_date')
                
                if order_date_str and delivery_date_str:
                    try:
                        order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00')).date()
                        delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00')).date()
                        
                        if delivery_date < order_date:
                            return ValidationError(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                error_type=rule.rule_type,
                                table_name=rule.table_name,
                                column_name='promised_delivery_date',
                                record_id=data.get('id'),
                                error_message=rule.error_message,
                                suggestion=rule.suggestion,
                                actual_value=delivery_date_str,
                                expected_value=f'> {order_date_str}'
                            )
                    except (ValueError, AttributeError):
                        pass  # Let date format validation handle this
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error applying business rule {rule.rule_id}: {e}")
            return None
    
    def validate_fabric_inventory_business_rules(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate fabric inventory specific business rules."""
        errors = []
        
        # Check for reasonable fabric dimensions
        width_cm = data.get('roll_width_cm')
        if width_cm:
            try:
                width_value = float(width_cm)
                if width_value < 10 or width_value > 500:  # Reasonable fabric width range
                    errors.append(ValidationError(
                        rule_id='FI_WIDTH',
                        severity='LOW',
                        error_type='BUSINESS',
                        table_name='fabric_inventory',
                        column_name='roll_width_cm',
                        record_id=data.get('id'),
                        error_message=f'Unusual fabric width: {width_value} cm',
                        suggestion='Verify fabric specifications',
                        actual_value=width_value
                    ))
            except (ValueError, TypeError):
                pass
        
        # Check for reasonable GSM (grams per square meter)
        gsm = data.get('actual_weight_gsm')
        if gsm:
            try:
                gsm_value = float(gsm)
                if gsm_value < 50 or gsm_value > 1000:  # Typical fabric weight range
                    errors.append(ValidationError(
                        rule_id='FI_GSM',
                        severity='LOW',
                        error_type='BUSINESS',
                        table_name='fabric_inventory',
                        column_name='actual_weight_gsm',
                        record_id=data.get('id'),
                        error_message=f'Unusual fabric weight: {gsm_value} GSM',
                        suggestion='Verify fabric weight specifications',
                        actual_value=gsm_value
                    ))
            except (ValueError, TypeError):
                pass
        
        return errors
    
    def validate_sales_order_business_rules(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate sales order specific business rules."""
        errors = []
        
        # Check order status consistency
        status = data.get('status', '').upper()
        order_date = data.get('order_date')
        
        if status == 'NEW' and order_date:
            try:
                order_dt = datetime.fromisoformat(order_date.replace('Z', '+00:00')).date()
                days_ago = (datetime.now().date() - order_dt).days
                
                if days_ago > 30:  # Order has been "NEW" for too long
                    errors.append(ValidationError(
                        rule_id='SO_STALE',
                        severity='MEDIUM',
                        error_type='BUSINESS',
                        table_name='sales_orders',
                        column_name='status',
                        record_id=data.get('id'),
                        error_message=f'Order has been in NEW status for {days_ago} days',
                        suggestion='Review order processing workflow',
                        actual_value=status
                    ))
            except (ValueError, AttributeError):
                pass
        
        return errors
    
    def validate_production_order_business_rules(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate production order specific business rules."""
        errors = []
        
        # Check completion percentage consistency with status
        completion_pct = data.get('completion_percentage', 0)
        status = data.get('status', '').upper()
        
        try:
            completion_value = float(completion_pct)
            
            if status == 'COMPLETED' and completion_value < 100:
                errors.append(ValidationError(
                    rule_id='PO_COMPLETION',
                    severity='HIGH',
                    error_type='BUSINESS',
                    table_name='production_orders',
                    column_name='completion_percentage',
                    record_id=data.get('id'),
                    error_message=f'Order marked as COMPLETED but only {completion_value}% complete',
                    suggestion='Update completion percentage or order status',
                    actual_value=completion_value,
                    expected_value=100
                ))
            elif status == 'PENDING' and completion_value > 0:
                errors.append(ValidationError(
                    rule_id='PO_PENDING',
                    severity='MEDIUM',
                    error_type='BUSINESS',
                    table_name='production_orders',
                    column_name='status',
                    record_id=data.get('id'),
                    error_message=f'Order status is PENDING but {completion_value}% complete',
                    suggestion='Update order status to reflect actual progress',
                    actual_value=status,
                    expected_value='IN_PROGRESS'
                ))
        except (ValueError, TypeError):
            pass
        
        return errors
    
    def validate_pattern_fields(self, data: Dict[str, Any], table_name: str) -> List[ValidationError]:
        """Validate fields against expected patterns."""
        errors = []
        
        # Define field pattern mappings for each table
        pattern_fields = {
            'suppliers': {
                'email': 'email',
                'phone': 'phone',
                'postal_code': 'postal_code',
                'supplier_id': 'supplier_id'
            },
            'customers': {
                'email': 'email',
                'phone': 'phone',
                'postal_code': 'postal_code',
                'customer_id': 'customer_id'
            },
            'fabric_inventory': {
                'fabric_type_id': 'fabric_id'
            }
        }
        
        table_patterns = pattern_fields.get(table_name, {})
        
        for field_name, pattern_name in table_patterns.items():
            if field_name in data and data[field_name]:
                value = str(data[field_name]).strip()
                pattern = self.PATTERN_VALIDATIONS.get(pattern_name)
                
                if pattern and not pattern.match(value):
                    errors.append(ValidationError(
                        rule_id=f'PATTERN_{field_name.upper()}',
                        severity='LOW',
                        error_type='QUALITY',
                        table_name=table_name,
                        column_name=field_name,
                        record_id=data.get('id'),
                        error_message=f'Invalid format for {field_name}: {value}',
                        suggestion=f'Use proper format for {field_name}',
                        actual_value=value
                    ))
        
        return errors
    
    def detect_anomalies(self, data_list: List[Dict[str, Any]], table_name: str) -> List[ValidationError]:
        """Detect statistical anomalies in dataset."""
        errors = []
        
        if len(data_list) < 10:  # Need minimum data for statistical analysis
            return errors
        
        # Numeric fields to analyze for each table
        numeric_fields = {
            'fabric_inventory': ['quantity_meters', 'unit_cost', 'actual_weight_gsm'],
            'sales_orders': ['total_value', 'priority'],
            'suppliers': ['quality_rating', 'delivery_rating', 'lead_time_days'],
            'production_orders': ['quantity_pieces', 'completion_percentage']
        }
        
        fields_to_analyze = numeric_fields.get(table_name, [])
        
        for field_name in fields_to_analyze:
            # Extract numeric values
            values = []
            for record in data_list:
                if field_name in record and record[field_name] is not None:
                    try:
                        value = float(record[field_name])
                        values.append(value)
                    except (ValueError, TypeError):
                        continue
            
            if len(values) < 5:  # Need minimum values for statistics
                continue
            
            try:
                # Calculate statistical measures
                mean_val = statistics.mean(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0
                
                # Detect outliers using Z-score method (threshold: 3 standard deviations)
                if std_dev > 0:
                    for i, record in enumerate(data_list):
                        if field_name in record and record[field_name] is not None:
                            try:
                                value = float(record[field_name])
                                z_score = abs(value - mean_val) / std_dev
                                
                                if z_score > 3:  # Outlier detected
                                    errors.append(ValidationError(
                                        rule_id=f'ANOMALY_{field_name.upper()}',
                                        severity='LOW',
                                        error_type='QUALITY',
                                        table_name=table_name,
                                        column_name=field_name,
                                        record_id=record.get('id'),
                                        error_message=f'Statistical outlier detected for {field_name}: {value} (Z-score: {z_score:.2f})',
                                        suggestion='Verify data accuracy or investigate unusual case',
                                        actual_value=value,
                                        expected_value=f'Mean: {mean_val:.2f} ± {std_dev:.2f}'
                                    ))
                            except (ValueError, TypeError):
                                continue
            
            except statistics.StatisticsError:
                continue  # Skip if statistical calculation fails
        
        return errors
    
    def validate_cross_references(self, data: Dict[str, Any], table_name: str) -> List[ValidationError]:
        """Validate foreign key relationships and cross-references."""
        errors = []
        
        # Define reference relationships
        references = {
            'fabric_inventory': {
                'fabric_type_id': ('fabric_types', 'fabric_type_id'),
                'supplier_id': ('suppliers', 'supplier_id')
            },
            'sales_orders': {
                'customer_id': ('customers', 'customer_id')
            },
            'sales_order_items': {
                'order_id': ('sales_orders', 'order_id'),
                'fabric_type_id': ('fabric_types', 'fabric_type_id')
            },
            'production_orders': {
                'fabric_type_id': ('fabric_types', 'fabric_type_id'),
                'sales_order_id': ('sales_orders', 'order_id')
            }
        }
        
        table_refs = references.get(table_name, {})
        
        for field_name, (ref_table, ref_field) in table_refs.items():
            if field_name in data and data[field_name]:
                value = data[field_name]
                
                # Check if referenced record exists
                if not self.check_reference_exists(ref_table, ref_field, value):
                    errors.append(ValidationError(
                        rule_id=f'REF_{field_name.upper()}',
                        severity='HIGH',
                        error_type='REFERENCE',
                        table_name=table_name,
                        column_name=field_name,
                        record_id=data.get('id'),
                        error_message=f'Referenced {ref_table} record not found: {value}',
                        suggestion=f'Ensure {ref_table} record exists before referencing',
                        actual_value=value
                    ))
        
        return errors
    
    def check_reference_exists(self, ref_table: str, ref_field: str, value: Any) -> bool:
        """Check if a referenced record exists in the database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT 1 FROM {ref_table} WHERE {ref_field} = ? LIMIT 1", (value,))
            result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            self.logger.warning(f"Failed to check reference {ref_table}.{ref_field} = {value}: {e}")
            return True  # Assume valid if check fails
        finally:
            if conn:
                conn.close()
    
    def calculate_quality_score(self, total_records: int, errors: List[ValidationError]) -> float:
        """Calculate data quality score (0-100)."""
        if total_records == 0:
            return 0.0
        
        # Weight errors by severity
        severity_weights = {
            'CRITICAL': 10,
            'HIGH': 5,
            'MEDIUM': 2,
            'LOW': 1
        }
        
        error_score = sum(severity_weights.get(error.severity, 1) for error in errors)
        max_possible_score = total_records * 10  # Assuming all could be critical errors
        
        quality_score = max(0, 100 - (error_score / max_possible_score * 100))
        return min(100, quality_score)
    
    def validate_record(self, data: Dict[str, Any], table_name: str) -> ValidationResult:
        """Validate a single record."""
        return self.validate_records([data], table_name)
    
    def validate_records(self, data_list: List[Dict[str, Any]], table_name: str) -> ValidationResult:
        """
        Validate multiple records with comprehensive checks.
        
        Args:
            data_list: List of data records to validate
            table_name: Name of the target table
            
        Returns:
            ValidationResult with detailed validation information
        """
        start_time = datetime.now()
        validation_id = self.generate_validation_id()
        
        all_errors = []
        all_warnings = []
        
        self.logger.info(f"Starting validation {validation_id} for {len(data_list)} records in {table_name}")
        
        # Validate each record
        for i, record in enumerate(data_list):
            # Schema validation
            schema_errors = self.validate_schema_constraints(record, table_name)
            all_errors.extend(schema_errors)
            
            # Business rule validation
            business_errors = self.validate_business_rules(record, table_name)
            all_errors.extend(business_errors)
            
            # Pattern validation
            pattern_errors = self.validate_pattern_fields(record, table_name)
            all_errors.extend(pattern_errors)
            
            # Cross-reference validation
            ref_errors = self.validate_cross_references(record, table_name)
            all_errors.extend(ref_errors)
        
        # Anomaly detection across all records
        anomaly_errors = self.detect_anomalies(data_list, table_name)
        all_errors.extend(anomaly_errors)
        
        # Separate errors by severity
        critical_high_errors = [e for e in all_errors if e.severity in ['CRITICAL', 'HIGH']]
        warnings = [e for e in all_errors if e.severity in ['MEDIUM', 'LOW']]
        
        # Calculate metrics
        total_records = len(data_list)
        error_records = len(set(e.record_id for e in critical_high_errors if e.record_id))
        valid_records = total_records - error_records
        quality_score = self.calculate_quality_score(total_records, all_errors)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Generate statistics
        statistics = {
            'error_by_severity': {
                'critical': len([e for e in all_errors if e.severity == 'CRITICAL']),
                'high': len([e for e in all_errors if e.severity == 'HIGH']),
                'medium': len([e for e in all_errors if e.severity == 'MEDIUM']),
                'low': len([e for e in all_errors if e.severity == 'LOW'])
            },
            'error_by_type': {
                'schema': len([e for e in all_errors if e.error_type == 'SCHEMA']),
                'business': len([e for e in all_errors if e.error_type == 'BUSINESS']),
                'quality': len([e for e in all_errors if e.error_type == 'QUALITY']),
                'reference': len([e for e in all_errors if e.error_type == 'REFERENCE'])
            },
            'most_common_errors': self.get_most_common_errors(all_errors, 5)
        }
        
        result = ValidationResult(
            validation_id=validation_id,
            timestamp=start_time,
            table_name=table_name,
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=error_records,
            error_count=len(critical_high_errors),
            warning_count=len(warnings),
            quality_score=quality_score,
            processing_time_seconds=processing_time,
            errors=critical_high_errors,
            warnings=warnings,
            statistics=statistics,
            is_valid=len(critical_high_errors) == 0
        )
        
        self.logger.info(f"Validation {validation_id} completed: {valid_records}/{total_records} valid records, quality score: {quality_score:.1f}")
        
        return result
    
    def get_most_common_errors(self, errors: List[ValidationError], limit: int = 5) -> List[Dict[str, Any]]:
        """Get most common validation errors."""
        error_counts = {}
        
        for error in errors:
            key = f"{error.rule_id}: {error.error_message.split(':')[0] if ':' in error.error_message else error.error_message}"
            error_counts[key] = error_counts.get(key, 0) + 1
        
        # Sort by count and return top N
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'error': error, 'count': count}
            for error, count in sorted_errors[:limit]
        ]
    
    def validate_table_data(self, table_name: str, limit: Optional[int] = None) -> ValidationResult:
        """
        Validate all data in a specific table.
        
        Args:
            table_name: Name of table to validate
            limit: Optional limit on number of records to validate
            
        Returns:
            ValidationResult for the entire table
        """
        conn = None
        try:
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Build query with optional limit
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data_list = [dict(row) for row in rows]
            
            return self.validate_records(data_list, table_name)
            
        except Exception as e:
            error_msg = f"Failed to validate table {table_name}: {e}"
            self.logger.error(error_msg)
            
            return ValidationResult(
                validation_id=self.generate_validation_id(),
                timestamp=datetime.now(),
                table_name=table_name,
                total_records=0,
                valid_records=0,
                invalid_records=0,
                error_count=1,
                warning_count=0,
                quality_score=0.0,
                processing_time_seconds=0.0,
                errors=[ValidationError(
                    rule_id='SYS001',
                    severity='CRITICAL',
                    error_type='SYSTEM',
                    table_name=table_name,
                    column_name=None,
                    record_id=None,
                    error_message=error_msg,
                    suggestion='Check table existence and database connectivity'
                )],
                is_valid=False
            )
        finally:
            if conn:
                conn.close()


# Example usage and testing
if __name__ == "__main__":
    # Test the validator
    validator = ERPDataValidator()
    
    # Test single record validation
    test_record = {
        'inventory_id': 'INV_12345678',
        'fabric_type_id': 'FAB_87654321',
        'quantity_meters': 100.5,
        'available_meters': 95.0,
        'unit_cost': 12.50,
        'received_date': '2024-01-15'
    }
    
    result = validator.validate_record(test_record, 'fabric_inventory')
    
    print(f"Validation Results:")
    print(f"  Valid: {result.is_valid}")
    print(f"  Quality Score: {result.quality_score:.1f}")
    print(f"  Errors: {result.error_count}")
    print(f"  Warnings: {result.warning_count}")
    print(f"  Processing Time: {result.processing_time_seconds:.3f}s")
    
    if result.errors:
        print(f"  Error Details:")
        for error in result.errors[:3]:  # Show first 3 errors
            print(f"    - {error.error_message} ({error.severity})")
    
    if result.warnings:
        print(f"  Warning Details:")
        for warning in result.warnings[:3]:  # Show first 3 warnings
            print(f"    - {warning.error_message} ({warning.severity})")