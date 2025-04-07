"""
Functions for validating process steps and connections.
"""
import logging
from typing import List, Optional, Tuple, Set, Dict, Any

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

def validate_next_step_id(steps, next_step_id: str) -> bool:
    """Validate that a next step ID is either 'End' or an existing step.
    
    Args:
        steps: List of ProcessStep objects
        next_step_id: The next step ID to validate
        
    Returns:
        True if the next step is valid (either 'End' or an existing step ID),
        False otherwise
    """
    # "End" is always a valid next step
    if next_step_id.lower() == 'end':
        return True
        
    # Check if the step ID exists in the current steps
    if any(step.step_id == next_step_id for step in steps):
        return True
        
    # Return False for any other value
    return False
        
def validate_next_step(step, steps) -> List[str]:
    """Validate that the next step IDs in the step are valid.
    
    Args:
        step: The step to validate
        steps: List of ProcessStep objects
        
    Returns:
        List of validation issue messages, empty if all is valid
    """
    issues = []
    
    # Validate next_step_success
    if not validate_next_step_id(steps, step.next_step_success):
        issues.append(f"Next step on success path '{step.next_step_success}' does not exist")
        
    # Validate next_step_failure
    if not validate_next_step_id(steps, step.next_step_failure):
        issues.append(f"Next step on failure path '{step.next_step_failure}' does not exist")
        
    return issues

def find_missing_steps(steps) -> List[Tuple[str, str, str]]:
    """Find steps that are referenced but not yet defined.
    
    Args:
        steps: List of ProcessStep objects
        
    Returns:
        A list of tuples (missing_step_id, referencing_step_id, path_type),
        where path_type is either 'success' or 'failure'.
    """
    missing_steps = []
    existing_step_ids = {step.step_id for step in steps}
    
    for step in steps:
        if (step.next_step_success.lower() != 'end' and 
            step.next_step_success not in existing_step_ids):
            missing_steps.append((step.next_step_success, step.step_id, 'success'))
        
        if (step.next_step_failure.lower() != 'end' and 
            step.next_step_failure not in existing_step_ids):
            missing_steps.append((step.next_step_failure, step.step_id, 'failure'))
    
    return missing_steps

def validate_process_flow(steps) -> List[str]:
    """Validate the entire process flow and return a list of issues.
    
    Args:
        steps: List of ProcessStep objects
        
    Returns:
        List of validation issue messages, empty if all is valid
    """
    issues = []
    
    # Check for at least one step and end points
    if not steps:
        issues.append("Process must have at least one step")
        return issues
        
    has_end = any(step.next_step_success.lower() == 'end' or 
                 step.next_step_failure.lower() == 'end' for step in steps)
    
    if not has_end:
        issues.append("Process must have at least one path that leads to 'End'")
    
    # Check all paths for circular references and missing steps
    if steps:
        first_step = steps[0]
        
        # Helper function to check a path
        def check_path(start_id: str, path_name: str) -> None:
            visited: Set[str] = set()
            current = start_id
            path: List[str] = []
            
            while current is not None and current.lower() != 'end':
                path.append(current)
                
                if current in visited:
                    issues.append(f"Circular reference detected in {path_name} path: {' -> '.join(path)}")
                    break
                
                visited.add(current)
                
                step = next((s for s in steps if s.step_id == current), None)
                if step is None:
                    issues.append(f"Step name '{current}' referenced in {path_name} path not found")
                    break
                
                if path_name == "success":
                    current = step.next_step_success
                else:
                    current = step.next_step_failure
        
        # Check both success and failure paths starting from the first step
        check_path(first_step.step_id, "success")
        check_path(first_step.step_id, "failure")
    
    # Check for disconnected steps
    all_step_ids = {step.step_id for step in steps}
    referenced_steps = set()
    
    for step in steps:
        if step.next_step_success.lower() != 'end':
            referenced_steps.add(step.next_step_success)
        if step.next_step_failure.lower() != 'end':
            referenced_steps.add(step.next_step_failure)
    
    # Get the first step ID which doesn't need to be referenced
    first_step_id = steps[0].step_id if steps else ""
    disconnected = all_step_ids - referenced_steps - {first_step_id}  # First step doesn't need to be referenced
    if disconnected:
        issues.append(f"Disconnected step names found: {', '.join(disconnected)}")
    return issues

def validate_notes(notes, steps) -> List[str]:
    """Validate notes and return a list of issues.
    
    Args:
        notes: List of ProcessNote objects
        steps: List of ProcessStep objects
        
    Returns:
        List of validation issue messages, empty if all is valid
    """
    issues = []
    
    # Check for duplicate note IDs
    note_ids = [note.note_id for note in notes]
    if len(note_ids) != len(set(note_ids)):
        issues.append("Duplicate note IDs found")
    
    # Check for orphaned notes
    step_ids = {step.step_id for step in steps}
    for note in notes:
        if note.related_step_id not in step_ids:
            issues.append(f"Note {note.note_id} references non-existent step name '{note.related_step_id}'")
    
    return issues
