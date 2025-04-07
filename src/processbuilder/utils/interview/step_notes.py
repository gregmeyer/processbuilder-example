"""
Functions for handling step notes input in the Process Builder interview.
"""
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_step_notes(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str
) -> Optional[str]:
    """Handle the step notes input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        
    Returns:
        The step notes or None if skipped
    """
    # First get manual input
    notes = get_step_input("Enter notes for this step (optional, press Enter to skip):", allow_empty=True)
    
    # If notes are skipped and AI is available, offer a suggestion
    if not notes and builder.openai_client:
        want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for step notes?")
        if want_suggestion:
            try:
                show_loading_animation("Generating note suggestion", in_menu=True)
                suggested_notes = builder.generate_step_notes(step_id, description, decision)
                if suggested_notes:
                    print(f"\nAI suggests the following notes:\n\n{suggested_notes}\n")
                    use_suggested = prompt_for_confirmation("Would you like to use this note?")
                    if use_suggested:
                        return suggested_notes
            except Exception as e:
                print(f"Error generating note suggestion: {str(e)}")
    
    # Return the manually entered notes
    return notes if notes else None 