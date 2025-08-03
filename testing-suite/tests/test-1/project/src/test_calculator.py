"""
Comprehensive Test Suite for Super Complex Calculator

This module contains extensive unit tests for all calculator functionality
including basic arithmetic, scientific functions, expression parsing,
memory management, history, and unit conversions.
"""

import unittest
import math
import json
import os
import tempfile
from typing import List, Any

# Import all calculator modules
try:
    from calculator import Calculator, CalculatorError, DivisionByZeroError, DomainError, InvalidInputError
    from expression_parser import ExpressionParser, ParseError
    from memory_manager import MemoryManager, MemoryError
    from history_manager import HistoryManager, HistoryError, CalculationEntry
    from unit_converter import UnitConverter, ConversionError
except ImportError:
    # Fallback for different import paths
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from calculator import Calculator, CalculatorError, DivisionByZeroError, DomainError, InvalidInputError
    from expression_parser import ExpressionParser, ParseError
    from memory_manager import MemoryManager, MemoryError
    from history_manager import HistoryManager, HistoryError, CalculationEntry
    from unit_converter import UnitConverter, ConversionError


class TestCalculator(unittest.TestCase):
    """Test cases for the core Calculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        # Addition
        self.assertEqual(self.calc.add(2, 3), 5)
        self.assertEqual(self.calc.add(-1, 1), 0)
        self.assertEqual(self.calc.add(0.1, 0.2), 0.30000000000000004)  # Floating point precision
        
        # Subtraction
        self.assertEqual(self.calc.subtract(5, 3), 2)
        self.assertEqual(self.calc.subtract(0, 5), -5)
        
        # Multiplication
        self.assertEqual(self.calc.multiply(3, 4), 12)
        self.assertEqual(self.calc.multiply(-2, 3), -6)
        self.assertEqual(self.calc.multiply(0, 100), 0)
        
        # Division
        self.assertEqual(self.calc.divide(10, 2), 5.0)
        self.assertEqual(self.calc.divide(7, 3), 7/3)
        
        # Division by zero
        with self.assertRaises(DivisionByZeroError):
            self.calc.divide(5, 0)
        
        # Modulo
        self.assertEqual(self.calc.modulo(10, 3), 1)
        self.assertEqual(self.calc.modulo(15, 5), 0)
        
        with self.assertRaises(DivisionByZeroError):
            self.calc.modulo(5, 0)
        
        # Power
        self.assertEqual(self.calc.power(2, 3), 8)
        self.assertEqual(self.calc.power(4, 0.5), 2.0)
        self.assertEqual(self.calc.power(2, -1), 0.5)
    
    def test_scientific_functions(self):
        """Test scientific functions."""
        # Trigonometric functions (in radians)
        self.assertAlmostEqual(self.calc.sin(0), 0, places=10)
        self.assertAlmostEqual(self.calc.sin(math.pi/2), 1, places=10)
        self.assertAlmostEqual(self.calc.cos(0), 1, places=10)
        self.assertAlmostEqual(self.calc.cos(math.pi), -1, places=10)
        self.assertAlmostEqual(self.calc.tan(0), 0, places=10)
        self.assertAlmostEqual(self.calc.tan(math.pi/4), 1, places=10)
        
        # Test degrees mode
        self.assertAlmostEqual(self.calc.sin(90, degrees=True), 1, places=10)
        self.assertAlmostEqual(self.calc.cos(180, degrees=True), -1, places=10)
        
        # Inverse trigonometric functions
        self.assertAlmostEqual(self.calc.asin(1), math.pi/2, places=10)
        self.assertAlmostEqual(self.calc.acos(0), math.pi/2, places=10)
        self.assertAlmostEqual(self.calc.atan(1), math.pi/4, places=10)
        
        # Domain errors
        with self.assertRaises(DomainError):
            self.calc.asin(2)  # Outside [-1, 1]
        with self.assertRaises(DomainError):
            self.calc.acos(-2)  # Outside [-1, 1]
        
        # Logarithmic functions
        self.assertAlmostEqual(self.calc.ln(math.e), 1, places=10)
        self.assertAlmostEqual(self.calc.log10(100), 2, places=10)
        self.assertAlmostEqual(self.calc.log(8, 2), 3, places=10)
        
        with self.assertRaises(DomainError):
            self.calc.ln(-1)  # Negative input
        with self.assertRaises(DomainError):
            self.calc.log(5, 1)  # Invalid base
        
        # Exponential and square root
        self.assertAlmostEqual(self.calc.exp(1), math.e, places=10)
        self.assertEqual(self.calc.sqrt(9), 3.0)
        self.assertEqual(self.calc.sqrt(2), math.sqrt(2))
        
        with self.assertRaises(DomainError):
            self.calc.sqrt(-1)  # Negative input
    
    def test_statistical_functions(self):
        """Test statistical functions."""
        data = [1, 2, 3, 4, 5]
        
        # Mean
        self.assertEqual(self.calc.mean(data), 3.0)
        
        # Median
        self.assertEqual(self.calc.median(data), 3)
        self.assertEqual(self.calc.median([1, 2, 3, 4]), 2.5)
        
        # Mode
        mode_data = [1, 2, 2, 3, 4]
        self.assertEqual(self.calc.mode(mode_data), 2)
        
        # Standard deviation and variance
        self.assertAlmostEqual(self.calc.standard_deviation(data), math.sqrt(2.5), places=10)
        self.assertAlmostEqual(self.calc.variance(data), 2.5, places=10)
        
        # Empty data errors
        with self.assertRaises(InvalidInputError):
            self.calc.mean([])
        with self.assertRaises(InvalidInputError):
            self.calc.median([])
    
    def test_advanced_math(self):
        """Test advanced mathematical functions."""
        # Factorial
        self.assertEqual(self.calc.factorial(0), 1)
        self.assertEqual(self.calc.factorial(5), 120)
        
        with self.assertRaises(DomainError):
            self.calc.factorial(-1)  # Negative input
        with self.assertRaises(InvalidInputError):
            self.calc.factorial(5.5)  # Non-integer input
        
        # Combinations and permutations
        self.assertEqual(self.calc.combinations(5, 2), 10)
        self.assertEqual(self.calc.combinations(4, 4), 1)
        self.assertEqual(self.calc.permutations(5, 2), 20)
        self.assertEqual(self.calc.permutations(4, 4), 24)
        
        with self.assertRaises(DomainError):
            self.calc.combinations(3, 5)  # k > n
        
        # GCD and LCM
        self.assertEqual(self.calc.gcd(12, 18), 6)
        self.assertEqual(self.calc.gcd(17, 13), 1)  # Coprime numbers
        self.assertEqual(self.calc.lcm(4, 6), 12)
        self.assertEqual(self.calc.lcm(7, 11), 77)  # Coprime numbers
    
    def test_constants(self):
        """Test mathematical constants."""
        self.assertAlmostEqual(self.calc.get_constant('pi'), math.pi, places=10)
        self.assertAlmostEqual(self.calc.get_constant('e'), math.e, places=10)
        self.assertAlmostEqual(self.calc.get_constant('tau'), math.tau, places=10)
        
        with self.assertRaises(InvalidInputError):
            self.calc.get_constant('unknown')
    
    def test_precision_and_formatting(self):
        """Test precision setting and result formatting."""
        self.calc.set_precision(2)
        
        # Test formatting
        self.assertEqual(self.calc.format_result(3.14159), "3.14")
        self.assertEqual(self.calc.format_result(5.0), "5")
        self.assertEqual(self.calc.format_result(123), "123")
        
        # Test invalid precision
        with self.assertRaises(InvalidInputError):
            self.calc.set_precision(-1)


class TestExpressionParser(unittest.TestCase):
    """Test cases for the ExpressionParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
        self.parser = ExpressionParser(self.calc)
    
    def test_basic_expressions(self):
        """Test basic expression parsing."""
        self.assertEqual(self.parser.parse("2 + 3"), 5)
        self.assertEqual(self.parser.parse("2 * 3 + 4"), 10)
        self.assertEqual(self.parser.parse("(2 + 3) * 4"), 20)
        self.assertEqual(self.parser.parse("2^3"), 8)
        self.assertEqual(self.parser.parse("10 / 2"), 5.0)
    
    def test_operator_precedence(self):
        """Test operator precedence."""
        self.assertEqual(self.parser.parse("2 + 3 * 4"), 14)  # Not 20
        self.assertEqual(self.parser.parse("2 * 3 + 4"), 10)  # Not 14
        self.assertEqual(self.parser.parse("2^3*2"), 16)  # 8*2, not 2^6
        self.assertEqual(self.parser.parse("2*3^2"), 18)  # 2*9, not 6^2
    
    def test_functions(self):
        """Test function calls in expressions."""
        self.assertAlmostEqual(self.parser.parse("sin(0)"), 0, places=10)
        self.assertAlmostEqual(self.parser.parse("cos(pi)"), -1, places=10)
        self.assertEqual(self.parser.parse("sqrt(9)"), 3.0)
        self.assertEqual(self.parser.parse("factorial(4)"), 24)
        self.assertAlmostEqual(self.parser.parse("log(e)"), 1, places=10)
    
    def test_constants(self):
        """Test constants in expressions."""
        self.assertAlmostEqual(self.parser.parse("pi"), math.pi, places=10)
        self.assertAlmostEqual(self.parser.parse("e"), math.e, places=10)
        self.assertAlmostEqual(self.parser.parse("2*pi"), 2*math.pi, places=10)
    
    def test_variables(self):
        """Test variable support."""
        self.parser.set_variable("x", 5)
        self.parser.set_variable("y", 3)
        
        self.assertEqual(self.parser.parse("x"), 5)
        self.assertEqual(self.parser.parse("x + y"), 8)
        self.assertEqual(self.parser.parse("x^2 + y^2"), 34)
        
        with self.assertRaises(ParseError):
            self.parser.parse("undefined_var")
    
    def test_implicit_multiplication(self):
        """Test implicit multiplication."""
        self.parser.set_variable("x", 2)
        
        self.assertAlmostEqual(self.parser.parse("2pi"), 2*math.pi, places=10)
        self.assertEqual(self.parser.parse("3x"), 6)
        self.assertEqual(self.parser.parse("2(3+4)"), 14)
        self.assertAlmostEqual(self.parser.parse("2sin(pi/2)"), 2, places=10)
    
    def test_unary_operators(self):
        """Test unary plus and minus."""
        self.assertEqual(self.parser.parse("-5"), -5)
        self.assertEqual(self.parser.parse("+5"), 5)
        self.assertEqual(self.parser.parse("-(2+3)"), -5)
        self.assertEqual(self.parser.parse("-sin(pi/2)"), -1)
    
    def test_complex_expressions(self):
        """Test complex nested expressions."""
        # Complex expression with multiple operations
        result = self.parser.parse("sin(pi/4)^2 + cos(pi/4)^2")
        self.assertAlmostEqual(result, 1, places=10)
        
        # Expression with variables and functions
        self.parser.set_variable("angle", math.pi/6)
        result = self.parser.parse("2*sin(angle)*cos(angle)")
        self.assertAlmostEqual(result, math.sin(math.pi/3), places=10)
    
    def test_error_handling(self):
        """Test error handling in expression parsing."""
        with self.assertRaises(ParseError):
            self.parser.parse("")  # Empty expression
        
        with self.assertRaises(ParseError):
            self.parser.parse("2 +")  # Incomplete expression
        
        with self.assertRaises(ParseError):
            self.parser.parse("2 + + 3")  # Invalid operators
        
        with self.assertRaises(ParseError):
            self.parser.parse("2 + 3)")  # Mismatched parentheses
        
        with self.assertRaises(ParseError):
            self.parser.parse("(2 + 3")  # Mismatched parentheses
        
        with self.assertRaises(ParseError):
            self.parser.parse("unknown_function(5)")  # Unknown function
    
    def test_expression_validation(self):
        """Test expression validation."""
        valid_expressions = [
            "2 + 3",
            "sin(pi/2)",
            "x^2 + y^2",
            "factorial(5)"
        ]
        
        invalid_expressions = [
            "",
            "2 +",
            "(2 + 3",
            "unknown_func(5)"
        ]
        
        for expr in valid_expressions:
            is_valid, error = self.parser.validate_expression(expr)
            self.assertTrue(is_valid, f"Expression should be valid: {expr}")
        
        for expr in invalid_expressions:
            is_valid, error = self.parser.validate_expression(expr)
            self.assertFalse(is_valid, f"Expression should be invalid: {expr}")


