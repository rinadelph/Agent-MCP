# eFab-AI-Enhanced Textile Manufacturing ERP Database Schema
"""
Comprehensive database schema for textile manufacturing ERP system.
Designed for high-volume sensor data processing while maintaining ACID compliance
for business transactions. Integrates with Agent-MCP's existing infrastructure.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from ..core.config import logger, get_db_path
from .connection import get_db_connection, check_vss_loadability, is_vss_loadable


class TextileERPSchema:
    """
    Textile ERP schema manager with optimized time-series handling
    and high-performance sensor data ingestion.
    """
    
    def __init__(self):
        self.schema_version = "1.0.0"
        
    def init_textile_erp_tables(self) -> None:
        """
        Initialize all textile ERP tables with proper indexing and partitioning strategies.
        This function should be called during application startup after base schema init.
        """
        logger.info("Initializing Textile ERP database schema...")
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Enable WAL mode and optimize for high-volume writes
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=memory")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            # === CORE MANUFACTURING TABLES ===
            self._create_fabric_inventory_tables(cursor)
            self._create_production_tables(cursor)
            self._create_quality_control_tables(cursor)
            self._create_machine_management_tables(cursor)
            self._create_worker_management_tables(cursor)
            
            # === SENSOR DATA TABLES ===
            self._create_sensor_data_tables(cursor)
            self._create_machine_performance_tables(cursor)
            self._create_environmental_monitoring_tables(cursor)
            self._create_quality_inspection_tables(cursor)
            
            # === ERP INTEGRATION TABLES ===
            self._create_sales_order_tables(cursor)
            self._create_purchase_order_tables(cursor)
            self._create_customer_management_tables(cursor)
            self._create_supplier_management_tables(cursor)
            self._create_financial_transaction_tables(cursor)
            
            # === DATA PIPELINE TABLES ===
            self._create_etl_pipeline_tables(cursor)
            self._create_data_quality_tables(cursor)
            self._create_aggregation_tables(cursor)
            
            # === INTEGRATION WITH AGENT-MCP ===
            self._create_mcp_integration_tables(cursor)
            
            # Create all indexes
            self._create_performance_indexes(cursor)
            
            # Create views for common queries
            self._create_analytical_views(cursor)
            
            # Create triggers for automated processes
            self._create_automation_triggers(cursor)
            
            conn.commit()
            logger.info("Textile ERP schema initialized successfully.")
            
        except sqlite3.Error as e:
            logger.error(f"Database error during textile ERP schema initialization: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise RuntimeError(f"Failed to initialize textile ERP schema: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during textile ERP schema initialization: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise RuntimeError(f"Unexpected error during textile ERP schema initialization: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def _create_fabric_inventory_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create fabric inventory management tables."""
        
        # Fabric Types Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fabric_types (
                fabric_type_id TEXT PRIMARY KEY,
                fabric_name TEXT NOT NULL,
                fabric_category TEXT NOT NULL, -- Cotton, Polyester, Blend, etc.
                fiber_composition TEXT, -- JSON: {"cotton": 60, "polyester": 40}
                weight_gsm INTEGER, -- Grams per square meter
                width_cm INTEGER,
                color_fastness_rating INTEGER,
                shrinkage_percentage REAL,
                care_instructions TEXT,
                sustainability_score INTEGER, -- 1-100 environmental impact score
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Fabric Inventory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fabric_inventory (
                inventory_id TEXT PRIMARY KEY,
                fabric_type_id TEXT NOT NULL,
                lot_number TEXT NOT NULL,
                supplier_id TEXT,
                quantity_meters REAL NOT NULL,
                reserved_meters REAL DEFAULT 0,
                available_meters REAL GENERATED ALWAYS AS (quantity_meters - reserved_meters) STORED,
                unit_cost REAL,
                location_warehouse TEXT,
                location_zone TEXT,
                location_bin TEXT,
                received_date TEXT NOT NULL,
                expiry_date TEXT,
                quality_grade TEXT, -- A, B, C grading
                defect_notes TEXT,
                color_code TEXT,
                dye_lot TEXT,
                roll_width_cm REAL,
                actual_weight_gsm REAL,
                moisture_content REAL,
                tensile_strength REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            )
        """)
        
        # Inventory Movements (for audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id TEXT NOT NULL,
                movement_type TEXT NOT NULL, -- IN, OUT, ADJUSTMENT, TRANSFER
                quantity_meters REAL NOT NULL,
                reference_id TEXT, -- Production order, sales order, etc.
                reference_type TEXT, -- PRODUCTION, SALE, ADJUSTMENT, etc.
                reason TEXT,
                moved_by TEXT, -- Agent ID or user ID
                moved_at TEXT NOT NULL,
                from_location TEXT,
                to_location TEXT,
                FOREIGN KEY (inventory_id) REFERENCES fabric_inventory (inventory_id)
            )
        """)
        
    def _create_production_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create production order and tracking tables."""
        
        # Production Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_orders (
                order_id TEXT PRIMARY KEY,
                sales_order_id TEXT,
                product_type TEXT NOT NULL,
                fabric_type_id TEXT NOT NULL,
                quantity_pieces INTEGER NOT NULL,
                quantity_meters REAL,
                priority INTEGER DEFAULT 3, -- 1=High, 2=Medium, 3=Low
                planned_start_date TEXT,
                planned_end_date TEXT,
                actual_start_date TEXT,
                actual_end_date TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, CANCELLED, HOLD
                completion_percentage REAL DEFAULT 0,
                assigned_line TEXT,
                supervisor_id TEXT,
                special_instructions TEXT,
                quality_requirements TEXT, -- JSON with quality parameters
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id),
                FOREIGN KEY (sales_order_id) REFERENCES sales_orders (order_id)
            )
        """)
        
        # Production Operations (steps in production process)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_operations (
                operation_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                operation_sequence INTEGER NOT NULL,
                operation_name TEXT NOT NULL, -- Cutting, Sewing, Finishing, etc.
                machine_id TEXT,
                operator_id TEXT,
                planned_duration_minutes INTEGER,
                actual_duration_minutes INTEGER,
                start_time TEXT,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, FAILED
                quality_check_required BOOLEAN DEFAULT 0,
                quality_check_passed BOOLEAN,
                defect_count INTEGER DEFAULT 0,
                rework_required BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES production_orders (order_id),
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (operator_id) REFERENCES workers (worker_id)
            )
        """)
        
        # Production Line Status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_lines (
                line_id TEXT PRIMARY KEY,
                line_name TEXT NOT NULL,
                line_type TEXT NOT NULL, -- CUTTING, SEWING, FINISHING
                capacity_pieces_per_hour REAL,
                current_order_id TEXT,
                status TEXT NOT NULL DEFAULT 'IDLE', -- IDLE, RUNNING, MAINTENANCE, BREAKDOWN
                efficiency_percentage REAL,
                last_maintenance_date TEXT,
                next_maintenance_due TEXT,
                supervisor_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (current_order_id) REFERENCES production_orders (order_id)
            )
        """)
        
    def _create_quality_control_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create quality control and inspection tables."""
        
        # Quality Control Standards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_standards (
                standard_id TEXT PRIMARY KEY,
                fabric_type_id TEXT,
                product_type TEXT,
                parameter_name TEXT NOT NULL, -- Stitch count, seam strength, etc.
                min_value REAL,
                max_value REAL,
                target_value REAL,
                tolerance REAL,
                unit TEXT,
                test_method TEXT,
                critical BOOLEAN DEFAULT 0, -- Critical vs non-critical defect
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id)
            )
        """)
        
        # Quality Inspections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_inspections (
                inspection_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                operation_id TEXT,
                inspection_type TEXT NOT NULL, -- INCOMING, IN_PROCESS, FINAL
                inspector_id TEXT NOT NULL,
                sample_size INTEGER,
                inspection_date TEXT NOT NULL,
                overall_result TEXT NOT NULL, -- PASS, FAIL, CONDITIONAL
                defect_rate REAL,
                critical_defects INTEGER DEFAULT 0,
                major_defects INTEGER DEFAULT 0,
                minor_defects INTEGER DEFAULT 0,
                notes TEXT,
                corrective_action TEXT,
                reinspection_required BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES production_orders (order_id),
                FOREIGN KEY (operation_id) REFERENCES production_operations (operation_id),
                FOREIGN KEY (inspector_id) REFERENCES workers (worker_id)
            )
        """)
        
        # Quality Test Results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_test_results (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT NOT NULL,
                standard_id TEXT NOT NULL,
                measured_value REAL NOT NULL,
                test_result TEXT NOT NULL, -- PASS, FAIL
                deviation REAL, -- Deviation from target
                test_equipment TEXT,
                test_conditions TEXT, -- JSON with temperature, humidity, etc.
                tested_at TEXT NOT NULL,
                FOREIGN KEY (inspection_id) REFERENCES quality_inspections (inspection_id),
                FOREIGN KEY (standard_id) REFERENCES quality_standards (standard_id)
            )
        """)
        
    def _create_machine_management_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create machine and loom management tables."""
        
        # Machines Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                machine_id TEXT PRIMARY KEY,
                machine_name TEXT NOT NULL,
                machine_type TEXT NOT NULL, -- LOOM, CUTTING, SEWING, FINISHING
                model TEXT,
                manufacturer TEXT,
                year_installed INTEGER,
                line_id TEXT,
                status TEXT NOT NULL DEFAULT 'IDLE', -- IDLE, RUNNING, MAINTENANCE, BREAKDOWN
                current_operation_id TEXT,
                capacity_per_hour REAL,
                power_rating_kw REAL,
                maintenance_schedule_hours INTEGER,
                total_runtime_hours REAL DEFAULT 0,
                last_maintenance_at TEXT,
                next_maintenance_due TEXT,
                efficiency_rating REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (line_id) REFERENCES production_lines (line_id),
                FOREIGN KEY (current_operation_id) REFERENCES production_operations (operation_id)
            )
        """)
        
        # Machine Specifications (for looms and specialized equipment)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_specifications (
                spec_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                spec_name TEXT NOT NULL,
                spec_value TEXT NOT NULL,
                spec_unit TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id)
            )
        """)
        
        # Machine Maintenance Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_maintenance (
                maintenance_id TEXT PRIMARY KEY,
                machine_id TEXT NOT NULL,
                maintenance_type TEXT NOT NULL, -- PREVENTIVE, CORRECTIVE, EMERGENCY
                scheduled_date TEXT,
                actual_date TEXT,
                duration_minutes INTEGER,
                technician_id TEXT,
                description TEXT,
                parts_replaced TEXT, -- JSON list
                cost REAL,
                next_service_due TEXT,
                status TEXT NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (technician_id) REFERENCES workers (worker_id)
            )
        """)
        
    def _create_worker_management_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create worker assignment and tracking tables."""
        
        # Workers Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                employee_number TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                department TEXT NOT NULL, -- CUTTING, SEWING, FINISHING, QC, MAINTENANCE
                role TEXT NOT NULL, -- OPERATOR, SUPERVISOR, TECHNICIAN, INSPECTOR
                shift TEXT, -- MORNING, AFTERNOON, NIGHT
                skill_level INTEGER DEFAULT 1, -- 1-5 skill rating
                hourly_rate REAL,
                hire_date TEXT,
                active BOOLEAN DEFAULT 1,
                certifications TEXT, -- JSON list of certifications
                performance_rating REAL DEFAULT 3.0, -- 1-5 performance rating
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Worker Assignments (current assignments)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_assignments (
                assignment_id TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                machine_id TEXT,
                line_id TEXT,
                operation_id TEXT,
                assigned_date TEXT NOT NULL,
                shift_start TEXT,
                shift_end TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED, CANCELLED
                productivity_target REAL,
                actual_productivity REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (worker_id) REFERENCES workers (worker_id),
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (line_id) REFERENCES production_lines (line_id),
                FOREIGN KEY (operation_id) REFERENCES production_operations (operation_id)
            )
        """)
        
        # Worker Performance Tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_performance (
                performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                date TEXT NOT NULL,
                shift TEXT NOT NULL,
                hours_worked REAL,
                pieces_completed INTEGER,
                defect_count INTEGER,
                efficiency_percentage REAL,
                quality_score REAL,
                attendance_status TEXT, -- PRESENT, ABSENT, LATE
                notes TEXT,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
            )
        """)
        
    def _create_sensor_data_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create optimized sensor data tables with partitioning strategy."""
        
        # Sensor Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                sensor_id TEXT PRIMARY KEY,
                sensor_type TEXT NOT NULL, -- TEMPERATURE, HUMIDITY, VIBRATION, CURRENT, VOLTAGE, etc.
                machine_id TEXT,
                location TEXT,
                measurement_unit TEXT NOT NULL,
                sampling_rate_hz REAL DEFAULT 1.0,
                min_range REAL,
                max_range REAL,
                calibration_date TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id)
            )
        """)
        
        # Raw Sensor Readings (high-frequency data)
        # This table uses a time-based partitioning strategy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                value REAL NOT NULL,
                quality_flag INTEGER DEFAULT 0, -- 0=Good, 1=Suspect, 2=Bad
                batch_id TEXT, -- For bulk inserts
                created_at TEXT NOT NULL,
                FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id)
            )
        """)
        
        # Time-series aggregated data (for performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings_hourly (
                agg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                hour_timestamp TEXT NOT NULL, -- Truncated to hour
                avg_value REAL,
                min_value REAL,
                max_value REAL,
                stddev_value REAL,
                sample_count INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id),
                UNIQUE(sensor_id, hour_timestamp)
            )
        """)
        
        # Daily aggregations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings_daily (
                agg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                date TEXT NOT NULL,
                avg_value REAL,
                min_value REAL,
                max_value REAL,
                stddev_value REAL,
                sample_count INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id),
                UNIQUE(sensor_id, date)
            )
        """)
        
    def _create_machine_performance_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create machine performance metrics tables."""
        
        # Real-time Machine Status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_status_realtime (
                status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL, -- RUNNING, IDLE, MAINTENANCE, ERROR
                speed_rpm REAL,
                temperature_c REAL,
                vibration_level REAL,
                power_consumption_kw REAL,
                production_count INTEGER,
                efficiency_percentage REAL,
                error_code TEXT,
                operator_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (operator_id) REFERENCES workers (worker_id)
            )
        """)
        
        # Machine Performance Summaries (hourly)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_performance_hourly (
                perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                hour_timestamp TEXT NOT NULL,
                runtime_minutes REAL,
                idle_time_minutes REAL,
                maintenance_time_minutes REAL,
                total_production INTEGER,
                avg_efficiency REAL,
                avg_power_consumption REAL,
                downtime_events INTEGER,
                quality_issues INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                UNIQUE(machine_id, hour_timestamp)
            )
        """)
        
        # Machine Downtime Events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_downtime (
                downtime_id TEXT PRIMARY KEY,
                machine_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_minutes REAL,
                downtime_type TEXT NOT NULL, -- BREAKDOWN, MAINTENANCE, NO_WORK, CHANGEOVER
                reason_code TEXT,
                description TEXT,
                repair_actions TEXT,
                technician_id TEXT,
                cost_estimate REAL,
                resolved BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (technician_id) REFERENCES workers (worker_id)
            )
        """)
        
    def _create_environmental_monitoring_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create environmental monitoring tables."""
        
        # Environmental Zones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_zones (
                zone_id TEXT PRIMARY KEY,
                zone_name TEXT NOT NULL,
                zone_type TEXT NOT NULL, -- PRODUCTION, STORAGE, OFFICE
                area_sqm REAL,
                target_temperature_c REAL,
                target_humidity_percent REAL,
                air_changes_per_hour REAL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Environmental Readings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature_c REAL,
                humidity_percent REAL,
                air_pressure_hpa REAL,
                air_quality_index REAL,
                dust_level_ugm3 REAL,
                light_level_lux REAL,
                noise_level_db REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (zone_id) REFERENCES environmental_zones (zone_id)
            )
        """)
        
        # Environmental Alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_alerts (
                alert_id TEXT PRIMARY KEY,
                zone_id TEXT NOT NULL,
                parameter_name TEXT NOT NULL,
                alert_level TEXT NOT NULL, -- WARNING, CRITICAL
                threshold_value REAL,
                actual_value REAL,
                triggered_at TEXT NOT NULL,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                resolved_at TEXT,
                resolution_notes TEXT,
                FOREIGN KEY (zone_id) REFERENCES environmental_zones (zone_id)
            )
        """)
        
    def _create_quality_inspection_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create automated quality inspection data tables."""
        
        # Automated Quality Inspections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automated_inspections (
                inspection_id TEXT PRIMARY KEY,
                machine_id TEXT NOT NULL,
                operation_id TEXT,
                timestamp TEXT NOT NULL,
                inspection_type TEXT NOT NULL, -- VISUAL, DIMENSIONAL, WEIGHT
                sample_id TEXT,
                pass_fail_result TEXT NOT NULL, -- PASS, FAIL
                confidence_score REAL, -- 0-1 AI confidence
                defect_types TEXT, -- JSON array of detected defects
                image_path TEXT,
                measurements TEXT, -- JSON with dimensional data
                created_at TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines (machine_id),
                FOREIGN KEY (operation_id) REFERENCES production_operations (operation_id)
            )
        """)
        
        # Defect Classification
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defect_types (
                defect_id TEXT PRIMARY KEY,
                defect_name TEXT NOT NULL,
                defect_category TEXT NOT NULL, -- STITCHING, FABRIC, DIMENSIONAL, COLOR
                severity_level TEXT NOT NULL, -- MINOR, MAJOR, CRITICAL
                description TEXT,
                root_causes TEXT, -- JSON array
                prevention_measures TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
    def _create_sales_order_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create sales order management tables."""
        
        # Sales Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_number TEXT UNIQUE NOT NULL,
                order_date TEXT NOT NULL,
                requested_delivery_date TEXT,
                promised_delivery_date TEXT,
                actual_delivery_date TEXT,
                status TEXT NOT NULL DEFAULT 'NEW', -- NEW, CONFIRMED, IN_PRODUCTION, SHIPPED, DELIVERED, CANCELLED
                priority INTEGER DEFAULT 3,
                total_value REAL,
                currency TEXT DEFAULT 'USD',
                payment_terms TEXT,
                shipping_address TEXT,
                special_instructions TEXT,
                sales_rep_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
        """)
        
        # Sales Order Line Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_order_items (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                fabric_type_id TEXT NOT NULL,
                quantity_pieces INTEGER NOT NULL,
                quantity_meters REAL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                delivery_date TEXT,
                color_code TEXT,
                size_specifications TEXT, -- JSON
                quality_grade TEXT,
                produced_quantity INTEGER DEFAULT 0,
                shipped_quantity INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, IN_PRODUCTION, READY, SHIPPED
                FOREIGN KEY (order_id) REFERENCES sales_orders (order_id),
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id)
            )
        """)
        
    def _create_purchase_order_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create purchase order management tables."""
        
        # Purchase Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                order_id TEXT PRIMARY KEY,
                supplier_id TEXT NOT NULL,
                po_number TEXT UNIQUE NOT NULL,
                order_date TEXT NOT NULL,
                requested_delivery_date TEXT,
                expected_delivery_date TEXT,
                actual_delivery_date TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, CONFIRMED, SHIPPED, RECEIVED, CANCELLED
                total_value REAL,
                currency TEXT DEFAULT 'USD',
                payment_terms TEXT,
                delivery_address TEXT,
                buyer_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            )
        """)
        
        # Purchase Order Line Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                fabric_type_id TEXT,
                material_description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_measure TEXT NOT NULL, -- METERS, KG, PIECES
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                received_quantity REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PENDING',
                FOREIGN KEY (order_id) REFERENCES purchase_orders (order_id),
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id)
            )
        """)
        
    def _create_customer_management_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create customer management tables."""
        
        # Customers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                customer_code TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                postal_code TEXT,
                credit_limit REAL,
                payment_terms INTEGER DEFAULT 30, -- Days
                customer_type TEXT, -- RETAIL, WHOLESALE, MANUFACTURER
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
                tax_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Customer Preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_preferences (
                pref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                fabric_type_id TEXT,
                preferred_colors TEXT, -- JSON array
                preferred_quality_grade TEXT,
                price_sensitivity INTEGER DEFAULT 3, -- 1-5 scale
                delivery_time_preference INTEGER, -- Days
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id)
            )
        """)
        
    def _create_supplier_management_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create supplier management tables."""
        
        # Suppliers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id TEXT PRIMARY KEY,
                supplier_code TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                postal_code TEXT,
                supplier_type TEXT, -- FABRIC, THREAD, ACCESSORIES, MACHINERY
                payment_terms INTEGER DEFAULT 30,
                lead_time_days INTEGER DEFAULT 14,
                quality_rating REAL DEFAULT 3.0, -- 1-5 scale
                delivery_rating REAL DEFAULT 3.0,
                price_rating REAL DEFAULT 3.0,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                certifications TEXT, -- JSON array
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Supplier Performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_performance (
                perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id TEXT NOT NULL,
                evaluation_date TEXT NOT NULL,
                quality_score REAL NOT NULL,
                delivery_score REAL NOT NULL,
                price_competitiveness REAL NOT NULL,
                service_score REAL NOT NULL,
                overall_score REAL NOT NULL,
                comments TEXT,
                evaluator_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            )
        """)
        
    def _create_financial_transaction_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create financial transaction tables."""
        
        # Financial Transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id TEXT PRIMARY KEY,
                transaction_type TEXT NOT NULL, -- SALE, PURCHASE, PAYMENT, RECEIPT, ADJUSTMENT
                reference_id TEXT, -- Order ID, Invoice ID, etc.
                reference_type TEXT, -- SALES_ORDER, PURCHASE_ORDER, etc.
                customer_id TEXT,
                supplier_id TEXT,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                transaction_date TEXT NOT NULL,
                due_date TEXT,
                payment_status TEXT DEFAULT 'PENDING', -- PENDING, PAID, OVERDUE, CANCELLED
                payment_method TEXT,
                description TEXT,
                gl_account TEXT, -- General ledger account code
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            )
        """)
        
        # Cost Centers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_centers (
                cost_center_id TEXT PRIMARY KEY,
                cost_center_name TEXT NOT NULL,
                department TEXT NOT NULL,
                manager_id TEXT,
                budget_amount REAL,
                budget_period TEXT, -- MONTHLY, QUARTERLY, ANNUAL
                active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        
        # Production Costs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_costs (
                cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                cost_type TEXT NOT NULL, -- MATERIAL, LABOR, OVERHEAD
                cost_center_id TEXT,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                cost_date TEXT NOT NULL,
                description TEXT,
                quantity REAL,
                unit_cost REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES production_orders (order_id),
                FOREIGN KEY (cost_center_id) REFERENCES cost_centers (cost_center_id)
            )
        """)
        
    def _create_etl_pipeline_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create ETL pipeline and data processing tables."""
        
        # ETL Job Definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etl_jobs (
                job_id TEXT PRIMARY KEY,
                job_name TEXT NOT NULL,
                job_type TEXT NOT NULL, -- SENSOR_DATA, PRODUCTION_DATA, QUALITY_DATA
                source_system TEXT,
                target_table TEXT,
                schedule_cron TEXT,
                transformation_rules TEXT, -- JSON
                active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # ETL Job Executions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etl_executions (
                execution_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'RUNNING', -- RUNNING, SUCCESS, FAILED, CANCELLED
                records_processed INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                error_message TEXT,
                log_file_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES etl_jobs (job_id)
            )
        """)
        
        # Data Staging Area
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_staging (
                staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                source_data TEXT, -- JSON of raw data
                processed_data TEXT, -- JSON of processed data
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSED, ERROR
                error_details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES etl_jobs (job_id),
                FOREIGN KEY (execution_id) REFERENCES etl_executions (execution_id)
            )
        """)
        
    def _create_data_quality_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create data quality monitoring tables."""
        
        # Data Quality Rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_rules (
                rule_id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                column_name TEXT,
                rule_type TEXT NOT NULL, -- NOT_NULL, RANGE_CHECK, FORMAT_CHECK, REFERENCE_CHECK
                rule_expression TEXT, -- SQL or regex expression
                severity TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
                active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Data Quality Checks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_checks (
                check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                execution_time TEXT NOT NULL,
                records_checked INTEGER,
                records_passed INTEGER,
                records_failed INTEGER,
                pass_rate REAL,
                status TEXT NOT NULL, -- PASS, FAIL, WARNING
                details TEXT, -- JSON with failure details
                created_at TEXT NOT NULL,
                FOREIGN KEY (rule_id) REFERENCES data_quality_rules (rule_id)
            )
        """)
        
        # Data Quality Issues
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_issues (
                issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                rule_id TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT,
                issue_description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN', -- OPEN, INVESTIGATING, RESOLVED, IGNORED
                assigned_to TEXT,
                resolution_notes TEXT,
                detected_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (check_id) REFERENCES data_quality_checks (check_id),
                FOREIGN KEY (rule_id) REFERENCES data_quality_rules (rule_id)
            )
        """)
        
    def _create_aggregation_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create pre-aggregated tables for faster analytics."""
        
        # Daily Production Summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_production_summary (
                summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                production_date TEXT NOT NULL,
                line_id TEXT,
                fabric_type_id TEXT,
                total_pieces_produced INTEGER DEFAULT 0,
                total_meters_produced REAL DEFAULT 0,
                total_runtime_hours REAL DEFAULT 0,
                total_downtime_minutes REAL DEFAULT 0,
                average_efficiency REAL DEFAULT 0,
                defect_count INTEGER DEFAULT 0,
                defect_rate REAL DEFAULT 0,
                labor_hours REAL DEFAULT 0,
                total_cost REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (line_id) REFERENCES production_lines (line_id),
                FOREIGN KEY (fabric_type_id) REFERENCES fabric_types (fabric_type_id),
                UNIQUE(production_date, line_id, fabric_type_id)
            )
        """)
        
        # Monthly KPI Summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_kpi_summary (
                kpi_id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL, -- YYYY-MM format
                total_production_pieces INTEGER DEFAULT 0,
                total_production_meters REAL DEFAULT 0,
                overall_efficiency REAL DEFAULT 0,
                quality_pass_rate REAL DEFAULT 0,
                customer_satisfaction REAL DEFAULT 0,
                on_time_delivery_rate REAL DEFAULT 0,
                total_revenue REAL DEFAULT 0,
                total_costs REAL DEFAULT 0,
                gross_margin REAL DEFAULT 0,
                active_customers INTEGER DEFAULT 0,
                new_customers INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(year_month)
            )
        """)
        
    def _create_mcp_integration_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create tables for Agent-MCP integration."""
        
        # Textile ERP Tasks (extends the main tasks table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS textile_tasks (
                task_id TEXT PRIMARY KEY,
                erp_entity_type TEXT NOT NULL, -- PRODUCTION_ORDER, QUALITY_INSPECTION, etc.
                erp_entity_id TEXT NOT NULL,
                task_category TEXT NOT NULL, -- PRODUCTION, QUALITY, INVENTORY, MAINTENANCE
                ai_recommendations TEXT, -- JSON with AI suggestions
                automation_level INTEGER DEFAULT 0, -- 0=Manual, 1=Semi-auto, 2=Fully-auto
                business_impact TEXT, -- LOW, MEDIUM, HIGH, CRITICAL
                estimated_savings REAL, -- Cost savings estimate
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id)
            )
        """)
        
        # AI/ML Model Performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_model_performance (
                perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                use_case TEXT NOT NULL, -- QUALITY_PREDICTION, DEMAND_FORECAST, etc.
                accuracy_score REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                training_date TEXT,
                evaluation_date TEXT NOT NULL,
                data_size INTEGER,
                feature_importance TEXT, -- JSON
                created_at TEXT NOT NULL
            )
        """)
        
        # Process Optimization Suggestions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_suggestions (
                suggestion_id TEXT PRIMARY KEY,
                process_area TEXT NOT NULL, -- PRODUCTION, QUALITY, INVENTORY, ENERGY
                suggestion_type TEXT NOT NULL, -- EFFICIENCY, COST_REDUCTION, QUALITY_IMPROVEMENT
                description TEXT NOT NULL,
                current_state_metrics TEXT, -- JSON
                projected_improvement TEXT, -- JSON
                implementation_effort TEXT, -- LOW, MEDIUM, HIGH
                estimated_roi REAL,
                confidence_level REAL, -- 0-1
                status TEXT DEFAULT 'PROPOSED', -- PROPOSED, APPROVED, IMPLEMENTING, COMPLETED, REJECTED
                agent_id TEXT, -- Which agent suggested this
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
    def _create_performance_indexes(self, cursor: sqlite3.Cursor) -> None:
        """Create indexes for optimal query performance."""
        
        # Fabric Inventory Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fabric_inventory_type ON fabric_inventory (fabric_type_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fabric_inventory_supplier ON fabric_inventory (supplier_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fabric_inventory_location ON fabric_inventory (location_warehouse, location_zone)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_movements_inventory_id ON inventory_movements (inventory_id, moved_at)")
        
        # Production Order Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders (status, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_orders_dates ON production_orders (planned_start_date, planned_end_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_operations_order ON production_operations (order_id, operation_sequence)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_operations_machine ON production_operations (machine_id, start_time)")
        
        # Quality Control Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_inspections_order ON quality_inspections (order_id, inspection_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_inspections_result ON quality_inspections (overall_result, inspection_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_test_results_inspection ON quality_test_results (inspection_id)")
        
        # Machine Management Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machines_type_status ON machines (machine_type, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_maintenance_machine_date ON machine_maintenance (machine_id, actual_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_maintenance_type ON machine_maintenance (maintenance_type, status)")
        
        # Worker Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workers_department_active ON workers (department, active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_assignments_worker ON worker_assignments (worker_id, assigned_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_performance_worker_date ON worker_performance (worker_id, date)")
        
        # Sensor Data Indexes (Critical for performance)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_timestamp ON sensor_readings (sensor_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_hourly_sensor_hour ON sensor_readings_hourly (sensor_id, hour_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_daily_sensor_date ON sensor_readings_daily (sensor_id, date)")
        
        # Machine Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_status_machine_timestamp ON machine_status_realtime (machine_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_performance_machine_hour ON machine_performance_hourly (machine_id, hour_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_downtime_machine_start ON machine_downtime (machine_id, start_time)")
        
        # Environmental Monitoring Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_environmental_readings_zone_timestamp ON environmental_readings (zone_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_environmental_alerts_zone_triggered ON environmental_alerts (zone_id, triggered_at)")
        
        # Sales & Purchase Order Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_date ON sales_orders (customer_id, order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_orders_status ON sales_orders (status, order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_date ON purchase_orders (supplier_id, order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders (status, order_date)")
        
        # Financial Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_type_date ON financial_transactions (transaction_type, transaction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_customer ON financial_transactions (customer_id, transaction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_supplier ON financial_transactions (supplier_id, transaction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_costs_order ON production_costs (order_id, cost_date)")
        
        # ETL Pipeline Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_etl_executions_job_start ON etl_executions (job_id, start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_staging_job_execution ON data_staging (job_id, execution_id)")
        
        # Data Quality Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_quality_checks_rule_time ON data_quality_checks (rule_id, execution_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_quality_issues_status ON data_quality_issues (status, detected_at)")
        
        # Aggregation Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_production_summary_date_line ON daily_production_summary (production_date, line_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_kpi_summary_year_month ON monthly_kpi_summary (year_month)")
        
        # MCP Integration Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_textile_tasks_entity ON textile_tasks (erp_entity_type, erp_entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_textile_tasks_category ON textile_tasks (task_category, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_model_performance_name_date ON ai_model_performance (model_name, evaluation_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_optimization_suggestions_area_status ON optimization_suggestions (process_area, status)")
        
    def _create_analytical_views(self, cursor: sqlite3.Cursor) -> None:
        """Create views for common analytical queries."""
        
        # Production Efficiency View
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_production_efficiency AS
            SELECT 
                po.order_id,
                po.product_type,
                ft.fabric_name,
                pl.line_name,
                po.quantity_pieces,
                po.planned_start_date,
                po.planned_end_date,
                po.actual_start_date,
                po.actual_end_date,
                CASE 
                    WHEN po.actual_end_date IS NOT NULL AND po.planned_end_date IS NOT NULL 
                    THEN julianday(po.planned_end_date) - julianday(po.actual_end_date)
                    ELSE NULL 
                END AS schedule_variance_days,
                po.completion_percentage,
                po.status,
                (
                    SELECT AVG(mph.avg_efficiency) 
                    FROM machine_performance_hourly mph 
                    JOIN machines m ON mph.machine_id = m.machine_id 
                    WHERE m.line_id = pl.line_id
                    AND mph.hour_timestamp BETWEEN po.actual_start_date AND COALESCE(po.actual_end_date, datetime('now'))
                ) AS avg_line_efficiency
            FROM production_orders po
            JOIN fabric_types ft ON po.fabric_type_id = ft.fabric_type_id
            LEFT JOIN production_lines pl ON po.assigned_line = pl.line_id
        """)
        
        # Quality Metrics View
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_quality_metrics AS
            SELECT 
                qi.order_id,
                po.product_type,
                ft.fabric_name,
                qi.inspection_date,
                qi.inspection_type,
                qi.overall_result,
                qi.defect_rate,
                qi.critical_defects,
                qi.major_defects,
                qi.minor_defects,
                (qi.critical_defects + qi.major_defects + qi.minor_defects) AS total_defects,
                CASE 
                    WHEN qi.sample_size > 0 
                    THEN ROUND((qi.critical_defects + qi.major_defects + qi.minor_defects) * 100.0 / qi.sample_size, 2)
                    ELSE 0 
                END AS defect_percentage
            FROM quality_inspections qi
            JOIN production_orders po ON qi.order_id = po.order_id
            JOIN fabric_types ft ON po.fabric_type_id = ft.fabric_type_id
        """)
        
        # Inventory Status View
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_inventory_status AS
            SELECT 
                fi.inventory_id,
                ft.fabric_name,
                ft.fabric_category,
                fi.lot_number,
                s.company_name AS supplier_name,
                fi.quantity_meters,
                fi.reserved_meters,
                fi.available_meters,
                fi.location_warehouse,
                fi.location_zone,
                fi.location_bin,
                fi.quality_grade,
                fi.received_date,
                julianday('now') - julianday(fi.received_date) AS age_days,
                CASE 
                    WHEN fi.available_meters <= 0 THEN 'OUT_OF_STOCK'
                    WHEN fi.available_meters < 100 THEN 'LOW_STOCK'
                    WHEN julianday('now') - julianday(fi.received_date) > 365 THEN 'AGING'
                    ELSE 'NORMAL'
                END AS status_flag
            FROM fabric_inventory fi
            JOIN fabric_types ft ON fi.fabric_type_id = ft.fabric_type_id
            LEFT JOIN suppliers s ON fi.supplier_id = s.supplier_id
        """)
        
        # Machine Utilization View
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_machine_utilization AS
            SELECT 
                m.machine_id,
                m.machine_name,
                m.machine_type,
                pl.line_name,
                m.status,
                (
                    SELECT SUM(mph.runtime_minutes) / 60.0 
                    FROM machine_performance_hourly mph 
                    WHERE mph.machine_id = m.machine_id 
                    AND mph.hour_timestamp >= date('now', '-7 days')
                ) AS runtime_hours_7_days,
                (
                    SELECT AVG(mph.avg_efficiency) 
                    FROM machine_performance_hourly mph 
                    WHERE mph.machine_id = m.machine_id 
                    AND mph.hour_timestamp >= date('now', '-7 days')
                ) AS avg_efficiency_7_days,
                (
                    SELECT COUNT(*) 
                    FROM machine_downtime md 
                    WHERE md.machine_id = m.machine_id 
                    AND md.start_time >= date('now', '-7 days')
                ) AS downtime_events_7_days
            FROM machines m
            LEFT JOIN production_lines pl ON m.line_id = pl.line_id
        """)
        
    def _create_automation_triggers(self, cursor: sqlite3.Cursor) -> None:
        """Create triggers for automated processes."""
        
        # Automatically update inventory available meters
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_update_inventory_available
            AFTER UPDATE ON fabric_inventory
            FOR EACH ROW
            BEGIN
                UPDATE fabric_inventory 
                SET updated_at = datetime('now')
                WHERE inventory_id = NEW.inventory_id;
            END
        """)
        
        # Automatically create sensor aggregations (hourly)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_aggregate_sensor_hourly
            AFTER INSERT ON sensor_readings
            FOR EACH ROW
            WHEN NEW.quality_flag = 0
            BEGIN
                INSERT OR REPLACE INTO sensor_readings_hourly (
                    sensor_id,
                    hour_timestamp,
                    avg_value,
                    min_value,
                    max_value,
                    sample_count,
                    created_at
                )
                SELECT 
                    NEW.sensor_id,
                    datetime(NEW.timestamp, 'start of hour'),
                    AVG(value),
                    MIN(value),
                    MAX(value),
                    COUNT(*),
                    datetime('now')
                FROM sensor_readings 
                WHERE sensor_id = NEW.sensor_id 
                AND timestamp >= datetime(NEW.timestamp, 'start of hour')
                AND timestamp < datetime(NEW.timestamp, 'start of hour', '+1 hour')
                AND quality_flag = 0;
            END
        """)
        
        # Update production order completion percentage
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_update_production_completion
            AFTER UPDATE ON production_operations
            FOR EACH ROW
            WHEN NEW.status = 'COMPLETED' AND OLD.status != 'COMPLETED'
            BEGIN
                UPDATE production_orders 
                SET 
                    completion_percentage = (
                        SELECT 
                            ROUND(
                                (COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) * 100.0) / COUNT(*), 
                                2
                            )
                        FROM production_operations 
                        WHERE order_id = NEW.order_id
                    ),
                    updated_at = datetime('now')
                WHERE order_id = NEW.order_id;
                
                -- If all operations are complete, update order status
                UPDATE production_orders 
                SET 
                    status = 'COMPLETED',
                    actual_end_date = datetime('now')
                WHERE order_id = NEW.order_id
                AND NOT EXISTS (
                    SELECT 1 FROM production_operations 
                    WHERE order_id = NEW.order_id AND status != 'COMPLETED'
                );
            END
        """)
        
        # Create MCP task when quality issue detected
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_create_quality_task
            AFTER INSERT ON quality_inspections
            FOR EACH ROW
            WHEN NEW.overall_result = 'FAIL' OR NEW.critical_defects > 0
            BEGIN
                INSERT INTO tasks (
                    task_id,
                    title,
                    description,
                    created_by,
                    status,
                    priority,
                    created_at,
                    updated_at
                ) VALUES (
                    'QUALITY-' || NEW.inspection_id,
                    'Quality Issue Detected - Order ' || NEW.order_id,
                    'Quality inspection failed with ' || NEW.critical_defects || 
                    ' critical defects and ' || NEW.major_defects || ' major defects. ' ||
                    'Immediate attention required.',
                    'textile_erp_system',
                    'pending',
                    CASE WHEN NEW.critical_defects > 0 THEN 'high' ELSE 'medium' END,
                    datetime('now'),
                    datetime('now')
                );
                
                INSERT INTO textile_tasks (
                    task_id,
                    erp_entity_type,
                    erp_entity_id,
                    task_category,
                    business_impact,
                    created_at
                ) VALUES (
                    'QUALITY-' || NEW.inspection_id,
                    'QUALITY_INSPECTION',
                    NEW.inspection_id,
                    'QUALITY',
                    CASE WHEN NEW.critical_defects > 0 THEN 'HIGH' ELSE 'MEDIUM' END,
                    datetime('now')
                );
            END
        """)
        
    def create_partitioned_sensor_tables(self, cursor: sqlite3.Cursor, start_date: datetime, num_months: int = 12) -> None:
        """
        Create monthly partitioned sensor tables for high-volume time-series data.
        This provides better performance for time-based queries and easier archival.
        """
        
        for i in range(num_months):
            month_date = start_date + timedelta(days=30*i)
            table_suffix = month_date.strftime("%Y_%m")
            
            # Monthly sensor readings table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS sensor_readings_{table_suffix} (
                    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL CHECK (timestamp LIKE '{month_date.strftime("%Y-%m")}%'),
                    value REAL NOT NULL,
                    quality_flag INTEGER DEFAULT 0,
                    batch_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id)
                )
            """)
            
            # Indexes for partitioned table
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_sensor_readings_{table_suffix}_sensor_timestamp ON sensor_readings_{table_suffix} (sensor_id, timestamp)")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_sensor_readings_{table_suffix}_timestamp ON sensor_readings_{table_suffix} (timestamp)")
            
        logger.info(f"Created {num_months} partitioned sensor tables")


# Integration functions for Agent-MCP

def get_textile_production_context() -> Dict[str, Any]:
    """Get current textile production context for Agent-MCP."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get active production orders
        cursor.execute("""
            SELECT COUNT(*) as active_orders, 
                   SUM(quantity_pieces) as total_pieces,
                   AVG(completion_percentage) as avg_completion
            FROM production_orders 
            WHERE status IN ('IN_PROGRESS', 'PENDING')
        """)
        production_summary = dict(cursor.fetchone() or {})
        
        # Get quality metrics
        cursor.execute("""
            SELECT AVG(defect_rate) as avg_defect_rate,
                   COUNT(*) as total_inspections,
                   SUM(CASE WHEN overall_result = 'PASS' THEN 1 ELSE 0 END) as passed_inspections
            FROM quality_inspections 
            WHERE inspection_date >= date('now', '-7 days')
        """)
        quality_summary = dict(cursor.fetchone() or {})
        
        # Get machine status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM machines 
            GROUP BY status
        """)
        machine_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        return {
            'production': production_summary,
            'quality': quality_summary,
            'machines': machine_status,
            'timestamp': datetime.now().isoformat()
        }
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting textile production context: {e}")
        return {}
    finally:
        if conn:
            conn.close()


def initialize_textile_erp_schema():
    """Initialize the textile ERP schema - called during application startup."""
    try:
        schema_manager = TextileERPSchema()
        schema_manager.init_textile_erp_tables()
        logger.info("Textile ERP schema initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize textile ERP schema: {e}")
        return False


# Schema version for migration management
TEXTILE_ERP_SCHEMA_VERSION = "1.0.0"

def get_schema_version() -> str:
    """Get the current textile ERP schema version."""
    return TEXTILE_ERP_SCHEMA_VERSION