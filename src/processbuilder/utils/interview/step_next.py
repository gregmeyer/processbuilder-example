"""
Functions for handling next step inputs in the Process Builder interview.
"""
from typing import Optional, Tuple, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ...builder import ProcessBuilder

from ..ui_helpers import show_loading_animation
from ..input_handlers import get_step_input, prompt_for_confirmation

def handle_next_step_input(
    builder: 'ProcessBuilder', 
    path_type: str
) -> str:
    """Get valid next step input from the user.
    
    Args:
        builder: The ProcessBuilder instance
        path_type: The path type ("success" or "failure")
        
    Returns:
        The next step ID or "End"
    """
    while True:
        next_step = get_step_input(f"What's the next step if {path_type}? (Enter 'End' if final step)")
        
        # Handle 'End' case-insensitively
        if next_step.lower() == 'end':
            return 'end'  # Always return lowercase
            
        # For non-'End' steps, convert spaces to underscores and ensure alphanumeric
        next_step = ''.join(c if c.isalnum() else '_' for c in next_step)
        next_step = next_step.strip('_')
        
        if builder.validate_next_step(next_step):
            return next_step
        print("Please enter a valid step name or 'End' to finish the process.")

def handle_success_path(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str,
    success_outcome: str,
    failure_outcome: str
) -> str:
    """Handle the next step for success path input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        success_outcome: The step success outcome
        failure_outcome: The step failure outcome
        
    Returns:
        The next step for success path
    """
    # First get manual input
    next_step_success = handle_next_step_input(builder, "successful")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the next step on success?")
            if want_suggestion:
                show_loading_animation("Generating next step suggestion", in_menu=True)
                suggested_next_success = builder.generate_next_step_suggestion(
                    step_id, description, decision, success_outcome, failure_outcome, True
                )
                if suggested_next_success:
                    print(f"AI suggests the following next step for success: '{suggested_next_success}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this next step?")
                    if use_suggested and builder.validate_next_step(suggested_next_success):
                        return suggested_next_success
        except Exception as e:
            print(f"Error generating next step suggestion: {str(e)}")
    
    # Return the manually entered next step if no AI suggestion is used
    return next_step_success

def handle_failure_path(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str,
    success_outcome: str,
    failure_outcome: str
) -> str:
    """Handle the next step for failure path input with optional AI suggestions.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        success_outcome: The step success outcome
        failure_outcome: The step failure outcome
        
    Returns:
        The next step for failure path
    """
    # First get manual input
    next_step_failure = handle_next_step_input(builder, "failed")
    
    # Then offer AI suggestion if available
    if builder.openai_client:
        try:
            want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the next step on failure?")
            if want_suggestion:
                show_loading_animation("Generating next step suggestion", in_menu=True)
                suggested_next_failure = builder.generate_next_step_suggestion(
                    step_id, description, decision, success_outcome, failure_outcome, False
                )
                if suggested_next_failure:
                    print(f"AI suggests the following next step for failure: '{suggested_next_failure}'")
                    use_suggested = prompt_for_confirmation("Would you like to use this next step?")
                    if use_suggested and builder.validate_next_step(suggested_next_failure):
                        return suggested_next_failure
        except Exception as e:
            print(f"Error generating next step suggestion: {str(e)}")
    
    # Return the manually entered next step if no AI suggestion is used
    return next_step_failure

def handle_next_steps(
    builder: 'ProcessBuilder', 
    step_id: str, 
    description: str, 
    decision: str,
    success_outcome: str,
    failure_outcome: str
) -> Tuple[str, str]:
    """Handle both next steps input.
    
    Args:
        builder: The ProcessBuilder instance
        step_id: The step ID
        description: The step description
        decision: The step decision
        success_outcome: The step success outcome
        failure_outcome: The step failure outcome
        
    Returns:
        Tuple of (next_step_success, next_step_failure)
    """
    next_step_success = handle_success_path(
        builder, step_id, description, decision, success_outcome, failure_outcome
    )
    next_step_failure = handle_failure_path(
        builder, step_id, description, decision, success_outcome, failure_outcome
    )
    return next_step_success, next_step_failure 