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
    
    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """Create RGB color ANSI code."""
        return f'\033[38;2;{r};{g};{b}m'
    
    @staticmethod
    def gradient_text(text: str, start_color: tuple, end_color: tuple) -> str:
        """Apply gradient color to text."""
        if len(text) <= 1:
            return TUITheme.colorize(text, TUITheme.rgb(*start_color))
        
        result = ""
        for i, char in enumerate(text):
            if char in [' ', '\n']:
                result += char
                continue
                
            # Calculate gradient position (0.0 to 1.0)
            progress = i / (len(text) - 1) if len(text) > 1 else 0
            
            # Interpolate RGB values
            r = int(start_color[0] + (end_color[0] - start_color[0]) * progress)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * progress)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * progress)
            
            result += TUITheme.rgb(r, g, b) + char
        
        return result + TUITheme.RESET


# ASCII art variants for different terminal widths

# Full banner (requires ~77 chars width)
AGENT_MCP_FULL_LOGO = [
    " █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ███╗   ███╗ ██████╗██████╗ ",
    "██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗",
    "███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██╔████╔██║██║     ██████╔╝",
    "██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██║╚██╔╝██║██║     ██╔═══╝ ",
    "██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║ ╚═╝ ██║╚██████╗██║     ",
    "╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝     "
]

# Split banner - AGENT on top, MCP below (requires ~38 chars each)
AGENT_LOGO = [
    " █████╗  ██████╗ ███████╗███╗   ██╗████████╗",
    "██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝",
    "███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ",
    "██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ",
    "██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ",
    "╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   "
]

MCP_LOGO = [
    "███╗   ███╗ ██████╗██████╗ ",
    "████╗ ████║██╔════╝██╔══██╗",
    "██╔████╔██║██║     ██████╔╝",
    "██║╚██╔╝██║██║     ██╔═══╝ ",
    "██║ ╚═╝ ██║╚██████╗██║     ",
    "╚═╝     ╚═╝ ╚═════╝╚═╝     "
]

# Compact banner (requires ~32 chars width)
AGENT_MCP_COMPACT = [
    "█████╗  ███████╗ ██████╗ ███╗   ██╗████████╗",
    "██╔══██╗██╔════╝ ██╔════╝ ████╗  ██║╚══██╔══╝",
    "███████║██║  ███╗██║      ██╔██╗ ██║   ██║   ",
    "██╔══██║██║   ██║██║   ██╗██║╚██╗██║   ██║   ",
    "██║  ██║╚██████╔╝╚██████╔╝██║ ╚████║   ██║   ",
    "╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ",
    "",
    "███╗   ███╗ ██████╗██████╗ ",
    "████╗ ████║██╔════╝██╔══██╗",
    "██╔████╔██║██║     ██████╔╝",
    "██║╚██╔╝██║██║     ██╔═══╝ ",
    "██║ ╚═╝ ██║╚██████╗██║     ",
    "╚═╝     ╚═╝ ╚═════╝╚═╝     "
]

# Mini banner (requires ~20 chars width)
AGENT_MCP_MINI = [
    "█████╗  ██████╗ ███████╗",
    "██╔══██╗██╔════╝ ██╔════╝",
    "███████║██║  ███╗█████╗  ",
    "██╔══██║██║   ██║██╔══╝  ",
    "██║  ██║╚██████╔╝███████╗",
    "╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
    "",
    "███╗   ███╗ ██████╗██████╗ ",
    "████╗ ████║██╔════╝██╔══██╗",
    "██╔████╔██║██║     ██████╔╝",
    "██║╚██╔╝██║██║     ██╔═══╝ ",
    "██║ ╚═╝ ██║╚██████╗██║     ",
    "╚═╝     ╚═╝ ╚═════╝╚═╝     "
]

# Tiny banner (requires ~12 chars width)
AGENT_MCP_TINY = [
    "█████╗  ██████╗ ",
    "██╔══██╗██╔════╝",
    "███████║██║  ███╗",
    "██╔══██║██║   ██║",
    "██║  ██║╚██████╔╝",
    "╚═╝  ╚═╝ ╚═════╝ ",
    "",
    "███╗   ███╗ ██████╗",
    "████╗ ████║██╔════╝",
    "██╔████╔██║██║     ",
    "██║╚██╔╝██║██║     ",
    "██║ ╚═╝ ██║╚██████╗",
    "╚═╝     ╚═╝ ╚═════╝"
]