class TestMemoryManager(unittest.TestCase):
    """Test cases for the MemoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.memory = MemoryManager()
    
    def test_basic_memory_operations(self):
        """Test basic memory store and recall operations."""
        # Store values
        self.memory.store(42.5, "M1")
        self.memory.store(10, "M2")
        
        # Recall values
        self.assertEqual(self.memory.recall("M1"), 42.5)
        self.assertEqual(self.memory.recall("M2"), 10)
        
        # Test empty slot
        with self.assertRaises(MemoryError):
            self.memory.recall("M3")
    
    def test_memory_arithmetic(self):
        """Test memory arithmetic operations."""
        self.memory.store(10, "M1")
        
        # Add to memory
        result = self.memory.add(5, "M1")
        self.assertEqual(result, 15)
        self.assertEqual(self.memory.recall("M1"), 15)
        
        # Subtract from memory
        result = self.memory.subtract(3, "M1")
        self.assertEqual(result, 12)
        self.assertEqual(self.memory.recall("M1"), 12)
        
        # Add to empty slot (should initialize to 0)
        result = self.memory.add(7, "M2")
        self.assertEqual(result, 7)
        self.assertEqual(self.memory.recall("M2"), 7)
    
    def test_memory_clear(self):
        """Test memory clearing operations."""
        self.memory.store(100, "M1")
        self.memory.store(200, "M2")
        
        # Clear specific slot
        self.memory.clear("M1")
        self.assertTrue(self.memory.is_slot_empty("M1"))
        self.assertFalse(self.memory.is_slot_empty("M2"))
        
        # Clear all slots
        self.memory.clear("ALL")
        self.assertTrue(self.memory.is_slot_empty("M1"))
        self.assertTrue(self.memory.is_slot_empty("M2"))
        self.assertEqual(self.memory.get_slot_count(), 0)
    
    def test_slot_name_validation(self):
        """Test memory slot name validation and normalization."""
        # Test various slot name formats
        self.memory.store(1, "M1")
        self.memory.store(2, "m2")  # Lowercase
        self.memory.store(3, "M3")
        self.memory.store(4, "4")   # Number only (should become M4)
        
        # Test recall with different formats
        self.assertEqual(self.memory.recall("M1"), 1)
        self.assertEqual(self.memory.recall("m2"), 2)
        self.assertEqual(self.memory.recall("M2"), 2)  # Case insensitive
        self.assertEqual(self.memory.recall("M4"), 4)  # Number normalized to M4
        
        # Test invalid slot names
        with self.assertRaises(MemoryError):
            self.memory.store(1, "")  # Empty name
        
        with self.assertRaises(MemoryError):
            self.memory.store(1, "invalid_name")  # Invalid format
    
    def test_active_slot(self):
        """Test active slot functionality."""
        # Default active slot
        self.assertEqual(self.memory.get_active_slot(), "M1")
        
        # Set active slot
        self.memory.set_active_slot("M3")
        self.assertEqual(self.memory.get_active_slot(), "M3")
        
        # Store without specifying slot (should use active)
        self.memory.store(99)
        self.assertEqual(self.memory.recall("M3"), 99)
    
    def test_memory_info(self):
        """Test memory information retrieval."""
        self.memory.store(10, "M1")
        self.memory.store(20, "M2")
        
        info = self.memory.get_memory_info()
        self.assertEqual(info['occupied_slots'], 2)
        self.assertEqual(info['active_slot'], "M1")
        self.assertIn("M1", info['slots'])
        self.assertIn("M2", info['slots'])
        
        # Test history
        history = self.memory.get_memory_history(limit=5)
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]['operation'], 'MS')  # Most recent first
    
    def test_memory_persistence(self):
        """Test saving and loading memory state."""
        # Store some values
        self.memory.store(42, "M1")
        self.memory.store(84, "M2")
        self.memory.set_active_slot("M2")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            self.memory.save_to_file(temp_file)
            
            # Create new memory manager and load
            new_memory = MemoryManager()
            new_memory.load_from_file(temp_file)
            
            # Verify loaded state
            self.assertEqual(new_memory.recall("M1"), 42)
            self.assertEqual(new_memory.recall("M2"), 84)
            self.assertEqual(new_memory.get_active_slot(), "M2")
            
        finally:
            os.unlink(temp_file)


class TestHistoryManager(unittest.TestCase):
    """Test cases for the HistoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.history = HistoryManager()
    
    def test_basic_history_operations(self):
        """Test basic history add and retrieval."""
        # Add calculations
        id1 = self.history.add_calculation("2 + 3", 5)
        id2 = self.history.add_calculation("sin(pi/2)", 1.0, {"pi": 3.14159})
        
        # Test retrieval
        self.assertEqual(self.history.get_last_result(), 1.0)
        self.assertEqual(self.history.get_result_by_id(id1), 5)
        self.assertEqual(self.history.get_result_by_index(0), 1.0)  # Most recent
        self.assertEqual(self.history.get_result_by_index(1), 5)    # Second most recent
        
        # Test entry retrieval
        entry1 = self.history.get_entry_by_id(id1)
        self.assertEqual(entry1.expression, "2 + 3")
        self.assertEqual(entry1.result, 5)
    
    def test_history_search(self):
        """Test history search functionality."""
        # Add test data
        self.history.add_calculation("sin(x)", 0.5)
        self.history.add_calculation("cos(x)", 0.866)
        self.history.add_calculation("tan(x)", 0.577)
        self.history.add_calculation("2 + 3", 5)
        
        # Search by expression
        trig_results = self.history.search_by_expression("sin")
        self.assertEqual(len(trig_results), 1)
        self.assertEqual(trig_results[0].expression, "sin(x)")
        
        # Case insensitive search
        all_trig = self.history.search_by_expression("x", case_sensitive=False)
        self.assertEqual(len(all_trig), 3)
        
        # Search by result
        result_matches = self.history.search_by_result(5.0)
        self.assertEqual(len(result_matches), 1)
        self.assertEqual(result_matches[0].expression, "2 + 3")
    
    def test_history_display(self):
        """Test history display formatting."""
        self.history.add_calculation("1 + 1", 2)
        self.history.add_calculation("2 * 3", 6)
        self.history.add_calculation("sqrt(9)", 3)
        
        # Get display
        display = self.history.get_history_display(limit=2, include_id=True)
        self.assertEqual(len(display), 2)
        self.assertIn("sqrt(9) = 3", display[0])  # Most recent first
        self.assertIn("2 * 3 = 6", display[1])
    
    def test_history_statistics(self):
        """Test history statistics."""
        # Add diverse calculations
        calculations = [
            ("2 + 3", 5),
            ("4 - 1", 3),
            ("2 * 6", 12),
            ("10 / 2", 5),
            ("sin(pi)", 0),
            ("log(e)", 1)
        ]
        
        for expr, result in calculations:
            self.history.add_calculation(expr, result)
        
        stats = self.history.get_statistics()
        self.assertEqual(stats['total_calculations'], 6)
        self.assertIsNotNone(stats['average_result'])
        self.assertIsNotNone(stats['most_common_operations'])
        self.assertEqual(stats['unique_expressions'], 6)
    
    def test_history_limits(self):
        """Test history size limits."""
        # Create history manager with small limit
        small_history = HistoryManager(max_entries=3)
        
        # Add more entries than the limit
        for i in range(5):
            small_history.add_calculation(f"calculation_{i}", i)
        
        # Should only keep the last 3
        self.assertEqual(len(small_history), 3)
        self.assertEqual(small_history.get_result_by_index(0), 4)  # Most recent
        self.assertEqual(small_history.get_result_by_index(2), 2)  # Oldest kept
    
    def test_history_persistence(self):
        """Test saving and loading history."""
        # Add some history
        self.history.add_calculation("test_expr_1", 10)
        self.history.add_calculation("test_expr_2", 20)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            self.history.save_to_file(temp_file)
            
            # Create new history and load
            new_history = HistoryManager()
            count = new_history.load_from_file(temp_file)
            
            self.assertEqual(count, 2)
            self.assertEqual(new_history.get_last_result(), 20)
            
            # Test search after loading
            matches = new_history.search_by_expression("test_expr_1")
            self.assertEqual(len(matches), 1)
            
        finally:
            os.unlink(temp_file)
    
    def test_history_export(self):
        """Test history export to text."""
        self.history.add_calculation("export_test", 42)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            self.history.export_to_text(temp_file)
            
            # Read and verify export
            with open(temp_file, 'r') as f:
                content = f.read()
            
            self.assertIn("export_test", content)
            self.assertIn("42", content)
            
        finally:
            os.unlink(temp_file)


