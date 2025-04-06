"""
Main ProcessBuilder class for building and managing processes.
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple
import openai
from datetime import datetime

from .models import ProcessStep, ProcessNote
from .config import Config
from .utils import (
    sanitize_id,
    validate_process_flow,
    validate_notes,
    write_csv
)

def show_loading_animation(message: str, duration: float = 0.5) -> None:
    """Show a simple loading animation while waiting for AI response.
    
    Args:
        message: The message to display while loading
        duration: How long to show each frame in seconds
    """
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    start_time = time.time()
    
    try:
        while True:
            for frame in frames:
                sys.stdout.write(f"\r{frame} {message}...")
                sys.stdout.flush()
                time.sleep(duration)
                if time.time() - start_time > 5:  # Timeout after 5 seconds
                    break
            if time.time() - start_time > 5:
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\r" + " " * (len(message) + 4) + "\r")  # Clear the line
        sys.stdout.flush()

class ProcessBuilder:
    """Main class for building processes through interactive interviews."""
    
    def __init__(self, process_name: str, config: Optional[Config] = None):
        self.process_name = process_name
        self.steps: List[ProcessStep] = []
        self.notes: List[ProcessNote] = []
        self.current_note_id = 1
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir: Optional[Path] = None
        self.step_count = 0
        
        # Initialize configuration
        self.config = config or Config()
        
        # Initialize OpenAI client if API key is available
        if self.config.has_openai:
            try:
                self.openai_client = openai.OpenAI(api_key=self.config.openai_api_key)
                # Test the connection
                self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {str(e)}")
                print("AI evaluation features will be disabled.")
                self.openai_client = None
        else:
            self.openai_client = None
            
        # Generate suggested first step title
        self.suggested_first_step = self.generate_first_step_title()

    def generate_first_step_title(self) -> str:
        """Generate an intelligent first step title based on the process name."""
        if not self.openai_client:
            return "Initial Step"
            
        try:
            prompt = f"""Given the process name "{self.process_name}", suggest an appropriate title for the first step.
The title should:
1. Be clear and descriptive
2. Start with a verb
3. Be specific to the process
4. Be concise (2-5 words)
5. Follow business process naming conventions

