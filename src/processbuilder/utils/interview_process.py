"""
Main interview process for Process Builder.
"""

import os
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

from .input_handlers import get_step_input, prompt_for_confirmation
from .ui_helpers import print_header, display_menu, clear_screen
from .file_operations import save_csv_data
from .process_management import view_all_steps, edit_step, generate_outputs
from .interview import (
    handle_step_title,
    handle_step_description,
    handle_step_decision,
    handle_step_outcomes,
    handle_next_steps,
    handle_step_notes,
    handle_validation_rules,
    handle_error_codes
)

def create_step(builder: 'ProcessBuilder', is_first_step: bool = False) -> bool:
    """Creates a new step in the process builder.
    
    Args:
        builder: The ProcessBuilder instance
        is_first_step: Whether this is the first step in the process
        
    Returns:
        True if a step was created, False otherwise
    """
    # Get step title with optional AI help
    title = handle_step_title(builder, is_first_step)
    if not title:
        return False
    
    # Create the step ID
    step_id = builder.create_step_id(title)
    print(f"\nCreating step with ID: {step_id}")
    
    # Get step description with optional AI help
    description = handle_step_description(builder, step_id)
    
    # Get step decision with optional AI help
    decision = handle_step_decision(builder, step_id, description)
    
    # Get success and failure outcomes with optional AI help
    success_outcome, failure_outcome = handle_step_outcomes(
        builder, step_id, description, decision
    )
    
    # Get next steps for success and failure paths with optional AI help
    next_step_success, next_step_failure = handle_next_steps(
        builder, step_id, description, decision, success_outcome, failure_outcome
    )
    
    # Get optional notes with optional AI help
    notes = handle_step_notes(builder, step_id, description, decision)
    
    # Get optional validation rules with optional AI help
    validation_rules = handle_validation_rules(builder, step_id, description, decision)
    
    # Get optional error codes with optional AI help
    error_codes = handle_error_codes(builder, step_id, description, decision, failure_outcome)
    
    # Add the step to the builder
    builder.add_step(
        step_id=step_id,
        title=title,
        description=description,
        decision=decision,
        success_outcome=success_outcome,
        failure_outcome=failure_outcome,
        next_step_success=next_step_success,
        next_step_failure=next_step_failure,
        notes=notes,
        validation_rules=validation_rules,
        error_codes=error_codes
    )
    
    print(f"\nStep '{step_id}' successfully added to the process!")
    return True

def add_more_steps(builder: 'ProcessBuilder') -> None:
    """Prompt the user to add more steps to the process.
    
    Args:
        builder: The ProcessBuilder instance
    """
    is_first_step = len(builder.steps) == 0
    
    while True:
        if is_first_step:
            print("\nLet's add the first step to your process.")
            if create_step(builder, is_first_step=True):
                is_first_step = False
            else:
                print("No step was created. Exiting.")
                break
        else:
            add_another = prompt_for_confirmation("\nWould you like to add another step?")
            if add_another:
                if not create_step(builder):
                    print("No step was created.")
            else:
                break

def run_interview(builder: 'ProcessBuilder') -> None:
    """Run the interactive interview process.
    
    Args:
        builder: The ProcessBuilder instance
    """
    clear_screen()
    print_header(f"Process Builder: {builder.name}")
    
    # Main interactive menu
    while True:
        choice = display_menu([
            "Add steps to the process",
            "View all steps in the process",
            "Edit an existing step",
            "Generate outputs",
            "Save and exit",
            "Exit without saving"
        ])
        
        if choice == "1":
            # Add steps
            add_more_steps(builder)
            
        elif choice == "2":
            # View all steps
            view_all_steps(builder)
            
        elif choice == "3":
            # Edit a step
            if builder.steps:
                edit_step(builder)
            else:
                print("There are no steps to edit. Please add steps first.")
            
        elif choice == "4":
            # Generate outputs
            if builder.steps:
                generate_outputs(builder)
            else:
                print("There are no steps to generate outputs from. Please add steps first.")
            
        elif choice == "5":
            # Save and exit
            output_dir = get_step_input("Enter the output directory for saving the CSV file:")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{builder.name}.csv")
            
            try:
                # Convert the process to CSV format
                csv_data = builder.to_csv()
                if not csv_data:
                    print("Warning: No data to save. Process may be empty.")
                else:
                    # Save the data
                    saved = save_csv_data(csv_data, output_path)
                    if saved:
                        print(f"Process saved to {output_path}")
                    else:
                        print("Failed to save the process.")
            except AttributeError as e:
                print(f"Error: Unable to save process. {str(e)}")
                print("This may be due to a missing method or attribute. Please contact support.")
            except Exception as e:
                print(f"Error while saving: {str(e)}")
            
            break
            
        elif choice == "6":
            # Exit without saving
            confirm_exit = prompt_for_confirmation("Are you sure you want to exit without saving?")
            if confirm_exit:
                print("Exiting without saving. All changes will be lost.")
                break
        
        print()  # Add a blank line for spacing 