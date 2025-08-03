"""
Super Complex Calculator - Core Calculator Class

This module contains the main Calculator class that integrates all calculator functionality
including basic arithmetic, scientific functions, statistical operations, and advanced math.
"""

import math
import statistics
from typing import Union, List, Optional, Dict, Any
from decimal import Decimal, getcontext, InvalidOperation

# Set high precision for Decimal calculations
getcontext().prec = 50


class CalculatorError(Exception):
    """Base exception class for calculator errors."""
    pass


class DivisionByZeroError(CalculatorError):
    """Raised when attempting division by zero."""
    pass


class DomainError(CalculatorError):
    """Raised when a mathematical function is called with invalid domain values."""
    pass


class InvalidInputError(CalculatorError):
    """Raised when input is invalid or malformed."""
    pass


class Calculator:
    """
    Super Complex Calculator with advanced mathematical functionality.
    
    Provides basic arithmetic, scientific functions, statistical operations,
    and advanced mathematical computations with robust error handling.
    """
    
    # Mathematical constants
    CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
        'nan': math.nan
    }
    
    def __init__(self):
        """Initialize the calculator."""
        self.last_result = 0
        self._precision = 10  # Default decimal places for display
    
    def set_precision(self, precision: int) -> None:
        """Set the display precision for floating point numbers."""
        if precision < 0:
            raise InvalidInputError("Precision must be non-negative")
        self._precision = precision
    
    def get_constant(self, name: str) -> float:
        """Get a mathematical constant by name."""
        name = name.lower()
        if name not in self.CONSTANTS:
            raise InvalidInputError(f"Unknown constant: {name}")
        return self.CONSTANTS[name]
    
    # Basic Arithmetic Operations
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers."""
        try:
            result = a + b
            self.last_result = result
            return result
        except (TypeError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for addition: {e}")
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract b from a."""
        try:
            result = a - b
            self.last_result = result
            return result
        except (TypeError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for subtraction: {e}")
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers."""
        try:
            result = a * b
            self.last_result = result
            return result
        except (TypeError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for multiplication: {e}")
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> float:
        """Divide a by b."""
        if b == 0:
            raise DivisionByZeroError("Division by zero is not allowed")
        try:
            result = a / b
            self.last_result = result
            return result
        except (TypeError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for division: {e}")
    
    def modulo(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Calculate a modulo b."""
        if b == 0:
            raise DivisionByZeroError("Modulo by zero is not allowed")
        try:
            result = a % b
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for modulo: {e}")
    
    def power(self, base: Union[int, float], exponent: Union[int, float]) -> Union[int, float]:
        """Calculate base raised to the power of exponent."""
        try:
            result = base ** exponent
            if math.isinf(result):
                raise OverflowError("Result is too large")
            if math.isnan(result):
                raise DomainError("Invalid domain for power operation")
            self.last_result = result
            return result
        except (TypeError, ValueError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for power: {e}")
    
    # Scientific Functions
    def sin(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate sine of x. Set degrees=True for degree input."""
        try:
            angle = math.radians(x) if degrees else x
            result = math.sin(angle)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for sine: {e}")
    
    def cos(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate cosine of x. Set degrees=True for degree input."""
        try:
            angle = math.radians(x) if degrees else x
            result = math.cos(angle)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for cosine: {e}")
    
    def tan(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate tangent of x. Set degrees=True for degree input."""
        try:
            angle = math.radians(x) if degrees else x
            result = math.tan(angle)
            if math.isinf(result):
                raise DomainError("Tangent undefined (approaching infinity)")
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for tangent: {e}")
    
    def asin(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate arcsine of x. Returns degrees if degrees=True."""
        if not -1 <= x <= 1:
            raise DomainError("Arcsine domain error: input must be between -1 and 1")
        try:
            result = math.asin(x)
            if degrees:
                result = math.degrees(result)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for arcsine: {e}")
    
    def acos(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate arccosine of x. Returns degrees if degrees=True."""
        if not -1 <= x <= 1:
            raise DomainError("Arccosine domain error: input must be between -1 and 1")
        try:
            result = math.acos(x)
            if degrees:
                result = math.degrees(result)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for arccosine: {e}")
    
    def atan(self, x: Union[int, float], degrees: bool = False) -> float:
        """Calculate arctangent of x. Returns degrees if degrees=True."""
        try:
            result = math.atan(x)
            if degrees:
                result = math.degrees(result)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for arctangent: {e}")
    
    def log(self, x: Union[int, float], base: Union[int, float] = math.e) -> float:
        """Calculate logarithm of x with given base (natural log by default)."""
        if x <= 0:
            raise DomainError("Logarithm domain error: input must be positive")
        if base <= 0 or base == 1:
            raise DomainError("Logarithm base error: base must be positive and not equal to 1")
        try:
            result = math.log(x, base)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for logarithm: {e}")
    
    def ln(self, x: Union[int, float]) -> float:
        """Calculate natural logarithm of x."""
        return self.log(x, math.e)
    
    def log10(self, x: Union[int, float]) -> float:
        """Calculate base-10 logarithm of x."""
        return self.log(x, 10)
    
    def exp(self, x: Union[int, float]) -> float:
        """Calculate e raised to the power of x."""
        try:
            result = math.exp(x)
            if math.isinf(result):
                raise OverflowError("Exponential result is too large")
            self.last_result = result
            return result
        except (TypeError, ValueError, OverflowError) as e:
            raise InvalidInputError(f"Invalid input for exponential: {e}")
    
    def sqrt(self, x: Union[int, float]) -> float:
        """Calculate square root of x."""
        if x < 0:
            raise DomainError("Square root domain error: input must be non-negative")
        try:
            result = math.sqrt(x)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for square root: {e}")
    
    # Statistical Functions
    def mean(self, data: List[Union[int, float]]) -> float:
        """Calculate arithmetic mean of a list of numbers."""
        if not data:
            raise InvalidInputError("Cannot calculate mean of empty dataset")
        try:
            result = statistics.mean(data)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid data for mean calculation: {e}")
    
    def median(self, data: List[Union[int, float]]) -> float:
        """Calculate median of a list of numbers."""
        if not data:
            raise InvalidInputError("Cannot calculate median of empty dataset")
        try:
            result = statistics.median(data)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid data for median calculation: {e}")
    
    def mode(self, data: List[Union[int, float]]) -> Union[int, float]:
        """Calculate mode of a list of numbers."""
        if not data:
            raise InvalidInputError("Cannot calculate mode of empty dataset")
        try:
            result = statistics.mode(data)
            self.last_result = result
            return result
        except (TypeError, ValueError, statistics.StatisticsError) as e:
            raise InvalidInputError(f"Invalid data for mode calculation: {e}")
    
    def standard_deviation(self, data: List[Union[int, float]], population: bool = False) -> float:
        """Calculate standard deviation. Set population=True for population std dev."""
        if len(data) < 2:
            raise InvalidInputError("Need at least 2 data points for standard deviation")
        try:
            result = statistics.pstdev(data) if population else statistics.stdev(data)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid data for standard deviation: {e}")
    
    def variance(self, data: List[Union[int, float]], population: bool = False) -> float:
        """Calculate variance. Set population=True for population variance."""
        if len(data) < 2:
            raise InvalidInputError("Need at least 2 data points for variance")
        try:
            result = statistics.pvariance(data) if population else statistics.variance(data)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid data for variance: {e}")
    
    # Advanced Mathematical Functions
    def factorial(self, n: int) -> int:
        """Calculate factorial of n."""
        if not isinstance(n, int):
            raise InvalidInputError("Factorial input must be an integer")
        if n < 0:
            raise DomainError("Factorial domain error: input must be non-negative")
        if n > 170:  # Prevents overflow
            raise OverflowError("Factorial input too large (maximum 170)")
        try:
            result = math.factorial(n)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for factorial: {e}")
    
    def combinations(self, n: int, k: int) -> int:
        """Calculate combinations C(n,k) = n! / (k!(n-k)!)."""
        if not isinstance(n, int) or not isinstance(k, int):
            raise InvalidInputError("Combination inputs must be integers")
        if n < 0 or k < 0:
            raise DomainError("Combination inputs must be non-negative")
        if k > n:
            raise DomainError("k cannot be greater than n in combinations")
        try:
            result = math.comb(n, k)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for combinations: {e}")
    
    def permutations(self, n: int, k: int) -> int:
        """Calculate permutations P(n,k) = n! / (n-k)!."""
        if not isinstance(n, int) or not isinstance(k, int):
            raise InvalidInputError("Permutation inputs must be integers")
        if n < 0 or k < 0:
            raise DomainError("Permutation inputs must be non-negative")
        if k > n:
            raise DomainError("k cannot be greater than n in permutations")
        try:
            result = math.perm(n, k)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for permutations: {e}")
    
    def gcd(self, a: int, b: int) -> int:
        """Calculate greatest common divisor of a and b."""
        if not isinstance(a, int) or not isinstance(b, int):
            raise InvalidInputError("GCD inputs must be integers")
        try:
            result = math.gcd(a, b)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for GCD: {e}")
    
    def lcm(self, a: int, b: int) -> int:
        """Calculate least common multiple of a and b."""
        if not isinstance(a, int) or not isinstance(b, int):
            raise InvalidInputError("LCM inputs must be integers")
        try:
            result = math.lcm(a, b)
            self.last_result = result
            return result
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"Invalid input for LCM: {e}")
    
    # Utility Methods
    def format_result(self, result: Union[int, float]) -> str:
        """Format a result for display with appropriate precision."""
        if isinstance(result, int):
            return str(result)
        elif isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            else:
                return f"{result:.{self._precision}f}".rstrip('0').rstrip('.')
        else:
            return str(result)
    
    def get_last_result(self) -> Union[int, float]:
        """Get the last calculated result."""
        return self.last_result
    
    def clear_last_result(self) -> None:
        """Clear the last result."""
        self.last_result = 0


if __name__ == "__main__":
    # Simple test of the calculator
    calc = Calculator()
    print("Calculator initialized successfully!")
    print(f"2 + 3 = {calc.add(2, 3)}")
    print(f"sin(π/2) = {calc.sin(calc.get_constant('pi') / 2)}")
    print(f"factorial(5) = {calc.factorial(5)}")