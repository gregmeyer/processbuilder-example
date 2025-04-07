"""
Utility functions for the Process Builder.

This package contains modules for:
- User input handling
- UI helpers and display functions
- File operations
- Process management
- Interview process
"""
import re
import csv
from pathlib import Path
from typing import Dict, Set, List

from .input_handlers import get_step_input, prompt_for_confirmation
from .ui_helpers import clear_screen, print_header, display_menu, show_loading_animation, show_startup_animation
from .file_operations import load_csv_data, save_csv_data
from .process_management import view_all_steps, edit_step, generate_outputs
from .interview_process import create_step, add_more_steps, run_interview

def sanitize_id(id_str: str) -> str:
    """Sanitize a string to make it a valid Mermaid ID."""
    # Keep meaningful characters while ensuring safe node IDs
    safe_id = re.sub(r'[^a-zA-Z0-9_\s-]', '', id_str)
    safe_id = re.sub(r'[\s-]+', '_', safe_id)
    
    # Handle common keywords in step names
    if any(word in safe_id.lower() for word in ['success', 'failure', 'error', 'end']):
        safe_id = f"step_{safe_id}"
    
    # Ensure ID starts with a letter (Mermaid requirement)
    if not safe_id or not safe_id[0].isalpha():
        safe_id = 'node_' + safe_id
        
    return safe_id

def validate_process_flow(steps) -> List[str]:
    """Validate the entire process flow and return a list of issues."""
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
    """Validate notes and return a list of issues."""
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

def write_csv(data: list[dict], filepath: Path, fieldnames: list[str]) -> None:
    """Write data to a CSV file."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

__all__ = [
    # Input handlers
    'get_step_input',
    'prompt_for_confirmation',
    
    # UI helpers
    'clear_screen',
    'print_header',
    'display_menu',
    'show_loading_animation',
    'show_startup_animation',
    
    # File operations
    'load_csv_data',
    'save_csv_data',
    
    # Process management
    'view_all_steps',
    'edit_step',
    'generate_outputs',
    
    # Interview process
    'create_step',
    'add_more_steps',
    'run_interview',
    
    # Utility functions
    'sanitize_id',
    'validate_process_flow',
    'validate_notes',
    'write_csv',
]
