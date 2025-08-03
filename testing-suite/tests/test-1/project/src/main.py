"""
Super Complex Calculator - Main CLI Interface

This is the main command-line interface for the Super Complex Calculator.
It integrates all calculator functionality and provides an interactive user experience.
"""

import sys
import os
import traceback
from typing import Optional, Dict, Any, List, Union
import readline  # For better command line editing
import atexit

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculator import Calculator, CalculatorError
from expression_parser import ExpressionParser, ParseError
from memory_manager import MemoryManager, MemoryError
from history_manager import HistoryManager, HistoryError
from unit_converter import UnitConverter, ConversionError


class CalculatorCLI:
    """
    Command-line interface for the Super Complex Calculator.
    
    Features:
    - Interactive calculator with expression parsing
    - Memory management (M1, M2, etc.)
    - Calculation history with search and export
    - Unit conversions
    - Variable support
    - Help system and command completion
    - Persistent state (history and memory)
    """
    
    def __init__(self):
        """Initialize the calculator CLI."""
        self.calculator = Calculator()
        self.parser = ExpressionParser(self.calculator)
        self.memory = MemoryManager()
        self.history = HistoryManager(auto_save=True)
        self.converter = UnitConverter()
        
        self.running = True
        self.debug_mode = False
        self.precision = 10
        
        # Setup readline for command history
        self.setup_readline()
        
        # Load persistent state
        self.load_state()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def setup_readline(self) -> None:
        """Setup readline for better command line experience."""
        try:
            # Enable tab completion
            readline.set_completer(self.complete_command)
            readline.parse_and_bind("tab: complete")
            
            # Load command history
            histfile = os.path.expanduser("~/.calculator_history")
            try:
                readline.read_history_file(histfile)
            except FileNotFoundError:
                pass
            
            # Save history on exit
            atexit.register(readline.write_history_file, histfile)
            
        except ImportError:
            # readline not available
            pass
    
    def complete_command(self, text: str, state: int) -> Optional[str]:
        """Command completion for readline."""
        commands = [
            'help', 'quit', 'exit', 'clear', 'history', 'memory', 'convert',
            'vars', 'precision', 'debug', 'save', 'load', 'export', 'stats',
            'mem_clear', 'mem_list', 'hist_clear', 'hist_search'
        ]
        
        # Add memory slots
        commands.extend([f"M{i}" for i in range(1, 11)])
        
        # Add mathematical functions
        functions = [
            'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 
            'log', 'ln', 'log10', 'exp', 'sqrt', 'factorial',
            'abs', 'ceil', 'floor', 'round'
        ]
        commands.extend(functions)
        
        # Add constants
        constants = ['pi', 'e', 'tau']
        commands.extend(constants)
        
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        try:
            return matches[state]
        except IndexError:
            return None
    
    def load_state(self) -> None:
        """Load persistent state (history and memory)."""
        try:
            # Load history
            if os.path.exists("calculator_history.json"):
                self.history.load_from_file("calculator_history.json")
            
            # Load memory
            if os.path.exists("calculator_memory.json"):
                self.memory.load_from_file("calculator_memory.json")
        except Exception:
            pass  # Silent fail for state loading
    
    def save_state(self) -> None:
        """Save current state (history and memory)."""
        try:
            self.history.save_to_file("calculator_history.json")
            self.memory.save_to_file("calculator_memory.json")
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def cleanup(self) -> None:
        """Cleanup on exit."""
        self.save_state()
    
    def print_welcome(self) -> None:
        """Print welcome message."""
        print("=" * 60)
        print("🧮 Super Complex Calculator")
        print("=" * 60)
        print("Features:")
        print("  • Advanced mathematical expressions")
        print("  • Memory slots (M1, M2, etc.)")
        print("  • Calculation history")
        print("  • Unit conversions")
        print("  • Variables and constants")
        print("  • Scientific and statistical functions")
        print()
        print("Type 'help' for commands or start calculating!")
        print("Examples: '2+3*4', 'sin(pi/2)', 'convert 100 cm to m'")
        print("=" * 60)
    
    def print_help(self) -> None:
        """Print help information."""
        help_text = """
CALCULATOR COMMANDS:
==================

BASIC USAGE:
  <expression>              Calculate mathematical expression
  2 + 3 * 4                Example: basic arithmetic
  sin(pi/2)                Example: trigonometric function
  sqrt(x^2 + y^2)          Example: using variables
  2pi                      Example: implicit multiplication

MEMORY OPERATIONS:
  M1 = <value>             Store value in memory slot M1
  M1                       Recall value from memory slot M1
  M1 + <value>             Add value to memory slot M1
  M1 - <value>             Subtract value from memory slot M1
  mem_clear M1             Clear memory slot M1
  mem_clear ALL            Clear all memory slots
  mem_list                 List all memory slots

HISTORY OPERATIONS:
  history                  Show calculation history
  history 10               Show last 10 calculations
  hist_clear               Clear all history
  hist_search <term>       Search history for term
  H0, H1, H2               Use result from history (H0 = most recent)

VARIABLE OPERATIONS:
  x = 5                    Set variable x to 5
  y = sin(pi/4)           Set variable y to calculated value
  vars                     List all variables
  vars clear               Clear all variables

UNIT CONVERSIONS:
  convert 100 cm to m      Convert 100 centimeters to meters
  convert 32 f to c        Convert 32 Fahrenheit to Celsius
  convert 1 kg to lb       Convert 1 kilogram to pounds

FUNCTIONS:
  Mathematical: sin, cos, tan, asin, acos, atan
  Logarithmic: log, ln, log10, exp
  Other: sqrt, abs, factorial, ceil, floor, round
  Statistical: mean, median, mode, stdev, variance (for lists)

CONSTANTS:
  pi, e, tau, inf, nan

SYSTEM COMMANDS:
  help                     Show this help
  precision <n>            Set display precision to n decimal places
  debug [on/off]           Toggle debug mode
  clear                    Clear screen
  stats                    Show calculator statistics
  save <file>              Save history to file
  load <file>              Load history from file
  export <file>            Export history to text file
  quit, exit               Exit calculator

OPERATORS:
  +, -, *, /, %            Basic arithmetic
  ^, **                    Exponentiation
  ()                       Parentheses for grouping

EXAMPLES:
  sin(pi/4) * cos(pi/4)    Trigonometric calculation
  factorial(5) + 3!        Factorial operations  
  log(e^2)                 Logarithmic operations
  M1 = sqrt(16)            Store result in memory
  x = 5; y = 3; x^2 + y^2  Use variables
  convert 1 mile to km     Unit conversion
"""
        print(help_text)
    
    def handle_command(self, input_line: str) -> bool:
        """
        Handle a command input.
        
        Returns:
            True to continue, False to quit
        """
        line = input_line.strip()
        if not line:
            return True
        
        # Handle system commands
        if line.lower() in ['quit', 'exit', 'q']:
            return False
        elif line.lower() in ['help', '?']:
            self.print_help()
            return True
        elif line.lower() == 'clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            return True
        elif line.lower().startswith('precision'):
            self.handle_precision_command(line)
            return True
        elif line.lower().startswith('debug'):
            self.handle_debug_command(line)
            return True
        elif line.lower().startswith('history'):
            self.handle_history_command(line)
            return True
        elif line.lower() == 'vars':
            self.show_variables()
            return True
        elif line.lower() == 'vars clear':
            self.parser.clear_variables()
            print("All variables cleared.")
            return True
        elif line.lower() == 'mem_list':
            self.show_memory()
            return True
        elif line.lower().startswith('mem_clear'):
            self.handle_memory_clear(line)
            return True
        elif line.lower() == 'hist_clear':
            count = self.history.clear_history()
            print(f"Cleared {count} history entries.")
            return True
        elif line.lower().startswith('hist_search'):
            self.handle_history_search(line)
            return True
        elif line.lower().startswith('convert'):
            self.handle_conversion(line)
            return True
        elif line.lower() == 'stats':
            self.show_statistics()
            return True
        elif line.lower().startswith('save'):
            self.handle_save_command(line)
            return True
        elif line.lower().startswith('load'):
            self.handle_load_command(line)
            return True
        elif line.lower().startswith('export'):
            self.handle_export_command(line)
            return True
        
        # Handle calculations
        try:
            self.handle_calculation(line)
        except Exception as e:
            if self.debug_mode:
                print(f"Error: {e}")
                traceback.print_exc()
            else:
                print(f"Error: {e}")
        
        return True
    
    def handle_calculation(self, expression: str) -> None:
        """Handle a calculation expression."""
        original_expression = expression
        
        # Handle variable assignments
        if '=' in expression and not any(op in expression for op in ['==', '<=', '>=', '!=']):
            parts = expression.split('=', 1)
            if len(parts) == 2:
                var_name = parts[0].strip()
                var_expression = parts[1].strip()
                
                # Check if it's a memory operation (e.g., M1 = 5)
                if var_name.upper().startswith('M') and var_name[1:].isdigit():
                    if var_expression:
                        # Evaluate the expression first
                        result = self.parser.parse(var_expression)
                        self.memory.store(result, var_name)
                        print(f"{var_name} = {self.format_result(result)}")
                    else:
                        # Just recall the memory
                        result = self.memory.recall(var_name)
                        print(f"{var_name} = {self.format_result(result)}")
                    return
                
                # Regular variable assignment
                if var_expression:
                    result = self.parser.parse(var_expression)
                    self.parser.set_variable(var_name, result)
                    print(f"{var_name} = {self.format_result(result)}")
                    
                    # Add to history
                    self.history.add_calculation(original_expression, result, 
                                               self.parser.variables.copy())
                return
        
        # Handle memory recall (e.g., M1, M2)
        if expression.upper().startswith('M') and expression[1:].isdigit() and '=' not in expression:
            try:
                result = self.memory.recall(expression)
                print(f"{expression} = {self.format_result(result)}")
                return
            except MemoryError as e:
                print(f"Memory error: {e}")
                return
        
        # Handle memory operations (e.g., M1 + 5, M2 - 3)
        memory_ops = ['+', '-']
        for op in memory_ops:
            if op in expression:
                parts = expression.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    if left.upper().startswith('M') and left[1:].isdigit():
                        try:
                            value = self.parser.parse(right)
                            if op == '+':
                                result = self.memory.add(value, left)
                            else:  # op == '-'
                                result = self.memory.subtract(value, left)
                            
                            print(f"{left} = {self.format_result(result)} (after {op}{value})")
                            return
                        except (MemoryError, ParseError) as e:
                            print(f"Error: {e}")
                            return
        
        # Handle history references (H0, H1, H2, etc.)
        if expression.upper().startswith('H') and expression[1:].isdigit():
            try:
                index = int(expression[1:])
                result = self.history.get_result_by_index(index)
                print(f"{expression} = {self.format_result(result)}")
                return
            except (ValueError, HistoryError) as e:
                print(f"History error: {e}")
                return
        
        # Load memory values as variables
        memory_vars = self.memory.export_slots_to_dict()
        for name, value in memory_vars.items():
            self.parser.set_variable(name, value)
        
        # Regular expression evaluation
        result = self.parser.parse(expression)
        formatted_result = self.format_result(result)
        print(f"{formatted_result}")
        
        # Add to history
        variables_used = {k: v for k, v in self.parser.variables.items() 
                         if k in expression.lower()}
        self.history.add_calculation(original_expression, result, variables_used)
    
    def format_result(self, result: Union[int, float]) -> str:
        """Format a result for display."""
        return self.calculator.format_result(result)
    
    def handle_precision_command(self, line: str) -> None:
        """Handle precision setting command."""
        parts = line.split()
        if len(parts) == 2:
            try:
                precision = int(parts[1])
                if 0 <= precision <= 20:
                    self.precision = precision
                    self.calculator.set_precision(precision)
                    print(f"Display precision set to {precision} decimal places.")
                else:
                    print("Precision must be between 0 and 20.")
            except ValueError:
                print("Invalid precision value. Use: precision <number>")
        else:
            print(f"Current precision: {self.precision}")
    
    def handle_debug_command(self, line: str) -> None:
        """Handle debug mode command."""
        parts = line.split()
        if len(parts) == 2:
            if parts[1].lower() in ['on', 'true', '1']:
                self.debug_mode = True
                print("Debug mode enabled.")
            elif parts[1].lower() in ['off', 'false', '0']:
                self.debug_mode = False
                print("Debug mode disabled.")
            else:
                print("Use: debug on/off")
        else:
            self.debug_mode = not self.debug_mode
            print(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}.")
    
    def handle_history_command(self, line: str) -> None:
        """Handle history display command."""
        parts = line.split()
        limit = 10  # Default limit
        
        if len(parts) == 2:
            try:
                limit = int(parts[1])
            except ValueError:
                print("Invalid limit. Use: history <number>")
                return
        
        display = self.history.get_history_display(limit=limit, include_id=True)
        print("\nCalculation History:")
        print("-" * 40)
        for line in display:
            print(line)
    
    def handle_history_search(self, line: str) -> None:
        """Handle history search command."""
        parts = line.split(None, 1)
        if len(parts) < 2:
            print("Use: hist_search <search_term>")
            return
        
        search_term = parts[1]
        matches = self.history.search_by_expression(search_term)
        
        if matches:
            print(f"\nFound {len(matches)} matches for '{search_term}':")
            print("-" * 40)
            for i, match in enumerate(matches):
                print(f"{i+1:2d}. {match}")
        else:
            print(f"No matches found for '{search_term}'.")
    
    def handle_memory_clear(self, line: str) -> None:
        """Handle memory clear command."""
        parts = line.split()
        if len(parts) == 2:
            slot_name = parts[1]
            try:
                self.memory.clear(slot_name)
                print(f"Memory slot {slot_name} cleared.")
            except MemoryError as e:
                print(f"Memory error: {e}")
        else:
            print("Use: mem_clear <slot_name> or mem_clear ALL")
    
    def handle_conversion(self, line: str) -> None:
        """Handle unit conversion command."""
        # Parse: convert <value> <from_unit> to <to_unit>
        parts = line.split()
        if len(parts) != 5 or parts[3].lower() != 'to':
            print("Use: convert <value> <from_unit> to <to_unit>")
            print("Example: convert 100 cm to m")
            return
        
        try:
            value = float(parts[1])
            from_unit = parts[2]
            to_unit = parts[4]
            
            result = self.converter.convert(value, from_unit, to_unit)
            print(f"{value} {from_unit} = {self.format_result(result)} {to_unit}")
            
            # Add to history
            expression = f"convert {value} {from_unit} to {to_unit}"
            self.history.add_calculation(expression, result)
            
        except (ValueError, ConversionError) as e:
            print(f"Conversion error: {e}")
    
    def show_variables(self) -> None:
        """Show all defined variables."""
        if self.parser.variables:
            print("\nDefined Variables:")
            print("-" * 20)
            for name, value in sorted(self.parser.variables.items()):
                print(f"{name} = {self.format_result(value)}")
        else:
            print("No variables defined.")
    
    def show_memory(self) -> None:
        """Show all memory slots."""
        memory_info = self.memory.get_memory_info()
        if memory_info['slots']:
            print("\nMemory Slots:")
            print("-" * 20)
            for slot, value in sorted(memory_info['slots'].items()):
                active = " (active)" if slot == memory_info['active_slot'] else ""
                print(f"{slot} = {self.format_result(value)}{active}")
        else:
            print("No values in memory.")
    
    def show_statistics(self) -> None:
        """Show calculator statistics."""
        hist_stats = self.history.get_statistics()
        memory_info = self.memory.get_memory_info()
        
        print("\nCalculator Statistics:")
        print("=" * 30)
        print(f"Total calculations: {hist_stats['total_calculations']}")
        print(f"Memory slots used: {memory_info['occupied_slots']}")
        print(f"Variables defined: {len(self.parser.variables)}")
        print(f"Display precision: {self.precision}")
        
        if hist_stats['most_common_operations']:
            print("\nMost used operations:")
            for op, count in hist_stats['most_common_operations'][:5]:
                print(f"  {op}: {count}")
        
        if hist_stats['total_calculations'] > 0:
            print(f"\nResult statistics:")
            print(f"  Average: {self.format_result(hist_stats['average_result'])}")
            print(f"  Range: {self.format_result(hist_stats['result_range'][0])} to {self.format_result(hist_stats['result_range'][1])}")
    
    def handle_save_command(self, line: str) -> None:
        """Handle save command."""
        parts = line.split(None, 1)
        if len(parts) < 2:
            filename = "calculator_backup.json"
        else:
            filename = parts[1]
        
        try:
            self.history.save_to_file(filename)
            print(f"History saved to {filename}")
        except HistoryError as e:
            print(f"Save error: {e}")
    
    def handle_load_command(self, line: str) -> None:
        """Handle load command."""
        parts = line.split(None, 1)
        if len(parts) < 2:
            print("Use: load <filename>")
            return
        
        filename = parts[1]
        try:
            count = self.history.load_from_file(filename, merge=True)
            print(f"Loaded {count} history entries from {filename}")
        except HistoryError as e:
            print(f"Load error: {e}")
    
    def handle_export_command(self, line: str) -> None:
        """Handle export command."""
        parts = line.split(None, 1)
        if len(parts) < 2:
            filename = "calculator_export.txt"
        else:
            filename = parts[1]
        
        try:
            self.history.export_to_text(filename)
            print(f"History exported to {filename}")
        except HistoryError as e:
            print(f"Export error: {e}")
    
    def run(self) -> None:
        """Run the calculator CLI."""
        self.print_welcome()
        
        while self.running:
            try:
                line = input("calc> ")
                self.running = self.handle_command(line)
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            except Exception as e:
                if self.debug_mode:
                    print(f"Unexpected error: {e}")
                    traceback.print_exc()
                else:
                    print(f"Error: {e}")
        
        print("Thanks for using Super Complex Calculator!")


def main():
    """Main entry point."""
    cli = CalculatorCLI()
    cli.run()


if __name__ == "__main__":
    main()