"""Process Interviewer module for handling interactive process building."""

from typing import Optional, List, TYPE_CHECKING
from pathlib import Path
import logging
from .base import ProcessStep, ProcessNote
from ..utils import show_loading_animation, sanitize_string

if TYPE_CHECKING:
    from ..builder import ProcessBuilder

log = logging.getLogger(__name__)

class ProcessInterviewer:
    """Handles the interactive interview process for building steps."""
    
    def __init__(self, input_handler=None):
        """Initialize the ProcessInterviewer.
        
        Args:
            input_handler: Optional custom input handler function
        """
        self.input_handler = input_handler or input
    
    def run_interview(self, builder: 'ProcessBuilder') -> None:
        """Run the interactive interview process.
        
        Args:
            builder: The ProcessBuilder instance to use
        """
        try:
            print(f"\n=== Process Builder: {builder.process_name} ===\n")
            
            while True:
                self.show_menu()
                choice = self.get_input("Enter your choice (1-4):")
                
                if choice == '1':
                    self.view_all_steps(builder)
                elif choice == '2':
                    self.edit_step(builder)
                elif choice == '3':
                    self.add_new_step(builder)
                elif choice == '4':
                    break
                else:
                    print("Invalid choice. Please try again.")
            
            # Generate outputs before exiting
            builder.generate_outputs()
            
        except Exception as e:
            print(f"An error occurred during interview: {str(e)}")
            log.error(f"Interview error: {str(e)}")
    
    def show_menu(self) -> None:
        """Display the main menu."""
        print("\n" + "="*50)
        print("=== Process Builder Menu ===")
        print("1. View all steps")
        print("2. Edit a step")
        print("3. Add new step")
        print("4. Generate outputs and exit")
        print("="*50 + "\n")
    
    def get_input(self, prompt: str) -> str:
        """Get input from the user.
        
        Args:
            prompt: The prompt to display
            
        Returns:
            The user's input
        """
        return self.input_handler(f"{prompt}\n> ").strip()
    
    def view_all_steps(self, builder: 'ProcessBuilder') -> None:
        """Display all steps with their flow connections.
        
        Args:
            builder: The ProcessBuilder instance
        """
        if not builder.steps:
            print("\nNo steps defined yet.")
            return
            
        print("\n=== Process Steps ===\n")
        for step in builder.steps:
            # Find predecessors
            predecessors = []
            for s in builder.steps:
                if s.next_step_success == step.step_id:
                    predecessors.append((s.step_id, "Success"))
                if s.next_step_failure == step.step_id:
                    predecessors.append((s.step_id, "Failure"))
            
            # Display step details
            print(f"Step: {step.step_id}")
            print(f"Description: {step.description}")
            print(f"Decision: {step.decision}")
            print(f"Success Outcome: {step.success_outcome}")
            print(f"Failure Outcome: {step.failure_outcome}")
            
            print("\nPredecessors:")
            if predecessors:
                for pred_id, path_type in predecessors:
                    print(f"  - {pred_id} ({path_type} path)")
            else:
                print("  None (Start of process)")
            
            print("\nSuccessors:")
            print(f"  - {step.next_step_success} (Success)")
            print(f"  - {step.next_step_failure} (Failure)")
            
            if step.note_id:
                try:
                    note = next(n for n in builder.notes if n.note_id == step.note_id)
                    print(f"\nNote: {note.content}")
                except StopIteration:
                    log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
                    print(f"\nNote: [Referenced note {step.note_id} not found]")
            
            if step.validation_rules:
                print(f"Validation Rules: {step.validation_rules}")
            if step.error_codes:
                print(f"Error Codes: {step.error_codes}")
            print("-" * 80 + "\n")
    
    def edit_step(self, builder: 'ProcessBuilder') -> None:
        """Edit an existing step.
        
        Args:
            builder: The ProcessBuilder instance
        """
        if not builder.steps:
            print("\nNo steps to edit.")
            return
            
        # Display available steps
        print("\nAvailable steps:")
        for i, step in enumerate(builder.steps, 1):
            print(f"{i}. {step.step_id}")
        
        try:
            choice = int(self.get_input("Enter step number to edit:"))
            if choice < 1 or choice > len(builder.steps):
                print("Invalid step number.")
                return
                
            step = builder.steps[choice - 1]
            
            print("\nEditing step:", step.step_id)
            print("Enter new values (or press Enter to keep current value)")
            
            # Get new values with AI suggestions
            if builder.openai_client:
                print("\nGenerating AI suggestions...")
                show_loading_animation("Generating suggestions")
                
                # Generate suggestions for each field
                suggestions = {
                    "description": builder.step_generator.generate_step_description(
                        builder.process_name, step.step_id, step.description
                    ),
                    "decision": builder.step_generator.generate_step_decision(
                        builder.process_name, step.step_id, step.description
                    ),
                    "outcomes": builder.step_generator.generate_step_outcomes(
                        builder.process_name, step.step_id, step.description, step.decision
                    ),
                    "note": builder.step_generator.generate_step_note(
                        builder.process_name, step.step_id, step.description, step.decision, 
                        (step.success_outcome, step.failure_outcome)
                    ),
                    "validation": builder.step_generator.generate_validation_rules(
                        builder.process_name, step.step_id, step.description, step.decision,
                        (step.success_outcome, step.failure_outcome)
                    ),
                    "error_codes": builder.step_generator.generate_error_codes(
                        builder.process_name, step.step_id, step.description, step.decision,
                        (step.success_outcome, step.failure_outcome)
                    )
                }
                
                # Apply suggestions if user accepts them
                for field, suggestion in suggestions.items():
                    if suggestion:
                        print(f"\nAI suggests {field}: '{suggestion}'")
                        use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                        if use_suggestion:
                            if field == "outcomes":
                                step.success_outcome, step.failure_outcome = suggestion
                            else:
                                setattr(step, field, suggestion)
            
            # Validate and save changes
            issues = builder.validator.validate_step(step, builder.steps)
            if issues:
                print("\n=== Validation Issues ===")
                for issue in issues:
                    print(f"- {issue}")
                print("\nPlease fix these issues.")
                
                save_anyway = self.get_input("Save changes anyway? (y/n)").lower() == 'y'
                if not save_anyway:
                    print("\nChanges not saved due to validation issues.")
                    return
            
            builder.save_state()
            print("\nStep updated successfully.")
            
        except Exception as e:
            print(f"Error editing step: {str(e)}")
            log.error(f"Step edit error: {str(e)}")
    
    def add_new_step(self, builder: 'ProcessBuilder') -> None:
        """Add a new step to the process.
        
        Args:
            builder: The ProcessBuilder instance
        """
        if len(builder.steps) == 0:
            # For the first step, offer to use the suggested name
            suggested_id = builder.suggested_first_step
            if suggested_id:
                use_suggested = self.get_input(f"\nWould you like to use the suggested first step '{suggested_id}'? (y/n)").lower() == 'y'
                if use_suggested:
                    step_id = suggested_id
                else:
                    step_id = self.get_input("Enter a step ID:")
            else:
                step_id = self.get_input("Enter a step ID:")
        else:
            step_id = self.get_input("Enter a step ID:")
        
        # Create a new step
        new_step = self.create_missing_step(builder, step_id)
        
        # Add the step with validation
        validation_issues = builder.add_step(new_step, interactive=True)
        if validation_issues:
            print("\n=== Validation Issues ===")
            for issue in validation_issues:
                print(f"- {issue}")
            print("\nPlease fix these issues and try again.")
        
        # After adding a step, ask if they want to add another
        while True:
            continue_process = self.get_input("\nWould you like to add another step? (y/n)").lower()
            if continue_process == 'y':
                step_id = self.get_input("Enter a step ID:")
                new_step = self.create_missing_step(builder, step_id)
                validation_issues = builder.add_step(new_step, interactive=True)
                if validation_issues:
                    print("\n=== Validation Issues ===")
                    for issue in validation_issues:
                        print(f"- {issue}")
                    print("\nPlease fix these issues and try again.")
            else:
                break
    
    def create_missing_step(self, builder: 'ProcessBuilder', step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> ProcessStep:
        """Create a missing step that was referenced by another step.
        
        Args:
            builder: The ProcessBuilder instance
            step_id: ID of the step to create
            predecessor_id: Optional ID of the step that references this one
            path_type: Optional path type ('success' or 'failure')
            
        Returns:
            A new ProcessStep
        """
        print(f"\nCreating missing step: {step_id}")
        
        # Initial AI confirmation
        use_ai = False
        if builder.openai_client:
            use_ai = self.get_input("\nWould you like to use AI suggestions for this step? (y/n)").lower() == 'y'
            if use_ai:
                print("\nI'll ask for your input first, then offer AI suggestions if you'd like.")
        
        # Get step description
        print("\nThe step name is used as a label in the process diagram.")
        description = self.get_input("What happens in this step?")
        
        if use_ai and builder.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the description? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating step description")
                    suggested_description = builder.step_generator.generate_step_description(
                        builder.process_name, step_id, predecessor_id, path_type
                    )
                    if suggested_description:
                        safe_description = sanitize_string(suggested_description)
                        print(f"\nAI suggests the following description: '{safe_description}'")
                        use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                        if use_suggested == 'y':
                            description = suggested_description
                except Exception as e:
                    print(f"Error generating description suggestion: {str(e)}")
        
        # Get decision
        print("\nThe decision is a yes/no question that determines which path to take next.")
        decision = self.get_input("What decision needs to be made in this step?")
        
        if use_ai and builder.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the decision? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating decision suggestion")
                    suggested_decision = builder.step_generator.generate_step_decision(
                        builder.process_name, step_id, description, predecessor_id, path_type
                    )
                    if suggested_decision:
                        safe_decision = sanitize_string(suggested_decision)
                        print(f"\nAI suggests the following decision: '{safe_decision}'")
                        use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                        if use_suggested == 'y':
                            decision = suggested_decision
                except Exception as e:
                    print(f"Error generating decision suggestion: {str(e)}")
        
        # Get outcomes
        print("\nThe success outcome tells you which step to go to next when the decision is 'yes'.")
        success_outcome = self.get_input("What happens if this step succeeds?")
        
        print("\nThe failure outcome tells you which step to go to next when the decision is 'no'.")
        failure_outcome = self.get_input("What happens if this step fails?")
        
        if use_ai and builder.openai_client:
            want_ai_help = self.get_input("\nWould you like to see AI suggestions for the outcomes? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating outcome suggestions")
                    suggested_success, suggested_failure = builder.step_generator.generate_step_outcomes(
                        builder.process_name, step_id, description, decision, predecessor_id, path_type
                    )
                    if suggested_success and suggested_failure:
                        safe_success = sanitize_string(suggested_success)
                        safe_failure = sanitize_string(suggested_failure)
                        print(f"\nAI suggests the following outcomes:")
                        print(f"Success: '{safe_success}'")
                        print(f"Failure: '{safe_failure}'")
                        use_suggested = self.get_input("Use these suggestions? (y/n)").lower()
                        if use_suggested == 'y':
                            success_outcome = suggested_success
                            failure_outcome = suggested_failure
                except Exception as e:
                    print(f"Error generating outcome suggestions: {str(e)}")
        
        # Optional note
        print("\nA note is a brief comment that appears next to the step in the diagram.")
        add_note = self.get_input("Would you like to add a note for this step? (y/n)").lower()
        note_id = None
        if add_note == 'y':
            note_content = self.get_input("What's the note content?")
            
            if use_ai and builder.openai_client:
                want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the note? (y/n)").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating note suggestion")
                        suggested_note = builder.step_generator.generate_step_note(
                            builder.process_name, step_id, description, decision, 
                            (success_outcome, failure_outcome)
                        )
                        if suggested_note:
                            safe_note = sanitize_string(suggested_note)
                            print(f"\nAI suggests the following note: '{safe_note}'")
                            use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                            if use_suggested == 'y':
                                note_content = suggested_note
                    except Exception as e:
                        print(f"Error generating note suggestion: {str(e)}")
            
            note_id = f"Note{builder.current_note_id}"
            builder.notes.append(ProcessNote(note_id, note_content, step_id))
            builder.current_note_id += 1
        
        # Create and return the step
        return ProcessStep(
            step_id=step_id,
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            note_id=note_id,
            next_step_success="end",  # Use lowercase 'end'
            next_step_failure="end",  # Use lowercase 'end'
            validation_rules=None,
            error_codes=None
        ) 