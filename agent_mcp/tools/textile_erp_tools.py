# Textile ERP MCP Tools
"""
MCP tools for textile manufacturing ERP integration.
Provides comprehensive tooling for production management, quality control,
inventory management, and manufacturing analytics.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

from ..core.config import logger
from ..db.actions.textile_erp_actions import (
    create_fabric_inventory_item,
    update_inventory_quantity,
    get_fabric_inventory_status,
    create_production_order,
    update_production_order_status,
    get_production_orders_by_status,
    create_quality_inspection,
    complete_quality_inspection,
    get_quality_metrics_summary,
    update_machine_status,
    record_machine_downtime,
    get_machine_utilization_report,
    get_production_dashboard_data,
    get_kpi_summary,
    create_optimization_suggestion,
    get_pending_optimizations,
)
from ..features.textile_data_pipeline import get_textile_pipeline, SensorReading
from .registry import tool


# === INVENTORY MANAGEMENT TOOLS ===

@tool
async def create_inventory_item(
    fabric_type_id: str,
    lot_number: str,
    quantity_meters: float,
    supplier_id: Optional[str] = None,
    unit_cost: Optional[float] = None,
    location_warehouse: Optional[str] = None,
    location_zone: Optional[str] = None,
    location_bin: Optional[str] = None,
    quality_grade: str = "A"
) -> Dict[str, Any]:
    """
    Create a new fabric inventory item.
    
    Args:
        fabric_type_id: ID of the fabric type
        lot_number: Lot/batch number from supplier
        quantity_meters: Quantity in meters
        supplier_id: Supplier ID (optional)
        unit_cost: Cost per meter (optional)
        location_warehouse: Warehouse location
        location_zone: Zone within warehouse
        location_bin: Specific bin location
        quality_grade: Quality grade (A, B, C)
    
    Returns:
        Dictionary with inventory_id and creation status
    """
    try:
        inventory_id = await create_fabric_inventory_item(
            fabric_type_id=fabric_type_id,
            lot_number=lot_number,
            quantity_meters=quantity_meters,
            supplier_id=supplier_id,
            unit_cost=unit_cost,
            location_warehouse=location_warehouse,
            location_zone=location_zone,
            location_bin=location_bin,
            quality_grade=quality_grade
        )
        
        if inventory_id:
            return {
                "success": True,
                "inventory_id": inventory_id,
                "message": f"Inventory item created successfully: {inventory_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create inventory item"
            }
    
    except Exception as e:
        logger.error(f"Error creating inventory item: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def update_fabric_inventory(
    inventory_id: str,
    quantity_change: float,
    movement_type: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update fabric inventory quantity with movement tracking.
    
    Args:
        inventory_id: Inventory item ID
        quantity_change: Change in quantity (positive for increase, negative for decrease)
        movement_type: Type of movement (IN, OUT, ADJUSTMENT, TRANSFER)
        reference_id: Reference document ID
        reference_type: Type of reference (PRODUCTION, SALE, ADJUSTMENT, etc.)
        reason: Reason for the movement
    
    Returns:
        Dictionary with update status
    """
    try:
        success = await update_inventory_quantity(
            inventory_id=inventory_id,
            quantity_change=quantity_change,
            movement_type=movement_type,
            reference_id=reference_id,
            reference_type=reference_type,
            reason=reason
        )
        
        return {
            "success": success,
            "message": f"Inventory updated: {quantity_change} meters {movement_type}"
        }
    
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_inventory_status() -> Dict[str, Any]:
    """
    Get current fabric inventory status with alerts.
    
    Returns:
        Dictionary with inventory status data
    """
    try:
        inventory_data = get_fabric_inventory_status()
        
        # Analyze inventory for alerts
        alerts = {
            "low_stock": [],
            "out_of_stock": [],
            "aging_inventory": []
        }
        
        for item in inventory_data:
            if item.get('status_flag') == 'LOW_STOCK':
                alerts['low_stock'].append(item)
            elif item.get('status_flag') == 'OUT_OF_STOCK':
                alerts['out_of_stock'].append(item)
            elif item.get('status_flag') == 'AGING':
                alerts['aging_inventory'].append(item)
        
        return {
            "success": True,
            "inventory_items": inventory_data,
            "alerts": alerts,
            "summary": {
                "total_items": len(inventory_data),
                "low_stock_count": len(alerts['low_stock']),
                "out_of_stock_count": len(alerts['out_of_stock']),
                "aging_count": len(alerts['aging_inventory'])
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting inventory status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === PRODUCTION MANAGEMENT TOOLS ===

@tool
async def create_new_production_order(
    product_type: str,
    fabric_type_id: str,
    quantity_pieces: int,
    sales_order_id: Optional[str] = None,
    priority: int = 3,
    planned_start_date: Optional[str] = None,
    planned_end_date: Optional[str] = None,
    special_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new production order.
    
    Args:
        product_type: Type of product to manufacture
        fabric_type_id: ID of fabric type to use
        quantity_pieces: Number of pieces to produce
        sales_order_id: Related sales order ID
        priority: Priority level (1=High, 2=Medium, 3=Low)
        planned_start_date: Planned start date (ISO format)
        planned_end_date: Planned end date (ISO format)
        special_instructions: Special production instructions
    
    Returns:
        Dictionary with order_id and creation status
    """
    try:
        order_id = await create_production_order(
            product_type=product_type,
            fabric_type_id=fabric_type_id,
            quantity_pieces=quantity_pieces,
            sales_order_id=sales_order_id,
            priority=priority,
            planned_start_date=planned_start_date,
            planned_end_date=planned_end_date,
            special_instructions=special_instructions
        )
        
        if order_id:
            return {
                "success": True,
                "order_id": order_id,
                "message": f"Production order created: {order_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create production order"
            }
    
    except Exception as e:
        logger.error(f"Error creating production order: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def update_production_status(
    order_id: str,
    status: str,
    assigned_line: Optional[str] = None,
    supervisor_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update production order status.
    
    Args:
        order_id: Production order ID
        status: New status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, HOLD)
        assigned_line: Production line assignment
        supervisor_id: Supervisor assignment
    
    Returns:
        Dictionary with update status
    """
    try:
        success = await update_production_order_status(
            order_id=order_id,
            status=status,
            assigned_line=assigned_line,
            supervisor_id=supervisor_id
        )
        
        return {
            "success": success,
            "message": f"Production order {order_id} status updated to {status}"
        }
    
    except Exception as e:
        logger.error(f"Error updating production status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_production_orders(status: str = "IN_PROGRESS") -> Dict[str, Any]:
    """
    Get production orders by status.
    
    Args:
        status: Order status to filter by
    
    Returns:
        Dictionary with production orders list
    """
    try:
        orders = get_production_orders_by_status(status)
        
        return {
            "success": True,
            "orders": orders,
            "count": len(orders)
        }
    
    except Exception as e:
        logger.error(f"Error getting production orders: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === QUALITY CONTROL TOOLS ===

@tool
async def start_quality_inspection(
    order_id: str,
    inspection_type: str,
    inspector_id: str,
    operation_id: Optional[str] = None,
    sample_size: int = 1
) -> Dict[str, Any]:
    """
    Start a new quality inspection.
    
    Args:
        order_id: Production order ID
        inspection_type: Type of inspection (INCOMING, IN_PROCESS, FINAL)
        inspector_id: Inspector's ID
        operation_id: Specific operation being inspected
        sample_size: Number of samples to inspect
    
    Returns:
        Dictionary with inspection_id and status
    """
    try:
        inspection_id = await create_quality_inspection(
            order_id=order_id,
            inspection_type=inspection_type,
            inspector_id=inspector_id,
            operation_id=operation_id,
            sample_size=sample_size
        )
        
        if inspection_id:
            return {
                "success": True,
                "inspection_id": inspection_id,
                "message": f"Quality inspection started: {inspection_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create quality inspection"
            }
    
    except Exception as e:
        logger.error(f"Error starting quality inspection: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def complete_inspection(
    inspection_id: str,
    overall_result: str,
    defect_rate: float = 0.0,
    critical_defects: int = 0,
    major_defects: int = 0,
    minor_defects: int = 0,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete a quality inspection with results.
    
    Args:
        inspection_id: Quality inspection ID
        overall_result: Overall result (PASS, FAIL, CONDITIONAL)
        defect_rate: Overall defect rate percentage
        critical_defects: Number of critical defects
        major_defects: Number of major defects
        minor_defects: Number of minor defects
        notes: Additional notes
    
    Returns:
        Dictionary with completion status
    """
    try:
        success = await complete_quality_inspection(
            inspection_id=inspection_id,
            overall_result=overall_result,
            defect_rate=defect_rate,
            critical_defects=critical_defects,
            major_defects=major_defects,
            minor_defects=minor_defects,
            notes=notes
        )
        
        return {
            "success": success,
            "message": f"Quality inspection {inspection_id} completed with result: {overall_result}"
        }
    
    except Exception as e:
        logger.error(f"Error completing inspection: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_quality_metrics(days: int = 30) -> Dict[str, Any]:
    """
    Get quality metrics summary for the specified period.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Dictionary with quality metrics
    """
    try:
        metrics = get_quality_metrics_summary(days)
        
        return {
            "success": True,
            "metrics": metrics,
            "period_days": days
        }
    
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === MACHINE MANAGEMENT TOOLS ===

@tool
async def set_machine_status(
    machine_id: str,
    status: str,
    current_operation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update machine status.
    
    Args:
        machine_id: Machine ID
        status: New status (IDLE, RUNNING, MAINTENANCE, BREAKDOWN)
        current_operation_id: Currently running operation ID
    
    Returns:
        Dictionary with update status
    """
    try:
        success = await update_machine_status(
            machine_id=machine_id,
            status=status,
            current_operation_id=current_operation_id
        )
        
        return {
            "success": success,
            "message": f"Machine {machine_id} status updated to {status}"
        }
    
    except Exception as e:
        logger.error(f"Error updating machine status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def log_machine_downtime(
    machine_id: str,
    downtime_type: str,
    start_time: str,
    reason_code: Optional[str] = None,
    description: Optional[str] = None,
    technician_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record machine downtime event.
    
    Args:
        machine_id: Machine ID
        downtime_type: Type of downtime (BREAKDOWN, MAINTENANCE, NO_WORK, CHANGEOVER)
        start_time: Downtime start time (ISO format)
        reason_code: Reason code for downtime
        description: Detailed description
        technician_id: Technician handling the issue
    
    Returns:
        Dictionary with downtime_id and status
    """
    try:
        downtime_id = await record_machine_downtime(
            machine_id=machine_id,
            downtime_type=downtime_type,
            start_time=start_time,
            reason_code=reason_code,
            description=description,
            technician_id=technician_id
        )
        
        if downtime_id:
            return {
                "success": True,
                "downtime_id": downtime_id,
                "message": f"Downtime recorded: {downtime_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to record downtime"
            }
    
    except Exception as e:
        logger.error(f"Error logging downtime: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_machine_utilization(days: int = 7) -> Dict[str, Any]:
    """
    Get machine utilization report.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Dictionary with utilization data
    """
    try:
        utilization_data = get_machine_utilization_report(days)
        
        # Calculate summary statistics
        total_machines = len(utilization_data)
        running_machines = sum(1 for m in utilization_data if m.get('status') == 'RUNNING')
        avg_efficiency = sum(m.get('avg_efficiency_7_days', 0) for m in utilization_data if m.get('avg_efficiency_7_days')) / max(total_machines, 1)
        
        return {
            "success": True,
            "machines": utilization_data,
            "summary": {
                "total_machines": total_machines,
                "running_machines": running_machines,
                "utilization_rate": (running_machines / max(total_machines, 1)) * 100,
                "average_efficiency": round(avg_efficiency, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting machine utilization: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === SENSOR DATA TOOLS ===

@tool
async def ingest_sensor_data(readings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ingest batch of sensor readings into the data pipeline.
    
    Args:
        readings: List of sensor reading dictionaries with keys:
                 - sensor_id: Sensor identifier
                 - timestamp: ISO format timestamp
                 - value: Sensor value
                 - quality_flag: Quality flag (0=Good, 1=Suspect, 2=Bad)
    
    Returns:
        Dictionary with ingestion status
    """
    try:
        pipeline = get_textile_pipeline()
        
        sensor_readings = []
        for reading_data in readings:
            reading = SensorReading(
                sensor_id=reading_data['sensor_id'],
                timestamp=reading_data['timestamp'],
                value=float(reading_data['value']),
                quality_flag=reading_data.get('quality_flag', 0),
                metadata=reading_data.get('metadata')
            )
            sensor_readings.append(reading)
        
        await pipeline.ingest_sensor_batch(sensor_readings)
        
        return {
            "success": True,
            "message": f"Ingested {len(readings)} sensor readings",
            "readings_count": len(readings)
        }
    
    except Exception as e:
        logger.error(f"Error ingesting sensor data: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === ANALYTICS AND REPORTING TOOLS ===

@tool
def get_production_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive production dashboard data.
    
    Returns:
        Dictionary with dashboard metrics
    """
    try:
        dashboard_data = get_production_dashboard_data()
        
        return {
            "success": True,
            "dashboard": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_kpi_report(period: str = "monthly") -> Dict[str, Any]:
    """
    Get KPI summary report.
    
    Args:
        period: Period for KPI calculation (monthly, daily)
    
    Returns:
        Dictionary with KPI data
    """
    try:
        kpi_data = get_kpi_summary(period)
        
        return {
            "success": True,
            "kpis": kpi_data,
            "period": period,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting KPI report: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === AI/ML OPTIMIZATION TOOLS ===

@tool
async def suggest_process_optimization(
    process_area: str,
    suggestion_type: str,
    description: str,
    current_metrics: Dict[str, Any],
    projected_improvements: Dict[str, Any],
    implementation_effort: str = "MEDIUM",
    estimated_roi: Optional[float] = None,
    confidence_level: float = 0.8
) -> Dict[str, Any]:
    """
    Create an AI-generated process optimization suggestion.
    
    Args:
        process_area: Area of optimization (PRODUCTION, QUALITY, INVENTORY, ENERGY)
        suggestion_type: Type of optimization (EFFICIENCY, COST_REDUCTION, QUALITY_IMPROVEMENT)
        description: Detailed description of the suggestion
        current_metrics: Current state metrics dictionary
        projected_improvements: Projected improvement metrics dictionary
        implementation_effort: Effort level (LOW, MEDIUM, HIGH)
        estimated_roi: Estimated return on investment percentage
        confidence_level: AI confidence level (0-1)
    
    Returns:
        Dictionary with suggestion_id and status
    """
    try:
        suggestion_id = await create_optimization_suggestion(
            process_area=process_area,
            suggestion_type=suggestion_type,
            description=description,
            current_state_metrics=current_metrics,
            projected_improvement=projected_improvements,
            implementation_effort=implementation_effort,
            estimated_roi=estimated_roi,
            confidence_level=confidence_level
        )
        
        if suggestion_id:
            return {
                "success": True,
                "suggestion_id": suggestion_id,
                "message": f"Optimization suggestion created: {suggestion_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create optimization suggestion"
            }
    
    except Exception as e:
        logger.error(f"Error creating optimization suggestion: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_optimization_suggestions() -> Dict[str, Any]:
    """
    Get pending optimization suggestions.
    
    Returns:
        Dictionary with optimization suggestions list
    """
    try:
        suggestions = get_pending_optimizations()
        
        # Categorize suggestions by area and type
        categories = {}
        for suggestion in suggestions:
            area = suggestion['process_area']
            if area not in categories:
                categories[area] = []
            categories[area].append(suggestion)
        
        return {
            "success": True,
            "suggestions": suggestions,
            "categories": categories,
            "count": len(suggestions)
        }
    
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# === DATA PIPELINE TOOLS ===

@tool
def get_pipeline_status() -> Dict[str, Any]:
    """
    Get textile data pipeline status.
    
    Returns:
        Dictionary with pipeline status information
    """
    try:
        pipeline = get_textile_pipeline()
        status = pipeline.get_pipeline_status()
        
        return {
            "success": True,
            "pipeline_status": status,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def validate_data_quality(table_name: str, data_sample: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate data quality for a given table.
    
    Args:
        table_name: Name of the table to validate
        data_sample: Sample data to validate
    
    Returns:
        Dictionary with validation results
    """
    try:
        pipeline = get_textile_pipeline()
        validation_results = await pipeline.validate_data_quality(table_name, data_sample)
        
        return {
            "success": True,
            "validation_results": validation_results,
            "table_name": table_name
        }
    
    except Exception as e:
        logger.error(f"Error validating data quality: {e}")
        return {
            "success": False,
            "error": str(e)
        }