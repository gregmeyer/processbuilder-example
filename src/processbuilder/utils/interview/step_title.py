"""
Functions for handling step title input in the Process Builder interview.
"""
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_step_title(builder: 'ProcessBuilder', is_first_step: bool, options: dict = None) -> str:
    """Handle the step title input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        is_first_step: True if this is the first step
        options: Dictionary of options including AI suggestions preference
        
    Returns:
        The step title
    """
    options = options or {}
    
    # Handle first step differently (always offer suggestion for title)
    if is_first_step and builder.openai_client:
        try:
            suggested_title = builder.suggested_first_step
            print(f"\nTo help you get started, I suggest beginning with: '{suggested_title}'")
            use_suggested = prompt_for_confirmation("Would you like to use this title?")
            if use_suggested:
                # Convert spaces to underscores and ensure alphanumeric
                suggested_title = ''.join(c if c.isalnum() else '_' for c in suggested_title)
                suggested_title = suggested_title.strip('_')
                return suggested_title
            else:
                step_id = get_step_input("What is the title of this step?")
                # Convert spaces to underscores and ensure alphanumeric
                step_id = ''.join(c if c.isalnum() else '_' for c in step_id)
                step_id = step_id.strip('_')
                return step_id
        except Exception as e:
            print(f"Error generating step title suggestion: {str(e)}")
            step_id = get_step_input("What is the title of this step?")
            # Convert spaces to underscores and ensure alphanumeric
            step_id = ''.join(c if c.isalnum() else '_' for c in step_id)
            step_id = step_id.strip('_')
            return step_id
            
    # For subsequent steps, ask for manual input first
    step_id = get_step_input("What is the title of this step?")
    
    # Then offer AI suggestion if available and enabled
    if builder.openai_client and options.get('use_ai_suggestions', False):
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the step title?")
            if want_suggestion:
                show_loading_animation("Generating step title", in_menu=True)
                suggested_title = builder.generate_next_step_title()
                if suggested_title:
                    print(f"AI suggests the following title: '{suggested_title}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this title?")
                    if use_suggested:
                        # Convert spaces to underscores and ensure alphanumeric
                        suggested_title = ''.join(c if c.isalnum() else '_' for c in suggested_title)
                        suggested_title = suggested_title.strip('_')
                        return suggested_title
        except Exception as e:
            print(f"Error generating step title suggestion: {str(e)}")
    
    # Convert spaces to underscores and ensure alphanumeric
    step_id = ''.join(c if c.isalnum() else '_' for c in step_id)
    step_id = step_id.strip('_')
    
    # Return the manually entered title if no AI suggestion is used
    return step_id 