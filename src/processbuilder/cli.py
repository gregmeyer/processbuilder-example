"""
Command-line interface for the Process Builder.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional, List

from .builder import ProcessBuilder
from .config import Config
from .models import ProcessStep, ProcessNote

def get_step_input(prompt: str) -> str:
    """Get input from user with validation."""
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if response:
            return response
        print("Please provide a response.")

def get_next_step_input(builder: ProcessBuilder, prompt: str) -> str:
    """Get next step input with list of existing steps."""
    if builder.steps:
        print("\nExisting steps:")
        for i, step in enumerate(builder.steps, 1):
            print(f"{i}. {step.step_id}")
        print("Or enter 'End' to finish the process")
    
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if not response:
            print("Please provide a response.")
            continue
            
        # Check if it's a number reference to existing step
        if response.isdigit():
            step_num = int(response)
            if 1 <= step_num <= len(builder.steps):
                return builder.steps[step_num - 1].step_id
            print(f"Please enter a number between 1 and {len(builder.steps)}")
            continue
            
        # Check if it's 'End' or a new step name
        if response.lower() == 'end' or not any(s.step_id == response for s in builder.steps):
            return response
            
        print("Please enter a new step name or 'End'")

def run_interview(builder: ProcessBuilder) -> None:
    """Run the interactive interview process."""
    print(f"\n=== Process Builder: {builder.process_name} ===\n")
    
    while True:
        # Get step details
        step_id = get_step_input("What is the title of this step? (e.g., 'User Authentication', 'Data Validation')")
        description = get_step_input("What happens in this step?")
        decision = get_step_input("What decision needs to be made?")
        success_outcome = get_step_input("What happens if this step succeeds?")
        failure_outcome = get_step_input("What happens if this step fails?")
        
        # Optional note
        add_note = get_step_input("Would you like to add a note for this step? (y/n)").lower()
        note_id = None
        note_content = None
        if add_note == 'y':
            note_content = get_step_input("What's the note content?")
            note_id = f"Note{builder.current_note_id}"
            builder.current_note_id += 1
        
        # Get next steps with step selection
        next_step_success = get_next_step_input(
            builder,
            "What's the next step if successful? (Enter step number, new step name, or 'End')"
        )
        next_step_failure = get_next_step_input(
            builder,
            "What's the next step if failed? (Enter step number, new step name, or 'End')"
        )
        
        # Enhanced fields
        validation_rules = get_step_input("Any validation rules for this step? (Press Enter to skip)")
        error_codes = get_step_input("Any specific error codes? (Press Enter to skip)")
        retry_logic = get_step_input("Any retry logic? (Press Enter to skip)")
        
        # Create step
        step = ProcessStep(
            step_id=step_id,  # Use provided step ID instead of description
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            next_step_success=next_step_success,
            next_step_failure=next_step_failure,
            validation_rules=validation_rules if validation_rules else None,
            error_codes=error_codes if error_codes else None,
            retry_logic=retry_logic if retry_logic else None
        )
        
        # Add step and validate
        issues = builder.add_step(step)
        if issues:
            print("\n=== Validation Issues ===")
            for issue in issues:
                print(f"- {issue}")
            print("\nPlease fix these issues and try again.")
            continue
        
        # Add note if present
        if note_id and note_content:
            note = ProcessNote(
                note_id=note_id,
                content=note_content,
                related_step_id=step.step_id
            )
            note_issues = builder.add_note(note)
            if note_issues:
                print("\n=== Note Validation Issues ===")
                for issue in note_issues:
                    print(f"- {issue}")
                print("\nPlease fix these issues and try again.")
                continue
        
        # Evaluate step design
        print("\nEvaluating step design with AI...")
        design_feedback = builder.evaluate_step_design(step)
        print("\n=== Step Design Feedback ===")
        print(design_feedback)
        
        # Ask if user wants to modify the step based on feedback
        modify = get_step_input("\nWould you like to modify this step based on the feedback? (y/n)").lower()
        if modify == 'y':
            print("\nPlease re-enter the step details with improvements:")
            continue
        
        # Ask if user wants to add another step
        continue_process = get_step_input("Add another step? (y/n)").lower()
        if continue_process != 'y':
            break
    
    # Generate outputs
    builder.generate_csv()
    builder.generate_mermaid_diagram()
    llm_prompt = builder.generate_llm_prompt()
    print("\n=== LLM Prompt ===")
    print(llm_prompt)
    
    # Write LLM prompt to file
    if builder.output_dir:
        prompt_file = builder.output_dir / f"{builder.process_name}_prompt.txt"
        prompt_file.write_text(llm_prompt)
        print(f"LLM prompt saved to: {prompt_file}")

def load_from_csv(builder: ProcessBuilder, steps_csv_path: Path, notes_csv_path: Optional[Path] = None) -> None:
    """Load process steps and notes from CSV files."""
    import csv
    
    # Load steps from CSV
    try:
        with open(steps_csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                step = ProcessStep(
                    step_id=row["Step ID"],
                    description=row["Description"],
                    decision=row["Decision"],
                    success_outcome=row["Success Outcome"],
                    failure_outcome=row["Failure Outcome"],
                    note_id=row["Linked Note ID"] if row["Linked Note ID"] else None,
                    next_step_success=row["Next Step (Success)"],
                    next_step_failure=row["Next Step (Failure)"],
                    validation_rules=row["Validation Rules"] if row["Validation Rules"] else None,
                    error_codes=row["Error Codes"] if row["Error Codes"] else None,
                    retry_logic=row["Retry Logic"] if row["Retry Logic"] else None
                )
                issues = builder.add_step(step)
                if issues:
                    print(f"\nWarning: Issues found in step {step.step_id}:")
                    for issue in issues:
                        print(f"- {issue}")
    except FileNotFoundError:
        print(f"Error: Steps CSV file not found: {steps_csv_path}")
        sys.exit(1)
    
    # Load notes from CSV if provided
    if notes_csv_path:
        try:
            with open(notes_csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    note = ProcessNote(
                        note_id=row["Note ID"],
                        content=row["Content"],
                        related_step_id=row["Related Step ID"]
                    )
                    issues = builder.add_note(note)
                    if issues:
                        print(f"\nWarning: Issues found in note {note.note_id}:")
                        for issue in issues:
                            print(f"- {issue}")
        except FileNotFoundError:
            print(f"Error: Notes CSV file not found: {notes_csv_path}")
            sys.exit(1)

def main() -> None:
    """Main entry point for the process builder."""
    parser = argparse.ArgumentParser(description="Process Builder Utility")
    parser.add_argument("--steps-csv", help="Path to CSV file containing process steps")
    parser.add_argument("--notes-csv", help="Path to CSV file containing process notes")
    args = parser.parse_args()
    
    # Get process name
    process_name = input("Enter the name of the process: ").strip()
    
    # Initialize builder with configuration
    config = Config()
    builder = ProcessBuilder(process_name, config)
    
    # Determine if we're loading from CSV or running an interview
    if args.steps_csv:
        load_from_csv(builder, Path(args.steps_csv), Path(args.notes_csv) if args.notes_csv else None)
        
        # Generate outputs
        builder.generate_csv()
        builder.generate_mermaid_diagram()
        llm_prompt = builder.generate_llm_prompt()
        print("\n=== LLM Prompt ===")
        print(llm_prompt)
        
        # Write LLM prompt to file
        if builder.output_dir:
            prompt_file = builder.output_dir / f"{builder.process_name}_prompt.txt"
            prompt_file.write_text(llm_prompt)
            print(f"LLM prompt saved to: {prompt_file}")
    else:
        # Run the interactive interview
        run_interview(builder)

if __name__ == "__main__":
    main() 