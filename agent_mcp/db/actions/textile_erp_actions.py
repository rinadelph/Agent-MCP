# Textile ERP Database Actions
"""
Database action functions for textile ERP operations.
Provides clean interfaces for CRUD operations on textile manufacturing data.
"""

import sqlite3
import json
import uuid
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from ...core.config import logger
from ..connection import get_db_connection, execute_db_write


# === FABRIC INVENTORY ACTIONS ===

async def create_fabric_inventory_item(
    fabric_type_id: str,
    lot_number: str,
    quantity_meters: float,
    supplier_id: Optional[str] = None,
    unit_cost: Optional[float] = None,
    location_warehouse: Optional[str] = None,
    location_zone: Optional[str] = None,
    location_bin: Optional[str] = None,
    quality_grade: str = "A",
    color_code: Optional[str] = None,
    dye_lot: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """Create a new fabric inventory item."""
    
    def _create_inventory():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            inventory_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO fabric_inventory (
                    inventory_id, fabric_type_id, lot_number, supplier_id,
                    quantity_meters, unit_cost, location_warehouse, location_zone,
                    location_bin, received_date, quality_grade, color_code,
                    dye_lot, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inventory_id, fabric_type_id, lot_number, supplier_id,
                quantity_meters, unit_cost, location_warehouse, location_zone,
                location_bin, now, quality_grade, color_code, dye_lot, now, now
            ))
            
            # Record inventory movement
            cursor.execute("""
                INSERT INTO inventory_movements (
                    inventory_id, movement_type, quantity_meters, reference_type,
                    reason, moved_by, moved_at, to_location
                ) VALUES (?, 'IN', ?, 'RECEIPT', 'Initial inventory receipt', 'system', ?, ?)
            """, (inventory_id, quantity_meters, now, f"{location_warehouse}-{location_zone}-{location_bin}"))
            
            conn.commit()
            return inventory_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error creating fabric inventory: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    return await execute_db_write(_create_inventory)


async def update_inventory_quantity(
    inventory_id: str,
    quantity_change: float,
    movement_type: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
    reason: Optional[str] = None,
    moved_by: str = "system"
) -> bool:
    """Update inventory quantity and record movement."""
    
    def _update_quantity():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Check current inventory
            cursor.execute("SELECT quantity_meters FROM fabric_inventory WHERE inventory_id = ?", (inventory_id,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"Inventory item {inventory_id} not found")
                return False
            
            current_quantity = row['quantity_meters']
            new_quantity = current_quantity + quantity_change
            
            if new_quantity < 0:
                logger.error(f"Insufficient inventory: current={current_quantity}, requested={abs(quantity_change)}")
                return False
            
            # Update inventory
            cursor.execute("""
                UPDATE fabric_inventory 
                SET quantity_meters = ?, updated_at = ?
                WHERE inventory_id = ?
            """, (new_quantity, now, inventory_id))
            
            # Record movement
            cursor.execute("""
                INSERT INTO inventory_movements (
                    inventory_id, movement_type, quantity_meters, reference_id,
                    reference_type, reason, moved_by, moved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (inventory_id, movement_type, quantity_change, reference_id, reference_type, reason, moved_by, now))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error updating inventory quantity: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    return await execute_db_write(_update_quantity)


def get_fabric_inventory_status() -> List[Dict[str, Any]]:
    """Get current fabric inventory status."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM v_inventory_status
            ORDER BY fabric_name, received_date
        """)
        
        return [dict(row) for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting inventory status: {e}")
        return []
    finally:
        if conn:
            conn.close()


# === PRODUCTION ORDER ACTIONS ===

async def create_production_order(
    product_type: str,
    fabric_type_id: str,
    quantity_pieces: int,
    sales_order_id: Optional[str] = None,
    priority: int = 3,
    planned_start_date: Optional[str] = None,
    planned_end_date: Optional[str] = None,
    special_instructions: Optional[str] = None,
    quality_requirements: Optional[Dict] = None,
    created_by: str = "system"
) -> Optional[str]:
    """Create a new production order."""
    
    def _create_order():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            order_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO production_orders (
                    order_id, sales_order_id, product_type, fabric_type_id,
                    quantity_pieces, priority, planned_start_date, planned_end_date,
                    status, special_instructions, quality_requirements,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)
            """, (
                order_id, sales_order_id, product_type, fabric_type_id,
                quantity_pieces, priority, planned_start_date, planned_end_date,
                special_instructions, json.dumps(quality_requirements) if quality_requirements else None,
                created_by, now, now
            ))
            
            conn.commit()
            return order_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error creating production order: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    return await execute_db_write(_create_order)


async def update_production_order_status(
    order_id: str,
    status: str,
    assigned_line: Optional[str] = None,
    supervisor_id: Optional[str] = None
) -> bool:
    """Update production order status."""
    
    def _update_status():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            update_fields = ["status = ?", "updated_at = ?"]
            params = [status, now]
            
            if assigned_line:
                update_fields.append("assigned_line = ?")
                params.append(assigned_line)
                
            if supervisor_id:
                update_fields.append("supervisor_id = ?")
                params.append(supervisor_id)
            
            if status == "IN_PROGRESS" and not assigned_line:
                # Auto-assign actual start date
                update_fields.append("actual_start_date = ?")
                params.append(now)
            elif status == "COMPLETED":
                # Auto-assign actual end date
                update_fields.append("actual_end_date = ?")
                params.append(now)
            
            params.append(order_id)
            
            cursor.execute(f"""
                UPDATE production_orders 
                SET {', '.join(update_fields)}
                WHERE order_id = ?
            """, params)
            
            if cursor.rowcount == 0:
                logger.warning(f"Production order {order_id} not found")
                return False
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error updating production order status: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    return await execute_db_write(_update_status)


def get_production_orders_by_status(status: str) -> List[Dict[str, Any]]:
    """Get production orders by status."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT po.*, ft.fabric_name, pl.line_name
            FROM production_orders po
            JOIN fabric_types ft ON po.fabric_type_id = ft.fabric_type_id
            LEFT JOIN production_lines pl ON po.assigned_line = pl.line_id
            WHERE po.status = ?
            ORDER BY po.priority, po.created_at
        """, (status,))
        
        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            if order.get('quality_requirements'):
                try:
                    order['quality_requirements'] = json.loads(order['quality_requirements'])
                except json.JSONDecodeError:
                    order['quality_requirements'] = None
            orders.append(order)
        
        return orders
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting production orders: {e}")
        return []
    finally:
        if conn:
            conn.close()


