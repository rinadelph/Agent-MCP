"""
Memory Manager for Super Complex Calculator

This module provides comprehensive memory management functionality including
memory slots for storing values, memory operations (M+, M-, MR, MC, MS),
and persistent memory state management.
"""

from typing import Dict, Union, Optional, List, Tuple, Any
import json
import os
try:
    from .calculator import CalculatorError, InvalidInputError
except ImportError:
    from calculator import CalculatorError, InvalidInputError


class MemoryError(CalculatorError):
    """Raised when memory operations fail."""
    pass


class MemoryManager:
    """
    Advanced memory manager supporting multiple memory slots and operations.
    
    Features:
    - Multiple named memory slots (M1, M2, M3, etc.)
    - Standard memory operations: MS (Store), MR (Recall), M+ (Add), M- (Subtract), MC (Clear)
    - Persistent memory state (can be saved to/loaded from file)
    - Memory history and statistics
    """
    
    def __init__(self, max_slots: int = 10):
        """
        Initialize the memory manager.
        
        Args:
            max_slots: Maximum number of memory slots available
        """
        self.max_slots = max_slots
        self.memory_slots: Dict[str, Union[int, float]] = {}
        self.last_recalled: Optional[Union[int, float]] = None
        self.memory_history: List[Dict[str, Any]] = []
        self._active_slot = "M1"  # Default active memory slot
    
    def _validate_slot_name(self, slot_name: str) -> str:
        """
        Validate and normalize memory slot name.
        
        Args:
            slot_name: Name of the memory slot
            
        Returns:
            Normalized slot name
            
        Raises:
            MemoryError: If slot name is invalid
        """
        if not isinstance(slot_name, str):
            raise MemoryError("Memory slot name must be a string")
        
        # Normalize slot name (convert to uppercase, add M prefix if missing)
        slot_name = slot_name.upper().strip()
        
        if not slot_name:
            raise MemoryError("Memory slot name cannot be empty")
        
        # Add M prefix if not present
        if not slot_name.startswith('M'):
            if slot_name.isdigit():
                slot_name = f"M{slot_name}"
            else:
                raise MemoryError(f"Invalid memory slot name: {slot_name}")
        
        # Validate format (M followed by number or letter)
        if len(slot_name) < 2 or not (slot_name[1:].isalnum()):
            raise MemoryError(f"Invalid memory slot name format: {slot_name}")
        
        return slot_name
    
    def _add_to_history(self, operation: str, slot_name: str, 
                       value: Optional[Union[int, float]] = None,
                       old_value: Optional[Union[int, float]] = None) -> None:
        """Add an operation to the memory history."""
        history_entry = {
            'operation': operation,
            'slot': slot_name,
            'value': value,
            'old_value': old_value,
            'timestamp': self._get_timestamp()
        }
        self.memory_history.append(history_entry)
        
        # Keep history limited to prevent memory bloat
        if len(self.memory_history) > 1000:
            self.memory_history = self.memory_history[-500:]  # Keep last 500 entries
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def set_active_slot(self, slot_name: str) -> None:
        """
        Set the active memory slot for operations that don't specify a slot.
        
        Args:
            slot_name: Name of the memory slot to set as active
        """
        normalized_name = self._validate_slot_name(slot_name)
        self._active_slot = normalized_name
    
    def get_active_slot(self) -> str:
        """Get the currently active memory slot name."""
        return self._active_slot
    
    def store(self, value: Union[int, float], slot_name: Optional[str] = None) -> None:
        """
        Store a value in the specified memory slot (MS operation).
        
        Args:
            value: Value to store
            slot_name: Memory slot name (uses active slot if None)
            
        Raises:
            MemoryError: If operation fails
        """
        if not isinstance(value, (int, float)):
            raise MemoryError(f"Cannot store non-numeric value: {type(value)}")
        
        if slot_name is None:
            slot_name = self._active_slot
        else:
            slot_name = self._validate_slot_name(slot_name)
        
        old_value = self.memory_slots.get(slot_name)
        self.memory_slots[slot_name] = value
        self._add_to_history('MS', slot_name, value, old_value)
    
    def recall(self, slot_name: Optional[str] = None) -> Union[int, float]:
        """
        Recall a value from the specified memory slot (MR operation).
        
        Args:
            slot_name: Memory slot name (uses active slot if None)
            
        Returns:
            The value stored in the memory slot
            
        Raises:
            MemoryError: If slot is empty or doesn't exist
        """
        if slot_name is None:
            slot_name = self._active_slot
        else:
            slot_name = self._validate_slot_name(slot_name)
        
        if slot_name not in self.memory_slots:
            raise MemoryError(f"Memory slot {slot_name} is empty")
        
        value = self.memory_slots[slot_name]
        self.last_recalled = value
        self._add_to_history('MR', slot_name, value)
        
        return value
    
    def add(self, value: Union[int, float], slot_name: Optional[str] = None) -> Union[int, float]:
        """
        Add a value to the specified memory slot (M+ operation).
        
        Args:
            value: Value to add
            slot_name: Memory slot name (uses active slot if None)
            
        Returns:
            The new value in the memory slot
        """
        if not isinstance(value, (int, float)):
            raise MemoryError(f"Cannot add non-numeric value: {type(value)}")
        
        if slot_name is None:
            slot_name = self._active_slot
        else:
            slot_name = self._validate_slot_name(slot_name)
        
        old_value = self.memory_slots.get(slot_name, 0)
        new_value = old_value + value
        self.memory_slots[slot_name] = new_value
        self._add_to_history('M+', slot_name, value, old_value)
        
        return new_value
    
    def subtract(self, value: Union[int, float], slot_name: Optional[str] = None) -> Union[int, float]:
        """
        Subtract a value from the specified memory slot (M- operation).
        
        Args:
            value: Value to subtract
            slot_name: Memory slot name (uses active slot if None)
            
        Returns:
            The new value in the memory slot
        """
        if not isinstance(value, (int, float)):
            raise MemoryError(f"Cannot subtract non-numeric value: {type(value)}")
        
        if slot_name is None:
            slot_name = self._active_slot
        else:
            slot_name = self._validate_slot_name(slot_name)
        
        old_value = self.memory_slots.get(slot_name, 0)
        new_value = old_value - value
        self.memory_slots[slot_name] = new_value
        self._add_to_history('M-', slot_name, value, old_value)
        
        return new_value
    
    def clear(self, slot_name: Optional[str] = None) -> None:
        """
        Clear the specified memory slot (MC operation).
        
        Args:
            slot_name: Memory slot name (uses active slot if None). 
                      Use 'ALL' to clear all slots.
        """
        if slot_name is None:
            slot_name = self._active_slot
        elif slot_name.upper() == 'ALL':
            self.clear_all()
            return
        else:
            slot_name = self._validate_slot_name(slot_name)
        
        old_value = self.memory_slots.get(slot_name)
        if slot_name in self.memory_slots:
            del self.memory_slots[slot_name]
            self._add_to_history('MC', slot_name, None, old_value)
    
    def clear_all(self) -> None:
        """Clear all memory slots."""
        old_slots = self.memory_slots.copy()
        self.memory_slots.clear()
        self._add_to_history('MC_ALL', 'ALL', None, len(old_slots))
    
    def list_slots(self) -> Dict[str, Union[int, float]]:
        """
        Get a copy of all memory slots and their values.
        
        Returns:
            Dictionary mapping slot names to values
        """
        return self.memory_slots.copy()
    
    def is_slot_empty(self, slot_name: str) -> bool:
        """
        Check if a memory slot is empty.
        
        Args:
            slot_name: Memory slot name
            
        Returns:
            True if slot is empty, False otherwise
        """
        try:
            normalized_name = self._validate_slot_name(slot_name)
            return normalized_name not in self.memory_slots
        except MemoryError:
            return True
    
    def get_slot_count(self) -> int:
        """Get the number of occupied memory slots."""
        return len(self.memory_slots)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get comprehensive memory information.
        
        Returns:
            Dictionary with memory statistics and information
        """
        return {
            'active_slot': self._active_slot,
            'occupied_slots': len(self.memory_slots),
            'max_slots': self.max_slots,
            'slots': self.memory_slots.copy(),
            'last_recalled': self.last_recalled,
            'history_count': len(self.memory_history)
        }
    
    def get_memory_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get memory operation history.
        
        Args:
            limit: Maximum number of history entries to return (all if None)
            
        Returns:
            List of history entries (most recent first)
        """
        history = list(reversed(self.memory_history))  # Most recent first
        if limit is not None:
            history = history[:limit]
        return history
    
    def save_to_file(self, filename: str) -> None:
        """
        Save memory state to a JSON file.
        
        Args:
            filename: Path to the file to save to
            
        Raises:
            MemoryError: If save operation fails
        """
        try:
            data = {
                'memory_slots': self.memory_slots,
                'active_slot': self._active_slot,
                'last_recalled': self.last_recalled,
                'memory_history': self.memory_history[-100:],  # Save last 100 history entries
                'version': '1.0'
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
        except (IOError, OSError, json.JSONEncodeError) as e:
            raise MemoryError(f"Failed to save memory to file: {e}")
    
    def load_from_file(self, filename: str) -> None:
        """
        Load memory state from a JSON file.
        
        Args:
            filename: Path to the file to load from
            
        Raises:
            MemoryError: If load operation fails
        """
        if not os.path.exists(filename):
            raise MemoryError(f"Memory file not found: {filename}")
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Validate and load data
            if not isinstance(data, dict):
                raise MemoryError("Invalid memory file format")
            
            self.memory_slots = data.get('memory_slots', {})
            self._active_slot = data.get('active_slot', 'M1')
            self.last_recalled = data.get('last_recalled')
            self.memory_history = data.get('memory_history', [])
            
            # Validate loaded data
            for slot_name, value in self.memory_slots.items():
                if not isinstance(value, (int, float)):
                    raise MemoryError(f"Invalid value in slot {slot_name}: {type(value)}")
                    
        except (IOError, OSError, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to load memory from file: {e}")
    
    def export_slots_to_dict(self) -> Dict[str, Union[int, float]]:
        """Export memory slots for use with expression parser variables."""
        return {slot.lower(): value for slot, value in self.memory_slots.items()}
    
    def __str__(self) -> str:
        """String representation of memory manager state."""
        if not self.memory_slots:
            return "Memory: All slots empty"
        
        slot_list = []
        for slot, value in sorted(self.memory_slots.items()):
            active_indicator = " (active)" if slot == self._active_slot else ""
            slot_list.append(f"{slot}: {value}{active_indicator}")
        
        return "Memory: " + ", ".join(slot_list)
    
    def __repr__(self) -> str:
        """Detailed representation of memory manager."""
        return f"MemoryManager(slots={len(self.memory_slots)}, active={self._active_slot})"


if __name__ == "__main__":
    # Test the memory manager
    memory = MemoryManager()
    
    print("Memory Manager Test:")
    print(f"Initial state: {memory}")
    
    # Test basic operations
    memory.store(42.5, "M1")
    memory.store(10, "M2")
    print(f"After storing values: {memory}")
    
    # Test memory operations
    memory.add(7.5, "M1")
    print(f"After M1 + 7.5: {memory}")
    
    memory.subtract(2, "M2")
    print(f"After M2 - 2: {memory}")
    
    # Test recall
    value = memory.recall("M1")
    print(f"Recalled from M1: {value}")
    
    # Test memory info
    info = memory.get_memory_info()
    print(f"Memory info: {info}")