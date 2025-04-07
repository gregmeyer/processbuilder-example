"""
Helper functions for process management in the Process Builder.
"""
from typing import List, Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

from ..models import ProcessNote
from .input_handlers import get_step_input, prompt_for_confirmation

def view_all_steps(builder: 'ProcessBuilder') -> None:
    """Display all steps with their details and connections."""
    if not builder.steps:
        print("\nNo steps available. Please add steps first using option 3.")
        return
    
    print("="*40)
    print("=======  Process Steps  =======")
    print("="*40)
    print()  # Add space for better readability
    
    for i, step in enumerate(builder.steps, 1):
        # Find predecessor steps
        predecessors = []
        for other_step in builder.steps:
            if other_step.next_step_success == step.step_id:
                predecessors.append(f"{other_step.step_id} (success)")
            if other_step.next_step_failure == step.step_id:
                predecessors.append(f"{other_step.step_id} (failure)")
        
        print(f"\nStep {i}: {step.step_id}")
        print(f"Description: {step.description}")
        print(f"Decision: {step.decision}")
        print(f"Success Outcome: {step.success_outcome}")
        print(f"Failure Outcome: {step.failure_outcome}")
        
        # Show flow connections
        if predecessors:
            print("\nPredecessors:")
            for pred in predecessors:
                print(f"  - {pred}")
        else:
            print("\nPredecessors: None (Start of process)")
        
        # Show next steps
        print("\nNext Steps:")
        if step.next_step_success.lower() == 'end':
            print("  - End (Success)")
        else:
            print(f"  - {step.next_step_success} (Success)")
        if step.next_step_failure.lower() == 'end':
            print("  - End (Failure)")
        else:
            print(f"  - {step.next_step_failure} (Failure)")
        
        # Show additional details
        if step.note_id:
            note = next(n for n in builder.notes if n.note_id == step.note_id)
            print(f"\nNote: {note.content}")
        if step.validation_rules:
            print(f"\nValidation Rules: {step.validation_rules}")
        if step.error_codes:
            print(f"\nError Codes: {step.error_codes}")
        print("-" * 40)  # Separator between steps

def display_edit_options(step_id: str) -> None:
    """Display the edit options for a step."""
    print("="*40)
    print(f"=======  Edit options for step: {step_id}  =======")
    print("="*40)
    print("1. Title")
    print("2. Description")
    print("3. Decision")
    print("4. Success Outcome")
    print("5. Failure Outcome")
    print("6. Note")
    print("7. Validation Rules")
    print("8. Error Codes")
    print("9. Next Step (Success)")
    print("10. Next Step (Failure)")
    print("11. Cancel")
    print()  # Add consistent spacing

def handle_edit_selection(builder: 'ProcessBuilder', step, choice: str) -> None:
    """Handle the user's edit selection.
    
    Args:
        builder: The ProcessBuilder instance
        step: The step to edit
        choice: The user's choice
    """
    if choice == "1":
        print(f"\nCurrent title: {step.step_id}")
        new_title = input("Enter new title: ").strip()
        if new_title:
            step.step_id = new_title
            print(f"Title updated to: {new_title}")
        else:
            print("Title unchanged.")
    elif choice == "2":
        print(f"\nCurrent description: {step.description}")
        new_description = input("Enter new description: ").strip()
        if new_description:
            step.description = new_description
            print(f"Description updated.")
        else:
            print("Description unchanged.")
    elif choice == "3":
        print(f"\nCurrent decision: {step.decision}")
        new_decision = input("Enter new decision: ").strip()
        if new_decision:
            step.decision = new_decision
            print(f"Decision updated.")
        else:
            print("Decision unchanged.")
    elif choice == "4":
        print(f"\nCurrent success outcome: {step.success_outcome}")
        new_success = input("Enter new success outcome: ").strip()
        if new_success:
            step.success_outcome = new_success
            print(f"Success outcome updated.")
        else:
            print("Success outcome unchanged.")
    elif choice == "5":
        print(f"\nCurrent failure outcome: {step.failure_outcome}")
        new_failure = input("Enter new failure outcome: ").strip()
        if new_failure:
            step.failure_outcome = new_failure
            print(f"Failure outcome updated.")
        else:
            print("Failure outcome unchanged.")
    elif choice == "6":
        print("\nEdit Note:")
        if step.note_id:
            note = next(n for n in builder.notes if n.note_id == step.note_id)
            new_note = input("Enter new note content: ").strip()
            if new_note:
                note.content = new_note
        else:
            add_note = prompt_for_confirmation("No note exists. Would you like to add one?")
            if add_note:
                note_content = input("Enter note content: ").strip()
                if note_content:
                    note_id = f"Note{builder.current_note_id}"
                    builder.notes.append(ProcessNote(note_id, note_content, step.step_id))
                    step.note_id = note_id
                    builder.current_note_id += 1
    elif choice == "7":
        print("\nEdit Validation Rules:")
        if step.validation_rules:
            print(f"Current validation rules: {step.validation_rules}")
        new_rules = input("Enter new validation rules: ").strip()
        step.validation_rules = new_rules if new_rules else None
    elif choice == "8":
        print("\nEdit Error Codes:")
        if step.error_codes:
            print(f"Current error codes: {step.error_codes}")
        new_codes = input("Enter new error codes: ").strip()
        step.error_codes = new_codes if new_codes else None
    elif choice == "9":
        print(f"\nCurrent next step for success: {step.next_step_success}")
        while True:
            new_next = input("Enter new next step for success (or 'End'): ").strip()
            if builder.validate_next_step(new_next):
                step.next_step_success = new_next
                break
            print("Please enter a valid step name or 'End'")
    elif choice == "10":
        print(f"\nCurrent next step for failure: {step.next_step_failure}")
        while True:
            new_next = input("Enter new next step for failure (or 'End'): ").strip()
            if builder.validate_next_step(new_next):
                step.next_step_failure = new_next
                break
            print("Please enter a valid step name or 'End'")
    elif choice == "11":
        print("\nEdit cancelled.")
    else:
        print("\nInvalid choice. Please try again.")

