"""
Helper functions for process management in the Process Builder.
"""
from typing import List, Optional, TYPE_CHECKING
from pathlib import Path

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

from ..models.base import ProcessNote, ProcessStep
from .input_handlers import get_step_input, prompt_for_confirmation
from .output_handling import generate_csv, generate_mermaid_diagram, generate_llm_prompt, save_outputs
from .ui_helpers import show_loading_animation

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

def sanitize_node_name(name: str) -> str:
    """Sanitize a node name to be compatible with Mermaid syntax.
    
    Args:
        name: The original node name
        
    Returns:
        A sanitized version of the name that's safe for Mermaid
    """
    # Remove any characters that could cause issues in Mermaid
    sanitized = ''.join(c for c in name if c.isalnum() or c in ['_', '-'])
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed_step'
    return sanitized

def handle_edit_selection(builder: 'ProcessBuilder', step, choice: str, options: dict = None) -> None:
    """Handle the user's edit selection.
    
    Args:
        builder: The ProcessBuilder instance
        step: The step to edit
        choice: The user's choice
        options: Dictionary of options including AI suggestions preference
    """
    if choice == "1":
        print(f"\nCurrent title: {step.step_id}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the title?")
                if want_suggestion:
                    show_loading_animation("Generating title suggestion", in_menu=True)
                    suggested_title = builder.generate_step_title(step.step_id, step.step_id, "success")
                    if suggested_title:
                        print(f"AI suggests the following title: '{suggested_title}'")
                        use_suggested = prompt_for_confirmation("Would you like to use this title?")
                        if use_suggested:
                            step.step_id = sanitize_node_name(suggested_title)
                            print(f"Title updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating title suggestion: {str(e)}")
        
        while True:
            new_title = input("Enter new title: ").strip()
            if not new_title:
                print("Title unchanged.")
                break
            if not builder.validate_step_name(new_title):
                print("Step name must contain only alphanumeric characters, underscores, or hyphens.")
                continue
            # Sanitize the title
            new_title = sanitize_node_name(new_title)
            step.step_id = new_title
            print(f"Title updated to: {new_title}")
            break
        display_edit_options(step.step_id)
    elif choice == "2":
        print(f"\nCurrent description: {step.description}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the description?")
                if want_suggestion:
                    show_loading_animation("Generating description suggestion", in_menu=True)
                    suggested_description = builder.generate_step_description(step.step_id)
                    if suggested_description:
                        print(f"AI suggests the following description: '{suggested_description}'")
                        use_suggested = prompt_for_confirmation("Would you like to use this description?")
                        if use_suggested:
                            step.description = suggested_description
                            print(f"Description updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating description suggestion: {str(e)}")
        
        # Get manual input
        new_description = input("Enter new description: ").strip()
        if new_description:
            step.description = new_description
            print(f"Description updated.")
        else:
            print("Description unchanged.")
        display_edit_options(step.step_id)
    elif choice == "3":
        print(f"\nCurrent decision: {step.decision}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the decision?")
                if want_suggestion:
                    show_loading_animation("Generating decision suggestion", in_menu=True)
                    suggested_decision = builder.generate_step_decision(step.step_id, step.description)
                    if suggested_decision:
                        print(f"AI suggests the following decision: '{suggested_decision}'")
                        use_suggested = prompt_for_confirmation("Would you like to use this decision?")
                        if use_suggested:
                            step.decision = suggested_decision
                            print(f"Decision updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating decision suggestion: {str(e)}")
        
        new_decision = input("Enter new decision: ").strip()
        if new_decision:
            step.decision = new_decision
            print(f"Decision updated.")
        else:
            print("Decision unchanged.")
        display_edit_options(step.step_id)
    elif choice == "4":
        print(f"\nCurrent success outcome: {step.success_outcome}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the success outcome?")
                if want_suggestion:
                    show_loading_animation("Generating success outcome suggestion", in_menu=True)
                    suggested_outcome = builder.generate_step_success_outcome(step.step_id, step.description, step.decision)
                    if suggested_outcome:
                        print(f"AI suggests the following success outcome: '{suggested_outcome}'")
                        use_suggested = prompt_for_confirmation("Would you like to use this outcome?")
                        if use_suggested:
                            step.success_outcome = suggested_outcome
                            print(f"Success outcome updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating success outcome suggestion: {str(e)}")
        
        new_success = input("Enter new success outcome: ").strip()
        if new_success:
            step.success_outcome = new_success
            print(f"Success outcome updated.")
        else:
            print("Success outcome unchanged.")
        display_edit_options(step.step_id)
    elif choice == "5":
        print(f"\nCurrent failure outcome: {step.failure_outcome}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the failure outcome?")
                if want_suggestion:
                    show_loading_animation("Generating failure outcome suggestion", in_menu=True)
                    suggested_outcome = builder.generate_step_failure_outcome(step.step_id, step.description, step.decision)
                    if suggested_outcome:
                        print(f"AI suggests the following failure outcome: '{suggested_outcome}'")
                        use_suggested = prompt_for_confirmation("Would you like to use this outcome?")
                        if use_suggested:
                            step.failure_outcome = suggested_outcome
                            print(f"Failure outcome updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating failure outcome suggestion: {str(e)}")
        
        new_failure = input("Enter new failure outcome: ").strip()
        if new_failure:
            step.failure_outcome = new_failure
            print(f"Failure outcome updated.")
        else:
            print("Failure outcome unchanged.")
        display_edit_options(step.step_id)
    elif choice == "6":
        print("\nEdit Note:")
        if step.note_id:
            note = next(n for n in builder.notes if n.note_id == step.note_id)
            # Offer AI suggestion if available and enabled
            if builder.openai_client and options and options.get('use_ai_suggestions', False):
                try:
                    want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the note?")
                    if want_suggestion:
                        show_loading_animation("Generating note suggestion", in_menu=True)
                        suggested_note = builder.generate_step_note(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                        if suggested_note:
                            print(f"AI suggests the following note: '{suggested_note}'")
                            use_suggested = prompt_for_confirmation("Would you like to use this note?")
                            if use_suggested:
                                note.content = suggested_note
                                print(f"Note updated.")
                                display_edit_options(step.step_id)
                                return
                except Exception as e:
                    print(f"Error generating note suggestion: {str(e)}")
            
            new_note = input("Enter new note content: ").strip()
            if new_note:
                note.content = new_note
        else:
            add_note = prompt_for_confirmation("No note exists. Would you like to add one?")
            if add_note:
                # Offer AI suggestion if available and enabled
                if builder.openai_client and options and options.get('use_ai_suggestions', False):
                    try:
                        want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the note?")
                        if want_suggestion:
                            show_loading_animation("Generating note suggestion", in_menu=True)
                            suggested_note = builder.generate_step_note(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                            if suggested_note:
                                print(f"AI suggests the following note: '{suggested_note}'")
                                use_suggested = prompt_for_confirmation("Would you like to use this note?")
                                if use_suggested:
                                    note_content = suggested_note
                                    note_id = f"Note{builder.current_note_id}"
                                    builder.notes.append(ProcessNote(note_id, note_content, step.step_id))
                                    step.note_id = note_id
                                    builder.current_note_id += 1
                                    print(f"Note added.")
                                    display_edit_options(step.step_id)
                                    return
                    except Exception as e:
                        print(f"Error generating note suggestion: {str(e)}")
                
                note_content = input("Enter note content: ").strip()
                if note_content:
                    note_id = f"Note{builder.current_note_id}"
                    builder.notes.append(ProcessNote(note_id, note_content, step.step_id))
                    step.note_id = note_id
                    builder.current_note_id += 1
        display_edit_options(step.step_id)
    elif choice == "7":
        print("\nEdit Validation Rules:")
        if step.validation_rules:
            print(f"Current validation rules: {step.validation_rules}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the validation rules?")
                if want_suggestion:
                    show_loading_animation("Generating validation rules suggestion", in_menu=True)
                    suggested_rules = builder.generate_validation_rules(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                    if suggested_rules:
                        print(f"AI suggests the following validation rules:\n{suggested_rules}")
                        use_suggested = prompt_for_confirmation("Would you like to use these rules?")
                        if use_suggested:
                            step.validation_rules = suggested_rules
                            print(f"Validation rules updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating validation rules suggestion: {str(e)}")
        
        new_rules = input("Enter new validation rules: ").strip()
        step.validation_rules = new_rules if new_rules else None
        display_edit_options(step.step_id)
    elif choice == "8":
        print("\nEdit Error Codes:")
        if step.error_codes:
            print(f"Current error codes: {step.error_codes}")
        # Offer AI suggestion if available and enabled
        if builder.openai_client and options and options.get('use_ai_suggestions', False):
            try:
                want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the error codes?")
                if want_suggestion:
                    show_loading_animation("Generating error codes suggestion", in_menu=True)
                    suggested_codes = builder.generate_error_codes(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                    if suggested_codes:
                        print(f"AI suggests the following error codes:\n{suggested_codes}")
                        use_suggested = prompt_for_confirmation("Would you like to use these codes?")
                        if use_suggested:
                            step.error_codes = suggested_codes
                            print(f"Error codes updated.")
                            display_edit_options(step.step_id)
                            return
            except Exception as e:
                print(f"Error generating error codes suggestion: {str(e)}")
        
        new_codes = input("Enter new error codes: ").strip()
        step.error_codes = new_codes if new_codes else None
        display_edit_options(step.step_id)
    elif choice == "9":
        print(f"\nCurrent next step for success: {step.next_step_success}")
        while True:
            new_next = input("Enter new next step for success (or 'End'): ").strip()
            if new_next.lower() == 'end':
                step.next_step_success = 'End'
                break
            # Convert spaces to underscores for step names
            new_next = new_next.replace(' ', '_')
            
            # Offer AI suggestion if available and enabled
            if builder.openai_client and options and options.get('use_ai_suggestions', False):
                try:
                    want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the next step on success?")
                    if want_suggestion:
                        show_loading_animation("Generating next step suggestion", in_menu=True)
                        suggested_next = builder.generate_next_step_suggestion(
                            step.step_id, step.description, step.decision, 
                            step.success_outcome, step.failure_outcome, True
                        )
                        if suggested_next:
                            print(f"AI suggests the following next step for success: '{suggested_next}'")
                            use_suggested = prompt_for_confirmation("Would you like to use this next step?")
                            if use_suggested and builder.validate_next_step(suggested_next):
                                step.next_step_success = suggested_next
                                display_edit_options(step.step_id)
                                return
                except Exception as e:
                    print(f"Error generating next step suggestion: {str(e)}")
            
            if builder.validate_next_step(new_next):
                step.next_step_success = new_next
                break
            print("Please enter a valid step name or 'End'")
        display_edit_options(step.step_id)
    elif choice == "10":
        print(f"\nCurrent next step for failure: {step.next_step_failure}")
        while True:
            new_next = input("Enter new next step for failure (or 'End'): ").strip()
            if new_next.lower() == 'end':
                step.next_step_failure = 'End'
                break
            # Convert spaces to underscores for step names
            new_next = new_next.replace(' ', '_')
            
            # Offer AI suggestion if available and enabled
            if builder.openai_client and options and options.get('use_ai_suggestions', False):
                try:
                    want_suggestion = prompt_for_confirmation("Would you like an AI suggestion for the next step on failure?")
                    if want_suggestion:
                        show_loading_animation("Generating next step suggestion", in_menu=True)
                        suggested_next = builder.generate_next_step_suggestion(
                            step.step_id, step.description, step.decision, 
                            step.success_outcome, step.failure_outcome, False
                        )
                        if suggested_next:
                            print(f"AI suggests the following next step for failure: '{suggested_next}'")
                            use_suggested = prompt_for_confirmation("Would you like to use this next step?")
                            if use_suggested and builder.validate_next_step(suggested_next):
                                step.next_step_failure = suggested_next
                                display_edit_options(step.step_id)
                                return
                except Exception as e:
                    print(f"Error generating next step suggestion: {str(e)}")
            
            if builder.validate_next_step(new_next):
                step.next_step_failure = new_next
                break
            print("Please enter a valid step name or 'End'")
        display_edit_options(step.step_id)
    elif choice == "11":
        print("\nEdit cancelled.")
    else:
        print("\nInvalid choice. Please try again.")
        display_edit_options(step.step_id)

def validate_after_edit(builder: 'ProcessBuilder') -> List[str]:
    """Validate the process flow after an edit.
    
    Args:
        builder: The ProcessBuilder instance
        
    Returns:
        List of flow issues
    """
    try:
        # Validate the process flow after editing
        print("\nValidating process flow after edit...")
        is_valid, flow_issues = builder.validator.validate_process_flow(builder.steps, builder.start_step_id)
        
        if not is_valid and flow_issues:
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
    except Exception as e:
        print(f"\nAn error occurred during validation: {str(e)}")
        print("The edit has been saved, but there may be validation issues.")
        return []

def get_all_referenced_steps(builder: 'ProcessBuilder') -> List[str]:
    """Get all step IDs that are referenced as next steps but may not be defined yet.
    
    Args:
        builder: The ProcessBuilder instance
        
    Returns:
        List of referenced step IDs
    """
    referenced_steps = set()
    defined_steps = {step.step_id for step in builder.steps}
    
    # Collect all referenced steps
    for step in builder.steps:
        if step.next_step_success and step.next_step_success.lower() != 'end':
            referenced_steps.add(step.next_step_success)
        if step.next_step_failure and step.next_step_failure.lower() != 'end':
            referenced_steps.add(step.next_step_failure)
    
    # Return only steps that are referenced but not defined
    return list(referenced_steps - defined_steps)

def edit_step(builder: 'ProcessBuilder', options: dict = None) -> None:
    """Edit an existing step.
    
    Args:
        builder: The ProcessBuilder instance
        options: Dictionary of options including AI suggestions preference
    """
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
    
    # Get referenced but undefined steps
    referenced_steps = get_all_referenced_steps(builder)
    if referenced_steps:
        print("\nReferenced but undefined steps:")
        for i, step_id in enumerate(referenced_steps, len(builder.steps) + 1):
            print(f"{i}. {step_id} (not defined yet)")
    
    try:
        step_num = int(input("\nEnter step number to edit: ").strip())
        
        # Handle referenced but undefined steps
        if step_num > len(builder.steps):
            if step_num <= len(builder.steps) + len(referenced_steps):
                step_id = referenced_steps[step_num - len(builder.steps) - 1]
                print(f"\nCreating new step: {step_id}")
                # Create a new step with the referenced ID
                step = ProcessStep(
                    step_id=step_id,
                    description="",
                    decision="",
                    success_outcome="",
                    failure_outcome="",
                    next_step_success="end",
                    next_step_failure="end"
                )
                builder.steps.append(step)
            else:
                print("\nInvalid step number. Please try again.")
                return
        elif 1 <= step_num <= len(builder.steps):
            # Get the actual step by index
            step = builder.steps[step_num-1]
        else:
            print("\nInvalid step number. Please try again.")
            return
        
        # Show edit options
        display_edit_options(step.step_id)
        
        # Get edit choice
        edit_choice = input("Enter your choice (1-11): ").strip()
        
        # Handle edit choice
        handle_edit_selection(builder, step, edit_choice, options=options)  # Pass options to handle_edit_selection
        
        # Validate after edit
        flow_issues = validate_after_edit(builder)
        
        # Save the state after editing
        from .state_management import save_state
        save_state(
            process_name=builder.process_name,
            timestamp=builder.timestamp,
            steps=builder.steps,
            notes=builder.notes,
            start_step_id=builder.start_step_id,
            output_dir=builder.output_dir
        )
        print("\nChanges saved successfully.")
    except ValueError:
        print("\nPlease enter a valid number.")
    except Exception as e:
        print(f"\nAn error occurred while editing: {str(e)}")
        # Don't re-raise the exception, just log it and continue

def generate_outputs(builder: 'ProcessBuilder') -> None:
    """Generate all output files for the process.
    
    Args:
        builder: The ProcessBuilder instance
    """
    try:
        print("\nGenerating outputs...")
        show_loading_animation("Generating outputs", in_menu=True)
        
        # Use the save_outputs function to handle all output generation
        save_outputs(
            steps=builder.steps,
            notes=builder.notes,
            process_name=builder.name,
            timestamp=builder.timestamp,
            base_output_dir=None,  # Use default base directory
            default_output_dir="output"  # Use "output" as the default directory
        )
        
        print("\nAll outputs generated successfully!")
        
    except Exception as e:
        print(f"\nAn error occurred while generating outputs: {str(e)}")
        raise 