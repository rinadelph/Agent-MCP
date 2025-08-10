"""
Backtesting Engine for Textile ERP System

Provides comprehensive backtesting capabilities with historical data loading,
strategy execution, performance metrics, and event-driven simulation.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import pickle
from concurrent.futures import ThreadPoolExecutor
import threading
from abc import ABC, abstractmethod

from ...core.config import logger
from ...db.connection import get_db_connection


class BacktestState(Enum):
    """Backtesting execution states"""
    INITIALIZED = "initialized"
    LOADING_DATA = "loading_data"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BacktestConfig:
    """Configuration for backtesting scenarios"""
    
    # Time range
    start_date: datetime
    end_date: datetime
    
    # Data sources
    data_path: str = "/mnt/c/Users/psytz/TMUX Final/Tmux-Orchestrator/ERP Data"
    
    # Strategy configuration
    strategies: List[str] = field(default_factory=list)
    strategy_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Execution settings
    parallel_execution: bool = True
    max_workers: int = 4
    random_seed: Optional[int] = None
    
    # Simulation parameters
    simulation_frequency: str = "daily"  # hourly, daily, weekly
    warmup_period: int = 30  # days for strategy warmup
    
    # Performance tracking
    benchmark_strategy: Optional[str] = None
    risk_free_rate: float = 0.02
    
    # Output configuration
    save_results: bool = True
    output_directory: str = "backtest_results"
    detailed_logging: bool = True
    
    # Monte Carlo settings
    monte_carlo_runs: int = 1
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        
        if self.warmup_period < 0:
            raise ValueError("Warmup period must be non-negative")
        
        if not self.strategies:
            logger.warning("No strategies specified for backtesting")
        
        return True


class BacktestEvent:
    """Base class for backtesting events"""
    
    def __init__(self, timestamp: datetime, event_type: str, data: Dict[str, Any]):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
        self.processed = False
    
    def __repr__(self):
        return f"BacktestEvent({self.timestamp}, {self.event_type}, {len(self.data)} fields)"


class EventQueue:
    """Thread-safe event queue for backtesting"""
    
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
    
    def add_event(self, event: BacktestEvent):
        """Add event to queue in chronological order"""
        with self._lock:
            # Insert in chronological order
            inserted = False
            for i, existing_event in enumerate(self._queue):
                if event.timestamp <= existing_event.timestamp:
                    self._queue.insert(i, event)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(event)
    
    def get_next_event(self, current_time: datetime) -> Optional[BacktestEvent]:
        """Get next event at or before current time"""
        with self._lock:
            for i, event in enumerate(self._queue):
                if event.timestamp <= current_time and not event.processed:
                    event.processed = True
                    return event
            return None
    
    def peek_next_event(self) -> Optional[BacktestEvent]:
        """Peek at next unprocessed event without removing it"""
        with self._lock:
            for event in self._queue:
                if not event.processed:
                    return event
            return None
    
    def clear(self):
        """Clear all events from queue"""
        with self._lock:
            self._queue.clear()


class HistoricalDataLoader:
    """Load and process historical ERP data for backtesting"""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.cached_data = {}
        
    def load_yarn_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load yarn inventory and demand data"""
        try:
            # Load expected yarn report
            yarn_files = list(self.data_path.glob("*Expected_Yarn_Report*.csv")) + \
                        list(self.data_path.glob("*Yarn_Demand*.csv"))
            
            dataframes = []
            for file_path in yarn_files:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                    if 'PO Date' in df.columns:
                        df['PO Date'] = pd.to_datetime(df['PO Date'], errors='coerce')
                        df = df[(df['PO Date'] >= start_date) & (df['PO Date'] <= end_date)]
                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
                    continue
            
            if dataframes:
                combined_df = pd.concat(dataframes, ignore_index=True)
                logger.info(f"Loaded {len(combined_df)} yarn records")
                return combined_df
            
            logger.warning("No yarn data found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading yarn data: {e}")
            return pd.DataFrame()
    
    def load_inventory_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load inventory data from various locations"""
        try:
            inventory_files = list(self.data_path.glob("*Inventory*.csv")) + \
                             list(self.data_path.glob("*Inventory*.xlsx"))
            
            dataframes = []
            for file_path in inventory_files:
                try:
                    if file_path.suffix == '.xlsx':
                        df = pd.read_excel(file_path)
                    else:
                        df = pd.read_csv(file_path)
                    
                    # Try to find date columns
                    date_columns = [col for col in df.columns if 'date' in col.lower()]
                    if date_columns:
                        df[date_columns[0]] = pd.to_datetime(df[date_columns[0]], errors='coerce')
                        df = df[(df[date_columns[0]] >= start_date) & (df[date_columns[0]] <= end_date)]
                    
                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load inventory file {file_path}: {e}")
                    continue
            
            if dataframes:
                combined_df = pd.concat(dataframes, ignore_index=True)
                logger.info(f"Loaded {len(combined_df)} inventory records")
                return combined_df
            
            logger.warning("No inventory data found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
            return pd.DataFrame()
    
    def load_sales_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load sales order and activity data"""
        try:
            sales_files = list(self.data_path.glob("*Sales*.xlsx")) + \
                         list(self.data_path.glob("*SO_List*.xlsx")) + \
                         list(self.data_path.glob("*SO_List*.csv"))
            
            dataframes = []
            for file_path in sales_files:
                try:
                    if file_path.suffix == '.xlsx':
                        df = pd.read_excel(file_path)
                    else:
                        df = pd.read_csv(file_path)
                    
                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load sales file {file_path}: {e}")
                    continue
            
            if dataframes:
                combined_df = pd.concat(dataframes, ignore_index=True)
                logger.info(f"Loaded {len(combined_df)} sales records")
                return combined_df
            
            logger.warning("No sales data found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading sales data: {e}")
            return pd.DataFrame()
    
    def prepare_historical_dataset(self, config: BacktestConfig) -> Dict[str, pd.DataFrame]:
        """Prepare complete historical dataset for backtesting"""
        logger.info(f"Loading historical data from {config.start_date} to {config.end_date}")
        
        dataset = {
            'yarn_data': self.load_yarn_data(config.start_date, config.end_date),
            'inventory_data': self.load_inventory_data(config.start_date, config.end_date),
            'sales_data': self.load_sales_data(config.start_date, config.end_date)
        }
        
        # Add synthetic data if needed
        if len(dataset['yarn_data']) == 0:
            logger.info("No historical yarn data found, generating synthetic data")
            dataset['yarn_data'] = self._generate_synthetic_yarn_data(config)
        
        return dataset
    
    def _generate_synthetic_yarn_data(self, config: BacktestConfig) -> pd.DataFrame:
        """Generate synthetic yarn data for testing when historical data is unavailable"""
        date_range = pd.date_range(config.start_date, config.end_date, freq='D')
        
        yarn_types = ['Polyester', 'Cotton', 'Nylon', 'Lycra', 'Modal']
        colors = ['Natural', 'Black', 'Blue', 'Red', 'Green', 'Grey']
        
        data = []
        for i, date in enumerate(date_range):
            for j in range(np.random.poisson(5)):  # Average 5 orders per day
                yarn_type = np.random.choice(yarn_types)
                color = np.random.choice(colors)
                
                record = {
                    'PO Date': date,
                    'PO #': f'Y{date.strftime("%y%m%d")}{j:03d}',
                    'Type': yarn_type,
                    'Color': color,
                    'Price': np.random.uniform(1.0, 10.0),
                    'INVEN': np.random.uniform(0, 10000),
                    'PO Order Amt': np.random.uniform(1000, 50000),
                    'Rec\'d': np.random.uniform(0, 30000),
                    'PO Bal': np.random.uniform(0, 25000)
                }
                data.append(record)
        
        return pd.DataFrame(data)


