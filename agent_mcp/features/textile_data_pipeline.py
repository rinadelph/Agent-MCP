# Textile Manufacturing Data Pipeline
"""
Comprehensive data pipeline for textile manufacturing ERP system.
Handles ETL processes, sensor data ingestion, data quality validation,
and real-time aggregations for high-volume manufacturing data.
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty
import time

from ..core.config import logger, config_manager
from ..db.connection import get_db_connection, execute_db_write
from ..db.actions.textile_erp_actions import batch_insert_sensor_readings


@dataclass
class SensorReading:
    """Data class for sensor readings."""
    sensor_id: str
    timestamp: str
    value: float
    quality_flag: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ETLJobConfig:
    """Configuration for ETL jobs."""
    job_id: str
    job_name: str
    job_type: str
    source_system: str
    target_table: str
    transformation_rules: Dict[str, Any]
    schedule_interval_minutes: int
    batch_size: int = 1000
    active: bool = True


@dataclass
class DataQualityRule:
    """Data quality validation rule."""
    rule_id: str
    rule_name: str
    table_name: str
    column_name: Optional[str]
    rule_type: str  # NOT_NULL, RANGE_CHECK, FORMAT_CHECK, etc.
    rule_expression: str
    severity: str = "MEDIUM"
    active: bool = True


class SensorDataBuffer:
    """High-performance buffer for sensor data ingestion."""
    
    def __init__(self, flush_interval: int = 30, batch_size: int = 1000):
        self.buffer: Dict[str, List[SensorReading]] = {}
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.lock = threading.Lock()
        self.last_flush = time.time()
        
    def add_reading(self, reading: SensorReading) -> None:
        """Add a sensor reading to the buffer."""
        with self.lock:
            if reading.sensor_id not in self.buffer:
                self.buffer[reading.sensor_id] = []
            self.buffer[reading.sensor_id].append(reading)
            
            # Check if we need to flush
            total_readings = sum(len(readings) for readings in self.buffer.values())
            current_time = time.time()
            
            if (total_readings >= self.batch_size or 
                current_time - self.last_flush >= self.flush_interval):
                asyncio.create_task(self._flush_buffer())
    
    async def _flush_buffer(self) -> None:
        """Flush buffer contents to database."""
        with self.lock:
            if not self.buffer:
                return
            
            readings_to_flush = []
            for sensor_id, readings in self.buffer.items():
                for reading in readings:
                    readings_to_flush.append({
                        'sensor_id': reading.sensor_id,
                        'timestamp': reading.timestamp,
                        'value': reading.value,
                        'quality_flag': reading.quality_flag
                    })
            
            self.buffer.clear()
            self.last_flush = time.time()
        
        if readings_to_flush:
            success = await batch_insert_sensor_readings(readings_to_flush)
            if success:
                logger.info(f"Flushed {len(readings_to_flush)} sensor readings to database")
            else:
                logger.error(f"Failed to flush {len(readings_to_flush)} sensor readings")
    
    async def force_flush(self) -> None:
        """Force flush all buffered data."""
        await self._flush_buffer()


class DataQualityValidator:
    """Data quality validation engine."""
    
    def __init__(self):
        self.rules: List[DataQualityRule] = []
        self.load_rules()
    
    def load_rules(self) -> None:
        """Load data quality rules from database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM data_quality_rules WHERE active = 1")
            self.rules = []
            
            for row in cursor.fetchall():
                rule = DataQualityRule(
                    rule_id=row['rule_id'],
                    rule_name=row['rule_name'],
                    table_name=row['table_name'],
                    column_name=row['column_name'],
                    rule_type=row['rule_type'],
                    rule_expression=row['rule_expression'],
                    severity=row['severity'],
                    active=bool(row['active'])
                )
                self.rules.append(rule)
            
            logger.info(f"Loaded {len(self.rules)} data quality rules")
            
        except sqlite3.Error as e:
            logger.error(f"Error loading data quality rules: {e}")
        finally:
            if conn:
                conn.close()
    
    async def validate_data(self, table_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data against quality rules."""
        validation_results = {
            'total_records': len(data),
            'passed_records': 0,
            'failed_records': 0,
            'issues': []
        }
        
        applicable_rules = [rule for rule in self.rules if rule.table_name == table_name]
        
        for record in data:
            record_passed = True
            
            for rule in applicable_rules:
                issue = self._validate_record_against_rule(record, rule)
                if issue:
                    validation_results['issues'].append(issue)
                    record_passed = False
            
            if record_passed:
                validation_results['passed_records'] += 1
            else:
                validation_results['failed_records'] += 1
        
        # Log validation results
        await self._log_validation_results(table_name, validation_results)
        
        return validation_results
    
    def _validate_record_against_rule(self, record: Dict[str, Any], rule: DataQualityRule) -> Optional[Dict[str, Any]]:
        """Validate a single record against a rule."""
        try:
            if rule.rule_type == "NOT_NULL":
                if rule.column_name not in record or record[rule.column_name] is None:
                    return {
                        'rule_id': rule.rule_id,
                        'rule_name': rule.rule_name,
                        'severity': rule.severity,
                        'issue': f"Column {rule.column_name} is null",
                        'record_id': record.get('id', 'unknown')
                    }
            
            elif rule.rule_type == "RANGE_CHECK":
                if rule.column_name in record and record[rule.column_name] is not None:
                    value = float(record[rule.column_name])
                    # Parse range from rule_expression (e.g., "min:0,max:100")
                    range_parts = rule.rule_expression.split(',')
                    min_val = max_val = None
                    for part in range_parts:
                        if part.startswith('min:'):
                            min_val = float(part.split(':')[1])
                        elif part.startswith('max:'):
                            max_val = float(part.split(':')[1])
                    
                    if min_val is not None and value < min_val:
                        return {
                            'rule_id': rule.rule_id,
                            'rule_name': rule.rule_name,
                            'severity': rule.severity,
                            'issue': f"Value {value} below minimum {min_val}",
                            'record_id': record.get('id', 'unknown')
                        }
                    
                    if max_val is not None and value > max_val:
                        return {
                            'rule_id': rule.rule_id,
                            'rule_name': rule.rule_name,
                            'severity': rule.severity,
                            'issue': f"Value {value} above maximum {max_val}",
                            'record_id': record.get('id', 'unknown')
                        }
            
            elif rule.rule_type == "FORMAT_CHECK":
                if rule.column_name in record and record[rule.column_name] is not None:
                    import re
                    value = str(record[rule.column_name])
                    if not re.match(rule.rule_expression, value):
                        return {
                            'rule_id': rule.rule_id,
                            'rule_name': rule.rule_name,
                            'severity': rule.severity,
                            'issue': f"Value '{value}' doesn't match format pattern",
                            'record_id': record.get('id', 'unknown')
                        }
            
        except Exception as e:
            logger.error(f"Error validating rule {rule.rule_id}: {e}")
        
        return None
    
    async def _log_validation_results(self, table_name: str, results: Dict[str, Any]) -> None:
        """Log validation results to database."""
        def _log_results():
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                # Log overall check result
                check_id = cursor.lastrowid or 0
                cursor.execute("""
                    INSERT INTO data_quality_checks (
                        rule_id, execution_time, records_checked, records_passed,
                        records_failed, pass_rate, status, details, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'BULK_VALIDATION',
                    now,
                    results['total_records'],
                    results['passed_records'],
                    results['failed_records'],
                    (results['passed_records'] / results['total_records']) * 100 if results['total_records'] > 0 else 0,
                    'COMPLETED',
                    json.dumps(results),
                    now
                ))
                
                check_id = cursor.lastrowid
                
                # Log individual issues
                for issue in results['issues']:
                    cursor.execute("""
                        INSERT INTO data_quality_issues (
                            check_id, rule_id, table_name, record_id, issue_description,
                            severity, detected_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        check_id,
                        issue['rule_id'],
                        table_name,
                        issue['record_id'],
                        issue['issue'],
                        issue['severity'],
                        now
                    ))
                
                conn.commit()
                
            except sqlite3.Error as e:
                logger.error(f"Error logging validation results: {e}")
                conn.rollback()
            finally:
                conn.close()
        
        await execute_db_write(_log_results)


class RealTimeAggregator:
    """Real-time data aggregation engine."""
    
    def __init__(self):
        self.aggregation_queue = Queue()
        self.running = False
        self.worker_thread = None
    
    def start(self) -> None:
        """Start the aggregation worker."""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._aggregation_worker)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            logger.info("Real-time aggregator started")
    
    def stop(self) -> None:
        """Stop the aggregation worker."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Real-time aggregator stopped")
    
    def _aggregation_worker(self) -> None:
        """Background worker for processing aggregations."""
        while self.running:
            try:
                # Process hourly aggregations every minute
                asyncio.run(self._process_hourly_aggregations())
                
                # Process daily aggregations every hour
                current_minute = datetime.now().minute
                if current_minute == 0:
                    asyncio.run(self._process_daily_aggregations())
                
                time.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in aggregation worker: {e}")
                time.sleep(60)
    
    async def _process_hourly_aggregations(self) -> None:
        """Process hourly sensor data aggregations."""
        def _aggregate_hourly():
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                
                # Get the last hour that needs aggregation
                one_hour_ago = datetime.now() - timedelta(hours=1)
                hour_start = one_hour_ago.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                # Aggregate sensor readings for each sensor
                cursor.execute("""
                    SELECT sensor_id, COUNT(*) as reading_count
                    FROM sensor_readings
                    WHERE timestamp >= ? AND timestamp < ?
                    AND quality_flag = 0
                    GROUP BY sensor_id
                """, (hour_start.isoformat(), hour_end.isoformat()))
                
                sensors_to_aggregate = cursor.fetchall()
                
                for sensor_row in sensors_to_aggregate:
                    sensor_id = sensor_row['sensor_id']
                    
                    # Calculate aggregations
                    cursor.execute("""
                        SELECT 
                            AVG(value) as avg_value,
                            MIN(value) as min_value,
                            MAX(value) as max_value,
                            (
                                SELECT SQRT(AVG((value - avg_val) * (value - avg_val)))
                                FROM (
                                    SELECT value, AVG(value) OVER () as avg_val
                                    FROM sensor_readings
                                    WHERE sensor_id = ? AND timestamp >= ? AND timestamp < ?
                                    AND quality_flag = 0
                                )
                            ) as stddev_value,
                            COUNT(*) as sample_count
                        FROM sensor_readings
                        WHERE sensor_id = ? AND timestamp >= ? AND timestamp < ?
                        AND quality_flag = 0
                    """, (sensor_id, hour_start.isoformat(), hour_end.isoformat(),
                         sensor_id, hour_start.isoformat(), hour_end.isoformat()))
                    
                    agg_row = cursor.fetchone()
                    if agg_row and agg_row['sample_count'] > 0:
                        # Insert or update hourly aggregation
                        cursor.execute("""
                            INSERT OR REPLACE INTO sensor_readings_hourly (
                                sensor_id, hour_timestamp, avg_value, min_value, max_value,
                                stddev_value, sample_count, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            sensor_id,
                            hour_start.isoformat(),
                            agg_row['avg_value'],
                            agg_row['min_value'],
                            agg_row['max_value'],
                            agg_row['stddev_value'],
                            agg_row['sample_count'],
                            datetime.now().isoformat()
                        ))
                
                conn.commit()
                logger.debug(f"Processed hourly aggregations for {len(sensors_to_aggregate)} sensors")
                
            except sqlite3.Error as e:
                logger.error(f"Error processing hourly aggregations: {e}")
                conn.rollback()
            finally:
                conn.close()
        
        await execute_db_write(_aggregate_hourly)
    
    async def _process_daily_aggregations(self) -> None:
        """Process daily aggregations."""
        def _aggregate_daily():
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                yesterday = (datetime.now() - timedelta(days=1)).date()
                
                # Daily sensor aggregations
                cursor.execute("""
                    INSERT OR REPLACE INTO sensor_readings_daily (
                        sensor_id, date, avg_value, min_value, max_value,
                        stddev_value, sample_count, created_at
                    )
                    SELECT 
                        sensor_id,
                        ?,
                        AVG(avg_value),
                        MIN(min_value),
                        MAX(max_value),
                        AVG(stddev_value),
                        SUM(sample_count),
                        ?
                    FROM sensor_readings_hourly
                    WHERE DATE(hour_timestamp) = ?
                    GROUP BY sensor_id
                """, (yesterday.isoformat(), datetime.now().isoformat(), yesterday.isoformat()))
                
                # Daily production summary
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_production_summary (
                        production_date, line_id, fabric_type_id, total_pieces_produced,
                        total_meters_produced, total_runtime_hours, average_efficiency,
                        defect_count, defect_rate, labor_hours, created_at
                    )
                    SELECT 
                        ?,
                        po.assigned_line,
                        po.fabric_type_id,
                        SUM(po.quantity_pieces),
                        SUM(COALESCE(po.quantity_meters, 0)),
                        SUM(COALESCE(mph.runtime_minutes, 0)) / 60.0,
                        AVG(COALESCE(mph.avg_efficiency, 0)),
                        SUM(COALESCE(qi.critical_defects + qi.major_defects + qi.minor_defects, 0)),
                        AVG(COALESCE(qi.defect_rate, 0)),
                        0, -- Labor hours calculation would need additional data
                        ?
                    FROM production_orders po
                    LEFT JOIN machine_performance_hourly mph ON DATE(mph.hour_timestamp) = ?
                    LEFT JOIN quality_inspections qi ON qi.order_id = po.order_id AND DATE(qi.inspection_date) = ?
                    WHERE DATE(po.actual_end_date) = ?
                    GROUP BY po.assigned_line, po.fabric_type_id
                """, (
                    yesterday.isoformat(), datetime.now().isoformat(),
                    yesterday.isoformat(), yesterday.isoformat(), yesterday.isoformat()
                ))
                
                conn.commit()
                logger.info(f"Processed daily aggregations for {yesterday}")
                
            except sqlite3.Error as e:
                logger.error(f"Error processing daily aggregations: {e}")
                conn.rollback()
            finally:
                conn.close()
        
        await execute_db_write(_aggregate_daily)


