"""Step management utilities for ProcessBuilder."""

import logging
from typing import List, Optional, Tuple
from .models import ProcessStep, ProcessNote

log = logging.getLogger(__name__)

def create_step_id(title: str, existing_steps: List[ProcessStep]) -> str:
    """Create a valid, unique step ID from a title.
    
    Args:
        title: The title to convert to a step ID
        existing_steps: List of existing steps to check for uniqueness
        
    Returns:
        A valid, unique step ID
    """
    # Start with the title as the step ID
    step_id = title
    
    # Check for duplicates and add a number if needed
    if any(step.step_id == step_id for step in existing_steps):
        # Find the highest number suffix for this title
        base_id = step_id
        highest_suffix = 0
        
        for step in existing_steps:
            if step.step_id == base_id:
                highest_suffix = 1
            elif step.step_id.startswith(f"{base_id}_"):
                try:
                    suffix = int(step.step_id[len(base_id) + 1:])
                    highest_suffix = max(highest_suffix, suffix)
                except ValueError:
                    pass
        
        # Add suffix to make unique
        step_id = f"{base_id}_{highest_suffix + 1}"
    
    return step_id

def add_step(step: ProcessStep, steps: List[ProcessStep], validator) -> Tuple[bool, List[str]]:
    """Add a step to the process.
    
    Args:
        step: The ProcessStep to add
        steps: List of existing steps
        validator: ProcessValidator instance
        
    Returns:
        Tuple of (success, errors)
    """
    try:
        # Validate the step
        is_valid, errors = validator.validate_step(step)
        if not is_valid:
            log.error(f"Invalid step: {', '.join(errors)}")
            return False, errors
            
        # Add the step
        steps.append(step)
        return True, []
        
    except Exception as e:
        log.error(f"Error adding step: {str(e)}")
        return False, [str(e)]

def add_note(note: ProcessNote, notes: List[ProcessNote], validator) -> Tuple[bool, List[str]]:
    """Add a note to the process.
    
    Args:
        note: The ProcessNote to add
        notes: List of existing notes
        validator: ProcessValidator instance
        
    Returns:
        Tuple of (success, errors)
    """
    try:
        # Validate the note
        is_valid, errors = validator.validate_note(note)
        if not is_valid:
            log.error(f"Invalid note: {', '.join(errors)}")
            return False, errors
            
        # Add the note
        notes.append(note)
        return True, []
        
    except Exception as e:
        log.error(f"Error adding note: {str(e)}")
        return False, [str(e)]

def create_missing_step(
    step_id: str,
    predecessor_id: Optional[str] = None,
    path_type: Optional[str] = None,
    input_handler=None
) -> ProcessStep:
    """Create a missing step that was referenced by another step.
    
    Args:
        step_id: ID of the step to create
        predecessor_id: Optional ID of the step that references this one
        path_type: Optional path type ('success' or 'failure')
        input_handler: Optional custom input handler function
        
    Returns:
        A new ProcessStep with user-provided values
    """
    print(f"\nCreating missing step: {step_id}")
    
    # Get step description
    print("\nThe step name is used as a label in the process diagram.")
    description = input_handler("What happens in this step?")
    
    # Get decision
    print("\nThe decision is a yes/no question that determines which path to take next.")
    decision = input_handler("What decision needs to be made in this step?")
    
    # Get success outcome
    print("\nThe success outcome tells you which step to go to next when the decision is 'yes'.")
    success_outcome = input_handler("What happens if this step succeeds?")
    
    # Get failure outcome
    print("\nThe failure outcome tells you which step to go to next when the decision is 'no'.")
    failure_outcome = input_handler("What happens if this step fails?")
    
    # Create and return the step
    return ProcessStep(
        step_id=step_id,
        description=description,
        decision=decision,
        success_outcome=success_outcome,
        failure_outcome=failure_outcome,
        next_step_success="End",  # Default to End, will be updated later
        next_step_failure="End"   # Default to End, will be updated later
    )

def create_missing_step_noninteractive(
    step_id: str,
    predecessor_id: Optional[str] = None,
    path_type: Optional[str] = None
) -> ProcessStep:
    """Create a missing step with default values without requiring user input.
    
    Args:
        step_id: ID of the step to create
        predecessor_id: Optional ID of the step that references this one
        path_type: Optional path type ('success' or 'failure')
        
    Returns:
        A new ProcessStep with default values
    """
    print(f"\nFound missing step: {step_id}")
    if predecessor_id:
        print(f"Referenced by step: {predecessor_id} on {path_type} path")
    
    # Create default values
    description = f"Automatically generated step for: {step_id}"
    decision = f"Does the {step_id} step complete successfully?"
    success_outcome = "The step completed successfully."
    failure_outcome = "The step failed to complete."
    
    # Create and return the step with default values
    return ProcessStep(
        step_id=step_id,
        description=description,
        decision=decision,
        success_outcome=success_outcome,
        failure_outcome=failure_outcome,
        next_step_success="End",
        next_step_failure="End"
    ) 