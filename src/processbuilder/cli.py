"""
Command-line interface for the Process Builder.
"""
import argparse
import sys
import time
import random
import os
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

def show_loading_animation(message: str, duration: float = 2.0, in_menu: bool = True) -> None:
    """Show a simple loading animation with dots.
    
    Args:
        message: The message to display during loading
        duration: How long to show the animation
        in_menu: If True, don't clear the screen to preserve menu visibility
    """
    dot_frames = ["", ".", "..", "..."]
    start_time = time.time()
    dot_idx = 0
    
    while time.time() - start_time < duration:
        # Update the message with dots
        current_message = message + dot_frames[dot_idx]
        
        # Write the message in place
        sys.stdout.write("\r" + current_message)
        sys.stdout.flush()
        
        # Update dot index
        dot_idx = (dot_idx + 1) % len(dot_frames)
        time.sleep(0.2)
    
    # Clear the line
    sys.stdout.write("\r" + " " * (len(message) + 3) + "\r")
    sys.stdout.flush()

def show_startup_animation(in_menu: bool = False) -> None:
    """Show a cute ASCII art loading animation when starting the Process Builder.
    
    Args:
        in_menu: If True, don't clear the screen to preserve menu visibility
    """
    frames = [
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │   ⚙️        │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │      ⚙️     │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │             │
    │         ⚙️  │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │    ✨       │
    │         ⚙️  │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │    ✨ ✨    │
    │    ⚙️  ⚙️   │
    └─────────────┘
    """,
        """
    ┌─────────────┐
    │ Process     │
    │ Builder     │
    │  ✨ ✨ ✨   │
    │  ⚙️  ⚙️  ⚙️  │
    └─────────────┘
    """
    ]
    
    print("\033[?25l", end="")  # Hide cursor
    try:
        for _ in range(2):  # Show animation twice
            for frame in frames:
                # Only clear the screen if not in menu mode
                if not in_menu:
                    if sys.platform.startswith('win'):
                        os.system('cls')
                    else:
                        os.system('clear')
                
                # Print current frame
                print(frame)
                time.sleep(0.2)
    finally:
        print("\033[?25h", end="")  # Show cursor
        # Clear the animation, but only if not in menu mode
        if not in_menu:
            if sys.platform.startswith('win'):
                os.system('cls')
            else:
                os.system('clear')

def run_interview(builder: ProcessBuilder) -> None:
    """Run the interactive interview process."""
    print(f"\n=== Process Builder: {builder.process_name} ===\n")
    
    while True:
        # Get step title with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating step title", in_menu=True)
                if not builder.steps:  # First step
                    suggested_title = builder.suggested_first_step
                    if suggested_title:
                        print(f"AI suggests starting with: '{suggested_title}'")
                        use_suggested = input("Would you like to use this title? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            step_id = suggested_title
                        else:
                            step_id = get_step_input("What is the title of this step?\n> ")
                    else:
                        step_id = get_step_input("What is the title of this step?\n> ")
                else:
                    step_id = get_step_input("What is the title of this step?\n> ")
            except Exception as e:
                print(f"Error generating step title suggestion: {str(e)}")
                step_id = get_step_input("What is the title of this step?\n> ")
        else:
            step_id = get_step_input("What is the title of this step?\n> ")
        
        # Get step description with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating step description", in_menu=True)
                suggested_description = builder.generate_step_description(step_id)
                if suggested_description:
                    print(f"AI suggests the following description: '{suggested_description}'")
                    use_suggested = input("Would you like to use this description? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        description = suggested_description
                    else:
                        description = get_step_input("What happens in this step?\n> ")
                else:
                    description = get_step_input("What happens in this step?\n> ")
            except Exception as e:
                print(f"Error generating description suggestion: {str(e)}")
                description = get_step_input("What happens in this step?\n> ")
        else:
            description = get_step_input("What happens in this step?\n> ")
        
        # Get decision with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating decision suggestion", in_menu=True)
                suggested_decision = builder.generate_step_decision(step_id, description)
                if suggested_decision:
                    print(f"AI suggests the following decision: '{suggested_decision}'")
                    use_suggested = input("Would you like to use this decision? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        decision = suggested_decision
                    else:
                        decision = get_step_input("What decision needs to be made?\n> ")
                else:
                    decision = get_step_input("What decision needs to be made?\n> ")
            except Exception as e:
                print(f"Error generating decision suggestion: {str(e)}")
                decision = get_step_input("What decision needs to be made?\n> ")
        else:
            decision = get_step_input("What decision needs to be made?\n> ")
        
        # Get success outcome with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating success outcome suggestion", in_menu=True)
                suggested_success = builder.generate_step_success_outcome(step_id, description, decision)
                if suggested_success:
                    print(f"AI suggests the following success outcome: '{suggested_success}'")
                    use_suggested = input("Would you like to use this success outcome? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        success_outcome = suggested_success
                    else:
                        success_outcome = get_step_input("What happens if this step succeeds?\n> ")
                else:
                    success_outcome = get_step_input("What happens if this step succeeds?\n> ")
            except Exception as e:
                print(f"Error generating success outcome suggestion: {str(e)}")
                success_outcome = get_step_input("What happens if this step succeeds?\n> ")
        else:
            success_outcome = get_step_input("What happens if this step succeeds?\n> ")
        
        # Get failure outcome with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating failure outcome suggestion", in_menu=True)
                suggested_failure = builder.generate_step_failure_outcome(step_id, description, decision)
                if suggested_failure:
                    print(f"AI suggests the following failure outcome: '{suggested_failure}'")
                    use_suggested = input("Would you like to use this failure outcome? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        failure_outcome = suggested_failure
                    else:
                        failure_outcome = get_step_input("What happens if this step fails?\n> ")
                else:
                    failure_outcome = get_step_input("What happens if this step fails?\n> ")
            except Exception as e:
                print(f"Error generating failure outcome suggestion: {str(e)}")
                failure_outcome = get_step_input("What happens if this step fails?\n> ")
        else:
            failure_outcome = get_step_input("What happens if this step fails?\n> ")
        
        # Get next steps with AI suggestions
        if builder.openai_client:
            try:
                # Get success path suggestion
                show_loading_animation("Generating next step suggestion", in_menu=True)
                suggested_next_success = builder.generate_next_step_suggestion(
                    step_id, description, decision, success_outcome, failure_outcome, True
                )
                if suggested_next_success:
                    print(f"AI suggests the following next step for success: '{suggested_next_success}'")
                    use_suggested = input("Would you like to use this next step? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        next_step_success = suggested_next_success
                    else:
                        while True:
                            next_step_success = get_step_input("What's the next step if successful? (Enter 'End' if final step)\n> ")
                            if builder.validate_next_step(next_step_success):
                                break
                            print("Please enter a valid step name or 'End' to finish the process.")
                else:
                    while True:
                        next_step_success = get_step_input("What's the next step if successful? (Enter 'End' if final step)\n> ")
                        if builder.validate_next_step(next_step_success):
                            break
                        print("Please enter a valid step name or 'End' to finish the process.")
                
                # Get failure path suggestion
                show_loading_animation("Generating next step suggestion", in_menu=True)
                suggested_next_failure = builder.generate_next_step_suggestion(
                    step_id, description, decision, success_outcome, failure_outcome, False
                )
                if suggested_next_failure:
                    print(f"AI suggests the following next step for failure: '{suggested_next_failure}'")
                    use_suggested = input("Would you like to use this next step? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        next_step_failure = suggested_next_failure
                    else:
                        while True:
                            next_step_failure = get_step_input("What's the next step if failed? (Enter 'End' if final step)\n> ")
                            if builder.validate_next_step(next_step_failure):
                                break
                            print("Please enter a valid step name or 'End' to finish the process.")
                else:
                    while True:
                        next_step_failure = get_step_input("What's the next step if failed? (Enter 'End' if final step)\n> ")
                        if builder.validate_next_step(next_step_failure):
                            break
                        print("Please enter a valid step name or 'End' to finish the process.")
            except Exception as e:
                print(f"Error generating next step suggestions: {str(e)}")
                # Fall back to manual input for both paths
                while True:
                    next_step_success = get_step_input("What's the next step if successful? (Enter 'End' if final step)\n> ")
                    if builder.validate_next_step(next_step_success):
                        break
                    print("Please enter a valid step name or 'End' to finish the process.")
                
                while True:
                    next_step_failure = get_step_input("What's the next step if failed? (Enter 'End' if final step)\n> ")
                    if builder.validate_next_step(next_step_failure):
                        break
                    print("Please enter a valid step name or 'End' to finish the process.")
        else:
            # No AI client available, use manual input
            while True:
                next_step_success = get_step_input("What's the next step if successful? (Enter 'End' if final step)\n> ")
                if builder.validate_next_step(next_step_success):
                    break
                print("Please enter a valid step name or 'End' to finish the process.")
            
            while True:
                next_step_failure = get_step_input("What's the next step if failed? (Enter 'End' if final step)\n> ")
                if builder.validate_next_step(next_step_failure):
                    break
                print("Please enter a valid step name or 'End' to finish the process.")
        
        # Get note with AI suggestion
        add_note = input("Would you like to add a note for this step? (y/n)\n> ").lower()
        note_id = None
        if add_note == 'y':
            if builder.openai_client:
                try:
                    show_loading_animation("Generating note suggestion", in_menu=True)
                    suggested_note = builder.generate_step_note(
                        step_id, description, decision, success_outcome, failure_outcome
                    )
                    if suggested_note:
                        print(f"AI suggests the following note: '{suggested_note}'")
                        use_suggested = input("Would you like to use this note? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            note_content = suggested_note
                        else:
                            note_content = input("What's the note content?\n> ")
                    else:
                        note_content = input("What's the note content?\n> ")
                except Exception as e:
                    print(f"Error generating note suggestion: {str(e)}")
                    note_content = input("What's the note content?\n> ")
            else:
                note_content = input("What's the note content?\n> ")
            
            note_id = f"Note{builder.current_note_id}"
            builder.notes.append(ProcessNote(note_id, note_content, step_id))
            builder.current_note_id += 1
        
        # Get validation rules with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating validation rules suggestion", in_menu=True)
                suggested_rules = builder.generate_validation_rules(
                    step_id, description, decision, success_outcome, failure_outcome
                )
                if suggested_rules:
                    print(f"AI suggests the following validation rules:\n{suggested_rules}")
                    use_suggested = input("Would you like to use these validation rules? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        validation_rules = suggested_rules
                    else:
                        validation_rules = input("What are the validation rules for this step? (Press Enter to skip)\n> ").strip()
                        if not validation_rules:  # If empty, set to None
                            validation_rules = None
                else:
                    validation_rules = input("What are the validation rules for this step? (Press Enter to skip)\n> ").strip()
                    if not validation_rules:  # If empty, set to None
                        validation_rules = None
            except Exception as e:
                print(f"Error generating validation rules suggestion: {str(e)}")
                validation_rules = input("What are the validation rules for this step? (Press Enter to skip)\n> ").strip()
                if not validation_rules:  # If empty, set to None
                    validation_rules = None
        else:
            validation_rules = input("What are the validation rules for this step? (Press Enter to skip)\n> ").strip()
            if not validation_rules:  # If empty, set to None
                validation_rules = None
        
        # Get error codes with AI suggestion
        if builder.openai_client:
            try:
                show_loading_animation("Generating error codes suggestion", in_menu=True)
                suggested_codes = builder.generate_error_codes(
                    step_id, description, decision, success_outcome, failure_outcome
                )
                if suggested_codes:
                    print(f"AI suggests the following error codes:\n{suggested_codes}")
                    use_suggested = input("Would you like to use these error codes? (y/n)\n> ").lower()
                    if use_suggested == 'y':
                        error_codes = suggested_codes
                    else:
                        error_codes = input("Any specific error codes? (Press Enter to skip)\n> ").strip()
                        if not error_codes:  # If empty, set to None
                            error_codes = None
                else:
                    error_codes = input("Any specific error codes? (Press Enter to skip)\n> ").strip()
                    if not error_codes:  # If empty, set to None
                        error_codes = None
            except Exception as e:
                print(f"Error generating error codes suggestion: {str(e)}")
                error_codes = input("Any specific error codes? (Press Enter to skip)\n> ").strip()
                if not error_codes:  # If empty, set to None
                    error_codes = None
        else:
            error_codes = input("Any specific error codes? (Press Enter to skip)\n> ").strip()
            if not error_codes:  # If empty, set to None
                error_codes = None
        
        # Create the step
        step = ProcessStep(
            step_id=step_id,
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            note_id=note_id,
            next_step_success=next_step_success,
            next_step_failure=next_step_failure,
            validation_rules=validation_rules,
            error_codes=error_codes
        )
        
        # Add the step and check for issues
        issues = builder.add_step(step)
        if issues:
            print("\n=== Validation Issues ===")
            for issue in issues:
                print(f"- {issue}")
            print("\nPlease fix these issues and try again.")
            continue
        
        # Ask if user wants to add another step
        continue_process = get_step_input("Add another step? (y/n)\n> ").lower()
        if continue_process != 'y':
            break
    
    # Generate outputs
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

    # Add menu system for viewing and editing steps
    def show_menu():
        # Don't clear the screen when showing the menu to maintain visibility
        print("\n" + "="*50)
        print("=======  Process Builder Menu  =======")
        print("="*50)
        print()  # Consistent spacing
        print("1. View all steps with flow connections")
        print("2. Edit a step")
        print("3. Add a new step")
        print("4. Exit")
        print("="*50)
        print()  # Add consistent spacing after menu options
    # Display initial menu to start the interaction
    show_menu()
    
    while True:
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            # View all steps with flow connections
            print("\n" + "="*50)
            print("=======  Process Steps  =======")
            print("="*50)
            print()  # Add extra spacing for better readability
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
                print("-" * 80)  # Separator between steps
            # Clear spacing before menu redisplay
            print("\n" + "="*50)
            print()
            print("All steps displayed. What would you like to do next?")
            # Redisplay menu after viewing steps
            show_menu()
        elif choice == "2":
            # Edit a step
            if not builder.steps:
                print("\nNo steps to edit. Please add a step first.")
                continue
            print("\n" + "="*50)
            print("=======  Edit Step  =======")
            print("="*50)
            print()  # Add extra spacing for better readability
            
            # Display all steps for selection
            print("\nAvailable steps:")
            for i, step in enumerate(builder.steps, 1):
                print(f"{i}. {step.step_id}")
            
            try:
                step_num = int(input("\nEnter step number to edit: ").strip())
                
                if 1 <= step_num <= len(builder.steps):
                    step = builder.steps[step_num - 1]
                    print("\n" + "="*50)
                    print(f"=======  Edit options for step: {step.step_id}  =======")
                    print("="*50)
                    print()
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
                    # Display edit menu with clear separation
                    edit_choice = input("Enter your choice (1-11): ").strip()
                    
                    if edit_choice == "1":
                        print(f"\nCurrent title: {step.step_id}")
                        new_title = input("Enter new title: ").strip()
                        if new_title:
                            step.step_id = new_title
                            print(f"Title updated to: {new_title}")
                        else:
                            print("Title unchanged.")
                    elif edit_choice == "2":
                        print(f"\nCurrent description: {step.description}")
                        new_description = input("Enter new description: ").strip()
                        if new_description:
                            step.description = new_description
                            print(f"Description updated.")
                        else:
                            print("Description unchanged.")
                    elif edit_choice == "3":
                        print(f"\nCurrent decision: {step.decision}")
                        new_decision = input("Enter new decision: ").strip()
                        if new_decision:
                            step.decision = new_decision
                            print(f"Decision updated.")
                        else:
                            print("Decision unchanged.")
                    elif edit_choice == "4":
                        print(f"\nCurrent success outcome: {step.success_outcome}")
                        new_success = input("Enter new success outcome: ").strip()
                        if new_success:
                            step.success_outcome = new_success
                            print(f"Success outcome updated.")
                        else:
                            print("Success outcome unchanged.")
                    elif edit_choice == "5":
                        print(f"\nCurrent failure outcome: {step.failure_outcome}")
                        new_failure = input("Enter new failure outcome: ").strip()
                        if new_failure:
                            step.failure_outcome = new_failure
                            print(f"Failure outcome updated.")
                        else:
                            print("Failure outcome unchanged.")
                    elif edit_choice == "6":
                        print("\nEdit Note:")
                        if step.note_id:
                            note = next(n for n in builder.notes if n.note_id == step.note_id)
                            new_note = input("Enter new note content: ").strip()
                            if new_note:
                                note.content = new_note
                        else:
                            add_note = input("No note exists. Would you like to add one? (y/n): ").lower()
                            if add_note == 'y':
                                note_content = input("Enter note content: ").strip()
                                if note_content:
                                    note_id = f"Note{builder.current_note_id}"
                                    builder.notes.append(ProcessNote(note_id, note_content, step.step_id))
                                    step.note_id = note_id
                                    builder.current_note_id += 1
                    elif edit_choice == "7":
                        print("\nEdit Validation Rules:")
                        if step.validation_rules:
                            print(f"Current validation rules: {step.validation_rules}")
                        new_rules = input("Enter new validation rules: ").strip()
                        step.validation_rules = new_rules if new_rules else None
                    elif edit_choice == "8":
                        print("\nEdit Error Codes:")
                        if step.error_codes:
                            print(f"Current error codes: {step.error_codes}")
                        new_codes = input("Enter new error codes: ").strip()
                        step.error_codes = new_codes if new_codes else None
                    elif edit_choice == "9":
                        print(f"\nCurrent next step for success: {step.next_step_success}")
                        while True:
                            new_next = input("Enter new next step for success (or 'End'): ").strip()
                            if builder.validate_next_step(new_next):
                                step.next_step_success = new_next
                                break
                            print("Please enter a valid step name or 'End'")
                    elif edit_choice == "10":
                        print(f"\nCurrent next step for failure: {step.next_step_failure}")
                        while True:
                            new_next = input("Enter new next step for failure (or 'End'): ").strip()
                            if builder.validate_next_step(new_next):
                                step.next_step_failure = new_next
                                break
                            print("Please enter a valid step name or 'End'")
                    elif edit_choice == "11":
                        print("\nEdit cancelled.")
                        continue
                    else:
                        print("\nInvalid choice. Please try again.")
                    # Validate the process flow after editing
                    print("\nValidating process flow after edit...")
                    flow_issues = builder.validate_process_flow()
                    if flow_issues:
                        print("\n" + "="*50)
                        print("=======  Process Flow Validation Issues  =======")
                        print("="*50)
                        print()
                        for issue in flow_issues:
                            print(f"- {issue}")
                        print("\nPlease fix these issues in the next edit.")
                        print("The edit has been saved, but you may want to review these issues.")
                    else:
                        print("\nEdit successful! No validation issues found.")
                        print("The process flow is valid.")
                else:
                    print("\nInvalid step number. Please try again.")
            except ValueError:
                print("\nPlease enter a valid number.")
            except Exception as e:
                print(f"\nAn error occurred while editing: {str(e)}")
                
            # Clear separation before redisplaying menu
            print("\n" + "="*50)
            print()
            print("Step editing complete. What would you like to do next?")
            show_menu()
        elif choice == "3":
            # Add a new step
            run_interview(builder)  # Use the existing interview function to add a step
            
            # Clear separation before menu
            print("\n" + "="*50)
            print()
            print("Step added successfully! What would you like to do next?")
            # Redisplay menu after adding a step
            show_menu()
        elif choice == "4":
            # Exit
            print("\nExiting Process Builder menu. Your process has been saved.")
            break
        else:
            # Invalid choice
            print("\nInvalid choice. Please try again.")
            
            # Clear separation before redisplaying menu
            print("\n" + "="*50)
            print()
            print("Please select a valid option.")
            # Redisplay menu after invalid choice
            show_menu()
def load_from_csv(builder: ProcessBuilder, steps_csv_path: Path, notes_csv_path: Optional[Path] = None) -> None:
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
    
    # Show startup animation at the beginning
    show_startup_animation(in_menu=False)
    
    print("Welcome to Process Builder! 🚀\n")
    
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
        builder.generate_executive_summary()
    else:
        # Run the interactive interview
        run_interview(builder)

if __name__ == "__main__":
    main() 