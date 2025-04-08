"""Test script to load a process from CSV files."""

import csv
from pathlib import Path
from processbuilder.builder import ProcessBuilder
from processbuilder.models.base import ProcessStep, ProcessNote
from processbuilder.models.validator import ProcessValidator

def main():
    """Load a process from CSV files and print information about it."""
    # Create a ProcessBuilder instance
    builder = ProcessBuilder(process_name="make_a_sandwich")
    validator = ProcessValidator()
    
    # Load paths
    steps_path = Path("examples/make_a_sandwich/process_steps.csv")
    notes_path = Path("examples/make_a_sandwich/process_notes.csv")
    
    # First pass: Create step ID map
    step_id_map = {}  # Map from original ID to alphanumeric ID
    with open(steps_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert step ID to alphanumeric
            original_id = row["Step ID"]
            step_id = ''.join(c for c in original_id if c.isalnum())
            step_id_map[original_id] = step_id
            
            # Also map the next step IDs
            next_success = row["Next Step (Success)"]
            next_failure = row["Next Step (Failure)"]
            if next_success.lower() != 'end':
                next_success_id = ''.join(c for c in next_success if c.isalnum())
                step_id_map[next_success] = next_success_id
            if next_failure.lower() != 'end':
                next_failure_id = ''.join(c for c in next_failure if c.isalnum())
                step_id_map[next_failure] = next_failure_id
    
    # Second pass: Create steps with converted IDs
    steps = []
    with open(steps_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert step ID to alphanumeric
            step_id = step_id_map[row["Step ID"]]
            
            # Convert next step IDs to alphanumeric
            next_success = row["Next Step (Success)"]
            next_failure = row["Next Step (Failure)"]
            if next_success.lower() != 'end':
                next_success = step_id_map[next_success]
            if next_failure.lower() != 'end':
                next_failure = step_id_map[next_failure]
            
            # Create step with converted IDs
            step = ProcessStep(
                step_id=step_id,
                description=row["Description"],
                decision=row["Decision"],
                success_outcome=row["Success Outcome"],
                failure_outcome=row["Failure Outcome"],
                next_step_success=next_success,
                next_step_failure=next_failure
            )
            steps.append(step)
    
    # Add all steps to builder
    for step in steps:
        # If a next step doesn't exist in our step list, treat it as 'end'
        if step.next_step_success.lower() != 'end' and not any(s.step_id == step.next_step_success for s in steps):
            print(f"Warning: Step {step.step_id} references non-existent success step {step.next_step_success}, treating as 'end'")
            step.next_step_success = 'end'
        if step.next_step_failure.lower() != 'end' and not any(s.step_id == step.next_step_failure for s in steps):
            print(f"Warning: Step {step.step_id} references non-existent failure step {step.next_step_failure}, treating as 'end'")
            step.next_step_failure = 'end'
        
        # Add the step to the builder
        builder.add_step(step)
    
    # Add steps to validator and validate them
    validator.steps = steps
    invalid_steps = []
    for step in steps:
        is_valid, errors = validator.validate_step(step)
        if not is_valid:
            print(f"Warning: Step {step.step_id} has validation errors: {errors}")
            invalid_steps.append(step)
    
    # Load notes
    with open(notes_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert step ID to alphanumeric using the map
            original_step_id = row["Related Step ID"]
            step_id = step_id_map[original_step_id]
            
            # Truncate content to 200 characters if needed
            content = row["Content"]
            if len(content) > 200:
                content = content[:197] + "..."
            
            note = ProcessNote(
                note_id=row["Note ID"],
                content=content,
                step_id=step_id
            )
            is_valid, errors = validator.validate_note(note)
            if not is_valid:
                print(f"Warning: Note {note.note_id} has validation errors: {errors}")
                continue
            builder.add_note(note)
    
    # Print process information
    print(f"\nProcess loaded successfully!")
    print(f"Number of steps: {len(builder.steps)}")
    print(f"Number of notes: {len(builder.notes)}")
    print(f"Number of invalid steps: {len(invalid_steps)}")
    
    # Print first step and its notes
    if builder.steps:
        first_step = builder.steps[0]
        print(f"\nFirst step: {first_step.step_id}")
        print(f"Description: {first_step.description}")
        print(f"Decision: {first_step.decision}")
        print(f"Success outcome: {first_step.success_outcome}")
        print(f"Failure outcome: {first_step.failure_outcome}")
        print(f"Next step on success: {first_step.next_step_success}")
        print(f"Next step on failure: {first_step.next_step_failure}")
        
        # Print associated notes
        step_notes = [note for note in builder.notes if note.step_id == first_step.step_id]
        if step_notes:
            print("\nAssociated notes:")
            for note in step_notes:
                print(f"- {note.content}")

if __name__ == "__main__":
    main() 