Please provide just the step title, no additional text."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a business process expert. Create clear, concise step titles that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating first step title: {str(e)}")
            return "Initial Step"

    def find_missing_steps(self) -> List[Tuple[str, str, str]]:
        """Find steps that are referenced but don't exist yet.
        
        Returns:
            List of tuples containing (missing_step_id, predecessor_step_id, path_type)
            where path_type is either 'success' or 'failure'
        """
        missing_steps = []
        existing_step_ids = {step.step_id for step in self.steps}
        
        for step in self.steps:
            if (step.next_step_success.lower() != 'end' and 
                step.next_step_success not in existing_step_ids):
                missing_steps.append((step.next_step_success, step.step_id, 'success'))
            
            if (step.next_step_failure.lower() != 'end' and 
                step.next_step_failure not in existing_step_ids):
                missing_steps.append((step.next_step_failure, step.step_id, 'failure'))
        
        return missing_steps

    def parse_ai_suggestions(self, suggestions: str) -> dict:
        """Parse AI suggestions into a structured format.
        
        Args:
            suggestions: The raw AI suggestions text
            
        Returns:
            Dictionary containing suggested updates for each field
        """
        # Initialize with empty suggestions
        suggested_updates = {
            'description': None,
            'decision': None,
            'success_outcome': None,
            'failure_outcome': None,
            'validation_rules': None,
            'error_codes': None
        }
        
        try:
            # Create a prompt to parse the suggestions
            parse_prompt = f"""Parse the following process step suggestions into specific field updates:

{suggestions}

Please provide the updates in this exact format:
Description: [new description or None]
Decision: [new decision or None]
Success Outcome: [new success outcome or None]
Failure Outcome: [new failure outcome or None]
Validation Rules: [new validation rules or None]
Error Codes: [new error codes or None]

If a field should not be updated, use None."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Parse suggestions into specific field updates."},
                    {"role": "user", "content": parse_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent parsing
                max_tokens=500
            )
            
            # Parse the response
            parsed = response.choices[0].message.content.strip()
            for line in parsed.split('\n'):
                if ':' in line:
                    field, value = line.split(':', 1)
                    field = field.strip().lower()
                    value = value.strip()
                    if value.lower() != 'none':
                        suggested_updates[field] = value
                        
            return suggested_updates
            
        except Exception as e:
            print(f"Error parsing AI suggestions: {str(e)}")
            return suggested_updates

    def generate_step_description(self, step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate an intelligent step description based on context.
        
        Args:
            step_id: The current step ID
            predecessor_id: Optional ID of the step that references this step
            path_type: Optional path type ('success' or 'failure') that led here
        """
        if not self.openai_client:
            return ""
            
        try:
            # Build context for the prompt
            context = f"Process Name: {self.process_name}\n"
            context += f"Current Step: {step_id}\n"
            
            if predecessor_id:
                predecessor = next((s for s in self.steps if s.step_id == predecessor_id), None)
                if predecessor:
                    context += f"Predecessor Step: {predecessor.step_id}\n"
                    context += f"Predecessor Description: {predecessor.description}\n"
                    context += f"Predecessor Decision: {predecessor.decision}\n"
                    if path_type:
                        context += f"Path Type: {path_type}\n"
            
            prompt = f"""Given the following process context:

{context}

Suggest a clear and concise description of what happens in this step. The description should:
1. Be specific and actionable
2. Include key activities and inputs
3. Explain the purpose of the step
4. Be between 50-100 words
5. Follow business process documentation best practices

Please provide just the description, no additional text."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a business process expert. Create clear, concise step descriptions that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            description = response.choices[0].message.content.strip()
            
            # Validate word count
            words = description.split()
            if len(words) > 100:
                # If too long, truncate to 100 words
                description = ' '.join(words[:100])
            elif len(words) < 50:
                # If too short, try to generate a more detailed description
                prompt += "\nThe description was too short. Please provide a more detailed description between 50-100 words."
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a business process expert. Create clear, concise step descriptions that follow best practices."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                description = response.choices[0].message.content.strip()
            
            return description
        except Exception as e:
            print(f"Error generating step description: {str(e)}")
            return ""

    def generate_step_decision(self, step_id: str, description: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested decision for a step using OpenAI."""
        if not self.openai_client:
            return ""
        
        try:
            # Build context string
            context = f"Process: {self.process_name}\n"
            context += f"Current Step: {step_id}\n"
            context += f"Step Description: {description}\n"
            
            if predecessor_id:
                predecessor = next((s for s in self.steps if s.step_id == predecessor_id), None)
                if predecessor:
                    context += f"Previous Step: {predecessor.step_id}\n"
                    context += f"Previous Step Description: {predecessor.description}\n"
                    if path_type:
                        context += f"Path Type: {path_type}\n"
            
            prompt = f"""Based on the following process context:

{context}

Please suggest a clear, specific decision point for this step. The decision should:
1. Be a yes/no question
2. Be directly related to the step's purpose
3. Be specific and actionable
4. Help determine the next step in the process

Return only the decision question, without any additional explanation or formatting."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Provide clear, actionable decision points for process steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating decision suggestion: {str(e)}")
            return ""

    def generate_step_success_outcome(self, step_id: str, description: str, decision: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested success outcome for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            # Build context string
            context = f"Process: {self.process_name}\n"
            context += f"Current Step: {step_id} - {description}\n"
            context += f"Decision: {decision}\n"
            
            if predecessor_id:
                predecessor = next((s for s in self.steps if s.step_id == predecessor_id), None)
                if predecessor:
                    context += f"Previous Step: {predecessor.step_id} - {predecessor.description}\n"
                    if path_type:
                        context += f"Path Type: {path_type}\n"
            
            prompt = f"""Based on the following process context:

{context}

Please suggest a clear, specific success outcome for this step. The success outcome should:
1. Be a clear yes/no question
2. Directly relate to the step's purpose
3. Be specific and actionable
4. Help determine the next step