# === QUALITY CONTROL ACTIONS ===

async def create_quality_inspection(
    order_id: str,
    inspection_type: str,
    inspector_id: str,
    operation_id: Optional[str] = None,
    sample_size: int = 1
) -> Optional[str]:
    """Create a new quality inspection."""
    
    def _create_inspection():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            inspection_id = f"QI-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO quality_inspections (
                    inspection_id, order_id, operation_id, inspection_type,
                    inspector_id, sample_size, inspection_date, overall_result,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                inspection_id, order_id, operation_id, inspection_type,
                inspector_id, sample_size, now, now
            ))
            
            conn.commit()
            return inspection_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error creating quality inspection: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    return await execute_db_write(_create_inspection)


async def complete_quality_inspection(
    inspection_id: str,
    overall_result: str,
    defect_rate: float = 0.0,
    critical_defects: int = 0,
    major_defects: int = 0,
    minor_defects: int = 0,
    notes: Optional[str] = None
) -> bool:
    """Complete a quality inspection with results."""
    
    def _complete_inspection():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE quality_inspections 
                SET overall_result = ?, defect_rate = ?, critical_defects = ?,
                    major_defects = ?, minor_defects = ?, notes = ?
                WHERE inspection_id = ?
            """, (
                overall_result, defect_rate, critical_defects,
                major_defects, minor_defects, notes, inspection_id
            ))
            
            if cursor.rowcount == 0:
                logger.warning(f"Quality inspection {inspection_id} not found")
                return False
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error completing quality inspection: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    return await execute_db_write(_complete_inspection)


def get_quality_metrics_summary(days: int = 30) -> Dict[str, Any]:
    """Get quality metrics summary for the last N days."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_inspections,
                SUM(CASE WHEN overall_result = 'PASS' THEN 1 ELSE 0 END) as passed_inspections,
                AVG(defect_rate) as avg_defect_rate,
                SUM(critical_defects) as total_critical_defects,
                SUM(major_defects) as total_major_defects,
                SUM(minor_defects) as total_minor_defects
            FROM quality_inspections 
            WHERE inspection_date >= ?
        """, (start_date,))
        
        row = cursor.fetchone()
        if not row:
            return {}
        
        metrics = dict(row)
        if metrics['total_inspections'] > 0:
            metrics['pass_rate'] = round((metrics['passed_inspections'] / metrics['total_inspections']) * 100, 2)
        else:
            metrics['pass_rate'] = 0.0
        
        return metrics
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting quality metrics: {e}")
        return {}
    finally:
        if conn:
            conn.close()


# === MACHINE MANAGEMENT ACTIONS ===

async def update_machine_status(
    machine_id: str,
    status: str,
    current_operation_id: Optional[str] = None
) -> bool:
    """Update machine status."""
    
    def _update_status():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE machines 
                SET status = ?, current_operation_id = ?, updated_at = ?
                WHERE machine_id = ?
            """, (status, current_operation_id, now, machine_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"Machine {machine_id} not found")
                return False
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error updating machine status: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    return await execute_db_write(_update_status)