def validate_after_edit(builder: 'ProcessBuilder') -> List[str]:
    """Validate the process flow after an edit.
    
    Args:
        builder: The ProcessBuilder instance
        
    Returns:
        List of flow issues
    """
    # Validate the process flow after editing
    print("\nValidating process flow after edit...")
    flow_issues = builder.validate_process_flow()
    
    if flow_issues:
        print("="*40)
        print("=======  Process Flow Validation Issues  =======")
        print("="*40)
        print()
        for issue in flow_issues:
            print(f"- {issue}")
        print("\nPlease fix these issues in the next edit.")
        print("The edit has been saved, but you may want to review these issues.")
    else:
        print("\nEdit successful! No validation issues found.")
        print("The process flow is valid.")
    
    return flow_issues

def edit_step(builder: 'ProcessBuilder') -> None:
    """Edit an existing step."""
    if not builder.steps:
        print("\nNo steps to edit. Please add a step first.")
        return
        
    print("="*40)
    print("=======  Edit Step  =======")
    print("="*40)
    print()  # Add extra spacing for better readability
    
    # Display all steps for selection
    print("\nAvailable steps:")
    for i, step in enumerate(builder.steps, 1):
        print(f"{i}. {step.step_id}")
    
    try:
        step_num = int(input("\nEnter step number to edit: ").strip())
        
        if 1 <= step_num <= len(builder.steps):
            # Get the actual step by index
            step = builder.steps[step_num-1]
            
            # Show edit options
            display_edit_options(step.step_id)
            
            # Get edit choice
            edit_choice = input("Enter your choice (1-11): ").strip()
            
            # Handle edit choice
            handle_edit_selection(builder, step, edit_choice)
            
            # Validate after edit
            validate_after_edit(builder)
        else:
            print("\nInvalid step number. Please try again.")
    except ValueError:
        print("\nPlease enter a valid number.")
    except Exception as e:
        print(f"\nAn error occurred while editing: {str(e)}")

def generate_outputs(builder: 'ProcessBuilder') -> None:
    """Generate all outputs for the process."""
    if not builder.steps:
        print("\nNo steps available. Please add steps first using option 3.")
        return
        
    # Generate outputs
    print("\nGenerating outputs...")
    builder.generate_csv()
    builder.generate_mermaid_diagram()
    
    # Generate and save LLM prompt
    llm_prompt = builder.generate_llm_prompt()
    print("\n=== LLM Prompt ===")
    print(llm_prompt)
    
    if builder.output_dir:
        prompt_file = builder.output_dir / f"{builder.process_name}_prompt.txt"
        prompt_file.write_text(llm_prompt)
        print(f"LLM prompt saved to: {prompt_file}")
    
    # Generate and save executive summary
    executive_summary = builder.generate_executive_summary()
    print("\n=== Executive Summary ===")
    print(executive_summary)
    
    if builder.output_dir:
        summary_file = builder.output_dir / f"{builder.process_name}_executive_summary.md"
        summary_file.write_text(executive_summary)
        print(f"Executive summary saved to: {summary_file}") 