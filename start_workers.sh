#!/bin/bash
# start_workers.sh
# Comprehensive script to start all Celery components for Textile ERP system

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PATH="$PROJECT_DIR/.venv"
LOGS_DIR="$PROJECT_DIR/logs/celery"
PIDS_DIR="$PROJECT_DIR/pids"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create necessary directories
mkdir -p "$LOGS_DIR"
mkdir -p "$PIDS_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
check_venv() {
    if [ -d "$VENV_PATH" ]; then
        log_info "Using virtual environment: $VENV_PATH"
        source "$VENV_PATH/bin/activate"
    else
        log_warning "Virtual environment not found at $VENV_PATH"
        log_info "Using system Python"
    fi
}

# Check if Redis/RabbitMQ is running
check_broker() {
    local broker_url="${CELERY_BROKER_URL:-redis://localhost:6379/0}"
    log_info "Checking broker connectivity: $broker_url"
    
    if [[ $broker_url == redis* ]]; then
        # Check Redis
        if command -v redis-cli >/dev/null 2>&1; then
            if redis-cli ping >/dev/null 2>&1; then
                log_success "Redis broker is running"
                return 0
            else
                log_error "Redis broker is not responding"
                return 1
            fi
        else
            log_warning "redis-cli not found, cannot verify Redis connectivity"
        fi
    elif [[ $broker_url == amqp* ]]; then
        # Check RabbitMQ (basic check)
        if command -v rabbitmqctl >/dev/null 2>&1; then
            if rabbitmqctl status >/dev/null 2>&1; then
                log_success "RabbitMQ broker is running"
                return 0
            else
                log_error "RabbitMQ broker is not responding"
                return 1
            fi
        else
            log_warning "rabbitmqctl not found, cannot verify RabbitMQ connectivity"
        fi
    else
        log_warning "Unknown broker type, skipping broker check"
    fi
    
    return 0
}

# Start individual worker
start_worker() {
    local worker_name="$1"
    local queues="$2"
    local concurrency="$3"
    local log_file="$LOGS_DIR/${worker_name}.log"
    local pid_file="$PIDS_DIR/${worker_name}.pid"
    
    log_info "Starting $worker_name worker..."
    
    nohup python "$PROJECT_DIR/start_celery_worker.py" worker \
        --queues $queues \
        --concurrency "$concurrency" \
        --worker-name "$worker_name" \
        --log-level INFO \
        > "$log_file" 2>&1 &
    
    local pid=$!
    echo $pid > "$pid_file"
    
    # Wait a moment and check if process is still running
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        log_success "$worker_name started with PID $pid"
    else
        log_error "Failed to start $worker_name worker"
        return 1
    fi
}

# Start Celery Beat scheduler
start_beat() {
    local log_file="$LOGS_DIR/beat.log"
    local pid_file="$PIDS_DIR/beat.pid"
    
    log_info "Starting Celery Beat scheduler..."
    
    nohup python "$PROJECT_DIR/start_celery_worker.py" beat \
        > "$log_file" 2>&1 &
    
    local pid=$!
    echo $pid > "$pid_file"
    
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        log_success "Celery Beat started with PID $pid"
    else
        log_error "Failed to start Celery Beat"
        return 1
    fi
}

# Start Flower monitor
start_flower() {
    local port="${FLOWER_PORT:-5555}"
    local log_file="$LOGS_DIR/flower.log"
    local pid_file="$PIDS_DIR/flower.pid"
    
    log_info "Starting Flower monitor on port $port..."
    
    nohup python "$PROJECT_DIR/start_celery_worker.py" flower \
        --flower-port "$port" \
        > "$log_file" 2>&1 &
    
    local pid=$!
    echo $pid > "$pid_file"
    
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        log_success "Flower monitor started with PID $pid (http://localhost:$port)"
    else
        log_error "Failed to start Flower monitor"
        return 1
    fi
}

# Stop all workers
stop_workers() {
    log_info "Stopping all Celery workers..."
    
    for pid_file in "$PIDS_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local worker_name=$(basename "$pid_file" .pid)
            
            if kill -0 $pid 2>/dev/null; then
                log_info "Stopping $worker_name (PID: $pid)..."
                kill -TERM $pid
                
                # Wait up to 10 seconds for graceful shutdown
                for i in {1..10}; do
                    if ! kill -0 $pid 2>/dev/null; then
                        break
                    fi
                    sleep 1
                done
                
                # Force kill if still running
                if kill -0 $pid 2>/dev/null; then
                    log_warning "Force killing $worker_name (PID: $pid)..."
                    kill -KILL $pid
                fi
                
                log_success "$worker_name stopped"
            else
                log_warning "$worker_name PID file exists but process not running"
            fi
            
            rm -f "$pid_file"
        fi
    done
}

