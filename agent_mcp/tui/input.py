"""
Keyboard input handling for the terminal UI.
Provides utilities for capturing key presses including arrow keys.
"""

import sys
import time
from typing import Optional, Tuple
from enum import Enum

# For Windows compatibility
try:
    import msvcrt
except ImportError:
    msvcrt = None

# For Unix/Linux specific terminal control
if sys.platform != 'win32':
    import termios
    import tty
else:
    termios = None
    tty = None


class Key(Enum):
    """Enumeration of special keys."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESCAPE = "escape"
    BACKSPACE = "backspace"
    TAB = "tab"
    SPACE = "space"
    HOME = "home"
    END = "end"
    DELETE = "delete"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"


# ANSI escape sequences for special keys (Unix/Linux)
ANSI_KEY_SEQUENCES = {
    "\x1b[A": Key.UP,
    "\x1b[B": Key.DOWN,
    "\x1b[C": Key.RIGHT,
    "\x1b[D": Key.LEFT,
    "\r": Key.ENTER,
    "\n": Key.ENTER,
    "\x1b": Key.ESCAPE,
    "\x7f": Key.BACKSPACE,
    "\x08": Key.BACKSPACE,
    "\t": Key.TAB,
    " ": Key.SPACE,
    "\x1b[H": Key.HOME,
    "\x1b[F": Key.END,
    "\x1b[3~": Key.DELETE,
    "\x1b[5~": Key.PAGE_UP,
    "\x1b[6~": Key.PAGE_DOWN,
    # Additional sequences for different terminals
    "\x1bOA": Key.UP,
    "\x1bOB": Key.DOWN,
    "\x1bOC": Key.RIGHT,
    "\x1bOD": Key.LEFT,
    "\x1b[1~": Key.HOME,
    "\x1b[4~": Key.END,
}


def get_key_unix() -> Tuple[Optional[Key], Optional[str]]:
    """
    Get a single keypress on Unix/Linux systems.
    Returns tuple of (special_key, character).
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        key = sys.stdin.read(1)
        
        # Check for escape sequences
        if key == '\x1b':
            key += sys.stdin.read(2)
            timeout = 0.1  # 100ms timeout for additional chars
            start_time = time.time()
            
            # Read any additional characters (for longer sequences)
            while time.time() - start_time < timeout:
                if sys.stdin.isatty():
                    ready = sys.stdin.readable()
                    if ready:
                        key += sys.stdin.read(1)
                    else:
                        break
                else:
                    break
        
        # Check if this is a known special key
        if key in ANSI_KEY_SEQUENCES:
            return (ANSI_KEY_SEQUENCES[key], None)
        elif len(key) == 1:
            return (None, key)
        else:
            # Unknown escape sequence
            return (None, None)
            
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_key_windows() -> Tuple[Optional[Key], Optional[str]]:
    """
    Get a single keypress on Windows systems.
    Returns tuple of (special_key, character).
    """
    if msvcrt is None:
        raise NotImplementedError("Windows keyboard input requires msvcrt module")
    
    key = msvcrt.getch()
    
    # Handle function keys and special characters
    if key in [b'\xe0', b'\000']:
        key = msvcrt.getch()
        key_code = ord(key)
        
        windows_key_map = {
            72: Key.UP,
            80: Key.DOWN,
            75: Key.LEFT,
            77: Key.RIGHT,
            71: Key.HOME,
            79: Key.END,
            83: Key.DELETE,
            73: Key.PAGE_UP,
            81: Key.PAGE_DOWN,
        }
        
        if key_code in windows_key_map:
            return (windows_key_map[key_code], None)
    
    # Handle regular keys
    key_code = ord(key)
    
    if key_code == 13:  # Enter
        return (Key.ENTER, None)
    elif key_code == 27:  # Escape
        return (Key.ESCAPE, None)
    elif key_code == 8:  # Backspace
        return (Key.BACKSPACE, None)
    elif key_code == 9:  # Tab
        return (Key.TAB, None)
    elif key_code == 32:  # Space
        return (Key.SPACE, None)
    else:
        return (None, chr(key_code))


def get_key() -> Tuple[Optional[Key], Optional[str]]:
    """
    Cross-platform function to get a single keypress.
    Returns tuple of (special_key, character).
    """
    if sys.platform.startswith('win'):
        return get_key_windows()
    else:
        return get_key_unix()


