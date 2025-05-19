"""
Color definitions and styling utilities for the TUI.
Uses ANSI escape codes for terminal coloring.
"""

from typing import Dict, Optional

class TUITheme:
    """Centralized theme colors for the TUI."""
    
    # Basic ANSI colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Theme-specific colors
    PRIMARY = BRIGHT_CYAN
    SECONDARY = BRIGHT_BLUE
    SUCCESS = BRIGHT_GREEN
    WARNING = BRIGHT_YELLOW
    ERROR = BRIGHT_RED
    INFO = BRIGHT_WHITE
    
    # Component-specific colors
    HEADER = BRIGHT_MAGENTA
    BORDER = BLUE
    MENU_SELECTED = BG_BLUE + BRIGHT_WHITE
    MENU_NORMAL = WHITE
    TASK_RUNNING = GREEN
    TASK_STOPPED = YELLOW
    TASK_ERROR = RED
    AGENT_ACTIVE = BRIGHT_GREEN
    AGENT_INACTIVE = DIM + WHITE
    
    @staticmethod
    def colorize(text: str, color: str, bg_color: Optional[str] = None) -> str:
        """Apply color to text with optional background color."""
        colors = color
        if bg_color:
            colors += bg_color
        return f"{colors}{text}{TUITheme.RESET}"
    
    @staticmethod
    def bold(text: str) -> str:
        """Make text bold."""
        return f"{TUITheme.BOLD}{text}{TUITheme.RESET}"
    
    @staticmethod
    def dim(text: str) -> str:
        """Make text dim/faded."""
        return f"{TUITheme.DIM}{text}{TUITheme.RESET}"
    
    @staticmethod
    def underline(text: str) -> str:
        """Underline text."""
        return f"{TUITheme.UNDERLINE}{text}{TUITheme.RESET}"
    
    @staticmethod
    def header(text: str) -> str:
        """Format text as a header."""
        return TUITheme.colorize(TUITheme.bold(text), TUITheme.HEADER)
    
    @staticmethod
    def error(text: str) -> str:
        """Format text as an error message."""
        return TUITheme.colorize(text, TUITheme.ERROR)
    
    @staticmethod
    def success(text: str) -> str:
        """Format text as a success message."""
        return TUITheme.colorize(text, TUITheme.SUCCESS)
    
    @staticmethod
    def warning(text: str) -> str:
        """Format text as a warning message."""
        return TUITheme.colorize(text, TUITheme.WARNING)
    
    @staticmethod
    def info(text: str) -> str:
        """Format text as an info message."""
        return TUITheme.colorize(text, TUITheme.INFO)


# ASCII art for the logo
AGENT_MCP_LOGO = r"""
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ███╗   ███╗ ██████╗██████╗ 
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██╔████╔██║██║     ██████╔╝
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██║╚██╔╝██║██║     ██╔═══╝ 
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║ ╚═╝ ██║╚██████╗██║     
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝     
"""

# Status indicators (Unicode symbols)
STATUS_SYMBOLS = {
    'running': '●',     # Filled circle
    'stopped': '○',     # Empty circle
    'error': '✖',       # X mark
    'success': '✓',     # Check mark
    'warning': '⚠',     # Warning triangle
    'loading': '↻',     # Refresh symbol
    'paused': '‖',      # Pause symbol
    'arrow_right': '→', # Right arrow
    'arrow_down': '↓',  # Down arrow
    'arrow_up': '↑',    # Up arrow
}