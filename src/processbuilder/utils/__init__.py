"""
Utility functions for the Process Builder.

This package contains modules for:
- User input handling
- UI helpers and display functions
- File operations
- Process management
- Interview process
- AI generation functions
- Process validation
- Output handling
- State management
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

# Import AI functions
from .ai_generation import (
    sanitize_string,
    show_loading_animation,
    generate_step_description,
    generate_step_decision,
    generate_step_success_outcome,
    generate_step_failure_outcome,
    generate_step_note,
    generate_validation_rules,
    generate_error_codes,
    generate_executive_summary,
    parse_ai_suggestions,
    evaluate_step_design,
    generate_step_title
)

# Import validation functions
from .process_validation import (
    validate_next_step_id,
    validate_next_step,
    find_missing_steps,
    validate_process_flow,
    validate_notes
)

# Import output handling functions
from .output_handling import (
    generate_mermaid_diagram,
    export_to_json,
    export_to_csv,
    generate_mermaid_image,
    setup_output_directory,
    sanitize_id,
    write_csv,
    generate_csv,
    generate_llm_prompt,
    save_outputs
)

# Import state management functions
from .state_management import (
    save_state,
    load_state
)

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
    
    # AI generation
    'sanitize_string',
    'show_loading_animation',
    'generate_step_description',
    'generate_step_decision',
    'generate_step_success_outcome',
    'generate_step_failure_outcome',
    'generate_step_note',
    'generate_validation_rules',
    'generate_error_codes',
    'generate_executive_summary',
    'parse_ai_suggestions',
    'evaluate_step_design',
    'generate_step_title',
    
    # Validation
    'validate_next_step_id',
    'validate_next_step',
    'find_missing_steps',
    'validate_process_flow',
    'validate_notes',
    
    # Output handling
    'generate_mermaid_diagram',
    'export_to_json',
    'export_to_csv',
    'generate_mermaid_image',
    'setup_output_directory',
    'sanitize_id',
    'write_csv',
    'generate_csv',
    'generate_llm_prompt',
    'save_outputs',
    
    # State management
    'save_state',
    'load_state'
]
