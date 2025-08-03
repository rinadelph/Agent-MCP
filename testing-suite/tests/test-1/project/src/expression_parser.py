"""
Expression Parser for Super Complex Calculator

This module provides sophisticated expression parsing and evaluation capabilities,
including support for operator precedence, parentheses, variables, constants,
and implicit multiplication.
"""

import re
import math
from typing import Union, Dict, Any, Optional, List, Tuple
try:
    from .calculator import Calculator, CalculatorError, InvalidInputError, DomainError
except ImportError:
    from calculator import Calculator, CalculatorError, InvalidInputError, DomainError


class ParseError(CalculatorError):
    """Raised when expression parsing fails."""
    pass


class Token:
    """Represents a token in the expression."""
    
    def __init__(self, type_: str, value: Any, position: int = 0):
        self.type = type_  # 'NUMBER', 'OPERATOR', 'FUNCTION', 'VARIABLE', 'LPAREN', 'RPAREN'
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.position})"


class ExpressionParser:
    """
    Advanced expression parser supporting mathematical expressions with:
    - Basic arithmetic operators (+, -, *, /, %, ^, **)
    - Functions (sin, cos, log, sqrt, etc.)
    - Constants (pi, e, etc.)
    - Variables
    - Parentheses for grouping
    - Implicit multiplication (2pi, 3sin(x), etc.)
    """
    
    # Operator precedence (higher number = higher precedence)
    PRECEDENCE = {
        '+': 1, '-': 1,           # Addition, subtraction
        '*': 2, '/': 2, '%': 2,   # Multiplication, division, modulo
        '^': 3, '**': 3,          # Exponentiation
        'UNARY+': 4, 'UNARY-': 4, # Unary plus/minus
        'FUNCTION': 5             # Function calls
    }
    
    # Right associative operators
    RIGHT_ASSOCIATIVE = {'^', '**'}
    
    # Built-in functions mapping to calculator methods
    FUNCTIONS = {
        # Trigonometric functions
        'sin': 'sin', 'cos': 'cos', 'tan': 'tan',
        'asin': 'asin', 'acos': 'acos', 'atan': 'atan',
        # Logarithmic and exponential
        'log': 'log', 'ln': 'ln', 'log10': 'log10', 'exp': 'exp',
        # Other functions
        'sqrt': 'sqrt', 'factorial': 'factorial', 'abs': 'abs',
        'ceil': 'ceil', 'floor': 'floor', 'round': 'round'
    }
    
    def __init__(self, calculator: Calculator):
        """Initialize the parser with a calculator instance."""
        self.calculator = calculator
        self.variables: Dict[str, Union[int, float]] = {}
        self.tokens: List[Token] = []
        self.position = 0
    
    def set_variable(self, name: str, value: Union[int, float]) -> None:
        """Set a variable value."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise InvalidInputError(f"Invalid variable name: {name}")
        self.variables[name] = value
    
    def get_variable(self, name: str) -> Union[int, float]:
        """Get a variable value."""
        if name in self.variables:
            return self.variables[name]
        # Check if it's a constant
        try:
            return self.calculator.get_constant(name)
        except InvalidInputError:
            raise InvalidInputError(f"Undefined variable: {name}")
    
    def clear_variables(self) -> None:
        """Clear all variables."""
        self.variables.clear()
    
    def tokenize(self, expression: str) -> List[Token]:
        """
        Tokenize the input expression into a list of tokens.
        Handles implicit multiplication detection.
        """
        if not expression.strip():
            raise ParseError("Empty expression")
        
        # Clean the expression
        expr = expression.replace(' ', '').replace('\t', '').replace('\n', '')
        
        # Replace ** with ^ for easier processing
        expr = expr.replace('**', '^')
        
        tokens = []
        i = 0
        
        while i < len(expr):
            char = expr[i]
            
            # Numbers (including decimals and scientific notation)
            if char.isdigit() or char == '.':
                number_str = ''
                decimal_count = 0
                start_pos = i
                
                # Parse the number part
                while i < len(expr) and expr[i].isdigit():
                    number_str += expr[i]
                    i += 1
                
                # Handle decimal point
                if i < len(expr) and expr[i] == '.':
                    decimal_count += 1
                    number_str += expr[i]
                    i += 1
                    
                    # Parse digits after decimal
                    while i < len(expr) and expr[i].isdigit():
                        number_str += expr[i]
                        i += 1
                
                # Handle scientific notation
                if i < len(expr) and expr[i].lower() == 'e':
                    number_str += expr[i]
                    i += 1
                    
                    # Handle optional +/- after e
                    if i < len(expr) and expr[i] in '+-':
                        number_str += expr[i]
                        i += 1
                    
                    # Parse exponent digits
                    while i < len(expr) and expr[i].isdigit():
                        number_str += expr[i]
                        i += 1
                
                try:
                    if '.' in number_str or 'e' in number_str.lower():
                        value = float(number_str)
                    else:
                        value = int(number_str)
                    tokens.append(Token('NUMBER', value, start_pos))
                except ValueError:
                    raise ParseError(f"Invalid number format: {number_str}")
                continue
            
            # Operators
            elif char in '+-*/()%^':
                if char == '(':
                    tokens.append(Token('LPAREN', char, i))
                elif char == ')':
                    tokens.append(Token('RPAREN', char, i))
                else:
                    tokens.append(Token('OPERATOR', char, i))
                i += 1
                continue
            
            # Functions and variables
            elif char.isalpha() or char == '_':
                name = ''
                while i < len(expr) and (expr[i].isalnum() or expr[i] == '_'):
                    name += expr[i]
                    i += 1
                
                # Check if it's followed by a parenthesis (function)
                if i < len(expr) and expr[i] == '(':
                    if name.lower() in self.FUNCTIONS:
                        tokens.append(Token('FUNCTION', name.lower(), i - len(name)))
                    else:
                        raise ParseError(f"Unknown function: {name}")
                else:
                    tokens.append(Token('VARIABLE', name.lower(), i - len(name)))
                continue
            
            else:
                raise ParseError(f"Unexpected character: {char} at position {i}")
        
        # Handle implicit multiplication
        tokens = self._add_implicit_multiplication(tokens)
        
        return tokens
    
    def _add_implicit_multiplication(self, tokens: List[Token]) -> List[Token]:
        """Add implicit multiplication tokens where appropriate."""
        if not tokens:
            return tokens
        
        new_tokens = [tokens[0]]
        
        for i in range(1, len(tokens)):
            prev_token = tokens[i - 1]
            curr_token = tokens[i]
            
            # Add implicit multiplication between:
            # NUMBER and VARIABLE/FUNCTION/LPAREN
            # RPAREN and NUMBER/VARIABLE/FUNCTION/LPAREN
            # VARIABLE and NUMBER/VARIABLE/FUNCTION/LPAREN
            should_add_mult = (
                (prev_token.type == 'NUMBER' and curr_token.type in ['VARIABLE', 'FUNCTION', 'LPAREN']) or
                (prev_token.type == 'RPAREN' and curr_token.type in ['NUMBER', 'VARIABLE', 'FUNCTION', 'LPAREN']) or
                (prev_token.type == 'VARIABLE' and curr_token.type in ['NUMBER', 'VARIABLE', 'FUNCTION', 'LPAREN'])
            )
            
            if should_add_mult:
                new_tokens.append(Token('OPERATOR', '*', curr_token.position))
            
            new_tokens.append(curr_token)
        
        return new_tokens
    
    def _shunting_yard(self, tokens: List[Token]) -> List[Token]:
        """Convert infix notation to postfix using Shunting Yard algorithm."""
        output_queue = []
        operator_stack = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == 'NUMBER':
                output_queue.append(token)
            
            elif token.type == 'VARIABLE':
                output_queue.append(token)
            
            elif token.type == 'FUNCTION':
                operator_stack.append(token)
            
            elif token.type == 'OPERATOR':
                # Handle unary operators
                if token.value in ['+', '-'] and (
                    i == 0 or tokens[i-1].type in ['OPERATOR', 'LPAREN', 'FUNCTION']
                ):
                    unary_token = Token('OPERATOR', 'UNARY' + token.value, token.position)
                    token = unary_token
                
                while (operator_stack and 
                       operator_stack[-1].type in ['OPERATOR', 'FUNCTION'] and
                       operator_stack[-1].type != 'LPAREN' and
                       (self.PRECEDENCE.get(operator_stack[-1].value, 0) > 
                        self.PRECEDENCE.get(token.value, 0) or
                        (self.PRECEDENCE.get(operator_stack[-1].value, 0) == 
                         self.PRECEDENCE.get(token.value, 0) and
                         token.value not in self.RIGHT_ASSOCIATIVE))):
                    output_queue.append(operator_stack.pop())
                
                operator_stack.append(token)
            
            elif token.type == 'LPAREN':
                operator_stack.append(token)
            
            elif token.type == 'RPAREN':
                while operator_stack and operator_stack[-1].type != 'LPAREN':
                    output_queue.append(operator_stack.pop())
                
                if not operator_stack:
                    raise ParseError("Mismatched parentheses")
                
                operator_stack.pop()  # Remove the left parenthesis
                
                # If there's a function on top of the stack, pop it
                if operator_stack and operator_stack[-1].type == 'FUNCTION':
                    output_queue.append(operator_stack.pop())
            
            i += 1
        
        while operator_stack:
            if operator_stack[-1].type in ['LPAREN', 'RPAREN']:
                raise ParseError("Mismatched parentheses")
            output_queue.append(operator_stack.pop())
        
        return output_queue
    
    def _evaluate_postfix(self, postfix_tokens: List[Token]) -> Union[int, float]:
        """Evaluate postfix expression and return result."""
        if not postfix_tokens:
            raise ParseError("Empty expression")
            
        stack = []
        
        for token in postfix_tokens:
            if token.type == 'NUMBER':
                stack.append(token.value)
            
            elif token.type == 'VARIABLE':
                try:
                    value = self.get_variable(token.value)
                    stack.append(value)
                except InvalidInputError as e:
                    raise ParseError(str(e))
            
            elif token.type == 'OPERATOR':
                if token.value in ['UNARY+', 'UNARY-']:
                    if not stack:
                        raise ParseError(f"Insufficient operands for {token.value}")
                    operand = stack.pop()
                    result = operand if token.value == 'UNARY+' else -operand
                    stack.append(result)
                else:
                    if len(stack) < 2:
                        raise ParseError(f"Insufficient operands for {token.value}")
                    
                    b = stack.pop()
                    a = stack.pop()
                    
                    try:
                        if token.value == '+':
                            result = self.calculator.add(a, b)
                        elif token.value == '-':
                            result = self.calculator.subtract(a, b)
                        elif token.value == '*':
                            result = self.calculator.multiply(a, b)
                        elif token.value == '/':
                            result = self.calculator.divide(a, b)
                        elif token.value == '%':
                            result = self.calculator.modulo(a, b)
                        elif token.value in ['^', '**']:
                            result = self.calculator.power(a, b)
                        else:
                            raise ParseError(f"Unknown operator: {token.value}")
                        
                        stack.append(result)
                    except CalculatorError as e:
                        raise ParseError(f"Calculation error: {e}")
            
            elif token.type == 'FUNCTION':
                if not stack:
                    raise ParseError(f"Function {token.value} requires an argument")
                
                arg = stack.pop()
                
                try:
                    if token.value in self.FUNCTIONS:
                        method_name = self.FUNCTIONS[token.value]
                        if hasattr(self.calculator, method_name):
                            method = getattr(self.calculator, method_name)
                            result = method(arg)
                        else:
                            # Handle built-in functions not in calculator
                            if token.value == 'abs':
                                result = abs(arg)
                            elif token.value == 'ceil':
                                result = math.ceil(arg)
                            elif token.value == 'floor':
                                result = math.floor(arg)
                            elif token.value == 'round':
                                result = round(arg)
                            else:
                                raise ParseError(f"Function {token.value} not implemented")
                        
                        stack.append(result)
                    else:
                        raise ParseError(f"Unknown function: {token.value}")
                except CalculatorError as e:
                    raise ParseError(f"Function error: {e}")
                except (TypeError, ValueError) as e:
                    raise ParseError(f"Invalid argument for {token.value}: {e}")
        
        if len(stack) != 1:
            raise ParseError("Invalid expression")
        
        return stack[0]
    
    def parse(self, expression: str) -> Union[int, float]:
        """
        Parse and evaluate a mathematical expression.
        
        Args:
            expression: The mathematical expression to parse
            
        Returns:
            The calculated result
            
        Raises:
            ParseError: If the expression is invalid
        """
        try:
            # Tokenize the expression
            tokens = self.tokenize(expression)
            
            if not tokens:
                raise ParseError("Empty expression")
            
            # Check for incomplete expressions (ending with operator)
            last_token = tokens[-1]
            if last_token.type == 'OPERATOR' and last_token.value not in ['UNARY+', 'UNARY-']:
                raise ParseError("Incomplete expression (ends with operator)")
            
            # Check for consecutive binary operators (like "2 + + 3")
            for i in range(len(tokens) - 1):
                curr = tokens[i]
                next_token = tokens[i + 1]
                
                # Check for binary operator followed by binary operator
                if (curr.type == 'OPERATOR' and curr.value not in ['UNARY+', 'UNARY-'] and
                    next_token.type == 'OPERATOR' and next_token.value not in ['UNARY+', 'UNARY-']):
                    raise ParseError("Invalid consecutive operators")
            
            # Convert to postfix notation
            postfix = self._shunting_yard(tokens)
            
            # Evaluate postfix expression
            result = self._evaluate_postfix(postfix)
            
            return result
            
        except Exception as e:
            if isinstance(e, ParseError):
                raise
            else:
                raise ParseError(f"Parsing error: {e}")
    
    def validate_expression(self, expression: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an expression without evaluating it.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Tokenize the expression
            tokens = self.tokenize(expression)
            
            if not tokens:
                return False, "Empty expression"
            
            # Check for incomplete expressions (ending with operator)
            last_token = tokens[-1]
            if last_token.type == 'OPERATOR' and last_token.value not in ['UNARY+', 'UNARY-']:
                return False, "Incomplete expression (ends with operator)"
            
            # Check for consecutive binary operators (like "2 + + 3")
            for i in range(len(tokens) - 1):
                curr = tokens[i]
                next_token = tokens[i + 1]
                
                # Check for binary operator followed by binary operator
                if (curr.type == 'OPERATOR' and curr.value not in ['UNARY+', 'UNARY-'] and
                    next_token.type == 'OPERATOR' and next_token.value not in ['UNARY+', 'UNARY-']):
                    return False, "Invalid consecutive operators"
            
            # Try to convert to postfix (this will catch parentheses mismatches)
            self._shunting_yard(tokens)
            
            return True, None
        except Exception as e:
            return False, str(e)


if __name__ == "__main__":
    # Simple test of the expression parser
    calc = Calculator()
    parser = ExpressionParser(calc)
    
    # Set some variables
    parser.set_variable('x', 5)
    parser.set_variable('y', 3)
    
    test_expressions = [
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "2pi",
        "sin(pi/2)",
        "sqrt(x^2 + y^2)",
        "2x + 3y",
        "factorial(5)",
        "log(e^2)"
    ]
    
    print("Expression Parser Test:")
    for expr in test_expressions:
        try:
            result = parser.parse(expr)
            print(f"{expr} = {result}")
        except Exception as e:
            print(f"{expr} -> Error: {e}")