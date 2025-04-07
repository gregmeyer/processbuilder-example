"""
Helper functions for handling user input in the Process Builder.
"""
from typing import Optional, Any, List, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

def get_step_input(prompt: str, allow_empty: bool = False) -> str:
    """Get input from user with validation."""
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if response or allow_empty:
            return response
        print("Please provide a response.")

def get_next_step_input(builder: 'ProcessBuilder', prompt: str) -> str:
    """Get next step input with list of existing steps."""
    if builder.steps:
        print("\nExisting steps:")
        for i, step in enumerate(builder.steps, 1):
            print(f"{i}. {step.step_id}")
        print("Or enter 'End' to finish the process")
    
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if not response:
            print("Please provide a response.")
            continue
            
        # Check if it's a number reference to existing step
        if response.isdigit():
            step_num = int(response)
            if 1 <= step_num <= len(builder.steps):
                return builder.steps[step_num - 1].step_id
            print(f"Please enter a number between 1 and {len(builder.steps)}")
            continue
            
        # Check if it's 'End' or a new step name
        if response.lower() == 'end' or not any(s.step_id == response for s in builder.steps):
            return response
            
        print("Please enter a new step name or 'End'")

def prompt_for_confirmation(prompt: str) -> bool:
    """Prompt the user for confirmation (y/n)."""
    response = input(f"\n{prompt} (y/n)\n> ").lower().strip()
    return response == 'y'

def get_with_ai_suggestion(
    prompt: str,
    suggestion_fn=None,
    suggestion_args: Optional[dict] = None,
    loading_message: str = "Generating suggestion",
    required: bool = True
) -> str:
    """Generic function to handle AI suggestions for any field.
    
    Args:
        prompt: The prompt to display to the user
        suggestion_fn: Function to call to get AI suggestion
        suggestion_args: Arguments to pass to suggestion_fn
        loading_message: Message to display while loading
        required: Whether a response is required
    
    Returns:
        The user input or AI suggestion
    """
    from ..utils.ui_helpers import show_loading_animation
    
    suggestion_args = suggestion_args or {}
    
    # First ask if user wants an AI suggestion
    want_suggestion = prompt_for_confirmation("Would you like an AI suggestion?")
    
    if want_suggestion and suggestion_fn:
        # Show loading animation
        show_loading_animation(loading_message, in_menu=True)
        
        try:
            # Get AI suggestion
            suggestion = suggestion_fn(**suggestion_args)
            
            if suggestion:
                # Show suggestion and ask if user wants to use it
                print(f"AI suggests: '{suggestion}'")
                use_suggestion = prompt_for_confirmation("Would you like to use this suggestion?")
                
                if use_suggestion:
                    return suggestion
        except Exception as e:
            print(f"Error generating suggestion: {str(e)}")
    
    # If user doesn't want AI suggestion, get manual input
    if required:
        return get_step_input(prompt)
    
    # If not required, allow empty input
    response = input(f"\n{prompt} (Press Enter to skip)\n> ").strip()
    return response if response else None 