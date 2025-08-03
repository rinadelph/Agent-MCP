"""
Unit Converter for Super Complex Calculator

This module provides comprehensive unit conversion functionality including
length, weight, temperature, time, area, and volume conversions with
high precision and extensive unit support.
"""

from typing import Dict, List, Union, Optional, Tuple, Any
import math
try:
    from .calculator import CalculatorError, InvalidInputError
except ImportError:
    from calculator import CalculatorError, InvalidInputError


class ConversionError(CalculatorError):
    """Raised when unit conversion fails."""
    pass


class UnitConverter:
    """
    Comprehensive unit converter supporting multiple categories of units.
    
    Supported categories:
    - Length: meters, feet, inches, miles, kilometers, etc.
    - Weight/Mass: grams, pounds, ounces, kilograms, etc.
    - Temperature: Celsius, Fahrenheit, Kelvin
    - Time: seconds, minutes, hours, days, etc.
    - Area: square meters, acres, hectares, etc.
    - Volume: liters, gallons, cubic meters, etc.
    """
    
    def __init__(self):
        """Initialize the unit converter with conversion tables."""
        self._initialize_conversion_tables()
    
    def _initialize_conversion_tables(self) -> None:
        """Initialize all conversion factor tables."""
        
        # Length conversions (all to meters)
        self.length_units = {
            # Metric
            'mm': 0.001, 'millimeter': 0.001, 'millimeters': 0.001,
            'cm': 0.01, 'centimeter': 0.01, 'centimeters': 0.01,
            'm': 1.0, 'meter': 1.0, 'meters': 1.0, 'metre': 1.0, 'metres': 1.0,
            'km': 1000.0, 'kilometer': 1000.0, 'kilometers': 1000.0,
            
            # Imperial/US
            'in': 0.0254, 'inch': 0.0254, 'inches': 0.0254,
            'ft': 0.3048, 'foot': 0.3048, 'feet': 0.3048,
            'yd': 0.9144, 'yard': 0.9144, 'yards': 0.9144,
            'mi': 1609.344, 'mile': 1609.344, 'miles': 1609.344,
            
            # Other units
            'nmi': 1852.0, 'nautical_mile': 1852.0, 'nautical_miles': 1852.0,
            'au': 149597870700.0, 'astronomical_unit': 149597870700.0,
            'ly': 9460730472580800.0, 'light_year': 9460730472580800.0
        }
        
        # Weight/Mass conversions (all to grams)
        self.weight_units = {
            # Metric
            'mg': 0.001, 'milligram': 0.001, 'milligrams': 0.001,
            'g': 1.0, 'gram': 1.0, 'grams': 1.0,
            'kg': 1000.0, 'kilogram': 1000.0, 'kilograms': 1000.0,
            'ton': 1000000.0, 'tonne': 1000000.0, 'tonnes': 1000000.0,
            
            # Imperial/US
            'oz': 28.3495, 'ounce': 28.3495, 'ounces': 28.3495,
            'lb': 453.592, 'pound': 453.592, 'pounds': 453.592,
            'st': 6350.29, 'stone': 6350.29, 'stones': 6350.29,
            
            # Other units
            'grain': 0.0647989,
            'carat': 0.2,
            'troy_oz': 31.1035, 'troy_ounce': 31.1035
        }
        
        # Time conversions (all to seconds)
        self.time_units = {
            'ns': 1e-9, 'nanosecond': 1e-9, 'nanoseconds': 1e-9,
            'μs': 1e-6, 'microsecond': 1e-6, 'microseconds': 1e-6,
            'ms': 0.001, 'millisecond': 0.001, 'milliseconds': 0.001,
            's': 1.0, 'sec': 1.0, 'second': 1.0, 'seconds': 1.0,
            'min': 60.0, 'minute': 60.0, 'minutes': 60.0,
            'h': 3600.0, 'hr': 3600.0, 'hour': 3600.0, 'hours': 3600.0,
            'd': 86400.0, 'day': 86400.0, 'days': 86400.0,
            'wk': 604800.0, 'week': 604800.0, 'weeks': 604800.0,
            'mo': 2629746.0, 'month': 2629746.0, 'months': 2629746.0,  # Average month
            'yr': 31556952.0, 'year': 31556952.0, 'years': 31556952.0  # Average year
        }
        
        # Area conversions (all to square meters)
        self.area_units = {
            # Metric
            'mm²': 1e-6, 'sq_mm': 1e-6, 'square_millimeter': 1e-6,
            'cm²': 1e-4, 'sq_cm': 1e-4, 'square_centimeter': 1e-4,
            'm²': 1.0, 'sq_m': 1.0, 'square_meter': 1.0, 'square_meters': 1.0,
            'km²': 1e6, 'sq_km': 1e6, 'square_kilometer': 1e6,
            
            # Imperial/US
            'in²': 0.00064516, 'sq_in': 0.00064516, 'square_inch': 0.00064516,
            'ft²': 0.092903, 'sq_ft': 0.092903, 'square_foot': 0.092903,
            'yd²': 0.836127, 'sq_yd': 0.836127, 'square_yard': 0.836127,
            'mi²': 2589988.11, 'sq_mi': 2589988.11, 'square_mile': 2589988.11,
            
            # Other units
            'acre': 4046.86, 'acres': 4046.86,
            'hectare': 10000.0, 'hectares': 10000.0, 'ha': 10000.0
        }
        
        # Volume conversions (all to liters)
        self.volume_units = {
            # Metric
            'ml': 0.001, 'milliliter': 0.001, 'milliliters': 0.001,
            'cl': 0.01, 'centiliter': 0.01, 'centiliters': 0.01,
            'dl': 0.1, 'deciliter': 0.1, 'deciliters': 0.1,
            'l': 1.0, 'liter': 1.0, 'liters': 1.0, 'litre': 1.0, 'litres': 1.0,
            'm³': 1000.0, 'cubic_meter': 1000.0, 'cubic_meters': 1000.0,
            
            # Imperial/US
            'tsp': 0.00492892159, 'teaspoon': 0.00492892159, 'teaspoons': 0.00492892159,
            'tbsp': 0.01478676478, 'tablespoon': 0.01478676478, 'tablespoons': 0.01478676478,
            'fl_oz': 0.0295735, 'fluid_ounce': 0.0295735, 'fluid_ounces': 0.0295735,
            'cup': 0.236588, 'cups': 0.236588,
            'pt': 0.473176, 'pint': 0.473176, 'pints': 0.473176,
            'qt': 0.946353, 'quart': 0.946353, 'quarts': 0.946353,
            'gal': 3.78541, 'gallon': 3.78541, 'gallons': 3.78541,
            
            # UK Imperial (different from US)
            'uk_fl_oz': 0.0284131, 'uk_fluid_ounce': 0.0284131,
            'uk_pt': 0.568261, 'uk_pint': 0.568261,
            'uk_qt': 1.13652, 'uk_quart': 1.13652,
            'uk_gal': 4.54609, 'uk_gallon': 4.54609,
            
            # Other units
            'in³': 0.0163871, 'cubic_inch': 0.0163871,
            'ft³': 28.3168, 'cubic_foot': 28.3168,
            'yd³': 764.555, 'cubic_yard': 764.555
        }
        
        # Temperature units (special handling required)
        self.temperature_units = ['c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin', 'r', 'rankine']
        
        # Energy conversions (all to joules)
        self.energy_units = {
            'j': 1.0, 'joule': 1.0, 'joules': 1.0,
            'kj': 1000.0, 'kilojoule': 1000.0, 'kilojoules': 1000.0,
            'cal': 4.184, 'calorie': 4.184, 'calories': 4.184,
            'kcal': 4184.0, 'kilocalorie': 4184.0, 'kilocalories': 4184.0,
            'btu': 1055.06, 'british_thermal_unit': 1055.06,
            'kwh': 3600000.0, 'kilowatt_hour': 3600000.0, 'kilowatt_hours': 3600000.0,
            'ev': 1.602176634e-19, 'electron_volt': 1.602176634e-19
        }
        
        # Create mapping of unit categories
        self.unit_categories = {
            'length': self.length_units,
            'weight': self.weight_units,
            'mass': self.weight_units,  # Alias for weight
            'time': self.time_units,
            'area': self.area_units,
            'volume': self.volume_units,
            'energy': self.energy_units
        }
    
    def get_supported_categories(self) -> List[str]:
        """Get list of supported conversion categories."""
        return list(self.unit_categories.keys()) + ['temperature']
    
    def get_supported_units(self, category: str) -> List[str]:
        """Get list of supported units for a category."""
        category = category.lower()
        if category == 'temperature':
            return self.temperature_units
        elif category in self.unit_categories:
            return list(self.unit_categories[category].keys())
        else:
            raise ConversionError(f"Unsupported category: {category}")
    
    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit name (lowercase, remove spaces)."""
        return unit.lower().replace(' ', '_').replace('-', '_')
    
    def _find_unit_category(self, unit: str) -> Optional[str]:
        """Find which category a unit belongs to."""
        normalized_unit = self._normalize_unit(unit)
        
        if normalized_unit in self.temperature_units:
            return 'temperature'
        
        for category, units in self.unit_categories.items():
            if normalized_unit in units:
                return category
        
        return None
    
    def convert(self, value: Union[int, float], from_unit: str, to_unit: str) -> float:
        """
        Convert a value from one unit to another.
        
        Args:
            value: The value to convert
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Converted value
            
        Raises:
            ConversionError: If conversion is invalid or unsupported
        """
        if not isinstance(value, (int, float)):
            raise ConversionError(f"Value must be numeric, got {type(value)}")
        
        from_unit = self._normalize_unit(from_unit)
        to_unit = self._normalize_unit(to_unit)
        
        if from_unit == to_unit:
            return float(value)
        
        # Find categories for both units
        from_category = self._find_unit_category(from_unit)
        to_category = self._find_unit_category(to_unit)
        
        if from_category is None:
            raise ConversionError(f"Unknown unit: {from_unit}")
        if to_category is None:
            raise ConversionError(f"Unknown unit: {to_unit}")
        if from_category != to_category:
            raise ConversionError(f"Cannot convert between {from_category} and {to_category}")
        
        # Handle temperature conversions specially
        if from_category == 'temperature':
            return self._convert_temperature(value, from_unit, to_unit)
        
        # Handle other unit conversions
        conversion_table = self.unit_categories[from_category]
        
        # Convert to base unit, then to target unit
        base_value = value * conversion_table[from_unit]
        result = base_value / conversion_table[to_unit]
        
        return result
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature between different scales."""
        # Normalize unit names
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()
        
        # Convert to Celsius first
        if from_unit in ['c', 'celsius']:
            celsius = value
        elif from_unit in ['f', 'fahrenheit']:
            celsius = (value - 32) * 5/9
        elif from_unit in ['k', 'kelvin']:
            celsius = value - 273.15
        elif from_unit in ['r', 'rankine']:
            celsius = (value - 491.67) * 5/9
        else:
            raise ConversionError(f"Unknown temperature unit: {from_unit}")
        
        # Convert from Celsius to target
        if to_unit in ['c', 'celsius']:
            result = celsius
        elif to_unit in ['f', 'fahrenheit']:
            result = celsius * 9/5 + 32
        elif to_unit in ['k', 'kelvin']:
            result = celsius + 273.15
        elif to_unit in ['r', 'rankine']:
            result = celsius * 9/5 + 491.67
        else:
            raise ConversionError(f"Unknown temperature unit: {to_unit}")
        
        return result
    
    def convert_multiple(self, value: Union[int, float], from_unit: str, 
                        to_units: List[str]) -> Dict[str, float]:
        """
        Convert a value to multiple target units.
        
        Args:
            value: The value to convert
            from_unit: Source unit
            to_units: List of target units
            
        Returns:
            Dictionary mapping unit names to converted values
        """
        results = {}
        for to_unit in to_units:
            try:
                results[to_unit] = self.convert(value, from_unit, to_unit)
            except ConversionError as e:
                results[to_unit] = f"Error: {e}"
        
        return results
    
    def get_conversion_info(self, from_unit: str, to_unit: str) -> Dict[str, any]:
        """
        Get detailed information about a conversion.
        
        Args:
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Dictionary with conversion information
        """
        try:
            # Test conversion with value 1 to get the conversion factor
            factor = self.convert(1, from_unit, to_unit)
            
            from_category = self._find_unit_category(from_unit)
            to_category = self._find_unit_category(to_unit)
            
            return {
                'from_unit': from_unit,
                'to_unit': to_unit,
                'category': from_category,
                'conversion_factor': factor,
                'formula': f"1 {from_unit} = {factor} {to_unit}",
                'reverse_factor': 1/factor if factor != 0 else None,
                'is_temperature': from_category == 'temperature'
            }
        except ConversionError as e:
            return {
                'from_unit': from_unit,
                'to_unit': to_unit,
                'error': str(e)
            }
    
    def find_unit_suggestions(self, partial_unit: str, limit: int = 10) -> List[str]:
        """
        Find unit suggestions based on partial input.
        
        Args:
            partial_unit: Partial unit name
            limit: Maximum number of suggestions
            
        Returns:
            List of matching unit names
        """
        partial = partial_unit.lower()
        suggestions = []
        
        # Search in all categories
        for category_units in self.unit_categories.values():
            for unit in category_units.keys():
                if partial in unit.lower() and unit not in suggestions:
                    suggestions.append(unit)
        
        # Search in temperature units
        for unit in self.temperature_units:
            if partial in unit.lower() and unit not in suggestions:
                suggestions.append(unit)
        
        return suggestions[:limit]
    
    def validate_unit(self, unit: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a unit is supported.
        
        Args:
            unit: Unit name to validate
            
        Returns:
            (is_valid, category)
        """
        category = self._find_unit_category(unit)
        return category is not None, category
    
    def get_unit_info(self, unit: str) -> Dict[str, Any]:
        """
        Get detailed information about a unit.
        
        Args:
            unit: Unit name
            
        Returns:
            Dictionary with unit information
        """
        normalized = self._normalize_unit(unit)
        category = self._find_unit_category(unit)
        
        if category is None:
            return {
                'unit': unit,
                'valid': False,
                'error': 'Unknown unit'
            }
        
        info = {
            'unit': unit,
            'normalized': normalized,
            'category': category,
            'valid': True
        }
        
        # Add conversion factor info if not temperature
        if category != 'temperature':
            conversion_table = self.unit_categories[category]
            info['base_unit_factor'] = conversion_table[normalized]
        
        return info
    
    def __str__(self) -> str:
        """String representation of the unit converter."""
        total_units = sum(len(units) for units in self.unit_categories.values())
        total_units += len(self.temperature_units)
        return f"UnitConverter({len(self.unit_categories)} categories, {total_units} units)"


if __name__ == "__main__":
    # Test the unit converter
    converter = UnitConverter()
    
    print("Unit Converter Test:")
    print(f"Converter info: {converter}")
    
    # Test various conversions
    test_conversions = [
        (100, "cm", "m"),
        (32, "f", "c"),
        (1, "kg", "lb"),
        (1, "hour", "seconds"),
        (1, "acre", "m²"),
        (1, "gallon", "liters")
    ]
    
    print("\nTest conversions:")
    for value, from_unit, to_unit in test_conversions:
        try:
            result = converter.convert(value, from_unit, to_unit)
            print(f"{value} {from_unit} = {result:.6f} {to_unit}")
        except Exception as e:
            print(f"{value} {from_unit} -> {to_unit}: Error: {e}")
    
    # Test category listing
    print(f"\nSupported categories: {converter.get_supported_categories()}")
    
    # Test unit suggestions
    suggestions = converter.find_unit_suggestions("met")
    print(f"Suggestions for 'met': {suggestions}")