async def record_machine_downtime(
    machine_id: str,
    downtime_type: str,
    start_time: str,
    reason_code: Optional[str] = None,
    description: Optional[str] = None,
    technician_id: Optional[str] = None
) -> Optional[str]:
    """Record machine downtime event."""
    
    def _record_downtime():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            downtime_id = f"DT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO machine_downtime (
                    downtime_id, machine_id, start_time, downtime_type,
                    reason_code, description, technician_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                downtime_id, machine_id, start_time, downtime_type,
                reason_code, description, technician_id, now
            ))
            
            conn.commit()
            return downtime_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error recording machine downtime: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    return await execute_db_write(_record_downtime)


def get_machine_utilization_report(days: int = 7) -> List[Dict[str, Any]]:
    """Get machine utilization report."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM v_machine_utilization")
        
        return [dict(row) for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting machine utilization: {e}")
        return []
    finally:
        if conn:
            conn.close()


# === SENSOR DATA ACTIONS ===

async def batch_insert_sensor_readings(readings: List[Dict[str, Any]]) -> bool:
    """Batch insert sensor readings for high-performance ingestion."""
    
    def _batch_insert():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
            now = datetime.now().isoformat()
            
            # Prepare batch data
            batch_data = []
            for reading in readings:
                batch_data.append((
                    reading['sensor_id'],
                    reading['timestamp'],
                    reading['value'],
                    reading.get('quality_flag', 0),
                    batch_id,
                    now
                ))
            
            cursor.executemany("""
                INSERT INTO sensor_readings (
                    sensor_id, timestamp, value, quality_flag, batch_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, batch_data)
            
            conn.commit()
            logger.info(f"Batch inserted {len(readings)} sensor readings with batch_id {batch_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error batch inserting sensor readings: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    return await execute_db_write(_batch_insert)


def get_sensor_data_range(
    sensor_id: str,
    start_time: str,
    end_time: str,
    aggregation: str = "raw"
) -> List[Dict[str, Any]]:
    """Get sensor data for a time range with optional aggregation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if aggregation == "hourly":
            cursor.execute("""
                SELECT hour_timestamp as timestamp, avg_value, min_value, max_value, sample_count
                FROM sensor_readings_hourly
                WHERE sensor_id = ? AND hour_timestamp BETWEEN ? AND ?
                ORDER BY hour_timestamp
            """, (sensor_id, start_time, end_time))
        elif aggregation == "daily":
            cursor.execute("""
                SELECT date as timestamp, avg_value, min_value, max_value, sample_count
                FROM sensor_readings_daily
                WHERE sensor_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
            """, (sensor_id, start_time, end_time))
        else:
            cursor.execute("""
                SELECT timestamp, value, quality_flag
                FROM sensor_readings
                WHERE sensor_id = ? AND timestamp BETWEEN ? AND ?
                AND quality_flag = 0
                ORDER BY timestamp
            """, (sensor_id, start_time, end_time))
        
        return [dict(row) for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting sensor data: {e}")
        return []
    finally:
        if conn:
            conn.close()


# === ANALYTICS AND REPORTING ===

def get_production_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive production dashboard data."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        dashboard_data = {}
        
        # Active production orders
        cursor.execute("""
            SELECT status, COUNT(*) as count, SUM(quantity_pieces) as total_pieces
            FROM production_orders 
            WHERE status IN ('PENDING', 'IN_PROGRESS')
            GROUP BY status
        """)
        dashboard_data['active_orders'] = {row['status']: dict(row) for row in cursor.fetchall()}
        
        # Today's production
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COUNT(*) as orders_completed, SUM(quantity_pieces) as pieces_produced
            FROM production_orders
            WHERE DATE(actual_end_date) = ? AND status = 'COMPLETED'
        """, (today,))
        dashboard_data['today_production'] = dict(cursor.fetchone() or {})
        
        # Quality metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as inspections_today,
                SUM(CASE WHEN overall_result = 'PASS' THEN 1 ELSE 0 END) as passed_today,
                AVG(defect_rate) as avg_defect_rate
            FROM quality_inspections
            WHERE DATE(inspection_date) = ?
        """, (today,))
        dashboard_data['quality_today'] = dict(cursor.fetchone() or {})
        
        # Machine status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM machines
            GROUP BY status
        """)
        dashboard_data['machine_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Low inventory alerts
        cursor.execute("""
            SELECT COUNT(*) as low_stock_items
            FROM v_inventory_status
            WHERE status_flag IN ('LOW_STOCK', 'OUT_OF_STOCK')
        """)
        dashboard_data['inventory_alerts'] = dict(cursor.fetchone() or {})
        
        return dashboard_data
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting dashboard data: {e}")
        return {}
    finally:
        if conn:
            conn.close()


def get_kpi_summary(period: str = "monthly") -> Dict[str, Any]:
    """Get KPI summary for specified period."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if period == "monthly":
            current_month = datetime.now().strftime("%Y-%m")
            cursor.execute("""
                SELECT * FROM monthly_kpi_summary
                WHERE year_month = ?
            """, (current_month,))
        else:
            # Daily summary
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT 
                    production_date,
                    SUM(total_pieces_produced) as total_pieces,
                    AVG(average_efficiency) as avg_efficiency,
                    SUM(defect_count) as total_defects,
                    AVG(defect_rate) as avg_defect_rate
                FROM daily_production_summary
                WHERE production_date = ?
                GROUP BY production_date
            """, (today,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting KPI summary: {e}")
        return {}
    finally:
        if conn:
            conn.close()


# === AI/ML INTEGRATION FUNCTIONS ===

async def create_optimization_suggestion(
    process_area: str,
    suggestion_type: str,
    description: str,
    current_state_metrics: Dict[str, Any],
    projected_improvement: Dict[str, Any],
    implementation_effort: str = "MEDIUM",
    estimated_roi: Optional[float] = None,
    confidence_level: float = 0.8,
    agent_id: Optional[str] = None
) -> Optional[str]:
    """Create an AI-generated optimization suggestion."""
    
    def _create_suggestion():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            suggestion_id = f"OPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO optimization_suggestions (
                    suggestion_id, process_area, suggestion_type, description,
                    current_state_metrics, projected_improvement, implementation_effort,
                    estimated_roi, confidence_level, agent_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                suggestion_id, process_area, suggestion_type, description,
                json.dumps(current_state_metrics), json.dumps(projected_improvement),
                implementation_effort, estimated_roi, confidence_level,
                agent_id, now, now
            ))
            
            conn.commit()
            return suggestion_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error creating optimization suggestion: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    return await execute_db_write(_create_suggestion)


def get_pending_optimizations() -> List[Dict[str, Any]]:
    """Get pending optimization suggestions."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM optimization_suggestions
            WHERE status = 'PROPOSED'
            ORDER BY estimated_roi DESC, confidence_level DESC
        """)
        
        suggestions = []
        for row in cursor.fetchall():
            suggestion = dict(row)
            try:
                suggestion['current_state_metrics'] = json.loads(suggestion['current_state_metrics'])
                suggestion['projected_improvement'] = json.loads(suggestion['projected_improvement'])
            except json.JSONDecodeError:
                suggestion['current_state_metrics'] = {}
                suggestion['projected_improvement'] = {}
            suggestions.append(suggestion)
        
        return suggestions
        
    except sqlite3.Error as e:
        logger.error(f"Database error getting optimization suggestions: {e}")
        return []
    finally:
        if conn:
            conn.close()