# Ultra-minimal banner (requires ~8 chars width)  
AGENT_MCP_MICRO = [
    "███╗ ██████╗ ",
    "████╗██╔════╝",
    "██╔████║███╗ ",
    "██║╚██╔██╔══╝",
    "██║ ╚═╝██████╗",
    "╚═╝    ╚═════╝",
    "",
    "█╗   █╗ ██████╗",
    "██╗ ██║██╔════╝",
    "█████╔╝██║     ",
    "██╔██╗ ██║     ",
    "██║╚██╗╚██████╗",
    "╚═╝ ╚═╝ ╚═════╝"
]

# Text-only fallback for very small terminals
AGENT_MCP_TEXT = [
    "╭─────────────╮",
    "│ AGENT  MCP  │", 
    "╰─────────────╯"
]

# Legacy compatibility
AGENT_MCP_LOGO_LINES = AGENT_MCP_FULL_LOGO

# Color definitions for gradient (pink to cyan like your image)
GRADIENT_COLORS = {
    'pink_start': (255, 182, 255),    # Light pink
    'purple_mid': (182, 144, 255),    # Purple
    'blue_mid': (144, 182, 255),      # Light blue  
    'cyan_end': (144, 255, 255)       # Cyan
}

def get_responsive_agent_mcp_banner(terminal_width: int = None) -> str:
    """Generate the AGENT MCP banner with intelligent responsive sizing."""
    import shutil
    
    # Get terminal width if not provided
    if terminal_width is None:
        terminal_width = shutil.get_terminal_size().columns
    
    # Select appropriate banner variant based on terminal width
    if terminal_width >= 80:
        # Full banner for wide terminals
        logo_lines = AGENT_MCP_FULL_LOGO
    elif terminal_width >= 50:
        # Split banner - AGENT on top, MCP below for medium terminals
        logo_lines = AGENT_LOGO + [""] + MCP_LOGO  # Add spacing between
    elif terminal_width >= 35:
        # Compact banner for smaller terminals
        logo_lines = AGENT_MCP_COMPACT
    elif terminal_width >= 25:
        # Mini banner for very small terminals
        logo_lines = AGENT_MCP_MINI
    elif terminal_width >= 18:
        # Tiny banner for ultra-small terminals
        logo_lines = AGENT_MCP_TINY
    elif terminal_width >= 15:
        # Micro banner for extremely small terminals
        logo_lines = AGENT_MCP_MICRO
    else:
        # Text-only fallback for minimal terminals
        logo_lines = AGENT_MCP_TEXT
    
    # Apply gradient colors to the selected banner
    banner_lines = []
    
    for i, line in enumerate(logo_lines):
        if not line.strip():  # Skip empty lines but preserve them
            banner_lines.append(line)
            continue
            
        # Calculate color transition across the logo height
        total_lines = len([l for l in logo_lines if l.strip()])  # Count non-empty lines
        line_index = len([l for l in logo_lines[:i] if l.strip()])  # Current non-empty line index
        
        if line_index < total_lines // 2:
            # First half: pink to purple
            progress = line_index / (total_lines // 2) if total_lines // 2 > 0 else 0
            start_color = GRADIENT_COLORS['pink_start']
            end_color = GRADIENT_COLORS['purple_mid']
        else:
            # Second half: purple to cyan
            progress = (line_index - total_lines // 2) / (total_lines // 2) if total_lines // 2 > 0 else 0
            start_color = GRADIENT_COLORS['purple_mid'] 
            end_color = GRADIENT_COLORS['cyan_end']
        
        # Apply gradient to each line
        colored_line = TUITheme.gradient_text(line, start_color, end_color)
        banner_lines.append(colored_line)
    
    return '\n'.join(banner_lines)

def get_agent_mcp_banner() -> str:
    """Generate the AGENT MCP banner with gradient colors (legacy compatibility)."""
    return get_responsive_agent_mcp_banner()

# Legacy function name for backwards compatibility
def get_gemini_banner() -> str:
    """Legacy function name - returns AGENT MCP banner."""
    return get_agent_mcp_banner()

# Legacy ASCII art for the old logo
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