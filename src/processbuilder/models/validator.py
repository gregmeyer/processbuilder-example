"""Process Validator module for validating process steps and flow."""

from typing import List, Optional, Tuple
import logging
from .base import ProcessStep, ProcessNote

log = logging.getLogger(__name__)

class ProcessValidator:
    """Handles validation of process steps and flow."""
    
    def __init__(self):
        """Initialize the ProcessValidator."""
        self.steps = []
    
    def validate_step(self, step: ProcessStep, allow_future_steps: bool = False) -> Tuple[bool, List[str]]:
        """Validate a single process step.
        
        Args:
            step: The ProcessStep to validate
            allow_future_steps: If True, allow next steps that don't exist yet
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate step ID - allow any non-empty string
        if not step.step_id:
            errors.append("Step ID is required")
        elif not step.step_id.strip():
            errors.append("Step ID cannot be empty or just whitespace")
            
        # Validate description
        if not step.description:
            errors.append("Step description is required")
        elif len(step.description) < 10:
            errors.append("Step description must be at least 10 characters")
            
        # Validate decision
        if not step.decision:
            errors.append("Step decision is required")
        elif not step.decision.endswith("?"):
            errors.append("Step decision must be a question ending with '?'")
            
        # Validate outcomes
        if not step.success_outcome:
            errors.append("Success outcome is required")
        if not step.failure_outcome:
            errors.append("Failure outcome is required")
            
        # Validate next steps - 'end' is always valid
        if not step.next_step_success:
            errors.append("Success next step is required")
        elif not allow_future_steps:  # Only check if next step exists when not allowing future steps
            if step.next_step_success.lower() != 'end' and not any(s.step_id == step.next_step_success for s in self.steps):
                errors.append(f"Next step on success path '{step.next_step_success}' does not exist")
            
        if not step.next_step_failure:
            errors.append("Failure next step is required")
        elif not allow_future_steps:  # Only check if next step exists when not allowing future steps
            if step.next_step_failure.lower() != 'end' and not any(s.step_id == step.next_step_failure for s in self.steps):
                errors.append(f"Next step on failure path '{step.next_step_failure}' does not exist")
            
        return len(errors) == 0, errors
    
    def validate_next_step_references(
        self,
        step: ProcessStep,
        all_steps: List[ProcessStep]
    ) -> Tuple[bool, List[str]]:
        """Validate that a step's next step references exist.
        
        Args:
            step: The ProcessStep to validate
            all_steps: List of all ProcessSteps in the process
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Get all valid step IDs
        valid_step_ids = {s.step_id for s in all_steps}
        
        # Check success next step
        if step.next_step_success.lower() != 'end' and step.next_step_success not in valid_step_ids:
            errors.append(f"Success next step '{step.next_step_success}' does not exist")
            
        # Check failure next step
        if step.next_step_failure.lower() != 'end' and step.next_step_failure not in valid_step_ids:
            errors.append(f"Failure next step '{step.next_step_failure}' does not exist")
            
        return len(errors) == 0, errors
    
    def validate_process_flow(
        self,
        steps: List[ProcessStep],
        start_step_id: str
    ) -> Tuple[bool, List[str]]:
        """Validate the entire process flow.
        
        Args:
            steps: List of all ProcessSteps in the process
            start_step_id: ID of the start step
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if start step exists
        start_step = next((s for s in steps if s.step_id == start_step_id), None)
        if not start_step:
            errors.append(f"Start step '{start_step_id}' does not exist")
            return False, errors
            
        # Check for unreachable steps
        reachable_steps = {start_step_id}
        to_visit = [start_step_id]
        
        while to_visit:
            current_id = to_visit.pop()
            current_step = next(s for s in steps if s.step_id == current_id)
            
            # Add next steps if not already visited and not 'end'
            if current_step.next_step_success.lower() != 'end' and current_step.next_step_success not in reachable_steps:
                reachable_steps.add(current_step.next_step_success)
                to_visit.append(current_step.next_step_success)
                
            if current_step.next_step_failure.lower() != 'end' and current_step.next_step_failure not in reachable_steps:
                reachable_steps.add(current_step.next_step_failure)
                to_visit.append(current_step.next_step_failure)
                
        # Check for unreachable steps
        all_step_ids = {s.step_id for s in steps}
        unreachable = all_step_ids - reachable_steps
        if unreachable:
            errors.append(f"Unreachable steps: {', '.join(unreachable)}")
            
        # Check for cycles
        visited = set()
        path = []
        
        def has_cycle(step_id: str) -> bool:
            if step_id in visited:
                return step_id in path
                
            visited.add(step_id)
            path.append(step_id)
            
            step = next(s for s in steps if s.step_id == step_id)
            if step.next_step_success.lower() != 'end':
                if has_cycle(step.next_step_success):
                    return True
            if step.next_step_failure.lower() != 'end':
                if has_cycle(step.next_step_failure):
                    return True
                
            path.pop()
            return False
            
        if has_cycle(start_step_id):
            errors.append("Process contains a cycle")
            
        return len(errors) == 0, errors
    
    def find_missing_steps(
        self,
        steps: List[ProcessStep],
        start_step_id: str
    ) -> List[Tuple[str, str]]:
        """Find steps that are referenced but don't exist.
        
        Args:
            steps: List of all ProcessSteps in the process
            start_step_id: ID of the start step
            
        Returns:
            List of tuples (referencing_step_id, missing_step_id)
        """
        missing_steps = []
        existing_step_ids = {s.step_id for s in steps}
        
        # Check all steps' next step references
        for step in steps:
            if step.next_step_success.lower() != 'end' and step.next_step_success not in existing_step_ids:
                missing_steps.append((step.step_id, step.next_step_success))
            if step.next_step_failure.lower() != 'end' and step.next_step_failure not in existing_step_ids:
                missing_steps.append((step.step_id, step.next_step_failure))
                
        return missing_steps
    
    def validate_note(self, note: ProcessNote) -> Tuple[bool, List[str]]:
        """Validate a process note.
        
        Args:
            note: The ProcessNote to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate step ID reference
        if not note.step_id:
            errors.append("Step ID reference is required")
            
        # Validate note content
        if not note.content:
            errors.append("Note content is required")
        elif len(note.content) < 5:
            errors.append("Note content must be at least 5 characters")
        elif len(note.content) > 200:
            errors.append("Note content must be at most 200 characters")
            
        return len(errors) == 0, errors 