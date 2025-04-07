"""
Helper functions for UI operations in the Process Builder.
"""
import os
import sys
import time
from typing import List, Optional, Any

def show_loading_animation(message: str, duration: float = 2.0, in_menu: bool = True) -> None:
    """Show a simple loading animation with dots.
    
    Args:
        message: The message to display during loading
        duration: How long to show the animation
        in_menu: If True, don't clear the screen to preserve menu visibility
    """
    dot_frames = ["", ".", "..", "..."]
    start_time = time.time()
    dot_idx = 0
    
    while time.time() - start_time < duration:
        # Update the message with dots
        current_message = message + dot_frames[dot_idx]
        
        # Write the message in place
        sys.stdout.write("\r" + current_message)
        sys.stdout.flush()
        
        # Update dot index
        dot_idx = (dot_idx + 1) % len(dot_frames)
        time.sleep(0.2)
    
    # Clear the line
    sys.stdout.write("\r" + " " * (len(message) + 3) + "\r")
    sys.stdout.flush()

def show_startup_animation(in_menu: bool = False) -> None:
    """Show a cute ASCII art loading animation when starting the Process Builder.
    
    Args:
        in_menu: If True, don't clear the screen to preserve menu visibility
    """
    frames = [
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │   ⚙️        │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │      ⚙️     │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │         ⚙️  │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │    ✨       │
    │         ⚙️  │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │    ✨ ✨    │
    │    ⚙️  ⚙️   │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │  ✨ ✨ ✨   │
    │  ⚙️  ⚙️  ⚙️  │
    └─────────────┘
    """
    ]
    
    print("\033[?25l", end="")  # Hide cursor
    try:
        for _ in range(2):  # Show animation twice
            for frame in frames:
                # Only clear the screen if not in menu mode
                if not in_menu:
                    clear_screen()
                
                # Print current frame
                print(frame)
                time.sleep(0.2)
    finally:
        print("\033[?25h", end="")  # Show cursor
        # Clear the animation, but only if not in menu mode
        if not in_menu:
            clear_screen()

def clear_screen() -> None:
    """Clear the terminal screen."""
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')

def get_terminal_height() -> int:
    """Get terminal height in a cross-platform way."""
    try:
        # Try using os.get_terminal_size
        if hasattr(os, 'get_terminal_size'):
            return os.get_terminal_size().lines
        # Fall back to environment variables
        elif 'LINES' in os.environ:
            return int(os.environ['LINES'])
        # Default if nothing else works
        else:
            return 24
    except (OSError, ValueError):
        return 24  # Safe default

def print_header(header_text: str) -> None:
    """Print a nicely formatted header text.
    
    Args:
        header_text: The text to display in the header
    """
    print("="*40)
    print(f"  {header_text}")
    print("="*40)
    print()  # Add a blank line after header

def show_menu(process_name: str = None) -> None:
    """Show the main menu options.
    
    Args:
        process_name: Optional process name to display in header
    """
    # Clear the screen first
    clear_screen()
    
    # Show the process header if a name is provided
    if process_name:
        print_header(f"Process Builder: {process_name}")
    
    # Calculate available terminal height
    terminal_height = get_terminal_height()
    
    # Create space to push menu to bottom of screen (accounting for header and menu lines)
    header_lines = 3 if process_name else 0
    menu_lines = 3  # The menu itself takes 3 lines
    input_buffer = 2  # Space for input prompt
    content_buffer = 4  # Space to leave for content above menu
    
    # Calculate exact padding needed to position menu at bottom
    # Use a smaller buffer to ensure menu stays at bottom but content is visible
    padding_lines = max(1, terminal_height - header_lines - menu_lines - input_buffer - content_buffer)
    
    # Add just enough padding to position the menu near the bottom
    if padding_lines > 20:  # If terminal is very tall, don't add excessive whitespace
        padding_lines = 8  # Reduced for less empty space
    print("\n" * padding_lines)
    
    display_separator()
    print("Process Builder: 1:View | 2:Edit | 3:Add | 4:Output | 5:Exit")
    display_separator()

def display_menu(options: List[str]) -> str:
    """Display a menu of options and get user choice.
    
    Args:
        options: List of menu options to display
        
    Returns:
        The user's choice as a string
    """
    print()  # Add some spacing
    
    # Display options with numbers
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    print()  # Add some spacing
    
    # Get user choice
    while True:
        choice = input("Enter your choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return choice
        print(f"Please enter a number between 1 and {len(options)}")

def display_separator(char: str = "─", length: int = 40) -> None:
    """Display a separator line with the given character and length."""
    print(char * length) 