# Check worker status
status_workers() {
    log_info "Checking worker status..."
    
    local running_count=0
    local total_count=0
    
    for pid_file in "$PIDS_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local worker_name=$(basename "$pid_file" .pid)
            total_count=$((total_count + 1))
            
            if kill -0 $pid 2>/dev/null; then
                log_success "$worker_name is running (PID: $pid)"
                running_count=$((running_count + 1))
            else
                log_error "$worker_name is not running"
                rm -f "$pid_file"  # Clean up stale PID file
            fi
        fi
    done
    
    if [ $total_count -eq 0 ]; then
        log_warning "No workers configured"
    else
        log_info "$running_count/$total_count workers are running"
    fi
}

# Show logs
show_logs() {
    local worker_name="${1:-all}"
    
    if [ "$worker_name" = "all" ]; then
        log_info "Showing logs for all workers..."
        tail -f "$LOGS_DIR"/*.log
    else
        local log_file="$LOGS_DIR/${worker_name}.log"
        if [ -f "$log_file" ]; then
            log_info "Showing logs for $worker_name..."
            tail -f "$log_file"
        else
            log_error "Log file not found for $worker_name"
            return 1
        fi
    fi
}

# Main function
main() {
    local action="${1:-start}"
    
    case "$action" in
        "start")
            log_info "Starting Textile ERP Celery workers..."
            
            # Check prerequisites
            check_venv
            check_broker
            
            # Start workers with different configurations
            start_worker "high_priority" "high_priority,sensor_data" 4
            start_worker "production" "production,quality_control" 2
            start_worker "maintenance" "maintenance,inventory" 2
            start_worker "reports" "reports,low_priority" 1
            start_worker "general" "default" 2
            
            # Start Beat scheduler
            start_beat
            
            # Start Flower monitor
            start_flower
            
            log_success "All Celery components started successfully!"
            log_info "Logs are available in: $LOGS_DIR"
            log_info "Flower monitor: http://localhost:${FLOWER_PORT:-5555}"
            ;;
            
        "stop")
            stop_workers
            ;;
            
        "restart")
            log_info "Restarting all workers..."
            stop_workers
            sleep 5
            $0 start
            ;;
            
        "status")
            status_workers
            ;;
            
        "logs")
            show_logs "$2"
            ;;
            
        "worker")
            # Start specific worker type
            local worker_type="$2"
            check_venv
            check_broker
            
            case "$worker_type" in
                "high-priority")
                    start_worker "high_priority" "high_priority,sensor_data" 4
                    ;;
                "production")
                    start_worker "production" "production,quality_control" 2
                    ;;
                "maintenance")
                    start_worker "maintenance" "maintenance,inventory" 2
                    ;;
                "reports")
                    start_worker "reports" "reports,low_priority" 1
                    ;;
                *)
                    log_error "Unknown worker type: $worker_type"
                    echo "Available types: high-priority, production, maintenance, reports"
                    exit 1
                    ;;
            esac
            ;;
            
        "beat")
            check_venv
            check_broker
            start_beat
            ;;
            
        "flower")
            check_venv
            start_flower
            ;;
            
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start           Start all Celery components (default)
    stop            Stop all workers
    restart         Restart all workers
    status          Show worker status
    logs [worker]   Show logs (all workers or specific worker)
    worker TYPE     Start specific worker type
    beat            Start only Celery Beat scheduler
    flower          Start only Flower monitor
    help            Show this help message

Worker Types:
    high-priority   High priority and sensor data processing
    production      Production and quality control tasks
    maintenance     Maintenance and inventory tasks
    reports         Report generation and low priority tasks

Environment Variables:
    CELERY_BROKER_URL     Celery broker URL (default: redis://localhost:6379/0)
    CELERY_RESULT_BACKEND Result backend URL (default: redis://localhost:6379/0)
    FLOWER_PORT           Flower monitor port (default: 5555)

Examples:
    $0 start                    # Start all components
    $0 worker high-priority     # Start only high-priority worker
    $0 logs production          # Show production worker logs
    $0 status                   # Check worker status
EOF
            ;;
            
        *)
            log_error "Unknown action: $action"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Handle signals for graceful shutdown
trap 'log_warning "Interrupted! Stopping workers..."; stop_workers; exit 130' INT TERM

# Run main function
main "$@"