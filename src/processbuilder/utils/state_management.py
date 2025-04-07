"""
Functions for managing process state persistence.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

def save_state(process_name: str, timestamp: str, current_note_id: int, 
             step_count: int, steps, notes, state_dir: Path) -> bool:
    """Save the current process state to a JSON file.
    
    This saves all steps, notes, and builder metadata to allow
    resuming work on the process later.
    
    Args:
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        current_note_id: Current counter for note IDs
        step_count: Number of steps in the process
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        state_dir: Directory to save state files
        
    Returns:
        True if state was saved successfully, False otherwise
    """
    try:
        # Create state directory if it doesn't exist
        state_dir.mkdir(exist_ok=True)
        
        # Create a state file for this process
        state_file = state_dir / f"{process_name}.json"
        
        # Convert steps and notes to dicts, handling both objects with to_dict() and dict-like objects
        steps_data = []
        for step in steps:
            if hasattr(step, 'to_dict') and callable(step.to_dict):
                steps_data.append(step.to_dict())
            elif isinstance(step, dict):
                steps_data.append(step)
            else:
                log.warning(f"Unable to convert step to dict: {step}")
                steps_data.append({"error": "Step could not be converted to dict"})
        
        notes_data = []
        for note in notes:
            if hasattr(note, 'to_dict') and callable(note.to_dict):
                notes_data.append(note.to_dict())
            elif isinstance(note, dict):
                notes_data.append(note)
            else:
                log.warning(f"Unable to convert note to dict: {note}")
                notes_data.append({"error": "Note could not be converted to dict"})
        
        # Build the state dictionary
        state = {
            "process_name": process_name,
            "timestamp": timestamp,
            "current_note_id": current_note_id,
            "step_count": step_count,
            "steps": steps_data,
            "notes": notes_data
        }
        
        # Write the state to file
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
            
        log.debug(f"Saved process state to {state_file}")
        return True
    except Exception as e:
        log.warning(f"Failed to save process state: {str(e)}")
        return False

def load_state(process_name: str, state_dir: Path, 
              process_step_class, process_note_class) -> Tuple[Union[bool, Dict[str, Any]], Optional[List[Any]], Optional[List[Any]]]:
    """Load process state from a JSON file.
    
    Args:
        process_name: Name of the process
        state_dir: Directory containing state files
        process_step_class: The ProcessStep class to instantiate
        process_note_class: The ProcessNote class to instantiate
        
    Returns:
        Tuple containing:
        - Bool or Dict: False if state couldn't be loaded, otherwise a dict with metadata
        - List or None: List of ProcessStep objects or None if loading failed
        - List or None: List of ProcessNote objects or None if loading failed
    """
    # Check if state directory and file exist
    state_file = state_dir / f"{process_name}.json"
    if not state_file.exists():
        log.debug(f"No state file found for process: {process_name}")
        return False, None, None
        
    try:
        # Read the state from file
        with open(state_file, "r") as f:
            state = json.load(f)
            
        # Extract metadata
        metadata = {
            "timestamp": state.get("timestamp", ""),
            "current_note_id": state.get("current_note_id", 1),
            "step_count": state.get("step_count", 0),
        }
        
        # Load steps
        steps = []
        for step_data in state.get("steps", []):
            steps.append(process_step_class.from_dict(step_data))
            
        # Load notes
        notes = []
        for note_data in state.get("notes", []):
            notes.append(process_note_class.from_dict(note_data))
            
        log.debug(f"Successfully loaded state for process: {process_name}")
        return metadata, steps, notes
    except Exception as e:
        log.warning(f"Failed to load process state: {str(e)}")
        return False, None, None
