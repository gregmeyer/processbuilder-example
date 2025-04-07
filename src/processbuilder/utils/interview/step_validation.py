"""
Functions for handling validation rules input in the Process Builder interview.
"""
from typing import Optional, List, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_validation_rules(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str
) -> List[str]:
    """Handle validation rules input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        
    Returns:
        List of validation rules (may be empty)
    """
    validation_rules = []
    
    # First get manual input
    print("Enter validation rules for this step (optional, press Enter when done):")
    
    while True:
        rule = get_step_input("Validation rule (Enter to finish):", allow_empty=True)
        if not rule:
            break
        validation_rules.append(rule)
    
    # If no rules added and AI is available, offer a suggestion
    if not validation_rules and builder.openai_client:
        want_suggestion = prompt_for_confirmation("Would you like AI suggestions for validation rules?")
        if want_suggestion:
            try:
                show_loading_animation("Generating validation rule suggestions", in_menu=True)
                suggested_rules = builder.generate_validation_rules(step_id, description, decision)
                if suggested_rules:
                    print("\nAI suggests the following validation rules:")
                    for i, rule in enumerate(suggested_rules, 1):
                        print(f"{i}. {rule}")
                    print()
                    
                    use_suggested = prompt_for_confirmation("Would you like to use these validation rules?")
                    if use_suggested:
                        return suggested_rules
            except Exception as e:
                print(f"Error generating validation rule suggestions: {str(e)}")
    
    # Return the manually entered validation rules
    return validation_rules 