Format the response as a single question that can be answered with yes/no."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Provide clear, specific success outcomes for process steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating success outcome suggestion: {str(e)}")
            return ""

    def generate_step_failure_outcome(self, step_id: str, description: str, decision: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested failure outcome for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            # Build context string
            context = f"Process: {self.process_name}\n"
            context += f"Current Step: {step_id} - {description}\n"
            context += f"Decision: {decision}\n"
            
            if predecessor_id:
                predecessor = next((s for s in self.steps if s.step_id == predecessor_id), None)
                if predecessor:
                    context += f"Previous Step: {predecessor.step_id} - {predecessor.description}\n"
                    if path_type:
                        context += f"Path Type: {path_type}\n"
            
            prompt = f"""Based on the following process context:

{context}

Please suggest a clear, specific failure outcome for this step. The failure outcome should:
1. Clearly describe what happens when the step fails
2. Be specific about error handling or recovery steps
3. Help determine the next step in the failure path
4. Be actionable and informative

Format the response as a clear, concise statement describing the failure outcome."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Provide clear, specific failure outcomes for process steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating failure outcome suggestion: {str(e)}")
            return ""

    def create_missing_step(self, step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> ProcessStep:
        """Create a missing step that was referenced by another step."""
        print(f"\nCreating missing step: {step_id}")
        
        # Initial AI confirmation
        use_ai = False
        if self.openai_client:
            use_ai = input("\nWould you like to use AI suggestions for this step? (y/n)\n> ").lower() == 'y'
            if use_ai:
                print("\nI'll ask for your input first, then offer AI suggestions if you'd like.")
        
        # Get step description
        print("\nThe step name is used as a label in the process diagram.")
        description = input("What happens in this step?\n> ").strip()
        
        if use_ai and self.openai_client:
            want_ai_help = input("\nWould you like to see an AI suggestion for the description? (y/n)\n> ").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating step description")
                    suggested_description = self.generate_step_description(step_id, predecessor_id, path_type)
                    if suggested_description:
                        print(f"\nAI suggests the following description: '{suggested_description}'")
                        use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            description = suggested_description
                except Exception as e:
                    print(f"Error generating description suggestion: {str(e)}")
        
        # Get decision
        print("\nThe decision is a yes/no question that determines which path to take next.")
        decision = input("What decision needs to be made?\n> ").strip()
        
        if use_ai and self.openai_client:
            want_ai_help = input("\nWould you like to see an AI suggestion for the decision? (y/n)\n> ").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating decision suggestion")
                    suggested_decision = self.generate_step_decision(step_id, description, predecessor_id, path_type)
                    if suggested_decision:
                        print(f"\nAI suggests the following decision: '{suggested_decision}'")
                        use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            decision = suggested_decision
                except Exception as e:
                    print(f"Error generating decision suggestion: {str(e)}")
        
        # Get success outcome
        print("\nThe success outcome tells you which step to go to next when the decision is 'yes'.")
        success_outcome = input("What happens if this step succeeds?\n> ").strip()
        
        if use_ai and self.openai_client:
            want_ai_help = input("\nWould you like to see an AI suggestion for the success outcome? (y/n)\n> ").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating success outcome suggestion")
                    suggested_success = self.generate_step_success_outcome(step_id, description, decision, predecessor_id, path_type)
                    if suggested_success:
                        print(f"\nAI suggests the following success outcome: '{suggested_success}'")
                        use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            success_outcome = suggested_success
                except Exception as e:
                    print(f"Error generating success outcome suggestion: {str(e)}")
        
        # Get failure outcome
        print("\nThe failure outcome tells you which step to go to next when the decision is 'no'.")
        failure_outcome = input("What happens if this step fails?\n> ").strip()
        
        if use_ai and self.openai_client:
            want_ai_help = input("\nWould you like to see an AI suggestion for the failure outcome? (y/n)\n> ").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating failure outcome suggestion")
                    suggested_failure = self.generate_step_failure_outcome(step_id, description, decision, predecessor_id, path_type)
                    if suggested_failure:
                        print(f"\nAI suggests the following failure outcome: '{suggested_failure}'")
                        use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                        if use_suggested == 'y':
                            failure_outcome = suggested_failure
                except Exception as e:
                    print(f"Error generating failure outcome suggestion: {str(e)}")
        
        # Optional note
        print("\nA note is a brief comment that appears next to the step in the diagram.")
        add_note = input("Would you like to add a note for this step? (y/n)\n> ").lower()
        note_id = None
        if add_note == 'y':
            note_content = input("What's the note content?\n> ").strip()
            
            if use_ai and self.openai_client:
                want_ai_help = input("\nWould you like to see an AI suggestion for the note? (y/n)\n> ").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating note suggestion")
                        suggested_note = self.generate_step_note(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_note:
                            print(f"\nAI suggests the following note: '{suggested_note}'")
                            use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                            if use_suggested == 'y':
                                note_content = suggested_note
                    except Exception as e:
                        print(f"Error generating note suggestion: {str(e)}")
            
            note_id = f"Note{self.current_note_id}"
            self.notes.append(ProcessNote(note_id, note_content, step_id))
            self.current_note_id += 1
        
        # Enhanced fields
        print("\nValidation rules help ensure the step receives good input data.")
        add_validation = input("Would you like to add validation rules? (y/n)\n> ").lower()
        validation_rules = None
        if add_validation == 'y':
            validation_rules = input("Enter validation rules:\n> ").strip() or None
            
            if use_ai and self.openai_client:
                want_ai_help = input("\nWould you like to see an AI suggestion for the validation rules? (y/n)\n> ").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating validation rules suggestion")
                        suggested_validation = self.generate_validation_rules(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_validation:
                            print(f"\nAI suggests the following validation rules:\n{suggested_validation}")
                            use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                            if use_suggested == 'y':
                                validation_rules = suggested_validation
                    except Exception as e:
                        print(f"Error generating validation rules suggestion: {str(e)}")
        
        print("\nError codes help identify and track specific problems that might occur.")
        add_error_codes = input("Would you like to add error codes? (y/n)\n> ").lower()
        error_codes = None
        if add_error_codes == 'y':
            error_codes = input("Enter error codes:\n> ").strip() or None
            
            if use_ai and self.openai_client:
                want_ai_help = input("\nWould you like to see an AI suggestion for the error codes? (y/n)\n> ").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating error codes suggestion")
                        suggested_error_codes = self.generate_error_codes(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_error_codes:
                            print(f"\nAI suggests the following error codes:\n{suggested_error_codes}")
                            use_suggested = input("Use this suggestion? (y/n)\n> ").lower()
                            if use_suggested == 'y':
                                error_codes = suggested_error_codes
                    except Exception as e:
                        print(f"Error generating error codes suggestion: {str(e)}")
        
        # Create and return the step
        step = ProcessStep(
            step_id=step_id,
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            note_id=note_id,
            next_step_success="End",  # Default to End, will be updated later
            next_step_failure="End",  # Default to End, will be updated later
            validation_rules=validation_rules,
            error_codes=error_codes
        )
        
        return step

    def generate_step_title(self, step_id: str, predecessor_id: str, path_type: str) -> str:
        """Generate an intelligent step title based on context.
        
        Args:
            step_id: The current step ID
            predecessor_id: The ID of the step that references this step
            path_type: Either 'success' or 'failure' indicating which path led here
        """
        if not self.openai_client:
            return step_id
            
        try:
            # Get predecessor step details
            predecessor = next((s for s in self.steps if s.step_id == predecessor_id), None)
            if not predecessor:
                return step_id
                
            prompt = f"""Given the following process context:
Process Name: {self.process_name}
Predecessor Step: {predecessor.step_id}
Predecessor Description: {predecessor.description}
Predecessor Decision: {predecessor.decision}
Path Type: {path_type}
Current Step ID: {step_id}

Suggest an appropriate title for this step that:
1. Follows logically from the predecessor step
2. Is clear and descriptive
3. Starts with a verb
4. Is specific to the process
5. Is concise (2-5 words)
6. Follows business process naming conventions

Please provide just the step title, no additional text."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a business process expert. Create clear, concise step titles that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating step title: {str(e)}")
            return step_id

    def add_step(self, step: ProcessStep) -> List[str]:
        """Add a new step to the process and validate it."""
        # Validate the step
        issues = step.validate()
        if issues:
            return issues
            
        # Check for duplicate step ID
        if any(s.step_id == step.step_id for s in self.steps):
            issues.append(f"Step ID '{step.step_id}' already exists")
            return issues
            
        # Add the step
        self.steps.append(step)
        self.step_count += 1
        
        # Find and create any missing steps
        while True:
            missing_steps = self.find_missing_steps()
            if not missing_steps:
                break
                
            for missing_step_id, predecessor_id, path_type in missing_steps:
                print(f"\nFound missing step: {missing_step_id}")
                print(f"Referenced by step: {predecessor_id} on {path_type} path")
                
                new_step = self.create_missing_step(missing_step_id, predecessor_id, path_type)
                step_issues = self.add_step(new_step)
                
                if step_issues:
                    print("\n=== Validation Issues ===")
                    for issue in step_issues:
                        print(f"- {issue}")
                    print("\nPlease fix these issues and try again.")
                    continue
        
        # Validate the process flow
        flow_issues = validate_process_flow(self.steps)
        note_issues = validate_notes(self.notes, self.steps)
        
        return flow_issues + note_issues

    def add_note(self, note: ProcessNote) -> List[str]:
        """Add a new note to the process and validate it."""
        # Validate the note
        issues = note.validate()
        if issues:
            return issues
            
        # Check for duplicate note ID
        if any(n.note_id == note.note_id for n in self.notes):
            issues.append(f"Note ID '{note.note_id}' already exists")
            return issues
            
        # Check if related step exists
        if not any(s.step_id == note.related_step_id for s in self.steps):
            issues.append(f"Related step '{note.related_step_id}' does not exist")
            return issues
            
        # Add the note
        self.notes.append(note)
        
        # Link note to step
        for step in self.steps:
            if step.step_id == note.related_step_id:
                step.note_id = note.note_id
                break
                
        return []

    def evaluate_step_design(self, step: ProcessStep) -> str:
        """Evaluate a step's design using OpenAI."""
        if not self.openai_client:
            return "AI evaluation is not available - OPENAI_API_KEY not found or invalid."
            
        try:
            prompt = f"""Evaluate the following process step design:

Process Name: {self.process_name}
Step ID: {step.step_id}
Description: {step.description}
Decision: {step.decision}
Success Outcome: {step.success_outcome}
Failure Outcome: {step.failure_outcome}
Next Step (Success): {step.next_step_success}
Next Step (Failure): {step.next_step_failure}
Validation Rules: {step.validation_rules or 'None'}
Error Codes: {step.error_codes or 'None'}

Please provide:
1. A brief assessment of the step's design
2. Potential improvements or considerations
3. Any missing elements that should be addressed
4. Specific recommendations for validation or error handling if not provided

Keep the response concise and actionable."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Provide clear, actionable feedback on process step design."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error evaluating step design: {str(e)}"

    def setup_output_directory(self, base_dir: Optional[Path] = None) -> Path:
        """Set up the output directory structure for this run."""
        base_dir = base_dir or self.config.default_output_dir
        output_dir = base_dir / self.process_name / self.timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        return output_dir

    def generate_csv(self, base_output_dir: Optional[Path] = None) -> None:
        """Generate CSV files for the process."""
        output_dir = self.setup_output_directory(base_output_dir)
        
        # Process steps CSV
        steps_data = [
            {
                "Step ID": step.step_id,
                "Description": step.description,
                "Decision": step.decision,
                "Success Outcome": step.success_outcome,
                "Failure Outcome": step.failure_outcome,
                "Linked Note ID": step.note_id,
                "Next Step (Success)": step.next_step_success,
                "Next Step (Failure)": step.next_step_failure,
                "Validation Rules": step.validation_rules,
                "Error Codes": step.error_codes
            }
            for step in self.steps
        ]
        
        steps_file = output_dir / f"{self.process_name}_process.csv"
        write_csv(steps_data, steps_file, list(steps_data[0].keys()) if steps_data else [])
        
        # Notes CSV
        if self.notes:
            notes_data = [
                {
                    "Note ID": note.note_id,
                    "Content": note.content,
                    "Related Step ID": note.related_step_id
                }
                for note in self.notes
            ]
            
            notes_file = output_dir / f"{self.process_name}_notes.csv"
            write_csv(notes_data, notes_file, list(notes_data[0].keys()))
        
        print(f"\nCSV files generated in {output_dir}/")
        print(f"- Process steps: {steps_file}")
        if self.notes:
            print(f"- Notes: {notes_file}")

    def generate_mermaid_diagram(self, base_output_dir: Optional[Path] = None) -> str:
        """Generate a Mermaid diagram from the process steps."""
        if not self.output_dir:
            output_dir = self.setup_output_directory(base_output_dir)
        else:
            output_dir = self.output_dir
            
        mermaid_file = output_dir / f"{self.process_name}_diagram.mmd"
        
        # Start the diagram
        diagram = "```mermaid\ngraph TD\n"
        
        # Create a mapping from step_id to sanitized Mermaid node ID
        step_id_to_node_id = {}
        for step in self.steps:
            step_id_to_node_id[step.step_id] = f"Step_{sanitize_id(step.step_id)}"
        
        # Add nodes and edges
        for step in self.steps:
            # Get the sanitized node ID for this step
            safe_id = step_id_to_node_id[step.step_id]
            
            # Add the main step node
            diagram += f"    {safe_id}[\"{step.description}\"]\n"
            
            # Add decision node if there's a decision
            if step.decision:
                decision_id = f"Decision_{sanitize_id(step.step_id)}"
                diagram += f"    {decision_id}{{\"{step.decision}\"}}\n"
                diagram += f"    {safe_id} --> {decision_id}\n"
                
                # Add success path
                if step.next_step_success.lower() != 'end':
                    if step.next_step_success in step_id_to_node_id:
                        next_success = step_id_to_node_id[step.next_step_success]
                        diagram += f"    {decision_id} -->|Yes| {next_success}\n"
                    else:
                        future_id = f"Future_{sanitize_id(step.next_step_success)}"
                        step_id_to_node_id[step.next_step_success] = future_id
                        diagram += f"    {future_id}[\"{step.next_step_success}\"]\n"
                        diagram += f"    {decision_id} -->|Yes| {future_id}\n"
                else:
                    end_id = "ProcessEnd"
                    diagram += f"    {end_id}[\"Process End\"]\n"
                    diagram += f"    {decision_id} -->|Yes| {end_id}\n"
                
                # Add failure path
                if step.next_step_failure.lower() != 'end':
                    if step.next_step_failure in step_id_to_node_id:
                        next_failure = step_id_to_node_id[step.next_step_failure]
                        diagram += f"    {decision_id} -->|No| {next_failure}\n"
                    else:
                        failure_id = f"Future_{sanitize_id(step.next_step_failure)}"
                        step_id_to_node_id[step.next_step_failure] = failure_id
                        diagram += f"    {failure_id}[\"{step.next_step_failure}\"]\n"
                        diagram += f"    {decision_id} -->|No| {failure_id}\n"
                else:
                    end_id = "ProcessEnd"
                    if "ProcessEnd" not in diagram:
                        diagram += f"    {end_id}[\"Process End\"]\n"
                    diagram += f"    {decision_id} -->|No| {end_id}\n"
            
            # Add note if present
            if step.note_id:
                note = next(n for n in self.notes if n.note_id == step.note_id)
                note_id = f"Note_{sanitize_id(step.step_id)}"
                diagram += f"    {note_id}[\"{note.content}\"]\n"
                diagram += f"    {safe_id} -.-> {note_id}\n"
        
        # Add styling
        diagram += """
    classDef process fill:#E8F5E9,stroke:#66BB6A
    classDef decision fill:#FFF3E0,stroke:#FFB74D
    classDef note fill:#FFFDE7,stroke:#FFF9C4
    classDef end fill:#FFEBEE,stroke:#E57373
    
    class Step* process
    class Decision* decision
    class Note* note
    class End end