class BacktestEngine:
    """
    Main backtesting engine for textile ERP system.
    
    Provides event-driven backtesting with parallel strategy execution,
    comprehensive performance tracking, and statistical analysis.
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.config.validate()
        
        # Initialize components
        self.data_loader = HistoricalDataLoader(config.data_path)
        self.event_queue = EventQueue()
        self.strategies = {}
        self.results = {}
        
        # State management
        self.state = BacktestState.INITIALIZED
        self.current_time = config.start_date
        self.historical_data = {}
        
        # Performance tracking
        self.performance_metrics = {}
        self.execution_log = []
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        self._lock = threading.Lock()
        
        # Random seed for reproducibility
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
        
        logger.info(f"Initialized BacktestEngine with {len(config.strategies)} strategies")
    
    def register_strategy(self, name: str, strategy_class, **kwargs):
        """Register a strategy for backtesting"""
        try:
            strategy_params = self.config.strategy_params.get(name, {})
            strategy_params.update(kwargs)
            
            strategy = strategy_class(name=name, **strategy_params)
            self.strategies[name] = strategy
            logger.info(f"Registered strategy: {name}")
            
        except Exception as e:
            logger.error(f"Failed to register strategy {name}: {e}")
            raise
    
    def load_historical_data(self) -> bool:
        """Load and prepare historical data for backtesting"""
        try:
            self.state = BacktestState.LOADING_DATA
            logger.info("Loading historical data...")
            
            self.historical_data = self.data_loader.prepare_historical_dataset(self.config)
            
            # Generate events from historical data
            self._generate_events_from_data()
            
            logger.info(f"Data loading completed. Generated {len(self.event_queue._queue)} events")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            self.state = BacktestState.FAILED
            return False
    
    def _generate_events_from_data(self):
        """Generate backtesting events from historical data"""
        self.event_queue.clear()
        
        # Generate events from yarn data
        yarn_data = self.historical_data.get('yarn_data', pd.DataFrame())
        for _, row in yarn_data.iterrows():
            if pd.notna(row.get('PO Date')):
                event = BacktestEvent(
                    timestamp=row['PO Date'],
                    event_type='yarn_order',
                    data=row.to_dict()
                )
                self.event_queue.add_event(event)
        
        # Generate events from inventory data (if date columns exist)
        inventory_data = self.historical_data.get('inventory_data', pd.DataFrame())
        date_columns = [col for col in inventory_data.columns if 'date' in col.lower()]
        
        if date_columns:
            for _, row in inventory_data.iterrows():
                if pd.notna(row.get(date_columns[0])):
                    event = BacktestEvent(
                        timestamp=row[date_columns[0]],
                        event_type='inventory_update',
                        data=row.to_dict()
                    )
                    self.event_queue.add_event(event)
        
        logger.info(f"Generated {len(self.event_queue._queue)} events from historical data")
    
    async def run_backtest(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute the backtesting process with event-driven simulation.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary containing backtest results and performance metrics
        """
        try:
            self.state = BacktestState.RUNNING
            logger.info("Starting backtesting execution...")
            
            if not self.historical_data:
                if not self.load_historical_data():
                    raise RuntimeError("Failed to load historical data")
            
            # Initialize strategies
            for strategy in self.strategies.values():
                if hasattr(strategy, 'initialize'):
                    strategy.initialize(self.historical_data)
            
            total_days = (self.config.end_date - self.config.start_date).days
            current_day = 0
            
            # Main backtesting loop
            while self.current_time <= self.config.end_date and self.state == BacktestState.RUNNING:
                
                # Process events for current time
                await self._process_events_for_time(self.current_time)
                
                # Execute strategies
                if self.config.parallel_execution:
                    await self._execute_strategies_parallel()
                else:
                    await self._execute_strategies_sequential()
                
                # Update progress
                current_day += 1
                if progress_callback and current_day % 10 == 0:
                    progress = current_day / total_days
                    progress_callback(progress, self.current_time)
                
                # Advance time
                if self.config.simulation_frequency == 'daily':
                    self.current_time += timedelta(days=1)
                elif self.config.simulation_frequency == 'hourly':
                    self.current_time += timedelta(hours=1)
                elif self.config.simulation_frequency == 'weekly':
                    self.current_time += timedelta(weeks=1)
            
            # Finalize strategies and collect results
            self._finalize_backtest()
            
            self.state = BacktestState.COMPLETED
            logger.info("Backtesting completed successfully")
            
            return self.results
            
        except Exception as e:
            logger.error(f"Backtesting failed: {e}")
            self.state = BacktestState.FAILED
            raise
    
    async def _process_events_for_time(self, current_time: datetime):
        """Process all events scheduled for the current time"""
        while True:
            event = self.event_queue.get_next_event(current_time)
            if event is None:
                break
            
            # Distribute event to all strategies
            for strategy in self.strategies.values():
                if hasattr(strategy, 'process_event'):
                    try:
                        strategy.process_event(event)
                    except Exception as e:
                        logger.error(f"Strategy {strategy.name} failed to process event: {e}")
    
    async def _execute_strategies_parallel(self):
        """Execute all strategies in parallel for current time step"""
        tasks = []
        for strategy in self.strategies.values():
            if hasattr(strategy, 'execute_step'):
                task = asyncio.create_task(self._execute_strategy_step(strategy))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_strategies_sequential(self):
        """Execute all strategies sequentially for current time step"""
        for strategy in self.strategies.values():
            if hasattr(strategy, 'execute_step'):
                await self._execute_strategy_step(strategy)
    
    async def _execute_strategy_step(self, strategy):
        """Execute a single strategy step with error handling"""
        try:
            result = strategy.execute_step(self.current_time, self.historical_data)
            
            # Store strategy result
            if strategy.name not in self.results:
                self.results[strategy.name] = []
            
            self.results[strategy.name].append({
                'timestamp': self.current_time,
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Strategy {strategy.name} execution failed at {self.current_time}: {e}")
    
    def _finalize_backtest(self):
        """Finalize backtesting and collect comprehensive results"""
        logger.info("Finalizing backtest results...")
        
        # Finalize strategies
        for strategy in self.strategies.values():
            if hasattr(strategy, 'finalize'):
                try:
                    final_result = strategy.finalize()
                    self.results[f"{strategy.name}_final"] = final_result
                except Exception as e:
                    logger.error(f"Failed to finalize strategy {strategy.name}: {e}")
        
        # Calculate performance metrics
        self.performance_metrics = self._calculate_performance_metrics()
        self.results['performance_metrics'] = self.performance_metrics
        
        # Add configuration and metadata
        self.results['config'] = {
            'start_date': self.config.start_date.isoformat(),
            'end_date': self.config.end_date.isoformat(),
            'strategies': list(self.strategies.keys()),
            'simulation_frequency': self.config.simulation_frequency,
            'random_seed': self.config.random_seed
        }
        
        self.results['metadata'] = {
            'execution_time': datetime.now().isoformat(),
            'total_events_processed': len([e for e in self.event_queue._queue if e.processed]),
            'data_records_processed': sum(len(df) for df in self.historical_data.values())
        }
        
        # Save results if configured
        if self.config.save_results:
            self._save_results()
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics for all strategies"""
        metrics = {}
        
        for strategy_name, strategy_results in self.results.items():
            if strategy_name.endswith('_final') or not isinstance(strategy_results, list):
                continue
            
            if not strategy_results:
                continue
            
            strategy_metrics = {}
            
            # Extract numerical results
            values = []
            for result in strategy_results:
                if isinstance(result.get('result'), (int, float)):
                    values.append(result['result'])
                elif isinstance(result.get('result'), dict):
                    # Extract numerical values from result dict
                    for key, value in result['result'].items():
                        if isinstance(value, (int, float)):
                            values.append(value)
            
            if values:
                values = np.array(values)
                
                # Basic statistics
                strategy_metrics['mean'] = float(np.mean(values))
                strategy_metrics['std'] = float(np.std(values))
                strategy_metrics['min'] = float(np.min(values))
                strategy_metrics['max'] = float(np.max(values))
                strategy_metrics['median'] = float(np.median(values))
                
                # Risk metrics
                if len(values) > 1:
                    returns = np.diff(values) / values[:-1]
                    strategy_metrics['volatility'] = float(np.std(returns))
                    strategy_metrics['sharpe_ratio'] = float(
                        (np.mean(returns) - self.config.risk_free_rate / 252) / np.std(returns)
                        if np.std(returns) > 0 else 0
                    )
                    
                    # Maximum drawdown
                    cumulative = np.cumprod(1 + returns)
                    running_max = np.maximum.accumulate(cumulative)
                    drawdown = (cumulative - running_max) / running_max
                    strategy_metrics['max_drawdown'] = float(np.min(drawdown))
            
            metrics[strategy_name] = strategy_metrics
        
        return metrics
    
    def _save_results(self):
        """Save backtest results to disk"""
        try:
            output_dir = Path(self.config.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save main results as JSON
            results_file = output_dir / f"backtest_results_{timestamp}.json"
            with open(results_file, 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                serializable_results = self._make_json_serializable(self.results)
                json.dump(serializable_results, f, indent=2, default=str)
            
            # Save detailed data as pickle
            pickle_file = output_dir / f"backtest_data_{timestamp}.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump({
                    'results': self.results,
                    'historical_data': self.historical_data,
                    'config': self.config
                }, f)
            
            logger.info(f"Results saved to {results_file} and {pickle_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _make_json_serializable(self, obj):
        """Convert object to JSON serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        else:
            return obj
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        """Get performance metrics for a specific strategy"""
        return self.performance_metrics.get(strategy_name, {})
    
    def compare_strategies(self) -> pd.DataFrame:
        """Compare performance metrics across all strategies"""
        comparison_data = []
        
        for strategy_name, metrics in self.performance_metrics.items():
            if metrics:
                row = {'Strategy': strategy_name}
                row.update(metrics)
                comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)
    
    def run_monte_carlo(self, num_runs: int = None) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation with multiple random seeds.
        
        Args:
            num_runs: Number of Monte Carlo runs (defaults to config value)
            
        Returns:
            Aggregated results from multiple runs
        """
        num_runs = num_runs or self.config.monte_carlo_runs
        if num_runs <= 1:
            logger.warning("Monte Carlo runs set to 1 or less, running single backtest")
            return asyncio.run(self.run_backtest())
        
        logger.info(f"Starting Monte Carlo simulation with {num_runs} runs")
        
        monte_carlo_results = []
        original_seed = self.config.random_seed
        
        for run_i in range(num_runs):
            logger.info(f"Monte Carlo run {run_i + 1}/{num_runs}")
            
            # Set different random seed for each run
            if original_seed is not None:
                self.config.random_seed = original_seed + run_i
                np.random.seed(self.config.random_seed)
            
            # Reset engine state
            self.state = BacktestState.INITIALIZED
            self.current_time = self.config.start_date
            self.results = {}
            self.performance_metrics = {}
            
            # Run backtest
            try:
                results = asyncio.run(self.run_backtest())
                monte_carlo_results.append(results)
            except Exception as e:
                logger.error(f"Monte Carlo run {run_i + 1} failed: {e}")
                continue
        
        # Restore original seed
        self.config.random_seed = original_seed
        
        # Aggregate results
        aggregated_results = self._aggregate_monte_carlo_results(monte_carlo_results)
        
        logger.info("Monte Carlo simulation completed")
        return aggregated_results
    
    def _aggregate_monte_carlo_results(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple Monte Carlo runs"""
        if not results_list:
            return {}
        
        aggregated = {
            'monte_carlo_summary': {
                'num_runs': len(results_list),
                'successful_runs': len(results_list)
            },
            'strategy_statistics': {},
            'confidence_intervals': {}
        }
        
        # Collect strategy performance across runs
        strategy_performances = {}
        
        for result in results_list:
            perf_metrics = result.get('performance_metrics', {})
            for strategy_name, metrics in perf_metrics.items():
                if strategy_name not in strategy_performances:
                    strategy_performances[strategy_name] = {}
                
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        if metric_name not in strategy_performances[strategy_name]:
                            strategy_performances[strategy_name][metric_name] = []
                        strategy_performances[strategy_name][metric_name].append(value)
        
        # Calculate statistics for each strategy and metric
        for strategy_name, metrics_data in strategy_performances.items():
            strategy_stats = {}
            strategy_ci = {}
            
            for metric_name, values in metrics_data.items():
                if values:
                    values = np.array(values)
                    strategy_stats[metric_name] = {
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'min': float(np.min(values)),
                        'max': float(np.max(values)),
                        'median': float(np.median(values))
                    }
                    
                    # Calculate confidence intervals
                    confidence_intervals = {}
                    for confidence_level in self.config.confidence_levels:
                        alpha = 1 - confidence_level
                        lower_percentile = (alpha / 2) * 100
                        upper_percentile = (1 - alpha / 2) * 100
                        
                        confidence_intervals[f'{confidence_level:.0%}'] = {
                            'lower': float(np.percentile(values, lower_percentile)),
                            'upper': float(np.percentile(values, upper_percentile))
                        }
                    
                    strategy_ci[metric_name] = confidence_intervals
            
            aggregated['strategy_statistics'][strategy_name] = strategy_stats
            aggregated['confidence_intervals'][strategy_name] = strategy_ci
        
        return aggregated
    
    def pause_backtest(self):
        """Pause the running backtest"""
        if self.state == BacktestState.RUNNING:
            self.state = BacktestState.PAUSED
            logger.info("Backtest paused")
    
    def resume_backtest(self):
        """Resume a paused backtest"""
        if self.state == BacktestState.PAUSED:
            self.state = BacktestState.RUNNING
            logger.info("Backtest resumed")
    
    def stop_backtest(self):
        """Stop the backtest execution"""
        self.state = BacktestState.FAILED
        logger.info("Backtest stopped by user")
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        logger.info("BacktestEngine cleanup completed")


# Base strategy class for implementing custom strategies
class BaseStrategy(ABC):
    """Abstract base class for backtesting strategies"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.parameters = kwargs
        self.state = {}
        self.performance_history = []
    
    @abstractmethod
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize strategy with historical data"""
        pass
    
    @abstractmethod
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Any:
        """Execute strategy for current time step"""
        pass
    
    def process_event(self, event: BacktestEvent):
        """Process a backtesting event (optional override)"""
        pass
    
    def finalize(self) -> Any:
        """Finalize strategy and return final results (optional override)"""
        return {
            'final_state': self.state,
            'performance_history': self.performance_history
        }