class TestUnitConverter(unittest.TestCase):
    """Test cases for the UnitConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = UnitConverter()
    
    def test_length_conversions(self):
        """Test length unit conversions."""
        # Metric conversions
        self.assertAlmostEqual(self.converter.convert(1000, "mm", "m"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(100, "cm", "m"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "km", "m"), 1000.0, places=6)
        
        # Imperial conversions
        self.assertAlmostEqual(self.converter.convert(12, "inches", "feet"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(3, "feet", "yards"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(5280, "feet", "miles"), 1.0, places=6)
        
        # Mixed conversions
        self.assertAlmostEqual(self.converter.convert(1, "inch", "cm"), 2.54, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "mile", "km"), 1.609344, places=6)
    
    def test_weight_conversions(self):
        """Test weight/mass unit conversions."""
        # Metric conversions
        self.assertAlmostEqual(self.converter.convert(1000, "mg", "g"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1000, "g", "kg"), 1.0, places=6)
        
        # Imperial conversions
        self.assertAlmostEqual(self.converter.convert(16, "oz", "lb"), 1.0, places=6)
        
        # Mixed conversions
        self.assertAlmostEqual(self.converter.convert(1, "kg", "lb"), 2.20462, places=3)
        self.assertAlmostEqual(self.converter.convert(1, "lb", "oz"), 16.0, places=6)
    
    def test_temperature_conversions(self):
        """Test temperature unit conversions."""
        # Celsius to Fahrenheit
        self.assertAlmostEqual(self.converter.convert(0, "c", "f"), 32.0, places=6)
        self.assertAlmostEqual(self.converter.convert(100, "celsius", "fahrenheit"), 212.0, places=6)
        
        # Celsius to Kelvin
        self.assertAlmostEqual(self.converter.convert(0, "c", "k"), 273.15, places=6)
        self.assertAlmostEqual(self.converter.convert(100, "celsius", "kelvin"), 373.15, places=6)
        
        # Fahrenheit to Celsius
        self.assertAlmostEqual(self.converter.convert(32, "f", "c"), 0.0, places=6)
        self.assertAlmostEqual(self.converter.convert(212, "fahrenheit", "celsius"), 100.0, places=6)
        
        # Kelvin to Celsius
        self.assertAlmostEqual(self.converter.convert(273.15, "k", "c"), 0.0, places=6)
        self.assertAlmostEqual(self.converter.convert(373.15, "kelvin", "celsius"), 100.0, places=6)
    
    def test_time_conversions(self):
        """Test time unit conversions."""
        # Basic time conversions
        self.assertAlmostEqual(self.converter.convert(60, "s", "min"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(60, "min", "h"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(24, "h", "d"), 1.0, places=6)
        
        # Complex conversions
        self.assertAlmostEqual(self.converter.convert(1, "h", "s"), 3600.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "d", "s"), 86400.0, places=6)
    
    def test_area_conversions(self):
        """Test area unit conversions."""
        # Metric area
        self.assertAlmostEqual(self.converter.convert(10000, "cm²", "m²"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "hectare", "m²"), 10000.0, places=6)
        
        # Imperial area
        self.assertAlmostEqual(self.converter.convert(144, "sq_in", "sq_ft"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "acre", "sq_ft"), 43560.0, places=0)
    
    def test_volume_conversions(self):
        """Test volume unit conversions."""
        # Metric volume
        self.assertAlmostEqual(self.converter.convert(1000, "ml", "l"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(1, "m³", "l"), 1000.0, places=6)
        
        # US volume
        self.assertAlmostEqual(self.converter.convert(3, "tsp", "tbsp"), 1.0, places=6)
        self.assertAlmostEqual(self.converter.convert(2, "tbsp", "fl_oz"), 1.0, places=5)
        self.assertAlmostEqual(self.converter.convert(4, "qt", "gal"), 1.0, places=5)
    
    def test_conversion_errors(self):
        """Test conversion error handling."""
        # Unknown units
        with self.assertRaises(ConversionError):
            self.converter.convert(1, "unknown_unit", "m")
        
        with self.assertRaises(ConversionError):
            self.converter.convert(1, "m", "unknown_unit")
        
        # Incompatible units
        with self.assertRaises(ConversionError):
            self.converter.convert(1, "m", "kg")  # Length to weight
        
        with self.assertRaises(ConversionError):
            self.converter.convert(1, "celsius", "meter")  # Temperature to length
        
        # Invalid values
        with self.assertRaises(ConversionError):
            self.converter.convert("invalid", "m", "cm")
    
    def test_unit_validation(self):
        """Test unit validation and suggestions."""
        # Valid units
        valid, category = self.converter.validate_unit("meter")
        self.assertTrue(valid)
        self.assertEqual(category, "length")
        
        valid, category = self.converter.validate_unit("celsius")
        self.assertTrue(valid)
        self.assertEqual(category, "temperature")
        
        # Invalid units
        valid, category = self.converter.validate_unit("invalid_unit")
        self.assertFalse(valid)
        self.assertIsNone(category)
        
        # Unit suggestions
        suggestions = self.converter.find_unit_suggestions("met")
        self.assertIn("meter", suggestions)
        
        suggestions = self.converter.find_unit_suggestions("cel")
        self.assertIn("celsius", suggestions)
    
    def test_multiple_conversions(self):
        """Test converting to multiple units at once."""
        results = self.converter.convert_multiple(1, "m", ["cm", "mm", "km"])
        
        self.assertAlmostEqual(results["cm"], 100.0, places=6)
        self.assertAlmostEqual(results["mm"], 1000.0, places=6)
        self.assertAlmostEqual(results["km"], 0.001, places=6)
    
    def test_conversion_info(self):
        """Test conversion information retrieval."""
        info = self.converter.get_conversion_info("m", "cm")
        
        self.assertEqual(info["from_unit"], "m")
        self.assertEqual(info["to_unit"], "cm")
        self.assertEqual(info["category"], "length")
        self.assertAlmostEqual(info["conversion_factor"], 100.0, places=6)
        self.assertAlmostEqual(info["reverse_factor"], 0.01, places=6)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = Calculator()
        self.parser = ExpressionParser(self.calc)
        self.memory = MemoryManager()
        self.history = HistoryManager()
        self.converter = UnitConverter()
    
    def test_calculator_with_parser(self):
        """Test calculator integration with expression parser."""
        # Complex mathematical expression
        result = self.parser.parse("sin(pi/4)^2 + cos(pi/4)^2")
        self.assertAlmostEqual(result, 1.0, places=10)
        
        # Expression with variables
        self.parser.set_variable("radius", 5)
        area = self.parser.parse("pi * radius^2")
        self.assertAlmostEqual(area, math.pi * 25, places=10)
    
    def test_memory_with_parser(self):
        """Test memory integration with expression parsing."""
        # Store calculation results in memory
        result1 = self.parser.parse("2^3")  # 8
        self.memory.store(result1, "M1")
        
        result2 = self.parser.parse("3^2")  # 9
        self.memory.store(result2, "M2")
        
        # Use memory values in calculations
        mem_vars = self.memory.export_slots_to_dict()
        for name, value in mem_vars.items():
            self.parser.set_variable(name, value)
        
        combined_result = self.parser.parse("m1 + m2")  # 8 + 9 = 17
        self.assertEqual(combined_result, 17)
    
    def test_history_with_calculations(self):
        """Test history integration with calculations."""
        # Perform calculations and store in history
        expressions = [
            ("2 + 3", 5),
            ("factorial(4)", 24),
            ("sqrt(16)", 4),
            ("sin(pi/2)", 1)
        ]
        
        for expr, expected in expressions:
            result = self.parser.parse(expr)
            self.assertAlmostEqual(result, expected, places=6)
            self.history.add_calculation(expr, result)
        
        # Verify history
        self.assertEqual(len(self.history), 4)
        self.assertEqual(self.history.get_last_result(), 1.0)
        
        # Search history
        trig_calcs = self.history.search_by_expression("sin")
        self.assertEqual(len(trig_calcs), 1)
        self.assertEqual(trig_calcs[0].expression, "sin(pi/2)")
    
    def test_full_workflow(self):
        """Test a complete calculator workflow."""
        # 1. Set up variables
        self.parser.set_variable("x", 3)
        self.parser.set_variable("y", 4)
        
        # 2. Perform calculations and store results
        hypotenuse = self.parser.parse("sqrt(x^2 + y^2)")
        self.memory.store(hypotenuse, "M1")
        self.history.add_calculation("sqrt(x^2 + y^2)", hypotenuse, 
                                   {"x": 3, "y": 4})
        
        # 3. Use memory in further calculations
        self.memory.add(1, "M1")  # Add 1 to the stored hypotenuse
        modified_result = self.memory.recall("M1")
        
        # 4. Verify results
        self.assertEqual(hypotenuse, 5.0)
        self.assertEqual(modified_result, 6.0)
        
        # 5. Check history
        self.assertEqual(len(self.history), 1)
        entry = self.history.get_entry_by_index(0)
        self.assertEqual(entry.expression, "sqrt(x^2 + y^2)")
        self.assertEqual(entry.result, 5.0)
        self.assertIn("x", entry.variables)
        self.assertIn("y", entry.variables)


def run_performance_tests():
    """Run performance tests for complex calculations."""
    print("\nRunning performance tests...")
    import time
    
    calc = Calculator()
    parser = ExpressionParser(calc)
    
    # Test complex expression parsing speed
    complex_expr = "sin(cos(tan(sqrt(factorial(5) + log(e^2) * pi))))"
    
    start_time = time.time()
    for _ in range(1000):
        try:
            result = parser.parse(complex_expr)
        except:
            pass
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 1000
    print(f"Average time for complex expression parsing: {avg_time:.6f} seconds")
    
    # Test large number calculations
    large_expr = "factorial(50) + 2^100"
    start_time = time.time()
    try:
        result = parser.parse(large_expr)
        end_time = time.time()
        print(f"Large number calculation time: {end_time - start_time:.6f} seconds")
        print(f"Result magnitude: ~{len(str(int(result)))} digits")
    except Exception as e:
        print(f"Large number test failed: {e}")


if __name__ == "__main__":
    # Run all unit tests
    print("Running Super Complex Calculator Test Suite")
    print("=" * 50)
    
    # Create test suite
    test_classes = [
        TestCalculator,
        TestExpressionParser,
        TestMemoryManager,
        TestHistoryManager,
        TestUnitConverter,
        TestIntegration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            lines = traceback.split('\n')
            print(f"- {test}: {lines[-2] if len(lines) > 1 else 'Unknown error'}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            lines = traceback.split('\n')
            print(f"- {test}: {lines[-2] if len(lines) > 1 else 'Unknown error'}")
    
    # Run performance tests if all unit tests pass
    if not result.failures and not result.errors:
        run_performance_tests()
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed. Please fix issues before proceeding.")
    
    exit(0 if result.wasSuccessful() else 1)