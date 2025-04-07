"""
Functions for handling step outcomes input in the Process Builder interview.
"""
from typing import Optional, Tuple, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_success_outcome(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str
) -> str:
    """Handle the success outcome input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        
    Returns:
        The success outcome
    """
    # First get manual input
    success_outcome = get_step_input("What happens if this step succeeds?")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the success outcome?")
            if want_suggestion:
                show_loading_animation("Generating success outcome suggestion", in_menu=True)
                suggested_success = builder.generate_step_success_outcome(step_id, description, decision)
                if suggested_success:
                    print(f"AI suggests the following success outcome: '{suggested_success}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this success outcome?")
                    if use_suggested:
                        return suggested_success
        except Exception as e:
            print(f"Error generating success outcome suggestion: {str(e)}")
    
    # Return the manually entered success outcome if no AI suggestion is used
    return success_outcome

def handle_failure_outcome(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str
) -> str:
    """Handle the failure outcome input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        
    Returns:
        The failure outcome
    """
    # First get manual input
    failure_outcome = get_step_input("What happens if this step fails?")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the failure outcome?")
            if want_suggestion:
                show_loading_animation("Generating failure outcome suggestion", in_menu=True)
                suggested_failure = builder.generate_step_failure_outcome(step_id, description, decision)
                if suggested_failure:
                    print(f"AI suggests the following failure outcome: '{suggested_failure}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this failure outcome?")
                    if use_suggested:
                        return suggested_failure
        except Exception as e:
            print(f"Error generating failure outcome suggestion: {str(e)}")
    
    # Return the manually entered failure outcome if no AI suggestion is used
    return failure_outcome

def handle_step_outcomes(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str
) -> Tuple[str, str]:
    """Handle both success and failure outcomes input.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        
    Returns:
        Tuple of (success_outcome, failure_outcome)
    """
    success_outcome = handle_success_outcome(builder, step_id, description, decision)
    failure_outcome = handle_failure_outcome(builder, step_id, description, decision)
    return success_outcome, failure_outcome 