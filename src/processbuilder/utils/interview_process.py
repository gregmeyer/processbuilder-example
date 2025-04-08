"""
Main interview process for Process Builder.
"""

import os
from typing import Optional, TYPE_CHECKING
import csv

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

from ..models.base import ProcessStep, ProcessNote
from .input_handlers import get_step_input, get_next_step_input, prompt_for_confirmation
from .ui_helpers import print_header, display_menu, clear_screen
from .file_operations import save_csv_data
from .process_management import view_all_steps, edit_step, generate_outputs
from .interview import (
    handle_step_title,
    handle_step_description,
    handle_step_decision,
    handle_step_outcomes,
    handle_next_steps,
    handle_next_step_input,
    handle_step_notes,
    handle_validation_rules,
    handle_error_codes
)
from .state_management import save_state, load_state
from .output_generator import (
    generate_mermaid_diagram,
    generate_executive_summary,
    generate_llm_prompt
)

def create_step(builder: 'ProcessBuilder', is_first_step: bool = False, options: dict = None) -> bool:
    """Creates a new step in the process builder.
    
    Args:
        builder: The ProcessBuilder instance
        is_first_step: Whether this is the first step being created
        options: Optional dictionary of configuration options
        
    Returns:
        Whether the step was created successfully
    """
    if options is None:
        options = {}
    
    print("\n=== Creating New Step ===")
    
    # Get step details
    print("\nFirst, let's give this step a unique ID (this will be used to reference the step)")
    step_id = get_step_input(builder, "Step ID")
    
    print("\nNow, describe what happens in this step")
    description = get_step_input(builder, "Step Description")
    
    print("\nWhat decision needs to be made at this step? (This should be a yes/no question)")
    decision = get_step_input(builder, "Decision Question")
    
    # Ensure the decision ends with a question mark
    if not decision.endswith("?"):
        decision = decision + "?"
    
    print("\nWhat happens if the decision is 'yes'?")
    success_outcome = get_step_input(builder, "Success Outcome")
    
    print("\nWhat happens if the decision is 'no'?")
    failure_outcome = get_step_input(builder, "Failure Outcome")
    
    print("\nWhat's the next step if the decision is 'yes'?")
    print("(Enter 'End' if this is the final step, or enter the ID of the next step)")
    next_step_success = get_next_step_input(builder, "Next Step on Success")
    
    print("\nWhat's the next step if the decision is 'no'?")
    print("(Enter 'End' if this is the final step, or enter the ID of the next step)")
    next_step_failure = get_next_step_input(builder, "Next Step on Failure")
    
    # Create the step
    step = ProcessStep(
        step_id=step_id,
        description=description,
        decision=decision,
        success_outcome=success_outcome,
        failure_outcome=failure_outcome,
        next_step_success=next_step_success,
        next_step_failure=next_step_failure
    )
    
    # Add optional features if enabled
    if options.get('include_notes', False):
        note_id = handle_step_notes(builder, step_id, description, decision)
        if note_id:
            step.note_id = note_id
    
    if options.get('include_validation', False):
        validation_rules = handle_validation_rules(builder, step_id, description, decision)
        if validation_rules:
            step.validation_rules = validation_rules
    
    if options.get('include_error_codes', False):
        error_codes = handle_error_codes(builder, step_id, description, decision, failure_outcome)
        if error_codes:
            step.error_codes = error_codes
    
    # Add the step to the builder
    if not builder.add_step(step, interactive=True):
        return False
        
    # Save the state
    from datetime import datetime
    save_state(
        process_name=builder.process_name,
        timestamp=datetime.now(),
        steps=builder.steps,
        notes=builder.notes,
        start_step_id=builder.start_step_id
    )
    
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
    """Run the interactive interview process."""
    print("="*40)
    print("=======  Process Builder Interview  =======")
    print("="*40)
    print()
    
    # Check for saved processes and examples
    from pathlib import Path
    import os
    
    # Get the absolute path to the processbuilder-example directory
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    output_dir = base_dir / "output"
    examples_dir = base_dir / "examples"
    
    saved_processes = []
    example_processes = []
    
    # Check for saved processes
    if output_dir.exists():
        for process_dir in output_dir.iterdir():
            if process_dir.is_dir():
                # Check for timestamped subdirectories
                for timestamp_dir in process_dir.iterdir():
                    if timestamp_dir.is_dir():
                        # Check for any process files in the timestamp directory
                        has_process_files = False
                        for file in timestamp_dir.iterdir():
                            if file.suffix in ['.json', '.csv']:
                                has_process_files = True
                                break
                        if has_process_files:
                            saved_processes.append(process_dir.name)
                            break  # Found a valid process, move to next process directory
    
    # Check for example processes
    if examples_dir.exists():
        for process_dir in examples_dir.iterdir():
            if process_dir.is_dir() and not process_dir.name.startswith('.'):
                example_processes.append(process_dir.name)
    
    # Show menu options
    print("\nWould you like to:")
    print("1. Create a new process")
    if saved_processes:
        print("2. Load a saved process")
    if example_processes:
        print("3. Load an example process")
    
    # Get user choice
    process_loaded = False
    is_new_process = False
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        if choice == "1":
            print("\nCreating a new process...")
            is_new_process = True
            break
        elif choice == "2" and saved_processes:
            print("\nAvailable saved processes:")
            for i, process in enumerate(saved_processes, 1):
                print(f"{i}. {process}")
            while True:
                process_choice = input("\nEnter the number of the process to load: ").strip()
                if process_choice.isdigit() and 1 <= int(process_choice) <= len(saved_processes):
                    process_name = saved_processes[int(process_choice) - 1]
                    process_dir = output_dir / process_name
                    
                    # Find the most recent timestamp directory
                    timestamp_dirs = [d for d in process_dir.iterdir() if d.is_dir()]
                    if not timestamp_dirs:
                        print("\n" + "="*40)
                        print("ERROR: No timestamp directories found")
                        print("="*40)
                        print(f"Could not find any timestamp directories in {process_dir}")
                        print("\nPlease try again or create a new process.")
                        break
                    
                    # Sort by name (which is the timestamp) and get the most recent
                    latest_dir = sorted(timestamp_dirs, reverse=True)[0]
                    state_file = latest_dir / f"{process_name}_state.json"
                    
                    try:
                        # If state file doesn't exist, create it from CSV files
                        if not state_file.exists():
                            steps = []
                            notes = []
                            
                            # Read steps from CSV
                            steps_file = latest_dir / "process_steps.csv"
                            if steps_file.exists():
                                with open(steps_file, "r") as f:
                                    reader = csv.DictReader(f)
                                    for row in reader:
                                        if not row or not row.get("Step ID"):
                                            continue
                                            
                                        step = ProcessStep(
                                            step_id=row.get("Step ID", "").strip(),
                                            description=row.get("Description", "").strip(),
                                            decision=row.get("Decision", "").strip(),
                                            success_outcome=row.get("Success Outcome", "").strip(),
                                            failure_outcome=row.get("Failure Outcome", "").strip(),
                                            next_step_success=row.get("Next Step (Success)", "end").strip(),
                                            next_step_failure=row.get("Next Step (Failure)", "end").strip()
                                        )
                                        steps.append(step)
                            
                            # Read notes from CSV
                            notes_file = latest_dir / "process_notes.csv"
                            if notes_file.exists():
                                with open(notes_file, "r") as f:
                                    reader = csv.DictReader(f)
                                    for row in reader:
                                        if not row or not row.get("Note ID"):
                                            continue
                                            
                                        note = ProcessNote(
                                            note_id=row.get("Note ID", "").strip(),
                                            content=row.get("Content", "").strip(),
                                            step_id=row.get("Step ID", "").strip()
                                        )
                                        notes.append(note)
                            
                            # Create and save state
                            from datetime import datetime
                            state = {
                                "process_name": process_name,
                                "timestamp": datetime.now().isoformat(),
                                "steps": [step.to_dict() for step in steps],
                                "notes": [note.to_dict() for note in notes],
                                "start_step_id": steps[0].step_id if steps else None
                            }
                            
                            with open(state_file, 'w') as f:
                                import json
                                json.dump(state, f, indent=2)
                        
                        # Load the state (either existing or newly created)
                        state = load_state(str(state_file))
                        builder.process_name = state["process_name"]
                        builder.timestamp = state["timestamp"]
                        builder.steps = [ProcessStep.from_dict(step) for step in state["steps"]]
                        builder.notes = [ProcessNote.from_dict(note) for note in state["notes"]]
                        builder.start_step_id = state["start_step_id"]
                        print(f"\nSuccessfully loaded process: {process_name}")
                        process_loaded = True
                        break  # Break out of the process selection loop
                    except Exception as e:
                        print("\n" + "="*40)
                        print("ERROR: Failed to load process")
                        print("="*40)
                        print(f"Error details: {str(e)}")
                        print("\nPlease try again or create a new process.")
                        break  # Break out of the process selection loop
                else:
                    print("Invalid choice. Please try again.")
            if process_loaded:
                break  # Break out of the outer loop
        elif choice == "3" and example_processes:
            print("\nAvailable example processes:")
            for i, process in enumerate(example_processes, 1):
                print(f"{i}. {process}")
            while True:
                process_choice = input("\nEnter the number of the example to load: ").strip()
                if process_choice.isdigit() and 1 <= int(process_choice) <= len(example_processes):
                    process_name = example_processes[int(process_choice) - 1]
                    process_dir = examples_dir / process_name
                    steps_file = process_dir / "process_steps.csv"
                    notes_file = process_dir / "process_notes.csv"
                    try:
                        if steps_file.exists():
                            with open(steps_file, "r") as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    # Skip empty rows
                                    if not row or not row.get("Step ID"):
                                        continue
                                        
                                    # Get required fields with default values
                                    step_id = row.get("Step ID", "").strip()
                                    description = row.get("Description", "").strip()
                                    decision = row.get("Decision", "").strip()
                                    success_outcome = row.get("Success Outcome", "").strip()
                                    failure_outcome = row.get("Failure Outcome", "").strip()
                                    next_step_success = row.get("Next Step (Success)", "end").strip()
                                    next_step_failure = row.get("Next Step (Failure)", "end").strip()
                                    
                                    # Skip if required fields are empty
                                    if not all([step_id, description, decision, success_outcome, failure_outcome]):
                                        continue
                                        
                                    step = ProcessStep(
                                        step_id=step_id,
                                        description=description,
                                        decision=decision,
                                        success_outcome=success_outcome,
                                        failure_outcome=failure_outcome,
                                        next_step_success=next_step_success,
                                        next_step_failure=next_step_failure
                                    )
                                    builder.add_step(step, interactive=True)
                        if notes_file.exists():
                            with open(notes_file, "r") as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    # Skip empty rows
                                    if not row or not row.get("Note ID"):
                                        continue
                                        
                                    # Get required fields with default values
                                    note_id = row.get("Note ID", "").strip()
                                    content = row.get("Content", "").strip()
                                    step_id = row.get("Step ID", "").strip()
                                    
                                    # Skip if required fields are empty
                                    if not all([note_id, content, step_id]):
                                        continue
                                        
                                    note = ProcessNote(
                                        note_id=note_id,
                                        content=content,
                                        step_id=step_id
                                    )
                                    builder.notes.append(note)
                        builder.process_name = process_name  # Set the process name
                        
                        # Save the loaded example as a new process in the output directory
                        from datetime import datetime
                        timestamp = datetime.now()  # Get the actual datetime object
                        process_output_dir = output_dir / process_name
                        process_output_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save process state
                        save_state(
                            process_name=builder.process_name,
                            timestamp=timestamp,
                            steps=builder.steps,
                            notes=builder.notes,
                            start_step_id=builder.start_step_id,
                            output_dir=str(process_output_dir)
                        )
                        
                        print(f"\nSuccessfully loaded example process: {process_name}")
                        print(f"Saved as new process in: {process_output_dir}")
                        process_loaded = True
                        break  # Break out of the process selection loop
                    except Exception as e:
                        print("\n" + "="*40)
                        print("ERROR: Failed to load example process")
                        print("="*40)
                        print(f"Error details: {str(e)}")
                        print("\nPlease try again or create a new process.")
                        break  # Break out of the process selection loop
                else:
                    print("Invalid choice. Please try again.")
            if process_loaded:
                break  # Break out of the outer loop
        else:
            print("Invalid choice. Please try again.")
    
    # Show the main menu after loading a process or creating a new one
    print("\nProcess Information:")
    print(f"Process name: {builder.process_name}")
    print(f"Current steps: {len(builder.steps)}")
    print(f"Current notes: {len(builder.notes)}")
    print()
    
    # Define default options
    options = {
        'include_notes': False,
        'include_validation': False,
        'include_error_codes': False,
        'use_ai_suggestions': False
    }
    
    # Ask about options regardless of whether this is a new process or loaded
    options = {
        'include_notes': prompt_for_confirmation("Would you like to include notes for steps?"),
        'include_validation': prompt_for_confirmation("Would you like to include validation rules for steps?"),
        'include_error_codes': prompt_for_confirmation("Would you like to include error codes for steps?"),
        'use_ai_suggestions': prompt_for_confirmation("Would you like to use AI suggestions throughout the process?")
    }
    
    # Only create first step if this is a new process
    if is_new_process:
        if not create_step(builder, is_first_step=True, options=options):
            print("\nProcess creation cancelled.")
            return
    
    # Show the main menu
    while True:
        print("\nWould you like to:")
        print("1. View all steps")
        print("2. Edit a step")
        print("3. Add another step")
        print("4. Generate outputs")
        print("5. Start over")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            view_all_steps(builder)
        elif choice == "2":
            edit_step(builder, options=options)
        elif choice == "3":
            if not create_step(builder, options=options):
                print("\nStep creation cancelled.")
        elif choice == "4":
            generate_outputs(builder)
        elif choice == "5":
            # Clear the current process
            builder.steps = []
            builder.notes = []
            builder.process_name = ""
            builder.start_step_id = None
            
            # Show process creation menu again
            print("\nStarting a new process...")
            process_loaded = False
            is_new_process = True
            
            # Get process name
            while True:
                process_name = input("\nEnter a name for your process: ").strip()
                if process_name:
                    builder.process_name = process_name
                    break
                print("Process name cannot be empty.")
            
            # Ask about optional features
            options = {
                'include_notes': prompt_for_confirmation("Would you like to include notes for steps?"),
                'include_validation': prompt_for_confirmation("Would you like to include validation rules for steps?"),
                'include_error_codes': prompt_for_confirmation("Would you like to include error codes for steps?"),
                'use_ai_suggestions': prompt_for_confirmation("Would you like to use AI suggestions throughout the process?")
            }
            
            # Create first step
            if not create_step(builder, is_first_step=True, options=options):
                print("\nProcess creation cancelled.")
                continue
            
            # Show process information
            print("\nProcess Information:")
            print(f"Process name: {builder.process_name}")
            print(f"Current steps: {len(builder.steps)}")
            print(f"Current notes: {len(builder.notes)}")
            print()
            
        elif choice == "6":
            print("\nThank you for using the Process Builder!")
            break
        else:
            print("\nInvalid choice. Please try again.")