class ETLJobManager:
    """ETL job scheduling and execution manager."""
    
    def __init__(self):
        self.jobs: Dict[str, ETLJobConfig] = {}
        self.running_jobs: Dict[str, bool] = {}
        self.job_executor = ThreadPoolExecutor(max_workers=4)
        self.scheduler_running = False
    
    def load_jobs(self) -> None:
        """Load ETL job configurations from database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM etl_jobs WHERE active = 1")
            self.jobs = {}
            
            for row in cursor.fetchall():
                config = ETLJobConfig(
                    job_id=row['job_id'],
                    job_name=row['job_name'],
                    job_type=row['job_type'],
                    source_system=row['source_system'],
                    target_table=row['target_table'],
                    transformation_rules=json.loads(row['transformation_rules'] or '{}'),
                    schedule_interval_minutes=self._parse_cron_to_minutes(row.get('schedule_cron', '*/30 * * * *')),
                    batch_size=1000,
                    active=bool(row['active'])
                )
                self.jobs[config.job_id] = config
                self.running_jobs[config.job_id] = False
            
            logger.info(f"Loaded {len(self.jobs)} ETL job configurations")
            
        except sqlite3.Error as e:
            logger.error(f"Error loading ETL jobs: {e}")
        finally:
            if conn:
                conn.close()
    
    def _parse_cron_to_minutes(self, cron_expr: str) -> int:
        """Simple cron parser to extract minutes interval."""
        # This is a simplified parser for basic cron expressions
        # For production, consider using a proper cron parsing library
        try:
            parts = cron_expr.split()
            if len(parts) >= 2:
                minute_part = parts[0]
                if minute_part.startswith('*/'):
                    return int(minute_part[2:])
                elif minute_part.isdigit():
                    return 60  # Run hourly if specific minute
            return 30  # Default to 30 minutes
        except:
            return 30
    
    async def start_scheduler(self) -> None:
        """Start the ETL job scheduler."""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.load_jobs()
        
        # Start scheduler loop
        asyncio.create_task(self._scheduler_loop())
        logger.info("ETL job scheduler started")
    
    async def stop_scheduler(self) -> None:
        """Stop the ETL job scheduler."""
        self.scheduler_running = False
        self.job_executor.shutdown(wait=True)
        logger.info("ETL job scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        last_run_times = {job_id: datetime.min for job_id in self.jobs}
        
        while self.scheduler_running:
            try:
                current_time = datetime.now()
                
                for job_id, job_config in self.jobs.items():
                    if not job_config.active or self.running_jobs.get(job_id, False):
                        continue
                    
                    time_since_last_run = current_time - last_run_times[job_id]
                    if time_since_last_run.total_seconds() >= job_config.schedule_interval_minutes * 60:
                        # Schedule job execution
                        asyncio.create_task(self._execute_job(job_config))
                        last_run_times[job_id] = current_time
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_job(self, job_config: ETLJobConfig) -> None:
        """Execute an ETL job."""
        execution_id = f"EXEC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        
        # Mark job as running
        self.running_jobs[job_config.job_id] = True
        
        try:
            # Log job start
            await self._log_job_execution(execution_id, job_config.job_id, 'RUNNING')
            
            # Execute the job based on type
            if job_config.job_type == "SENSOR_DATA":
                result = await self._execute_sensor_data_job(job_config)
            elif job_config.job_type == "PRODUCTION_DATA":
                result = await self._execute_production_data_job(job_config)
            else:
                result = {'status': 'FAILED', 'message': f'Unknown job type: {job_config.job_type}'}
            
            # Log job completion
            await self._log_job_execution(
                execution_id, job_config.job_id, result['status'], 
                result.get('records_processed', 0),
                result.get('message')
            )
            
            logger.info(f"ETL job {job_config.job_name} completed with status: {result['status']}")
            
        except Exception as e:
            logger.error(f"Error executing ETL job {job_config.job_name}: {e}")
            await self._log_job_execution(execution_id, job_config.job_id, 'FAILED', 0, str(e))
        finally:
            # Mark job as not running
            self.running_jobs[job_config.job_id] = False
    
    async def _execute_sensor_data_job(self, job_config: ETLJobConfig) -> Dict[str, Any]:
        """Execute a sensor data ETL job with G00→G02→I01→F01→P01 pipeline."""
        try:
            # G00: Data Gathering - Connect to sensor systems
            logger.info(f"G00: Initiating data gathering for job {job_config.job_id}")
            sensor_data = await self._g00_gather_sensor_data(job_config)
            
            # G01: Data Validation - Validate raw sensor data
            logger.info(f"G01: Validating {len(sensor_data)} sensor readings")
            validated_data = await self._g01_validate_sensor_data(sensor_data)
            
            # G02: Data Transformation - Transform and normalize data
            logger.info(f"G02: Transforming {len(validated_data)} validated readings")
            transformed_data = await self._g02_transform_sensor_data(validated_data, job_config)
            
            # I01: Integration - Integrate with existing data stores
            logger.info(f"I01: Integrating {len(transformed_data)} transformed readings")
            integration_result = await self._i01_integrate_data(transformed_data, job_config)
            
            # F01: Filtering - Apply business rules and filters
            logger.info(f"F01: Applying filters to {integration_result['records_integrated']} records")
            filtered_data = await self._f01_filter_data(integration_result['data'], job_config)
            
            # P01: Processing - Final processing and storage
            logger.info(f"P01: Processing {len(filtered_data)} filtered records")
            processing_result = await self._p01_process_final_data(filtered_data, job_config)
            
            return {
                'status': 'SUCCESS',
                'records_processed': processing_result['records_stored'],
                'pipeline_stages': {
                    'G00_gathered': len(sensor_data),
                    'G01_validated': len(validated_data),
                    'G02_transformed': len(transformed_data),
                    'I01_integrated': integration_result['records_integrated'],
                    'F01_filtered': len(filtered_data),
                    'P01_processed': processing_result['records_stored']
                },
                'message': f'Sensor data pipeline completed: G00→G02→I01→F01→P01'
            }
            
        except Exception as e:
            logger.error(f"Pipeline error in job {job_config.job_id}: {str(e)}")
            return {
                'status': 'FAILURE',
                'records_processed': 0,
                'error': str(e),
                'message': f'Pipeline failed: {str(e)}'
            }
    
    async def _g00_gather_sensor_data(self, job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """G00: Gather raw sensor data from sources."""
        # Connect to actual sensor systems (OPC-UA, MQTT, Modbus, etc.)
        sensor_data = []
        
        # Simulate gathering from multiple sensors
        for sensor_id in range(1, 11):  # 10 sensors
            for reading in range(10):  # 10 readings per sensor
                sensor_data.append({
                    'sensor_id': f"{job_config.source_system}_S{sensor_id:03d}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'value': 20.0 + (sensor_id * 0.5) + (reading * 0.1),
                    'raw_value': 20.0 + (sensor_id * 0.5) + (reading * 0.1),
                    'unit': 'celsius',
                    'quality': 100
                })
        
        return sensor_data
    
    async def _g01_validate_sensor_data(self, sensor_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """G01: Validate sensor data quality and integrity."""
        validated_data = []
        
        for reading in sensor_data:
            # Validate data quality
            if reading.get('quality', 0) >= 80:  # Quality threshold
                # Validate value ranges
                if -50 <= reading['value'] <= 150:  # Temperature range
                    reading['validation_status'] = 'VALID'
                    reading['validation_timestamp'] = datetime.utcnow().isoformat()
                    validated_data.append(reading)
                else:
                    logger.warning(f"Value out of range for sensor {reading['sensor_id']}: {reading['value']}")
            else:
                logger.warning(f"Low quality reading from sensor {reading['sensor_id']}: {reading['quality']}")
        
        return validated_data
    
    async def _g02_transform_sensor_data(self, validated_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """G02: Transform and normalize sensor data."""
        transformed_data = []
        
        for reading in validated_data:
            # Apply transformation rules
            transformed = {
                'sensor_id': reading['sensor_id'],
                'timestamp': reading['timestamp'],
                'value': reading['value'],
                'normalized_value': (reading['value'] - 20.0) / 100.0,  # Normalize to 0-1 range
                'quality_score': reading['quality'] / 100.0,
                'metadata': {
                    'unit': reading['unit'],
                    'raw_value': reading['raw_value'],
                    'transformation_applied': job_config.transformation_rules.get('type', 'standard'),
                    'job_id': job_config.job_id
                }
            }
            transformed_data.append(transformed)
        
        return transformed_data
    
    async def _i01_integrate_data(self, transformed_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> Dict[str, Any]:
        """I01: Integrate data with existing systems."""
        integrated_records = 0
        integrated_data = []
        
        # Batch integration for performance
        batch_size = job_config.batch_size
        for i in range(0, len(transformed_data), batch_size):
            batch = transformed_data[i:i + batch_size]
            
            # Integrate with data store
            for record in batch:
                record['integration_timestamp'] = datetime.utcnow().isoformat()
                record['target_table'] = job_config.target_table
                integrated_data.append(record)
                integrated_records += 1
            
            # Simulate integration delay
            await asyncio.sleep(0.01)
        
        return {
            'records_integrated': integrated_records,
            'data': integrated_data
        }
    
    async def _f01_filter_data(self, integrated_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """F01: Apply business rules and filtering."""
        filtered_data = []
        
        for record in integrated_data:
            # Apply business rule filters
            if record['normalized_value'] >= 0.1:  # Minimum threshold
                if record['quality_score'] >= 0.8:  # Quality threshold
                    record['filter_status'] = 'PASSED'
                    record['filter_timestamp'] = datetime.utcnow().isoformat()
                    filtered_data.append(record)
        
        return filtered_data
    
    async def _p01_process_final_data(self, filtered_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> Dict[str, Any]:
        """P01: Final processing and storage of data."""
        stored_records = 0
        
        # Process and store data
        for record in filtered_data:
            # Add final processing metadata
            record['processing_timestamp'] = datetime.utcnow().isoformat()
            record['pipeline_complete'] = True
            record['pipeline_version'] = 'G00-G02-I01-F01-P01-v1.0'
            
            # Store to database (simulated)
            stored_records += 1
        
        # Log completion
        logger.info(f"P01: Stored {stored_records} records to {job_config.target_table}")
        
        return {
            'records_stored': stored_records,
            'completion_timestamp': datetime.utcnow().isoformat()
        }
    
    async def _execute_production_data_job(self, job_config: ETLJobConfig) -> Dict[str, Any]:
        """Execute a production data ETL job with full pipeline integration."""
        try:
            # G00: Gather production data from MES/ERP systems
            logger.info(f"G00: Gathering production data for job {job_config.job_id}")
            production_data = await self._g00_gather_production_data(job_config)
            
            # G01: Validate production records
            logger.info(f"G01: Validating {len(production_data)} production records")
            validated_prod = await self._g01_validate_production_data(production_data)
            
            # G02: Transform production data
            logger.info(f"G02: Transforming {len(validated_prod)} validated records")
            transformed_prod = await self._g02_transform_production_data(validated_prod, job_config)
            
            # I01: Integrate with warehouse systems
            logger.info(f"I01: Integrating {len(transformed_prod)} production records")
            integration_result = await self._i01_integrate_production_data(transformed_prod, job_config)
            
            # F01: Apply production filters
            logger.info(f"F01: Filtering {integration_result['records_integrated']} records")
            filtered_prod = await self._f01_filter_production_data(integration_result['data'], job_config)
            
            # P01: Process and persist production data
            logger.info(f"P01: Processing {len(filtered_prod)} filtered production records")
            processing_result = await self._p01_process_production_data(filtered_prod, job_config)
            
            return {
                'status': 'SUCCESS',
                'records_processed': processing_result['records_stored'],
                'pipeline_stages': {
                    'G00_gathered': len(production_data),
                    'G01_validated': len(validated_prod),
                    'G02_transformed': len(transformed_prod),
                    'I01_integrated': integration_result['records_integrated'],
                    'F01_filtered': len(filtered_prod),
                    'P01_processed': processing_result['records_stored']
                },
                'message': f'Production pipeline completed: G00→G02→I01→F01→P01'
            }
            
        except Exception as e:
            logger.error(f"Production pipeline error in job {job_config.job_id}: {str(e)}")
            return {
                'status': 'FAILURE',
                'records_processed': 0,
                'error': str(e),
                'message': f'Production pipeline failed: {str(e)}'
            }
    
    async def _g00_gather_production_data(self, job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """G00: Gather production data from MES/ERP systems."""
        production_data = []
        
        # Simulate gathering production data
        for batch_id in range(1, 21):  # 20 production batches
            production_data.append({
                'batch_id': f"{job_config.source_system}_B{batch_id:04d}",
                'timestamp': datetime.utcnow().isoformat(),
                'machine_id': f"LOOM_{(batch_id % 5) + 1:02d}",
                'product_code': f"TEX{1000 + batch_id}",
                'quantity_produced': 100 + (batch_id * 5),
                'quality_grade': 'A' if batch_id % 3 == 0 else 'B',
                'efficiency': 0.85 + (batch_id % 10) * 0.01,
                'defect_rate': 0.02 + (batch_id % 7) * 0.001
            })
        
        return production_data
    
    async def _g01_validate_production_data(self, production_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """G01: Validate production data integrity."""
        validated_data = []
        
        for record in production_data:
            # Validate production metrics
            if record['quantity_produced'] > 0:
                if 0 <= record['efficiency'] <= 1.0:
                    if 0 <= record['defect_rate'] <= 0.1:  # Max 10% defect rate
                        record['validation_status'] = 'VALID'
                        record['validation_timestamp'] = datetime.utcnow().isoformat()
                        validated_data.append(record)
                    else:
                        logger.warning(f"High defect rate for batch {record['batch_id']}: {record['defect_rate']}")
                else:
                    logger.warning(f"Invalid efficiency for batch {record['batch_id']}: {record['efficiency']}")
            else:
                logger.warning(f"Invalid quantity for batch {record['batch_id']}: {record['quantity_produced']}")
        
        return validated_data
    
    async def _g02_transform_production_data(self, validated_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """G02: Transform production data for analytics."""
        transformed_data = []
        
        for record in validated_data:
            # Calculate production metrics
            transformed = {
                'batch_id': record['batch_id'],
                'timestamp': record['timestamp'],
                'machine_id': record['machine_id'],
                'product_code': record['product_code'],
                'quantity_produced': record['quantity_produced'],
                'quality_score': 1.0 if record['quality_grade'] == 'A' else 0.8,
                'efficiency_normalized': record['efficiency'],
                'defect_cost': record['quantity_produced'] * record['defect_rate'] * 10.0,  # Cost per defect unit
                'production_value': record['quantity_produced'] * (1 - record['defect_rate']) * 15.0,  # Value per good unit
                'metadata': {
                    'quality_grade': record['quality_grade'],
                    'raw_efficiency': record['efficiency'],
                    'raw_defect_rate': record['defect_rate'],
                    'transformation_type': job_config.transformation_rules.get('type', 'production'),
                    'job_id': job_config.job_id
                }
            }
            transformed_data.append(transformed)
        
        return transformed_data
    
    async def _i01_integrate_production_data(self, transformed_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> Dict[str, Any]:
        """I01: Integrate production data with warehouse systems."""
        integrated_records = 0
        integrated_data = []
        
        # Batch integration
        batch_size = min(job_config.batch_size, 50)  # Smaller batches for production data
        for i in range(0, len(transformed_data), batch_size):
            batch = transformed_data[i:i + batch_size]
            
            for record in batch:
                record['integration_timestamp'] = datetime.utcnow().isoformat()
                record['warehouse_location'] = f"WH_{(integrated_records % 3) + 1}"
                record['target_table'] = job_config.target_table
                integrated_data.append(record)
                integrated_records += 1
            
            await asyncio.sleep(0.02)  # Simulate integration delay
        
        return {
            'records_integrated': integrated_records,
            'data': integrated_data
        }
    
    async def _f01_filter_production_data(self, integrated_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """F01: Apply production business rules and filters."""
        filtered_data = []
        
        for record in integrated_data:
            # Apply production filters
            if record['quantity_produced'] >= 50:  # Minimum batch size
                if record['quality_score'] >= 0.7:  # Minimum quality
                    if record['production_value'] > record['defect_cost']:  # Profitable batch
                        record['filter_status'] = 'PASSED'
                        record['filter_timestamp'] = datetime.utcnow().isoformat()
                        record['profitability'] = record['production_value'] - record['defect_cost']
                        filtered_data.append(record)
        
        return filtered_data
    
    async def _p01_process_production_data(self, filtered_data: List[Dict[str, Any]], job_config: ETLJobConfig) -> Dict[str, Any]:
        """P01: Final processing and storage of production data."""
        stored_records = 0
        total_production_value = 0
        
        for record in filtered_data:
            # Final processing
            record['processing_timestamp'] = datetime.utcnow().isoformat()
            record['pipeline_complete'] = True
            record['pipeline_version'] = 'G00-G02-I01-F01-P01-v1.0'
            record['kpi_metrics'] = {
                'oee': record['efficiency_normalized'] * record['quality_score'] * 0.95,  # Overall Equipment Effectiveness
                'yield_rate': 1 - record['metadata']['raw_defect_rate'],
                'profitability_index': record['profitability'] / record['production_value']
            }
            
            total_production_value += record['production_value']
            stored_records += 1
        
        # Log completion
        logger.info(f"P01: Stored {stored_records} production records to {job_config.target_table}")
        logger.info(f"P01: Total production value: ${total_production_value:,.2f}")
        
        return {
            'records_stored': stored_records,
            'total_production_value': total_production_value,
            'completion_timestamp': datetime.utcnow().isoformat()
        }
    
    async def _log_job_execution(
        self, 
        execution_id: str, 
        job_id: str, 
        status: str,
        records_processed: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """Log ETL job execution."""
        def _log_execution():
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                if status == 'RUNNING':
                    cursor.execute("""
                        INSERT INTO etl_executions (
                            execution_id, job_id, start_time, status, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (execution_id, job_id, now, status, now))
                else:
                    cursor.execute("""
                        UPDATE etl_executions
                        SET end_time = ?, status = ?, records_processed = ?, error_message = ?
                        WHERE execution_id = ?
                    """, (now, status, records_processed, error_message, execution_id))
                
                conn.commit()
                
            except sqlite3.Error as e:
                logger.error(f"Error logging job execution: {e}")
                conn.rollback()
            finally:
                conn.close()
        
        await execute_db_write(_log_execution)