```"""
        
        # Save to file
        mermaid_file.write_text(diagram)
        print(f"\nMermaid diagram generated: {mermaid_file}")
        return diagram

    def generate_llm_prompt(self) -> str:
        """Generate a prompt for an LLM to help document the process."""
        prompt = f"""I need help documenting the {self.process_name} process. Here's what I know so far:

Process Overview:
{self.process_name} is a workflow that handles the following steps:

"""
        
        for step in self.steps:
            prompt += f"""
Step {step.step_id}: {step.description}
- Decision: {step.decision}
- Success: {step.success_outcome}
- Failure: {step.failure_outcome}
"""
            if step.note_id:
                note = next(n for n in self.notes if n.note_id == step.note_id)
                prompt += f"- Note: {note.content}\n"
            
            if step.validation_rules:
                prompt += f"- Validation: {step.validation_rules}\n"
            if step.error_codes:
                prompt += f"- Error Codes: {step.error_codes}\n"
        
        prompt += """
Please help me:
1. Review this process for completeness
2. Identify any missing steps or edge cases
3. Suggest improvements to the workflow
4. Create a clear, visual representation of the process
"""
        
        return prompt 

    def generate_executive_summary(self) -> str:
        """Generate an executive summary of the process."""
        if not self.openai_client:
            return "AI features are not available - OPENAI_API_KEY not found or invalid."
            
        try:
            # Create a detailed prompt for the executive summary
            prompt = f"""Create an executive summary for the {self.process_name} process. Here's the process information:

Process Steps:
"""
            
            for step in self.steps:
                prompt += f"""
Step {step.step_id}: {step.description}
- Decision: {step.decision}
- Success: {step.success_outcome}
- Failure: {step.failure_outcome}
"""
                if step.note_id:
                    note = next(n for n in self.notes if n.note_id == step.note_id)
                    prompt += f"- Note: {note.content}\n"
                
                if step.validation_rules:
                    prompt += f"- Validation: {step.validation_rules}\n"
                if step.error_codes:
                    prompt += f"- Error Codes: {step.error_codes}\n"
            
            prompt += """
Please create an executive summary that includes:
1. Process Overview
2. Key Steps and Decision Points
3. Success and Failure Paths
4. Risk Mitigation Strategies
5. Implementation Considerations
6. Expected Outcomes

Format the response in clear sections with appropriate headers.
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process documentation expert. Create clear, concise executive summaries for business processes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating executive summary: {str(e)}"

    def run_interview(self) -> None:
        """Run the interactive interview process."""
        print(f"\n=== Process Builder: {self.process_name} ===\n")
        
        def show_menu():
            print("\n" + "="*50)
            print("=== Process Builder Menu ===")
            print("1. View all steps")
            print("2. Edit a step")
            print("3. Add new step")
            print("4. Generate outputs and exit")
            print("="*50 + "\n")
        
        # Show initial menu
        show_menu()
        
        while True:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                self.view_all_steps()
                # Always redisplay menu after viewing steps
                show_menu()
            elif choice == '2':
                self.edit_step()
                # Always redisplay menu after editing
                show_menu()
            elif choice == '3':
                self.add_step()
                # After adding a step, ask if they want to add another
                while True:
                    continue_process = input("\nAdd another step? (y/n)\n> ").lower()
                    if continue_process == 'y':
                        self.add_step()
                    else:
                        break
                # Always redisplay menu after adding steps
                show_menu()
            elif choice == '4':
                break
            else:
                print("Invalid choice. Please try again.")
                # Always redisplay menu after invalid choice
                show_menu()
        
        # Generate outputs
        self.generate_csv()
        self.generate_mermaid_diagram()
        
        # Generate and save LLM prompt
        llm_prompt = self.generate_llm_prompt()
        print("\n=== LLM Prompt ===")
        print(llm_prompt)
        
        if self.output_dir:
            prompt_file = self.output_dir / f"{self.process_name}_prompt.txt"
            prompt_file.write_text(llm_prompt)
            print(f"LLM prompt saved to: {prompt_file}")
        
        # Generate and save executive summary
        executive_summary = self.generate_executive_summary()
        print("\n=== Executive Summary ===")
        print(executive_summary)
        
        if self.output_dir:
            summary_file = self.output_dir / f"{self.process_name}_executive_summary.md"
            summary_file.write_text(executive_summary)
            print(f"Executive summary saved to: {summary_file}")

    def view_all_steps(self) -> None:
        """Display all steps with their flow connections."""
        if not self.steps:
            print("\nNo steps defined yet.")
            return
            
        print("\n=== Process Steps ===\n")
        for step in self.steps:
            # Find predecessors
            predecessors = []
            for s in self.steps:
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
                note = next(n for n in self.notes if n.note_id == step.note_id)
                print(f"\nNote: {note.content}")
            if step.validation_rules:
                print(f"Validation Rules: {step.validation_rules}")
            if step.error_codes:
                print(f"Error Codes: {step.error_codes}")
            print("-" * 80 + "\n")

    def edit_step(self) -> None:
        """Edit an existing step."""
        if not self.steps:
            print("\nNo steps to edit.")
            return
            
        # Display available steps
        print("\nAvailable steps:")
        for i, step in enumerate(self.steps, 1):
            print(f"{i}. {step.step_id}")
        
        try:
            choice = int(input("\nEnter step number to edit: ").strip())
            if choice < 1 or choice > len(self.steps):
                print("Invalid step number.")
                return
                
            step = self.steps[choice - 1]
            
            print("\nEditing step:", step.step_id)
            print("Enter new values (or press Enter to keep current value)")
            
            # Get new values with AI suggestions
            if self.openai_client:
                print("\nGenerating AI suggestions...")
                show_loading_animation("Generating suggestions")
                
                description_suggestion = self.generate_step_description(step.step_id)
                decision_suggestion = self.generate_step_decision(step.step_id, step.description)
                success_suggestion = self.generate_step_success_outcome(step.step_id, step.description, step.decision)
                failure_suggestion = self.generate_step_failure_outcome(step.step_id, step.description, step.decision)
                note_suggestion = self.generate_step_note(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                validation_suggestion = self.generate_validation_rules(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                error_suggestion = self.generate_error_codes(step.step_id, step.description, step.decision, step.success_outcome, step.failure_outcome)
                
                # Description
                if description_suggestion:
                    print(f"\nAI suggests description: '{description_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.description = description_suggestion
                    else:
                        new_desc = input(f"Description [{step.description}]: ").strip()
                        if new_desc:
                            step.description = new_desc
                
                # Decision
                if decision_suggestion:
                    print(f"\nAI suggests decision: '{decision_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.decision = decision_suggestion
                    else:
                        new_decision = input(f"Decision [{step.decision}]: ").strip()
                        if new_decision:
                            step.decision = new_decision
                
                # Success Outcome
                if success_suggestion:
                    print(f"\nAI suggests success outcome: '{success_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.success_outcome = success_suggestion
                    else:
                        new_success = input(f"Success Outcome [{step.success_outcome}]: ").strip()
                        if new_success:
                            step.success_outcome = new_success
                
                # Failure Outcome
                if failure_suggestion:
                    print(f"\nAI suggests failure outcome: '{failure_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.failure_outcome = failure_suggestion
                    else:
                        new_failure = input(f"Failure Outcome [{step.failure_outcome}]: ").strip()
                        if new_failure:
                            step.failure_outcome = new_failure
                
                # Note
                if note_suggestion:
                    print(f"\nAI suggests note: '{note_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        if step.note_id:
                            # Update existing note
                            note = next(n for n in self.notes if n.note_id == step.note_id)
                            note.content = note_suggestion
                        else:
                            # Create new note
                            note_id = f"Note{self.current_note_id}"
                            self.notes.append(ProcessNote(note_id, note_suggestion, step.step_id))
                            step.note_id = note_id
                            self.current_note_id += 1
                    else:
                        new_note = input(f"Note [{'None' if not step.note_id else next(n for n in self.notes if n.note_id == step.note_id).content}]: ").strip()
                        if new_note:
                            if step.note_id:
                                # Update existing note
                                note = next(n for n in self.notes if n.note_id == step.note_id)
                                note.content = new_note
                            else:
                                # Create new note
                                note_id = f"Note{self.current_note_id}"
                                self.notes.append(ProcessNote(note_id, new_note, step.step_id))
                                step.note_id = note_id
                                self.current_note_id += 1
                
                # Validation Rules
                if validation_suggestion:
                    print(f"\nAI suggests validation rules: '{validation_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.validation_rules = validation_suggestion
                    else:
                        new_validation = input(f"Validation Rules [{step.validation_rules or 'None'}]: ").strip()
                        if new_validation:
                            step.validation_rules = new_validation
                        elif new_validation == '':
                            step.validation_rules = None
                
                # Error Codes
                if error_suggestion:
                    print(f"\nAI suggests error codes: '{error_suggestion}'")
                    use_suggestion = input("Use this suggestion? (y/n): ").lower() == 'y'
                    if use_suggestion:
                        step.error_codes = error_suggestion
                    else:
                        new_errors = input(f"Error Codes [{step.error_codes or 'None'}]: ").strip()
                        if new_errors:
                            step.error_codes = new_errors
                        elif new_errors == '':
                            step.error_codes = None
            else:
                # Manual editing without AI suggestions
                new_desc = input(f"Description [{step.description}]: ").strip()
                if new_desc:
                    step.description = new_desc
                
                new_decision = input(f"Decision [{step.decision}]: ").strip()
                if new_decision:
                    step.decision = new_decision
                
                new_success = input(f"Success Outcome [{step.success_outcome}]: ").strip()
                if new_success:
                    step.success_outcome = new_success
                
                new_failure = input(f"Failure Outcome [{step.failure_outcome}]: ").strip()
                if new_failure:
                    step.failure_outcome = new_failure
                
                new_note = input(f"Note [{'None' if not step.note_id else next(n for n in self.notes if n.note_id == step.note_id).content}]: ").strip()
                if new_note:
                    if step.note_id:
                        # Update existing note
                        note = next(n for n in self.notes if n.note_id == step.note_id)
                        note.content = new_note
                    else:
                        # Create new note
                        note_id = f"Note{self.current_note_id}"
                        self.notes.append(ProcessNote(note_id, new_note, step.step_id))
                        step.note_id = note_id
                        self.current_note_id += 1
                
                new_validation = input(f"Validation Rules [{step.validation_rules or 'None'}]: ").strip()
                if new_validation:
                    step.validation_rules = new_validation
                elif new_validation == '':
                    step.validation_rules = None
                
                new_errors = input(f"Error Codes [{step.error_codes or 'None'}]: ").strip()
                if new_errors:
                    step.error_codes = new_errors
                elif new_errors == '':
                    step.error_codes = None
            
            # Next steps
            new_next_success = input(f"Next Step (Success) [{step.next_step_success}]: ").strip()
            if new_next_success:
                step.next_step_success = new_next_success
            
            new_next_failure = input(f"Next Step (Failure) [{step.next_step_failure}]: ").strip()
            if new_next_failure:
                step.next_step_failure = new_next_failure
            
            # Validate the process flow after edits
            flow_issues = validate_process_flow(self.steps)
            note_issues = validate_notes(self.notes, self.steps)
            
            if flow_issues or note_issues:
                print("\n=== Validation Issues ===")
                for issue in flow_issues + note_issues:
                    print(f"- {issue}")
                print("\nPlease fix these issues.")
            else:
                print("\nStep updated successfully.")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"Error editing step: {str(e)}")

    def generate_next_step_suggestion(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str, is_success_path: bool) -> str:
        """Generate a suggested next step name using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            # Build context string
            context = f"Process: {self.process_name}\n"
            context += f"Current Step: {step_id} - {description}\n"
            context += f"Decision: {decision}\n"
            context += f"Success Outcome: {success_outcome}\n"
            context += f"Failure Outcome: {failure_outcome}\n"
            context += f"Path Type: {'Success' if is_success_path else 'Failure'}\n"
            
            prompt = f"""Based on the following process context:

{context}

Please suggest a clear, descriptive name for the next step in this process. The step name should:
1. Start with a verb
2. Be clear and descriptive (2-5 words)
3. Follow logically from the {'success' if is_success_path else 'failure'} outcome
4. Be specific to the process flow
5. Follow business process naming conventions

Format the response as a single step name, or 'End' if this should be the final step."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Create clear, descriptive step names that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating next step suggestion: {str(e)}")
            return ""

    def generate_step_note(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str) -> str:
        """Generate a suggested note for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            context = f"""Process: {self.process_name}
Step ID: {step_id}
Description: {description}
Decision: {decision}
Success Outcome: {success_outcome}
Failure Outcome: {failure_outcome}

Please suggest a very concise note (10-20 words) that captures the key point or requirement for this step. The note should be brief and actionable."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process documentation expert. Provide very concise, actionable notes."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            note = response.choices[0].message.content.strip()
            # Ensure the note is within 10-20 words
            words = note.split()
            if len(words) > 20:
                note = ' '.join(words[:20])
            return note
        except Exception as e:
            print(f"Error generating note suggestion: {str(e)}")
            return ""

    def generate_validation_rules(self, step_id: str, description: str, decision: str, 
                                success_outcome: str, failure_outcome: str) -> str:
        """Generate suggested validation rules for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            context = f"""Process: {self.process_name}
Step ID: {step_id}
Description: {description}
Decision: {decision}
Success Outcome: {success_outcome}
Failure Outcome: {failure_outcome}

Please suggest 2-3 very concise validation rules (10-20 words each) for this step. Each rule should:
1. Be specific and actionable
2. Focus on one key validation point
3. Be brief and clear
4. Be easy to implement

Format the response as a bulleted list of very short validation rules."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process validation expert. Provide very concise, specific validation rules."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            rules = response.choices[0].message.content.strip()
            # Ensure each rule is within 10-20 words
            formatted_rules = []
            for rule in rules.split('\n'):
                if rule.strip().startswith('-') or rule.strip().startswith('*'):
                    words = rule.split()
                    if len(words) > 20:
                        rule = ' '.join(words[:20])
                    formatted_rules.append(rule)
            return '\n'.join(formatted_rules)
        except Exception as e:
            print(f"Error generating validation rules suggestion: {str(e)}")
            return ""

    def generate_error_codes(self, step_id: str, description: str, decision: str, 
                           success_outcome: str, failure_outcome: str) -> str:
        """Generate suggested error codes for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            context = f"""Process: {self.process_name}
Step ID: {step_id}
Description: {description}
Decision: {decision}
Success Outcome: {success_outcome}
Failure Outcome: {failure_outcome}

Please suggest error codes for this step that:
1. Are specific to potential failure scenarios
2. Follow a consistent naming convention
3. Include both technical and business error codes
4. Are descriptive and meaningful
5. Can be used for logging and monitoring

Format the response as a bulleted list of error codes with brief descriptions."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process error handling expert. Provide clear, specific error codes for process steps."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating error codes suggestion: {str(e)}")
            return "" 