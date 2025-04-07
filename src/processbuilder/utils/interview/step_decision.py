"""
Functions for handling step decision input in the Process Builder interview.
"""
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_step_decision(builder: 'ProcessBuilder', step_id: str, description: str) -> str:
    """Handle the step decision input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        
    Returns:
        The step decision
    """
    # First get manual input
    decision = get_step_input("What decision needs to be made?")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the decision?")
            if want_suggestion:
                show_loading_animation("Generating decision suggestion", in_menu=True)
                suggested_decision = builder.generate_step_decision(step_id, description)
                if suggested_decision:
                    print(f"AI suggests the following decision: '{suggested_decision}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this decision?")
                    if use_suggested:
                        return suggested_decision
        except Exception as e:
            print(f"Error generating decision suggestion: {str(e)}")
    
    # Return the manually entered decision if no AI suggestion is used
    return decision 