class InputHandler:
    """Handles keyboard input for the TUI."""
    
    def __init__(self):
        self.buffer = ""
        self.cursor_position = 0
        self.history = []
        self.history_position = -1
    
    def read_key(self) -> Tuple[Optional[Key], Optional[str]]:
        """Read a single key from the user."""
        return get_key()
    
    def process_input(self, special_key: Optional[Key], char: Optional[str]) -> Optional[str]:
        """
        Process a key input and update internal state.
        Returns completed input string when Enter is pressed, None otherwise.
        """
        if special_key == Key.ENTER:
            result = self.buffer
            if result.strip():  # Only add non-empty commands to history
                self.history.append(result)
            self.buffer = ""
            self.cursor_position = 0
            self.history_position = -1
            return result
        
        elif special_key == Key.BACKSPACE:
            if self.cursor_position > 0:
                self.buffer = (self.buffer[:self.cursor_position-1] + 
                              self.buffer[self.cursor_position:])
                self.cursor_position -= 1
        
        elif special_key == Key.DELETE:
            if self.cursor_position < len(self.buffer):
                self.buffer = (self.buffer[:self.cursor_position] + 
                              self.buffer[self.cursor_position+1:])
        
        elif special_key == Key.LEFT:
            if self.cursor_position > 0:
                self.cursor_position -= 1
        
        elif special_key == Key.RIGHT:
            if self.cursor_position < len(self.buffer):
                self.cursor_position += 1
        
        elif special_key == Key.HOME:
            self.cursor_position = 0
        
        elif special_key == Key.END:
            self.cursor_position = len(self.buffer)
        
        elif special_key == Key.UP:
            # Navigate history backwards
            if self.history and self.history_position < len(self.history) - 1:
                self.history_position += 1
                self.buffer = self.history[-(self.history_position + 1)]
                self.cursor_position = len(self.buffer)
        
        elif special_key == Key.DOWN:
            # Navigate history forwards
            if self.history_position > -1:
                self.history_position -= 1
                if self.history_position == -1:
                    self.buffer = ""
                else:
                    self.buffer = self.history[-(self.history_position + 1)]
                self.cursor_position = len(self.buffer)
        
        elif char is not None and char.isprintable():
            # Insert regular character at cursor position
            self.buffer = (self.buffer[:self.cursor_position] + char + 
                          self.buffer[self.cursor_position:])
            self.cursor_position += 1
        
        return None
    
    def get_buffer_display(self) -> str:
        """Get the current buffer with cursor visualization."""
        if self.cursor_position == len(self.buffer):
            # Cursor at end
            return self.buffer + "█"
        else:
            # Cursor in middle
            return (self.buffer[:self.cursor_position] + "█" + 
                   self.buffer[self.cursor_position:])
    
    def get_buffer(self) -> str:
        """Get the current buffer content."""
        return self.buffer
    
    def clear_buffer(self):
        """Clear the input buffer."""
        self.buffer = ""
        self.cursor_position = 0
    
    def set_buffer(self, text: str):
        """Set the buffer content."""
        self.buffer = text
        self.cursor_position = len(text)


# Utility functions for non-blocking input checking
def kbhit_unix() -> bool:
    """Check if a key has been pressed (Unix/Linux)."""
    import select
    return select.select([sys.stdin], [], [], 0.0)[0] != []


def kbhit_windows() -> bool:
    """Check if a key has been pressed (Windows)."""
    if msvcrt is None:
        return False
    return msvcrt.kbhit()


def kbhit() -> bool:
    """Cross-platform check if a key has been pressed."""
    if sys.platform.startswith('win'):
        return kbhit_windows()
    else:
        return kbhit_unix()


# Example usage and testing
if __name__ == "__main__":
    print("Testing keyboard input. Press various keys (Ctrl+C to exit):")
    print("Special keys: Arrow keys, Enter, Escape, Backspace, etc.")
    print()
    
    handler = InputHandler()
    
    try:
        while True:
            special_key, char = get_key()
            
            if special_key:
                print(f"Special key: {special_key.value}")
            elif char:
                print(f"Character: '{char}' (ASCII: {ord(char)})")
            
            # Test input handler
            result = handler.process_input(special_key, char)
            if result is not None:
                print(f"Completed input: '{result}'")
                print(f"Buffer display: {handler.get_buffer_display()}")
            else:
                print(f"Buffer: '{handler.get_buffer_display()}'")
            
            print()
    except KeyboardInterrupt:
        print("\nExiting...")