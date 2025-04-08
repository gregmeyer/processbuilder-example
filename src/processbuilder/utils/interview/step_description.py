"""
Functions for handling step description input in the Process Builder interview.
"""
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_step_description(builder: 'ProcessBuilder', step_id: str) -> str:
    """Handle the step description input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        
    Returns:
        The step description
    """
    # First get manual input
    while True:
        description = get_step_input("What happens in this step?")
        if len(description) >= 10:
            break
        print("Description must be at least 10 characters long. Please provide more details.")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the step description?")
            if want_suggestion:
                show_loading_animation("Generating step description", in_menu=True)
                suggested_description = builder.generate_step_description(step_id)
                if suggested_description:
                    print(f"AI suggests the following description: '{suggested_description}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this description?")
                    if use_suggested:
                        return suggested_description
        except Exception as e:
            print(f"Error generating description suggestion: {str(e)}")
    
    # Return the manually entered description if no AI suggestion is used
    return description 