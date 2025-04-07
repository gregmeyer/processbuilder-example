"""
Functions for handling step title input in the Process Builder interview.
"""
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_step_title(builder: 'ProcessBuilder', is_first_step: bool) -> str:
    """Handle the step title input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        is_first_step: True if this is the first step
        
    Returns:
        The step title
    """
    # Handle first step differently (suggest the initial step title)
    if is_first_step and builder.openai_client:
        try:
            suggested_title = builder.suggested_first_step
            print(f"AI suggests starting with: '{suggested_title}'")
            use_suggested = prompt_for_confirmation("Would you like to use this title?")
            if use_suggested:
                return suggested_title
            else:
                return get_step_input("What is the title of this step?")
        except Exception as e:
            print(f"Error generating step title suggestion: {str(e)}")
            return get_step_input("What is the title of this step?")
            
    # For subsequent steps, ask for manual input first
    step_id = get_step_input("What is the title of this step?")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the step title?")
            if want_suggestion:
                show_loading_animation("Generating step title", in_menu=True)
                suggested_title = builder.generate_next_step_title()
                if suggested_title:
                    print(f"AI suggests the following title: '{suggested_title}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this title?")
                    if use_suggested:
                        return suggested_title
        except Exception as e:
            print(f"Error generating step title suggestion: {str(e)}")
    
    # Return the manually entered title if no AI suggestion is used
    return step_id 