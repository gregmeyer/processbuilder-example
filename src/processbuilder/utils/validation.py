"""Validation utilities for ProcessBuilder."""

import logging
from typing import List, Tuple
from .models import ProcessStep, ProcessNote

log = logging.getLogger(__name__)

def validate_step(step: ProcessStep, existing_steps: List[ProcessStep]) -> Tuple[bool, List[str]]:
    """Validate a process step.
    
    Args:
        step: The ProcessStep to validate
        existing_steps: List of existing steps to check against
        
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    # Check required fields
    if not step.step_id:
        errors.append("Step ID is required")
    if not step.description:
        errors.append("Description is required")
    if not step.decision:
        errors.append("Decision is required")
    if not step.success_outcome:
        errors.append("Success outcome is required")
    if not step.failure_outcome:
        errors.append("Failure outcome is required")
    
    # Check for duplicate step IDs
    if any(s.step_id == step.step_id for s in existing_steps if s != step):
        errors.append(f"Duplicate step ID: {step.step_id}")
    
    # Check next step references
    if step.next_step_success and not any(s.step_id == step.next_step_success for s in existing_steps):
        errors.append(f"Invalid success next step: {step.next_step_success}")
    if step.next_step_failure and not any(s.step_id == step.next_step_failure for s in existing_steps):
        errors.append(f"Invalid failure next step: {step.next_step_failure}")
    
    return len(errors) == 0, errors

def validate_note(note: ProcessNote, existing_steps: List[ProcessStep]) -> Tuple[bool, List[str]]:
    """Validate a process note.
    
    Args:
        note: The ProcessNote to validate
        existing_steps: List of existing steps to check against
        
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    # Check required fields
    if not note.note_id:
        errors.append("Note ID is required")
    if not note.content:
        errors.append("Content is required")
    if not note.step_id:
        errors.append("Step ID is required")
    
    # Check step reference
    if not any(s.step_id == note.step_id for s in existing_steps):
        errors.append(f"Invalid step reference: {note.step_id}")
    
    return len(errors) == 0, errors

def validate_process(steps: List[ProcessStep], notes: List[ProcessNote]) -> Tuple[bool, List[str]]:
    """Validate an entire process.
    
    Args:
        steps: List of ProcessSteps
        notes: List of ProcessNotes
        
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    # Validate each step
    for step in steps:
        is_valid, step_errors = validate_step(step, steps)
        if not is_valid:
            errors.extend([f"Step {step.step_id}: {error}" for error in step_errors])
    
    # Validate each note
    for note in notes:
        is_valid, note_errors = validate_note(note, steps)
        if not is_valid:
            errors.extend([f"Note {note.note_id}: {error}" for error in note_errors])
    
    # Check for unreachable steps
    reachable_steps = {"Start"}
    for step in steps:
        if step.next_step_success:
            reachable_steps.add(step.next_step_success)
        if step.next_step_failure:
            reachable_steps.add(step.next_step_failure)
    
    unreachable = {s.step_id for s in steps} - reachable_steps
    if unreachable:
        errors.append(f"Unreachable steps: {', '.join(unreachable)}")
    
    return len(errors) == 0, errors 