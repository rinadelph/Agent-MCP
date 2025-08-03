"""
History Manager for Super Complex Calculator

This module provides comprehensive calculation history management including
storing calculation history, displaying previous calculations, reusing results,
and exporting/importing history data.
"""

import json
import os
import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
try:
    from .calculator import CalculatorError, InvalidInputError
except ImportError:
    from calculator import CalculatorError, InvalidInputError


class HistoryError(CalculatorError):
    """Raised when history operations fail."""
    pass


class CalculationEntry:
    """Represents a single calculation in the history."""
    
    def __init__(self, expression: str, result: Union[int, float], 
                 timestamp: Optional[str] = None, variables: Optional[Dict[str, Any]] = None):
        """
        Initialize a calculation entry.
        
        Args:
            expression: The original expression that was calculated
            result: The calculated result
            timestamp: ISO format timestamp (current time if None)
            variables: Variables used in the calculation
        """
        self.expression = expression
        self.result = result
        self.timestamp = timestamp or datetime.datetime.now().isoformat()
        self.variables = variables or {}
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate a unique ID for this calculation entry."""
        # Use timestamp and expression hash for ID
        import hashlib
        hash_obj = hashlib.md5(f"{self.timestamp}{self.expression}".encode())
        return hash_obj.hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'expression': self.expression,
            'result': self.result,
            'timestamp': self.timestamp,
            'variables': self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalculationEntry':
        """Create CalculationEntry from dictionary."""
        entry = cls(
            expression=data['expression'],
            result=data['result'],
            timestamp=data.get('timestamp'),
            variables=data.get('variables', {})
        )
        entry.id = data.get('id', entry.id)
        return entry
    
    def __str__(self) -> str:
        """String representation of the calculation entry."""
        return f"{self.expression} = {self.result}"
    
    def __repr__(self) -> str:
        """Detailed representation of the calculation entry."""
        return f"CalculationEntry(id={self.id}, expr='{self.expression}', result={self.result})"


class HistoryManager:
    """
    Advanced calculation history manager.
    
    Features:
    - Store unlimited calculation history
    - Display history with formatting options
    - Reuse previous results by ID or index
    - Search history by expression or result
    - Export/import history to/from files
    - Statistics and analysis of calculation patterns
    - Automatic cleanup of old entries (configurable)
    """
    
    def __init__(self, max_entries: int = 1000, auto_save: bool = False):
        """
        Initialize the history manager.
        
        Args:
            max_entries: Maximum number of history entries to keep
            auto_save: Whether to automatically save history to file
        """
        self.max_entries = max_entries
        self.auto_save = auto_save
        self.history: List[CalculationEntry] = []
        self.auto_save_file = "calculator_history.json"
        self._last_result_used = None
    
    def add_calculation(self, expression: str, result: Union[int, float], 
                       variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a calculation to the history.
        
        Args:
            expression: The expression that was calculated
            result: The calculated result
            variables: Variables used in the calculation
            
        Returns:
            The ID of the added calculation entry
        """
        if not isinstance(expression, str) or not expression.strip():
            raise HistoryError("Expression cannot be empty")
        
        if not isinstance(result, (int, float)):
            raise HistoryError(f"Result must be numeric, got {type(result)}")
        
        entry = CalculationEntry(expression.strip(), result, variables=variables)
        self.history.append(entry)
        
        # Maintain max entries limit
        if len(self.history) > self.max_entries:
            self.history = self.history[-self.max_entries:]
        
        # Auto-save if enabled
        if self.auto_save:
            try:
                self.save_to_file(self.auto_save_file)
            except HistoryError:
                pass  # Silent fail for auto-save
        
        return entry.id
    
    def get_last_result(self) -> Optional[Union[int, float]]:
        """Get the result of the most recent calculation."""
        if not self.history:
            return None
        return self.history[-1].result
    
    def get_result_by_id(self, entry_id: str) -> Union[int, float]:
        """
        Get a result by its entry ID.
        
        Args:
            entry_id: The ID of the calculation entry
            
        Returns:
            The result of the calculation
            
        Raises:
            HistoryError: If entry ID is not found
        """
        for entry in self.history:
            if entry.id == entry_id:
                self._last_result_used = entry.result
                return entry.result
        
        raise HistoryError(f"Calculation with ID '{entry_id}' not found")
    
    def get_result_by_index(self, index: int) -> Union[int, float]:
        """
        Get a result by its position in history (0 = most recent, -1 = oldest).
        
        Args:
            index: Index of the calculation (0-based from most recent)
            
        Returns:
            The result of the calculation
            
        Raises:
            HistoryError: If index is out of range
        """
        if not self.history:
            raise HistoryError("No calculations in history")
        
        try:
            # Convert to reverse index (0 = most recent)
            if index >= 0:
                actual_index = len(self.history) - 1 - index
            else:
                actual_index = -index - 1
            
            result = self.history[actual_index].result
            self._last_result_used = result
            return result
            
        except IndexError:
            raise HistoryError(f"History index {index} out of range (0 to {len(self.history)-1})")
    
    def get_entry_by_id(self, entry_id: str) -> CalculationEntry:
        """Get a complete calculation entry by its ID."""
        for entry in self.history:
            if entry.id == entry_id:
                return entry
        raise HistoryError(f"Calculation with ID '{entry_id}' not found")
    
    def get_entry_by_index(self, index: int) -> CalculationEntry:
        """Get a complete calculation entry by its index."""
        if not self.history:
            raise HistoryError("No calculations in history")
        
        try:
            if index >= 0:
                actual_index = len(self.history) - 1 - index
            else:
                actual_index = -index - 1
            return self.history[actual_index]
        except IndexError:
            raise HistoryError(f"History index {index} out of range")
    
    def search_by_expression(self, pattern: str, case_sensitive: bool = False) -> List[CalculationEntry]:
        """
        Search history by expression pattern.
        
        Args:
            pattern: Pattern to search for in expressions
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            List of matching calculation entries
        """
        if not case_sensitive:
            pattern = pattern.lower()
        
        matches = []
        for entry in self.history:
            expression = entry.expression if case_sensitive else entry.expression.lower()
            if pattern in expression:
                matches.append(entry)
        
        return matches
    
    def search_by_result(self, value: Union[int, float], tolerance: float = 1e-10) -> List[CalculationEntry]:
        """
        Search history by result value.
        
        Args:
            value: Result value to search for
            tolerance: Tolerance for floating point comparison
            
        Returns:
            List of matching calculation entries
        """
        matches = []
        for entry in self.history:
            if abs(entry.result - value) <= tolerance:
                matches.append(entry)
        
        return matches
    
    def get_history_display(self, limit: Optional[int] = None, 
                           reverse: bool = True, include_id: bool = False) -> List[str]:
        """
        Get formatted history for display.
        
        Args:
            limit: Maximum number of entries to display (all if None)
            reverse: Show most recent first if True
            include_id: Include calculation IDs in display
            
        Returns:
            List of formatted history strings
        """
        if not self.history:
            return ["No calculations in history"]
        
        entries = list(self.history)
        if reverse:
            entries.reverse()
        
        if limit:
            entries = entries[:limit]
        
        formatted = []
        for i, entry in enumerate(entries):
            if reverse:
                index = i
            else:
                index = len(self.history) - len(entries) + i
            
            if include_id:
                line = f"{index:3d}. {entry.expression} = {entry.result} (ID: {entry.id})"
            else:
                line = f"{index:3d}. {entry.expression} = {entry.result}"
            
            formatted.append(line)
        
        return formatted
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the calculation history.
        
        Returns:
            Dictionary with various statistics
        """
        if not self.history:
            return {
                'total_calculations': 0,
                'date_range': None,
                'most_common_operations': [],
                'average_result': None,
                'result_range': None
            }
        
        # Basic stats
        total = len(self.history)
        results = [entry.result for entry in self.history]
        
        # Date range
        timestamps = [entry.timestamp for entry in self.history]
        date_range = (min(timestamps), max(timestamps))
        
        # Operation analysis
        operation_count = {}
        for entry in self.history:
            # Simple operation detection
            expr = entry.expression.lower()
            if '+' in expr and '*' not in expr and '/' not in expr:
                op = 'addition'
            elif '-' in expr and '*' not in expr and '/' not in expr:
                op = 'subtraction'
            elif '*' in expr:
                op = 'multiplication'
            elif '/' in expr:
                op = 'division'
            elif 'sin' in expr or 'cos' in expr or 'tan' in expr:
                op = 'trigonometry'
            elif 'log' in expr or 'exp' in expr:
                op = 'logarithmic'
            elif 'sqrt' in expr or '^' in expr or '**' in expr:
                op = 'power/root'
            else:
                op = 'other'
            
            operation_count[op] = operation_count.get(op, 0) + 1
        
        # Sort operations by frequency
        most_common = sorted(operation_count.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_calculations': total,
            'date_range': date_range,
            'most_common_operations': most_common,
            'average_result': sum(results) / len(results),
            'result_range': (min(results), max(results)),
            'unique_expressions': len(set(entry.expression for entry in self.history))
        }
    
    def clear_history(self) -> int:
        """
        Clear all calculation history.
        
        Returns:
            Number of entries that were cleared
        """
        count = len(self.history)
        self.history.clear()
        self._last_result_used = None
        return count
    
    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove a specific entry from history.
        
        Args:
            entry_id: ID of the entry to remove
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        for i, entry in enumerate(self.history):
            if entry.id == entry_id:
                del self.history[i]
                return True
        return False
    
    def save_to_file(self, filename: str) -> None:
        """
        Save history to a JSON file.
        
        Args:
            filename: Path to save the history
            
        Raises:
            HistoryError: If save operation fails
        """
        try:
            data = {
                'version': '1.0',
                'saved_at': datetime.datetime.now().isoformat(),
                'max_entries': self.max_entries,
                'history': [entry.to_dict() for entry in self.history]
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
        except (IOError, OSError, json.JSONEncodeError) as e:
            raise HistoryError(f"Failed to save history to file: {e}")
    
    def load_from_file(self, filename: str, merge: bool = False) -> int:
        """
        Load history from a JSON file.
        
        Args:
            filename: Path to load the history from
            merge: If True, merge with existing history; if False, replace
            
        Returns:
            Number of entries loaded
            
        Raises:
            HistoryError: If load operation fails
        """
        if not os.path.exists(filename):
            raise HistoryError(f"History file not found: {filename}")
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'history' not in data:
                raise HistoryError("Invalid history file format")
            
            loaded_entries = []
            for entry_data in data['history']:
                try:
                    entry = CalculationEntry.from_dict(entry_data)
                    loaded_entries.append(entry)
                except Exception as e:
                    # Skip invalid entries but continue loading
                    continue
            
            if not merge:
                self.history = loaded_entries
            else:
                self.history.extend(loaded_entries)
                # Maintain max entries limit
                if len(self.history) > self.max_entries:
                    self.history = self.history[-self.max_entries:]
            
            return len(loaded_entries)
            
        except (IOError, OSError, json.JSONDecodeError) as e:
            raise HistoryError(f"Failed to load history from file: {e}")
    
    def export_to_text(self, filename: str, include_metadata: bool = True) -> None:
        """
        Export history to a human-readable text file.
        
        Args:
            filename: Path to save the text file
            include_metadata: Whether to include metadata in export
        """
        try:
            with open(filename, 'w') as f:
                if include_metadata:
                    f.write("Calculator History Export\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Exported: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total calculations: {len(self.history)}\n")
                    f.write("\n")
                
                for i, entry in enumerate(reversed(self.history)):
                    timestamp = datetime.datetime.fromisoformat(entry.timestamp)
                    f.write(f"{i+1:4d}. {entry.expression} = {entry.result}\n")
                    if include_metadata:
                        f.write(f"      Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        if entry.variables:
                            f.write(f"      Variables: {entry.variables}\n")
                        f.write("\n")
                
        except (IOError, OSError) as e:
            raise HistoryError(f"Failed to export history to text file: {e}")
    
    def __len__(self) -> int:
        """Get the number of entries in history."""
        return len(self.history)
    
    def __str__(self) -> str:
        """String representation of history manager."""
        return f"History: {len(self.history)} calculations"
    
    def __repr__(self) -> str:
        """Detailed representation of history manager."""
        return f"HistoryManager(entries={len(self.history)}, max={self.max_entries})"


if __name__ == "__main__":
    # Test the history manager
    history = HistoryManager()
    
    print("History Manager Test:")
    print(f"Initial state: {history}")
    
    # Add some calculations
    history.add_calculation("2 + 3", 5)
    history.add_calculation("sin(pi/2)", 1.0, {"pi": 3.14159})
    history.add_calculation("sqrt(16)", 4.0)
    
    print(f"After adding calculations: {history}")
    
    # Display history
    display = history.get_history_display(include_id=True)
    print("\nHistory Display:")
    for line in display:
        print(line)
    
    # Test search
    matches = history.search_by_expression("sin")
    print(f"\nSearch for 'sin': {len(matches)} matches")
    for match in matches:
        print(f"  {match}")
    
    # Get statistics
    stats = history.get_statistics()
    print(f"\nStatistics: {stats}")