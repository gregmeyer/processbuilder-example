"""
Functions for handling error codes input in the Process Builder interview.
"""
from typing import Optional, List, Dict, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_error_codes(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str,
    failure_outcome: str
) -> Dict[str, str]:
    """Handle error codes input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        failure_outcome: The step failure outcome
        
    Returns:
        Dictionary of error codes (may be empty)
    """
    error_codes = {}
    
    # First get manual input
    print("Enter error codes for this step (optional, press Enter when done):")
    
    while True:
        code = get_step_input("Error code (Enter to finish):", allow_empty=True)
        if not code:
            break
        
        description = get_step_input(f"Description for error code '{code}':")
        error_codes[code] = description
    
    # If no error codes added and AI is available, offer a suggestion
    if not error_codes and builder.openai_client:
        want_suggestion = prompt_for_confirmation("Would you like AI suggestions for error codes?")
        if want_suggestion:
            try:
                show_loading_animation("Generating error code suggestions", in_menu=True)
                suggested_codes = builder.generate_error_codes(step_id, description, decision, failure_outcome)
                if suggested_codes:
                    print("\nAI suggests the following error codes:")
                    for code, desc in suggested_codes.items():
                        print(f"{code}: {desc}")
                    print()
                    
                    use_suggested = prompt_for_confirmation("Would you like to use these error codes?")
                    if use_suggested:
                        return suggested_codes
            except Exception as e:
                print(f"Error generating error code suggestions: {str(e)}")
    
    # Return the manually entered error codes
    return error_codes 