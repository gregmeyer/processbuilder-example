"""
Functions for managing process state persistence.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import os
from datetime import datetime

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

def setup_output_directory(
    process_name: str,
    timestamp: datetime,
    base_output_dir: Optional[str] = None,
    default_output_dir: str = "output"
) -> str:
    """Set up the output directory for process files.
    
    Args:
        process_name: Name of the process
        timestamp: Timestamp for the process
        base_output_dir: Optional base directory for output
        default_output_dir: Default directory name if base not specified
        
    Returns:
        Path to the output directory
    """
    # Use provided base directory or default to current directory
    base_dir = Path(base_output_dir) if base_output_dir else Path.cwd()
    
    # Create output directory path
    output_dir = base_dir / default_output_dir / process_name / timestamp.strftime("%Y%m%d_%H%M%S")
    
    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return str(output_dir)

def save_state(
    process_name: str,
    timestamp: datetime,
    steps: list,
    notes: list,
    start_step_id: Optional[str] = None,
    output_dir: Optional[str] = None
) -> bool:
    """Save the current state to a file.
    
    Args:
        process_name: Name of the process
        timestamp: Timestamp for the process
        steps: List of process steps
        notes: List of process notes
        start_step_id: Optional ID of the start step
        output_dir: Optional output directory
        
    Returns:
        True if state was saved successfully, False otherwise
    """
    try:
        # Convert steps and notes to dictionaries
        state = {
            "process_name": process_name,
            "timestamp": timestamp.isoformat(),
            "start_step_id": start_step_id,
            "steps": [step.to_dict() for step in steps],
            "notes": [note.to_dict() for note in notes]
        }
        
        # Use provided output directory or create a default one
        if not output_dir:
            output_dir = setup_output_directory(process_name, timestamp)
        
        # Save state to file
        state_file = Path(output_dir) / f"{process_name}_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        log.info(f"State saved to {state_file}")
        return True
        
    except Exception as e:
        log.error(f"Error saving state: {str(e)}")
        return False

def load_state(file_path: str) -> Dict[str, Any]:
    """Load state from a file.
    
    Args:
        file_path: Path to the state file
        
    Returns:
        Dictionary containing the loaded state
    """
    try:
        with open(file_path, 'r') as f:
            state = json.load(f)
            
        # Convert timestamp string back to datetime
        state['timestamp'] = datetime.fromisoformat(state['timestamp'])
        
        return state
        
    except Exception as e:
        log.error(f"Error loading state: {str(e)}")
        raise
