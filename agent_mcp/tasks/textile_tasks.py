# agent_mcp/tasks/textile_tasks.py
"""
Background tasks for textile ERP system operations.
Handles sensor data processing, production scheduling, quality control,
inventory management, maintenance, and reporting.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import traceback

from celery import Task
from celery.exceptions import Retry
from ..core.celery_config import celery_app
from ..core.config import logger
from ..db.connection import get_db_connection
from ..db.actions.textile_erp_actions import TextileERPActions
from ..external.openai_service import OpenAIService

# Configure task logger
task_logger = logging.getLogger(__name__)


class TextileERPTask(Task):
    """Base task class with error handling and logging for textile ERP operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        task_logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            extra={"task_id": task_id, "args": args, "kwargs": kwargs}
        )
        
        # Store failure information in database
        try:
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO task_failures (task_id, task_name, error_message, args, kwargs, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, self.name, str(exc), json.dumps(args), json.dumps(kwargs), datetime.utcnow()))
                conn.commit()
        except Exception as db_error:
            task_logger.error(f"Failed to log task failure to database: {db_error}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        task_logger.info(f"Task {self.name}[{task_id}] completed successfully")


# Sensor Data Processing Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=3, default_retry_delay=60)
def process_sensor_batch(self, batch_id: str, sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process a batch of sensor data from textile machines.
    
    Args:
        batch_id: Unique identifier for the batch
        sensor_data: List of sensor readings
        
    Returns:
        Dict containing processing results
    """
    try:
        task_logger.info(f"Processing sensor batch {batch_id} with {len(sensor_data)} readings")
        
        processed_count = 0
        alerts_generated = 0
        anomalies_detected = 0
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            for reading in sensor_data:
                # Validate sensor reading
                if not _validate_sensor_reading(reading):
                    task_logger.warning(f"Invalid sensor reading in batch {batch_id}: {reading}")
                    continue
                
                # Store raw sensor data
                erp_actions.store_sensor_reading(reading)
                processed_count += 1
                
                # Check for anomalies
                if _detect_sensor_anomaly(reading):
                    anomalies_detected += 1
                    # Generate alert for anomaly
                    alert_id = erp_actions.create_alert(
                        alert_type="SENSOR_ANOMALY",
                        machine_id=reading.get("machine_id"),
                        severity="MEDIUM",
                        message=f"Anomaly detected in sensor {reading.get('sensor_type')}: {reading.get('value')}",
                        metadata=reading
                    )
                    alerts_generated += 1
                    task_logger.info(f"Generated anomaly alert {alert_id} for machine {reading.get('machine_id')}")
                
                # Check for critical thresholds
                if _check_critical_threshold(reading):
                    # Schedule high-priority alert processing
                    process_critical_alert.apply_async(
                        args=[reading],
                        queue="high_priority"
                    )
            
            conn.commit()
        
        result = {
            "batch_id": batch_id,
            "processed_count": processed_count,
            "alerts_generated": alerts_generated,
            "anomalies_detected": anomalies_detected,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed processing batch {batch_id}: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error processing sensor batch {batch_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=30)
def aggregate_sensor_data(self, time_period: str) -> Dict[str, Any]:
    """
    Aggregate sensor data for specified time period.
    
    Args:
        time_period: '5min', 'hourly', 'daily'
        
    Returns:
        Dict containing aggregation results
    """
    try:
        task_logger.info(f"Starting sensor data aggregation for period: {time_period}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Determine time range based on period
            now = datetime.utcnow()
            if time_period == "5min":
                start_time = now - timedelta(minutes=5)
            elif time_period == "hourly":
                start_time = now - timedelta(hours=1)
            elif time_period == "daily":
                start_time = now - timedelta(days=1)
            else:
                raise ValueError(f"Invalid time period: {time_period}")
            
            # Aggregate data by machine and sensor type
            aggregations = erp_actions.aggregate_sensor_data(start_time, now, time_period)
            
            # Store aggregated data
            for agg in aggregations:
                erp_actions.store_sensor_aggregation(agg)
            
            conn.commit()
        
        result = {
            "time_period": time_period,
            "aggregations_created": len(aggregations),
            "timestamp": now.isoformat()
        }
        
        task_logger.info(f"Completed sensor aggregation for {time_period}: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error aggregating sensor data for {time_period}: {exc}")
        raise self.retry(exc=exc)


# Production Order Management Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=120)
def optimize_production_schedule(self) -> Dict[str, Any]:
    """
    Optimize production schedule based on current orders, machine capacity, and material availability.
    
    Returns:
        Dict containing optimization results
    """
    try:
        task_logger.info("Starting production schedule optimization")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get pending production orders
            pending_orders = erp_actions.get_pending_production_orders()
            
            # Get machine availability
            machine_availability = erp_actions.get_machine_availability()
            
            # Get material inventory
            material_inventory = erp_actions.get_material_inventory()
            
            # Run optimization algorithm
            optimized_schedule = _optimize_schedule_algorithm(
                pending_orders, machine_availability, material_inventory
            )
            
            # Update production orders with optimized schedule
            updated_orders = []
            for order_update in optimized_schedule:
                erp_actions.update_production_order(
                    order_update["order_id"],
                    scheduled_start=order_update["scheduled_start"],
                    scheduled_end=order_update["scheduled_end"],
                    assigned_machine=order_update["machine_id"]
                )
                updated_orders.append(order_update["order_id"])
            
            conn.commit()
        
        result = {
            "orders_optimized": len(updated_orders),
            "updated_order_ids": updated_orders,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed production schedule optimization: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error optimizing production schedule: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=3, default_retry_delay=60)
def update_production_order(self, order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a production order with new information.
    
    Args:
        order_id: Production order ID
        updates: Dictionary of fields to update
        
    Returns:
        Dict containing update results
    """
    try:
        task_logger.info(f"Updating production order {order_id}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Validate order exists
            order = erp_actions.get_production_order(order_id)
            if not order:
                raise ValueError(f"Production order {order_id} not found")
            
            # Apply updates
            erp_actions.update_production_order(order_id, **updates)
            
            # Log the update
            erp_actions.log_production_order_change(
                order_id=order_id,
                changes=updates,
                changed_by="system",
                change_reason="Automated update"
            )
            
            conn.commit()
        
        result = {
            "order_id": order_id,
            "updates_applied": list(updates.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Updated production order {order_id}: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error updating production order {order_id}: {exc}")
        raise self.retry(exc=exc)


# Quality Control Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=60)
def process_quality_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a quality control alert and take appropriate actions.
    
    Args:
        alert_data: Quality alert information
        
    Returns:
        Dict containing processing results
    """
    try:
        task_logger.info(f"Processing quality alert: {alert_data.get('alert_id')}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            alert_id = alert_data["alert_id"]
            defect_type = alert_data.get("defect_type")
            machine_id = alert_data.get("machine_id")
            batch_id = alert_data.get("batch_id")
            
            # Record quality issue
            quality_issue_id = erp_actions.create_quality_issue(
                alert_id=alert_id,
                defect_type=defect_type,
                machine_id=machine_id,
                batch_id=batch_id,
                severity=alert_data.get("severity", "MEDIUM"),
                description=alert_data.get("description"),
                metadata=alert_data
            )
            
            # Determine corrective actions based on defect type
            actions_taken = []
            
            if defect_type in ["COLOR_VARIATION", "PATTERN_MISMATCH"]:
                # Adjust machine parameters
                erp_actions.schedule_machine_adjustment(machine_id, defect_type)
                actions_taken.append("MACHINE_ADJUSTMENT_SCHEDULED")
                
            if defect_type in ["THREAD_BREAK", "FABRIC_TEAR"]:
                # Stop production on affected machine
                erp_actions.request_production_halt(machine_id, "QUALITY_ISSUE")
                actions_taken.append("PRODUCTION_HALTED")
                
            if alert_data.get("severity") == "HIGH":
                # Notify quality control team
                send_email_notification.apply_async(
                    args=[
                        "quality_team@company.com",
                        f"High Severity Quality Alert: {defect_type}",
                        f"Quality issue {quality_issue_id} requires immediate attention on machine {machine_id}"
                    ],
                    queue="high_priority"
                )
                actions_taken.append("NOTIFICATION_SENT")
            
            conn.commit()
        
        result = {
            "alert_id": alert_id,
            "quality_issue_id": quality_issue_id,
            "actions_taken": actions_taken,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Processed quality alert {alert_id}: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error processing quality alert: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=1, default_retry_delay=300)
def analyze_defect_patterns(self) -> Dict[str, Any]:
    """
    Analyze defect patterns to identify trends and root causes.
    
    Returns:
        Dict containing analysis results
    """
    try:
        task_logger.info("Starting defect pattern analysis")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get quality issues from the last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            quality_issues = erp_actions.get_quality_issues_in_timeframe(start_time, end_time)
            
            if not quality_issues:
                return {"message": "No quality issues to analyze", "timestamp": end_time.isoformat()}
            
            # Analyze patterns
            analysis_results = _analyze_defect_patterns(quality_issues)
            
            # Store analysis results
            analysis_id = erp_actions.store_defect_analysis(analysis_results)
            
            # Generate recommendations if patterns found
            if analysis_results.get("patterns_found"):
                recommendations = _generate_quality_recommendations(analysis_results)
                erp_actions.store_quality_recommendations(analysis_id, recommendations)
                
                # Schedule follow-up actions if needed
                for rec in recommendations:
                    if rec.get("priority") == "HIGH":
                        process_quality_alert.apply_async(
                            args=[{
                                "alert_id": f"pattern_analysis_{analysis_id}",
                                "defect_type": "PATTERN_DETECTED",
                                "severity": "HIGH",
                                "description": rec["description"],
                                "recommendation": rec
                            }],
                            queue="quality_control"
                        )
            
            conn.commit()
        
        result = {
            "analysis_id": analysis_id,
            "issues_analyzed": len(quality_issues),
            "patterns_found": len(analysis_results.get("patterns", [])),
            "recommendations_generated": len(analysis_results.get("recommendations", [])),
            "timestamp": end_time.isoformat()
        }
        
        task_logger.info(f"Completed defect pattern analysis: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error analyzing defect patterns: {exc}")
        raise self.retry(exc=exc)


# Inventory Management Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=60)
def calculate_reorder_points(self) -> Dict[str, Any]:
    """
    Calculate reorder points for all materials based on usage patterns and lead times.
    
    Returns:
        Dict containing calculation results
    """
    try:
        task_logger.info("Starting reorder point calculations")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get all materials
            materials = erp_actions.get_all_materials()
            
            reorder_calculations = []
            reorders_needed = []
            
            for material in materials:
                material_id = material["material_id"]
                
                # Calculate usage rate (last 30 days)
                usage_data = erp_actions.get_material_usage(material_id, days=30)
                avg_daily_usage = sum(usage_data) / len(usage_data) if usage_data else 0
                
                # Get lead time
                lead_time_days = material.get("lead_time_days", 7)
                
                # Calculate safety stock (20% buffer)
                safety_stock = avg_daily_usage * lead_time_days * 0.2
                
                # Calculate reorder point
                reorder_point = (avg_daily_usage * lead_time_days) + safety_stock
                
                # Update material reorder point
                erp_actions.update_material_reorder_point(material_id, reorder_point)
                
                reorder_calculations.append({
                    "material_id": material_id,
                    "reorder_point": reorder_point,
                    "avg_daily_usage": avg_daily_usage,
                    "safety_stock": safety_stock
                })
                
                # Check if reorder is needed
                current_stock = material.get("current_stock", 0)
                if current_stock <= reorder_point:
                    # Schedule inventory update task
                    process_inventory_update.apply_async(
                        args=[{
                            "action": "REORDER_NEEDED",
                            "material_id": material_id,
                            "current_stock": current_stock,
                            "reorder_point": reorder_point,
                            "suggested_quantity": avg_daily_usage * lead_time_days * 2
                        }],
                        queue="inventory"
                    )
                    reorders_needed.append(material_id)
            
            conn.commit()
        
        result = {
            "calculations_completed": len(reorder_calculations),
            "reorders_needed": len(reorders_needed),
            "materials_needing_reorder": reorders_needed,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed reorder point calculations: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error calculating reorder points: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=3, default_retry_delay=60)
def process_inventory_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process inventory update or reorder request.
    
    Args:
        update_data: Inventory update information
        
    Returns:
        Dict containing processing results
    """
    try:
        action = update_data["action"]
        material_id = update_data["material_id"]
        
        task_logger.info(f"Processing inventory update - Action: {action}, Material: {material_id}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            if action == "REORDER_NEEDED":
                # Create purchase order request
                po_request_id = erp_actions.create_purchase_order_request(
                    material_id=material_id,
                    quantity=update_data["suggested_quantity"],
                    reason="AUTO_REORDER",
                    priority="NORMAL",
                    metadata=update_data
                )
                
                # Send notification to procurement team
                send_email_notification.apply_async(
                    args=[
                        "procurement@company.com",
                        f"Reorder Required: Material {material_id}",
                        f"Material {material_id} has reached reorder point. Purchase order request {po_request_id} created."
                    ],
                    queue="low_priority"
                )
                
                result_action = f"PO_REQUEST_CREATED:{po_request_id}"
                
            elif action == "STOCK_ADJUSTMENT":
                # Adjust stock levels
                erp_actions.adjust_material_stock(
                    material_id=material_id,
                    adjustment=update_data["adjustment"],
                    reason=update_data.get("reason", "SYSTEM_ADJUSTMENT"),
                    reference=update_data.get("reference")
                )
                result_action = "STOCK_ADJUSTED"
                
            elif action == "INCOMING_STOCK":
                # Process incoming stock
                erp_actions.add_material_stock(
                    material_id=material_id,
                    quantity=update_data["quantity"],
                    batch_number=update_data.get("batch_number"),
                    supplier_id=update_data.get("supplier_id")
                )
                result_action = "STOCK_ADDED"
                
            else:
                raise ValueError(f"Unknown inventory action: {action}")
            
            conn.commit()
        
        result = {
            "action": action,
            "material_id": material_id,
            "result": result_action,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Processed inventory update: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error processing inventory update: {exc}")
        raise self.retry(exc=exc)


# Maintenance Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=60)
def schedule_maintenance(self, machine_id: str, maintenance_type: str, priority: str = "NORMAL") -> Dict[str, Any]:
    """
    Schedule maintenance for a machine.
    
    Args:
        machine_id: Machine identifier
        maintenance_type: Type of maintenance (PREVENTIVE, CORRECTIVE, EMERGENCY)
        priority: Maintenance priority (LOW, NORMAL, HIGH, CRITICAL)
        
    Returns:
        Dict containing scheduling results
    """
    try:
        task_logger.info(f"Scheduling {maintenance_type} maintenance for machine {machine_id}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get machine information
            machine = erp_actions.get_machine(machine_id)
            if not machine:
                raise ValueError(f"Machine {machine_id} not found")
            
            # Determine maintenance window based on priority
            if priority == "CRITICAL":
                # Schedule immediately
                scheduled_time = datetime.utcnow() + timedelta(minutes=30)
            elif priority == "HIGH":
                # Schedule within next 4 hours
                scheduled_time = datetime.utcnow() + timedelta(hours=4)
            else:
                # Schedule during next maintenance window
                scheduled_time = _find_next_maintenance_window(machine_id, maintenance_type)
            
            # Create maintenance order
            maintenance_order_id = erp_actions.create_maintenance_order(
                machine_id=machine_id,
                maintenance_type=maintenance_type,
                priority=priority,
                scheduled_time=scheduled_time,
                estimated_duration=_estimate_maintenance_duration(maintenance_type),
                description=f"Scheduled {maintenance_type.lower()} maintenance"
            )
            
            # If high priority, halt production if needed
            if priority in ["HIGH", "CRITICAL"]:
                erp_actions.request_production_halt(
                    machine_id,
                    reason=f"MAINTENANCE_{priority}",
                    scheduled_time=scheduled_time
                )
                
                # Notify maintenance team
                send_email_notification.apply_async(
                    args=[
                        "maintenance@company.com",
                        f"{priority} Priority Maintenance Scheduled",
                        f"Maintenance order {maintenance_order_id} scheduled for machine {machine_id} at {scheduled_time}"
                    ],
                    queue="high_priority" if priority == "CRITICAL" else "default"
                )
            
            conn.commit()
        
        result = {
            "maintenance_order_id": maintenance_order_id,
            "machine_id": machine_id,
            "maintenance_type": maintenance_type,
            "priority": priority,
            "scheduled_time": scheduled_time.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Scheduled maintenance: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error scheduling maintenance for machine {machine_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=1, default_retry_delay=300)
def check_maintenance_schedule(self) -> Dict[str, Any]:
    """
    Check and update maintenance schedule based on machine usage and conditions.
    
    Returns:
        Dict containing check results
    """
    try:
        task_logger.info("Checking maintenance schedule")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get all machines
            machines = erp_actions.get_all_machines()
            
            maintenance_scheduled = []
            overdue_maintenance = []
            
            for machine in machines:
                machine_id = machine["machine_id"]
                
                # Check for overdue maintenance
                overdue = erp_actions.get_overdue_maintenance(machine_id)
                if overdue:
                    overdue_maintenance.extend(overdue)
                    
                    # Schedule urgent maintenance for overdue items
                    for maintenance in overdue:
                        schedule_maintenance.apply_async(
                            args=[machine_id, "CORRECTIVE", "HIGH"],
                            queue="maintenance"
                        )
                        maintenance_scheduled.append(f"{machine_id}:OVERDUE")
                
                # Check machine usage for preventive maintenance scheduling
                usage_hours = erp_actions.get_machine_usage_hours(machine_id, days=7)
                last_maintenance = erp_actions.get_last_maintenance(machine_id)
                
                if _should_schedule_preventive_maintenance(machine, usage_hours, last_maintenance):
                    schedule_maintenance.apply_async(
                        args=[machine_id, "PREVENTIVE", "NORMAL"],
                        queue="maintenance"
                    )
                    maintenance_scheduled.append(f"{machine_id}:PREVENTIVE")
            
            conn.commit()
        
        result = {
            "machines_checked": len(machines),
            "maintenance_scheduled": len(maintenance_scheduled),
            "overdue_found": len(overdue_maintenance),
            "scheduled_items": maintenance_scheduled,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed maintenance schedule check: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error checking maintenance schedule: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=3, default_retry_delay=60)
def process_maintenance_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process maintenance alert from machine sensors.
    
    Args:
        alert_data: Maintenance alert information
        
    Returns:
        Dict containing processing results
    """
    try:
        machine_id = alert_data["machine_id"]
        alert_type = alert_data["alert_type"]
        
        task_logger.info(f"Processing maintenance alert - Machine: {machine_id}, Type: {alert_type}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Determine maintenance priority based on alert type
            priority_mapping = {
                "VIBRATION_HIGH": "HIGH",
                "TEMPERATURE_HIGH": "CRITICAL",
                "OIL_PRESSURE_LOW": "HIGH",
                "BELT_TENSION_LOW": "NORMAL",
                "NOISE_LEVEL_HIGH": "NORMAL",
                "POWER_CONSUMPTION_HIGH": "NORMAL"
            }
            
            priority = priority_mapping.get(alert_type, "NORMAL")
            
            # Create maintenance alert record
            alert_id = erp_actions.create_maintenance_alert(
                machine_id=machine_id,
                alert_type=alert_type,
                priority=priority,
                sensor_data=alert_data.get("sensor_data"),
                description=alert_data.get("description"),
                metadata=alert_data
            )
            
            # Schedule appropriate maintenance
            if priority in ["HIGH", "CRITICAL"]:
                maintenance_result = schedule_maintenance.apply_async(
                    args=[machine_id, "CORRECTIVE", priority],
                    queue="high_priority"
                )
                scheduled_maintenance = maintenance_result.id
            else:
                # For normal priority, just log and schedule during next window
                scheduled_maintenance = None
                erp_actions.update_machine_maintenance_status(
                    machine_id,
                    f"ALERT_{alert_type}",
                    "Maintenance required - scheduled for next window"
                )
            
            conn.commit()
        
        result = {
            "alert_id": alert_id,
            "machine_id": machine_id,
            "alert_type": alert_type,
            "priority": priority,
            "scheduled_maintenance": scheduled_maintenance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Processed maintenance alert: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error processing maintenance alert: {exc}")
        raise self.retry(exc=exc)


# Critical Alert Processing
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=30)
def process_critical_alert(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process critical alerts that require immediate attention.
    
    Args:
        sensor_data: Critical sensor reading data
        
    Returns:
        Dict containing processing results
    """
    try:
        machine_id = sensor_data["machine_id"]
        sensor_type = sensor_data["sensor_type"]
        value = sensor_data["value"]
        
        task_logger.critical(f"Processing CRITICAL alert - Machine: {machine_id}, Sensor: {sensor_type}, Value: {value}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Create critical alert
            alert_id = erp_actions.create_alert(
                alert_type="CRITICAL_THRESHOLD",
                machine_id=machine_id,
                severity="CRITICAL",
                message=f"Critical threshold exceeded: {sensor_type} = {value}",
                metadata=sensor_data
            )
            
            actions_taken = []
            
            # Immediate actions based on sensor type
            if sensor_type == "TEMPERATURE" and value > 85:
                # Emergency shutdown
                erp_actions.emergency_machine_shutdown(machine_id, "OVERHEATING")
                actions_taken.append("EMERGENCY_SHUTDOWN")
                
            elif sensor_type == "PRESSURE" and value > 100:
                # Reduce pressure
                erp_actions.adjust_machine_pressure(machine_id, target_pressure=80)
                actions_taken.append("PRESSURE_REDUCED")
                
            elif sensor_type == "VIBRATION" and value > 50:
                # Stop machine
                erp_actions.stop_machine(machine_id, "EXCESSIVE_VIBRATION")
                actions_taken.append("MACHINE_STOPPED")
            
            # Schedule emergency maintenance
            emergency_maintenance.apply_async(
                args=[machine_id, sensor_data],
                queue="high_priority"
            )
            actions_taken.append("EMERGENCY_MAINTENANCE_SCHEDULED")
            
            # Send immediate notifications
            send_email_notification.apply_async(
                args=[
                    "emergency@company.com",
                    f"CRITICAL ALERT: Machine {machine_id}",
                    f"Critical alert {alert_id}: {sensor_type} threshold exceeded ({value}). Actions taken: {', '.join(actions_taken)}"
                ],
                queue="high_priority"
            )
            actions_taken.append("EMERGENCY_NOTIFICATION_SENT")
            
            conn.commit()
        
        result = {
            "alert_id": alert_id,
            "machine_id": machine_id,
            "sensor_type": sensor_type,
            "value": value,
            "actions_taken": actions_taken,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.critical(f"Processed critical alert: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error processing critical alert: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=1, default_retry_delay=60)
def emergency_shutdown_sequence(self, machine_id: str, reason: str) -> Dict[str, Any]:
    """
    Execute emergency shutdown sequence for a machine.
    
    Args:
        machine_id: Machine to shutdown
        reason: Reason for emergency shutdown
        
    Returns:
        Dict containing shutdown results
    """
    try:
        task_logger.critical(f"Executing emergency shutdown for machine {machine_id}: {reason}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Execute shutdown sequence
            shutdown_steps = []
            
            # 1. Stop production immediately
            erp_actions.emergency_production_stop(machine_id)
            shutdown_steps.append("PRODUCTION_STOPPED")
            
            # 2. Safe machine shutdown
            erp_actions.safe_machine_shutdown(machine_id)
            shutdown_steps.append("MACHINE_SHUTDOWN")
            
            # 3. Isolate machine power
            erp_actions.isolate_machine_power(machine_id)
            shutdown_steps.append("POWER_ISOLATED")
            
            # 4. Create emergency record
            emergency_id = erp_actions.create_emergency_record(
                machine_id=machine_id,
                emergency_type="SHUTDOWN",
                reason=reason,
                actions_taken=shutdown_steps,
                timestamp=datetime.utcnow()
            )
            shutdown_steps.append(f"EMERGENCY_RECORD_CREATED:{emergency_id}")
            
            # 5. Schedule immediate inspection
            schedule_maintenance.apply_async(
                args=[machine_id, "EMERGENCY", "CRITICAL"],
                queue="high_priority"
            )
            shutdown_steps.append("INSPECTION_SCHEDULED")
            
            # 6. Notify emergency response team
            send_email_notification.apply_async(
                args=[
                    "emergency@company.com",
                    f"EMERGENCY SHUTDOWN: Machine {machine_id}",
                    f"Emergency shutdown completed for machine {machine_id}. Reason: {reason}. Emergency ID: {emergency_id}"
                ],
                queue="high_priority"
            )
            shutdown_steps.append("EMERGENCY_TEAM_NOTIFIED")
            
            conn.commit()
        
        result = {
            "machine_id": machine_id,
            "reason": reason,
            "emergency_id": emergency_id,
            "shutdown_steps": shutdown_steps,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.critical(f"Emergency shutdown completed: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error in emergency shutdown sequence: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=30)
def emergency_maintenance(self, machine_id: str, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schedule and coordinate emergency maintenance.
    
    Args:
        machine_id: Machine requiring emergency maintenance
        trigger_data: Data that triggered the emergency
        
    Returns:
        Dict containing maintenance coordination results
    """
    try:
        task_logger.critical(f"Coordinating emergency maintenance for machine {machine_id}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Create emergency maintenance order
            maintenance_order_id = erp_actions.create_maintenance_order(
                machine_id=machine_id,
                maintenance_type="EMERGENCY",
                priority="CRITICAL",
                scheduled_time=datetime.utcnow(),
                estimated_duration=120,  # 2 hours initial estimate
                description=f"Emergency maintenance triggered by: {trigger_data}",
                metadata=trigger_data
            )
            
            # Get available technicians
            available_technicians = erp_actions.get_available_technicians(priority="EMERGENCY")
            
            if available_technicians:
                # Assign best available technician
                assigned_tech = available_technicians[0]  # Assuming first is best match
                erp_actions.assign_maintenance_technician(maintenance_order_id, assigned_tech["technician_id"])
                
                # Notify assigned technician
                send_email_notification.apply_async(
                    args=[
                        assigned_tech["email"],
                        f"EMERGENCY MAINTENANCE ASSIGNMENT: Machine {machine_id}",
                        f"You have been assigned emergency maintenance order {maintenance_order_id} for machine {machine_id}. Please respond immediately."
                    ],
                    queue="high_priority"
                )
                assigned_technician = assigned_tech["technician_id"]
            else:
                # No available technicians - escalate
                send_email_notification.apply_async(
                    args=[
                        "maintenance_manager@company.com",
                        f"CRITICAL: No Technicians Available for Emergency",
                        f"Emergency maintenance order {maintenance_order_id} for machine {machine_id} cannot be assigned. No technicians available."
                    ],
                    queue="high_priority"
                )
                assigned_technician = None
            
            # Request parts if needed
            required_parts = _estimate_emergency_parts(machine_id, trigger_data)
            if required_parts:
                for part in required_parts:
                    erp_actions.create_parts_request(
                        maintenance_order_id=maintenance_order_id,
                        part_id=part["part_id"],
                        quantity=part["quantity"],
                        priority="EMERGENCY"
                    )
            
            conn.commit()
        
        result = {
            "maintenance_order_id": maintenance_order_id,
            "machine_id": machine_id,
            "assigned_technician": assigned_technician,
            "parts_requested": len(required_parts) if required_parts else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.critical(f"Emergency maintenance coordinated: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error coordinating emergency maintenance: {exc}")
        raise self.retry(exc=exc)


# Report Generation Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=300)
def generate_daily_report(self, report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate daily production and quality report.
    
    Args:
        report_date: Date for the report (ISO format), defaults to yesterday
        
    Returns:
        Dict containing report generation results
    """
    try:
        if report_date:
            target_date = datetime.fromisoformat(report_date).date()
        else:
            target_date = (datetime.utcnow() - timedelta(days=1)).date()
        
        task_logger.info(f"Generating daily report for {target_date}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Collect report data
            report_data = {
                "report_date": target_date.isoformat(),
                "production_summary": erp_actions.get_daily_production_summary(target_date),
                "quality_metrics": erp_actions.get_daily_quality_metrics(target_date),
                "machine_utilization": erp_actions.get_daily_machine_utilization(target_date),
                "inventory_status": erp_actions.get_inventory_status(target_date),
                "maintenance_activities": erp_actions.get_daily_maintenance_activities(target_date),
                "alerts_summary": erp_actions.get_daily_alerts_summary(target_date),
            }
            
            # Generate report
            report_content = _generate_daily_report_content(report_data)
            
            # Store report
            report_id = erp_actions.store_daily_report(
                report_date=target_date,
                report_data=report_data,
                report_content=report_content
            )
            
            # Generate PDF report
            pdf_path = _generate_daily_report_pdf(report_id, report_content, target_date)
            
            # Send report to stakeholders
            send_daily_report_email.apply_async(
                args=[report_id, pdf_path, target_date.isoformat()],
                queue="reports"
            )
            
            conn.commit()
        
        result = {
            "report_id": report_id,
            "report_date": target_date.isoformat(),
            "pdf_generated": bool(pdf_path),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Generated daily report: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error generating daily report: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=600)
def generate_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate monthly comprehensive report.
    
    Args:
        year: Report year, defaults to last month
        month: Report month, defaults to last month
        
    Returns:
        Dict containing report generation results
    """
    try:
        if year and month:
            target_date = datetime(year, month, 1).date()
        else:
            # Default to last month
            today = datetime.utcnow().date()
            if today.month == 1:
                target_date = datetime(today.year - 1, 12, 1).date()
            else:
                target_date = datetime(today.year, today.month - 1, 1).date()
        
        task_logger.info(f"Generating monthly report for {target_date.year}-{target_date.month:02d}")
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get month boundaries
            start_date = target_date
            if target_date.month == 12:
                end_date = datetime(target_date.year + 1, 1, 1).date()
            else:
                end_date = datetime(target_date.year, target_date.month + 1, 1).date()
            
            # Collect comprehensive monthly data
            report_data = {
                "report_period": f"{target_date.year}-{target_date.month:02d}",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "production_analysis": erp_actions.get_monthly_production_analysis(start_date, end_date),
                "quality_trends": erp_actions.get_monthly_quality_trends(start_date, end_date),
                "efficiency_metrics": erp_actions.get_monthly_efficiency_metrics(start_date, end_date),
                "inventory_analysis": erp_actions.get_monthly_inventory_analysis(start_date, end_date),
                "maintenance_summary": erp_actions.get_monthly_maintenance_summary(start_date, end_date),
                "cost_analysis": erp_actions.get_monthly_cost_analysis(start_date, end_date),
                "performance_kpis": erp_actions.get_monthly_kpis(start_date, end_date),
            }
            
            # Generate comprehensive report
            report_content = _generate_monthly_report_content(report_data)
            
            # Store report
            report_id = erp_actions.store_monthly_report(
                report_period=f"{target_date.year}-{target_date.month:02d}",
                report_data=report_data,
                report_content=report_content
            )
            
            # Generate PDF report with charts
            pdf_path = _generate_monthly_report_pdf(report_id, report_content, report_data)
            
            # Send report to management
            send_monthly_report_email.apply_async(
                args=[report_id, pdf_path, f"{target_date.year}-{target_date.month:02d}"],
                queue="reports"
            )
            
            conn.commit()
        
        result = {
            "report_id": report_id,
            "report_period": f"{target_date.year}-{target_date.month:02d}",
            "pdf_generated": bool(pdf_path),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Generated monthly report: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error generating monthly report: {exc}")
        raise self.retry(exc=exc)


# Utility and Maintenance Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_sensor_data(self, retention_days: int = 90) -> Dict[str, Any]:
    """
    Clean up old sensor data to manage database size.
    
    Args:
        retention_days: Number of days to retain data
        
    Returns:
        Dict containing cleanup results
    """
    try:
        task_logger.info(f"Cleaning up sensor data older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Archive old data before deletion (optional)
            archived_count = erp_actions.archive_old_sensor_data(cutoff_date)
            
            # Delete old raw sensor data
            deleted_count = erp_actions.delete_old_sensor_data(cutoff_date)
            
            # Clean up related data
            deleted_aggregations = erp_actions.cleanup_old_aggregations(cutoff_date)
            deleted_logs = erp_actions.cleanup_old_logs(cutoff_date)
            
            conn.commit()
        
        result = {
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "archived_records": archived_count,
            "deleted_records": deleted_count,
            "deleted_aggregations": deleted_aggregations,
            "deleted_logs": deleted_logs,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed data cleanup: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error cleaning up old sensor data: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=600)
def backup_database(self) -> Dict[str, Any]:
    """
    Create database backup.
    
    Returns:
        Dict containing backup results
    """
    try:
        task_logger.info("Starting database backup")
        
        backup_timestamp = datetime.utcnow()
        backup_filename = f"textile_erp_backup_{backup_timestamp.strftime('%Y%m%d_%H%M%S')}.sql"
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Create backup
            backup_path = erp_actions.create_database_backup(backup_filename)
            
            # Verify backup integrity
            backup_valid = erp_actions.verify_backup_integrity(backup_path)
            
            # Store backup metadata
            backup_id = erp_actions.store_backup_metadata(
                backup_filename=backup_filename,
                backup_path=backup_path,
                backup_size=Path(backup_path).stat().st_size,
                backup_timestamp=backup_timestamp,
                integrity_check=backup_valid
            )
            
            conn.commit()
        
        # Clean up old backups (keep last 30 days)
        cleanup_old_backups.apply_async(args=[30], queue="low_priority")
        
        result = {
            "backup_id": backup_id,
            "backup_filename": backup_filename,
            "backup_path": backup_path,
            "backup_valid": backup_valid,
            "timestamp": backup_timestamp.isoformat()
        }
        
        task_logger.info(f"Database backup completed: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error creating database backup: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=1, default_retry_delay=300)
def cleanup_old_backups(self, retention_days: int = 30) -> Dict[str, Any]:
    """
    Clean up old backup files.
    
    Args:
        retention_days: Number of days to retain backups
        
    Returns:
        Dict containing cleanup results
    """
    try:
        task_logger.info(f"Cleaning up backups older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            
            # Get old backups
            old_backups = erp_actions.get_old_backups(cutoff_date)
            
            deleted_files = []
            errors = []
            
            for backup in old_backups:
                try:
                    # Delete backup file
                    if Path(backup["backup_path"]).exists():
                        Path(backup["backup_path"]).unlink()
                        deleted_files.append(backup["backup_filename"])
                    
                    # Remove backup metadata
                    erp_actions.delete_backup_metadata(backup["backup_id"])
                    
                except Exception as e:
                    errors.append(f"{backup['backup_filename']}: {str(e)}")
            
            conn.commit()
        
        result = {
            "retention_days": retention_days,
            "deleted_files": len(deleted_files),
            "deleted_file_names": deleted_files,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Completed backup cleanup: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error cleaning up old backups: {exc}")
        raise self.retry(exc=exc)


# Notification Tasks
@celery_app.task(base=TextileERPTask, bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send email notification.
    
    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body
        
    Returns:
        Dict containing send results
    """
    try:
        task_logger.info(f"Sending email notification to {recipient}")
        
        # TODO: Implement actual email sending logic
        # For now, just log the email
        task_logger.info(f"EMAIL TO: {recipient}")
        task_logger.info(f"SUBJECT: {subject}")
        task_logger.info(f"BODY: {body}")
        
        # Store notification record
        with get_db_connection() as conn:
            erp_actions = TextileERPActions(conn)
            notification_id = erp_actions.store_notification(
                notification_type="EMAIL",
                recipient=recipient,
                subject=subject,
                body=body,
                status="SENT",
                sent_at=datetime.utcnow()
            )
            conn.commit()
        
        result = {
            "notification_id": notification_id,
            "recipient": recipient,
            "subject": subject,
            "status": "SENT",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Email notification sent: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error sending email notification: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=60)
def send_daily_report_email(self, report_id: str, pdf_path: str, report_date: str) -> Dict[str, Any]:
    """
    Send daily report via email.
    
    Args:
        report_id: Report identifier
        pdf_path: Path to PDF report
        report_date: Report date
        
    Returns:
        Dict containing send results
    """
    try:
        task_logger.info(f"Sending daily report {report_id} for {report_date}")
        
        # Get report recipients
        recipients = [
            "production@company.com",
            "quality@company.com",
            "management@company.com"
        ]
        
        subject = f"Daily Production Report - {report_date}"
        body = f"""
        Please find attached the daily production report for {report_date}.
        
        Report ID: {report_id}
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        This is an automated report generated by the Textile ERP System.
        """
        
        sent_notifications = []
        for recipient in recipients:
            notification_result = send_email_notification.apply_async(
                args=[recipient, subject, body],
                queue="low_priority"
            )
            sent_notifications.append(notification_result.id)
        
        result = {
            "report_id": report_id,
            "report_date": report_date,
            "recipients": len(recipients),
            "notifications_sent": len(sent_notifications),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Daily report email sent: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error sending daily report email: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(base=TextileERPTask, bind=True, max_retries=2, default_retry_delay=60)
def send_monthly_report_email(self, report_id: str, pdf_path: str, report_period: str) -> Dict[str, Any]:
    """
    Send monthly report via email.
    
    Args:
        report_id: Report identifier
        pdf_path: Path to PDF report
        report_period: Report period (YYYY-MM)
        
    Returns:
        Dict containing send results
    """
    try:
        task_logger.info(f"Sending monthly report {report_id} for {report_period}")
        
        # Get report recipients (management level)
        recipients = [
            "ceo@company.com",
            "coo@company.com",
            "production_manager@company.com",
            "quality_manager@company.com"
        ]
        
        subject = f"Monthly Production Report - {report_period}"
        body = f"""
        Please find attached the comprehensive monthly production report for {report_period}.
        
        Report ID: {report_id}
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        This report includes production analysis, quality trends, efficiency metrics,
        and key performance indicators for the reporting period.
        
        This is an automated report generated by the Textile ERP System.
        """
        
        sent_notifications = []
        for recipient in recipients:
            notification_result = send_email_notification.apply_async(
                args=[recipient, subject, body],
                queue="low_priority"
            )
            sent_notifications.append(notification_result.id)
        
        result = {
            "report_id": report_id,
            "report_period": report_period,
            "recipients": len(recipients),
            "notifications_sent": len(sent_notifications),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_logger.info(f"Monthly report email sent: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Error sending monthly report email: {exc}")
        raise self.retry(exc=exc)


# Helper Functions
def _validate_sensor_reading(reading: Dict[str, Any]) -> bool:
    """Validate sensor reading data."""
    required_fields = ["machine_id", "sensor_type", "value", "timestamp"]
    return all(field in reading for field in required_fields)


def _detect_sensor_anomaly(reading: Dict[str, Any]) -> bool:
    """Detect if sensor reading indicates an anomaly."""
    # Simple anomaly detection - in production, use ML models
    sensor_type = reading.get("sensor_type")
    value = reading.get("value", 0)
    
    # Define normal ranges for different sensor types
    normal_ranges = {
        "TEMPERATURE": (15, 80),
        "PRESSURE": (10, 95),
        "VIBRATION": (0, 40),
        "HUMIDITY": (30, 70),
        "SPEED": (0, 1000)
    }
    
    if sensor_type in normal_ranges:
        min_val, max_val = normal_ranges[sensor_type]
        return not (min_val <= value <= max_val)
    
    return False


def _check_critical_threshold(reading: Dict[str, Any]) -> bool:
    """Check if sensor reading exceeds critical thresholds."""
    sensor_type = reading.get("sensor_type")
    value = reading.get("value", 0)
    
    # Define critical thresholds
    critical_thresholds = {
        "TEMPERATURE": 85,
        "PRESSURE": 100,
        "VIBRATION": 50
    }
    
    return sensor_type in critical_thresholds and value >= critical_thresholds[sensor_type]


def _optimize_schedule_algorithm(orders, machine_availability, material_inventory):
    """Optimize production schedule using simple heuristic algorithm."""
    # Simplified scheduling algorithm - in production, use advanced optimization
    optimized_schedule = []
    
    # Sort orders by priority and due date
    sorted_orders = sorted(orders, key=lambda x: (x.get("priority", 5), x.get("due_date", "")))
    
    for order in sorted_orders:
        # Find best machine for this order
        suitable_machines = [m for m in machine_availability 
                           if m.get("machine_type") == order.get("required_machine_type")]
        
        if suitable_machines:
            # Choose machine with earliest availability
            best_machine = min(suitable_machines, key=lambda x: x.get("next_available", ""))
            
            # Schedule the order
            optimized_schedule.append({
                "order_id": order["order_id"],
                "machine_id": best_machine["machine_id"],
                "scheduled_start": best_machine["next_available"],
                "scheduled_end": best_machine["next_available"] + timedelta(hours=order.get("estimated_hours", 4))
            })
    
    return optimized_schedule


def _analyze_defect_patterns(quality_issues):
    """Analyze defect patterns to identify trends."""
    patterns = []
    
    # Group by defect type
    defect_counts = {}
    machine_defects = {}
    
    for issue in quality_issues:
        defect_type = issue.get("defect_type", "UNKNOWN")
        machine_id = issue.get("machine_id", "UNKNOWN")
        
        defect_counts[defect_type] = defect_counts.get(defect_type, 0) + 1
        
        if machine_id not in machine_defects:
            machine_defects[machine_id] = {}
        machine_defects[machine_id][defect_type] = machine_defects[machine_id].get(defect_type, 0) + 1
    
    # Find patterns
    for defect_type, count in defect_counts.items():
        if count > 3:  # More than 3 occurrences indicates a pattern
            patterns.append({
                "pattern_type": "FREQUENT_DEFECT",
                "defect_type": defect_type,
                "occurrence_count": count,
                "severity": "HIGH" if count > 10 else "MEDIUM"
            })
    
    # Machine-specific patterns
    for machine_id, defects in machine_defects.items():
        total_defects = sum(defects.values())
        if total_defects > 5:
            patterns.append({
                "pattern_type": "MACHINE_SPECIFIC",
                "machine_id": machine_id,
                "total_defects": total_defects,
                "defect_breakdown": defects,
                "severity": "HIGH" if total_defects > 15 else "MEDIUM"
            })
    
    return {
        "patterns": patterns,
        "patterns_found": len(patterns) > 0,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


def _generate_quality_recommendations(analysis_results):
    """Generate quality improvement recommendations based on analysis."""
    recommendations = []
    
    for pattern in analysis_results.get("patterns", []):
        if pattern["pattern_type"] == "FREQUENT_DEFECT":
            recommendations.append({
                "priority": pattern["severity"],
                "type": "PROCESS_IMPROVEMENT",
                "description": f"Frequent {pattern['defect_type']} defects detected. Review and adjust process parameters.",
                "action_items": [
                    f"Review process settings for {pattern['defect_type']} prevention",
                    "Conduct operator training on quality standards",
                    "Implement additional quality checkpoints"
                ]
            })
        
        elif pattern["pattern_type"] == "MACHINE_SPECIFIC":
            recommendations.append({
                "priority": pattern["severity"],
                "type": "MACHINE_MAINTENANCE",
                "description": f"Machine {pattern['machine_id']} showing high defect rate.",
                "action_items": [
                    f"Schedule comprehensive maintenance for machine {pattern['machine_id']}",
                    "Calibrate machine sensors and actuators",
                    "Review operator training for this machine"
                ]
            })
    
    return recommendations


def _find_next_maintenance_window(machine_id, maintenance_type):
    """Find next available maintenance window for a machine."""
    # Simplified logic - in production, consider production schedule
    base_time = datetime.utcnow()
    
    if maintenance_type == "PREVENTIVE":
        # Schedule during typical maintenance hours (2-6 AM)
        next_window = base_time.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_window <= base_time:
            next_window += timedelta(days=1)
    else:
        # Schedule as soon as possible
        next_window = base_time + timedelta(hours=1)
    
    return next_window


def _estimate_maintenance_duration(maintenance_type):
    """Estimate maintenance duration in minutes."""
    durations = {
        "PREVENTIVE": 120,
        "CORRECTIVE": 180,
        "EMERGENCY": 240
    }
    return durations.get(maintenance_type, 120)


def _should_schedule_preventive_maintenance(machine, usage_hours, last_maintenance):
    """Determine if preventive maintenance should be scheduled."""
    # Simple logic - in production, use machine-specific maintenance schedules
    if not last_maintenance:
        return True
    
    last_maintenance_date = datetime.fromisoformat(last_maintenance["completed_at"])
    days_since_maintenance = (datetime.utcnow() - last_maintenance_date).days
    
    # Schedule if more than 30 days since last maintenance or high usage
    return days_since_maintenance > 30 or usage_hours > 168  # 168 hours = 1 week of continuous operation


def _estimate_emergency_parts(machine_id, trigger_data):
    """Estimate parts that might be needed for emergency maintenance."""
    # Simplified part estimation based on trigger type
    sensor_type = trigger_data.get("sensor_type", "")
    
    parts_map = {
        "TEMPERATURE": [{"part_id": "COOLING_FAN", "quantity": 1}],
        "VIBRATION": [{"part_id": "BEARING_SET", "quantity": 2}],
        "PRESSURE": [{"part_id": "PRESSURE_VALVE", "quantity": 1}]
    }
    
    return parts_map.get(sensor_type, [])


def _generate_daily_report_content(report_data):
    """Generate daily report content."""
    # Simplified report generation - in production, use templates
    content = f"""
    DAILY PRODUCTION REPORT - {report_data['report_date']}
    
    PRODUCTION SUMMARY:
    - Total Production: {report_data['production_summary'].get('total_units', 0)} units
    - Efficiency: {report_data['production_summary'].get('efficiency', 0)}%
    
    QUALITY METRICS:
    - Defect Rate: {report_data['quality_metrics'].get('defect_rate', 0)}%
    - Quality Score: {report_data['quality_metrics'].get('quality_score', 0)}/100
    
    MACHINE UTILIZATION:
    - Average Utilization: {report_data['machine_utilization'].get('average', 0)}%
    
    ALERTS:
    - Total Alerts: {report_data['alerts_summary'].get('total_alerts', 0)}
    - Critical Alerts: {report_data['alerts_summary'].get('critical_alerts', 0)}
    """
    return content


def _generate_monthly_report_content(report_data):
    """Generate monthly report content."""
    # Simplified monthly report generation
    content = f"""
    MONTHLY PRODUCTION REPORT - {report_data['report_period']}
    
    EXECUTIVE SUMMARY:
    - Total Production: {report_data['production_analysis'].get('total_units', 0)} units
    - Overall Efficiency: {report_data['efficiency_metrics'].get('overall_efficiency', 0)}%
    - Quality Score: {report_data['quality_trends'].get('average_quality', 0)}/100
    
    KEY PERFORMANCE INDICATORS:
    - On-Time Delivery: {report_data['performance_kpis'].get('on_time_delivery', 0)}%
    - Machine Uptime: {report_data['performance_kpis'].get('machine_uptime', 0)}%
    - Cost Efficiency: {report_data['cost_analysis'].get('cost_per_unit', 0)}
    
    TRENDS AND RECOMMENDATIONS:
    [Detailed analysis would be included here in production]
    """
    return content


def _generate_daily_report_pdf(report_id, content, report_date):
    """Generate PDF for daily report."""
    # TODO: Implement PDF generation
    # For now, return placeholder path
    return f"/reports/daily/daily_report_{report_date}_{report_id}.pdf"


def _generate_monthly_report_pdf(report_id, content, report_data):
    """Generate PDF for monthly report with charts."""
    # TODO: Implement PDF generation with charts
    # For now, return placeholder path
    return f"/reports/monthly/monthly_report_{report_data['report_period']}_{report_id}.pdf"