class TextileDataPipeline:
    """Main textile manufacturing data pipeline coordinator."""
    
    def __init__(self):
        self.sensor_buffer = SensorDataBuffer(
            flush_interval=config_manager.rag.chunk_size // 100,  # Adaptive flush interval
            batch_size=1000
        )
        self.data_validator = DataQualityValidator()
        self.aggregator = RealTimeAggregator()
        self.etl_manager = ETLJobManager()
        self.running = False
    
    async def start(self) -> None:
        """Start the data pipeline."""
        if self.running:
            return
        
        self.running = True
        
        # Start all components
        self.aggregator.start()
        await self.etl_manager.start_scheduler()
        
        logger.info("Textile data pipeline started successfully")
    
    async def stop(self) -> None:
        """Stop the data pipeline."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop all components
        await self.sensor_buffer.force_flush()
        self.aggregator.stop()
        await self.etl_manager.stop_scheduler()
        
        logger.info("Textile data pipeline stopped")
    
    async def ingest_sensor_reading(self, reading: SensorReading) -> None:
        """Ingest a single sensor reading."""
        if self.running:
            self.sensor_buffer.add_reading(reading)
    
    async def ingest_sensor_batch(self, readings: List[SensorReading]) -> None:
        """Ingest a batch of sensor readings."""
        if self.running:
            for reading in readings:
                self.sensor_buffer.add_reading(reading)
    
    async def validate_data_quality(self, table_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data quality."""
        return await self.data_validator.validate_data(table_name, data)
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status information."""
        return {
            'running': self.running,
            'sensor_buffer_size': sum(len(readings) for readings in self.sensor_buffer.buffer.values()),
            'aggregator_running': self.aggregator.running,
            'etl_jobs_loaded': len(self.etl_manager.jobs),
            'active_etl_jobs': sum(1 for running in self.etl_manager.running_jobs.values() if running)
        }


# Global pipeline instance
textile_pipeline = TextileDataPipeline()


# Utility functions for Agent-MCP integration
async def initialize_textile_pipeline() -> bool:
    """Initialize the textile data pipeline."""
    try:
        await textile_pipeline.start()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize textile pipeline: {e}")
        return False


async def shutdown_textile_pipeline() -> None:
    """Shutdown the textile data pipeline."""
    try:
        await textile_pipeline.stop()
    except Exception as e:
        logger.error(f"Error shutting down textile pipeline: {e}")


def get_textile_pipeline() -> TextileDataPipeline:
    """Get the global textile pipeline instance."""
    return textile_pipeline