def generate_outputs(builder: 'ProcessBuilder') -> None:
    """Generate output files for the process."""
    if not builder.steps:
        print("\nNo steps to generate outputs for.")
        return
    
    # Ask if user wants to save as an example
    save_as_example = prompt_for_confirmation("\nWould you like to save this process as an example?")
    
    if save_as_example:
        # Get example name
        while True:
            example_name = input("\nEnter a name for the example (use underscores instead of spaces): ").strip()
            if example_name:
                break
            print("Example name cannot be empty.")
        
        # Create example directory
        from pathlib import Path
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        example_dir = base_dir / "examples" / example_name
        example_dir.mkdir(parents=True, exist_ok=True)
        
        # Save steps as CSV
        steps_file = example_dir / "process_steps.csv"
        with open(steps_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Step ID", "Description", "Decision", "Success Outcome", "Failure Outcome", "Next Step (Success)", "Next Step (Failure)"])
            writer.writeheader()
            for step in builder.steps:
                writer.writerow({
                    "Step ID": step.step_id,
                    "Description": step.description,
                    "Decision": step.decision,
                    "Success Outcome": step.success_outcome,
                    "Failure Outcome": step.failure_outcome,
                    "Next Step (Success)": step.next_step_success,
                    "Next Step (Failure)": step.next_step_failure
                })
        
        # Save notes as CSV if any exist
        if builder.notes:
            notes_file = example_dir / "process_notes.csv"
            with open(notes_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Note ID", "Content", "Step ID"])
                writer.writeheader()
                for note in builder.notes:
                    writer.writerow({
                        "Note ID": note.note_id,
                        "Content": note.content,
                        "Step ID": note.step_id
                    })
        
        print(f"\nSuccessfully saved process as example: {example_name}")
        print(f"Example files saved in: {example_dir}")
    
    # Generate outputs in the output directory
    from datetime import datetime
    from pathlib import Path
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    output_dir = base_dir / "output"
    
    # Create process directory if it doesn't exist
    process_dir = output_dir / builder.process_name
    process_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamp for state file
    timestamp = datetime.now()
    
    # Save process state
    save_state(
        process_name=builder.process_name,
        timestamp=timestamp,
        steps=builder.steps,
        notes=builder.notes,
        start_step_id=builder.start_step_id,
        output_dir=str(process_dir)
    )
    
    # Save steps as CSV
    steps_file = process_dir / "process_steps.csv"
    with open(steps_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Step ID", "Description", "Decision", "Success Outcome", "Failure Outcome", "Next Step (Success)", "Next Step (Failure)"])
        writer.writeheader()
        for step in builder.steps:
            writer.writerow({
                "Step ID": step.step_id,
                "Description": step.description,
                "Decision": step.decision,
                "Success Outcome": step.success_outcome,
                "Failure Outcome": step.failure_outcome,
                "Next Step (Success)": step.next_step_success,
                "Next Step (Failure)": step.next_step_failure
            })
    
    # Save notes as CSV if any exist
    if builder.notes:
        notes_file = process_dir / "process_notes.csv"
        with open(notes_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Note ID", "Content", "Step ID"])
            writer.writeheader()
            for note in builder.notes:
                writer.writerow({
                    "Note ID": note.note_id,
                    "Content": note.content,
                    "Step ID": note.step_id
                })
    
    # Generate Mermaid diagram
    mermaid_file = process_dir / "process_diagram.mmd"
    with open(mermaid_file, "w") as f:
        f.write(generate_mermaid_diagram(builder.steps, builder.start_step_id))
    
    # Generate PNG diagram if mermaid-cli is installed
    try:
        import subprocess
        png_file = process_dir / "process_diagram.png"
        subprocess.run(["mmdc", "-i", str(mermaid_file), "-o", str(png_file)], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\nWarning: Could not generate PNG diagram. Please install mermaid-cli to generate PNG diagrams.")
    
    # Generate executive summary
    summary_file = process_dir / "executive_summary.md"
    with open(summary_file, "w") as f:
        f.write(generate_executive_summary(builder.steps, builder.notes))
    
    # Generate LLM prompt
    prompt_file = process_dir / "llm_prompt.txt"
    with open(prompt_file, "w") as f:
        f.write(generate_llm_prompt(builder.steps, builder.notes))
    
    print(f"\nSuccessfully generated outputs in: {process_dir}")
    print("Generated files:")
    print(f"- {process_dir / f'{builder.process_name}_state.json'}")
    print(f"- {process_dir / 'process_steps.csv'}")
    if builder.notes:
        print(f"- {process_dir / 'process_notes.csv'}")
    print(f"- {process_dir / 'process_diagram.mmd'}")
    print(f"- {process_dir / 'process_diagram.png'}")
    print(f"- {process_dir / 'executive_summary.md'}")
    print(f"- {process_dir / 'llm_prompt.txt'}")

    