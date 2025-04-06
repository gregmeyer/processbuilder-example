#!/usr/bin/env python3
"""
Process Builder Utility

A tool for building structured process definitions through interactive interviews.
Generates both CSV output and LLM prompts for process documentation.
"""

import csv
import os
import sys
import argparse
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import openai
from pathlib import Path

# Try to import dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv package is not installed. Installing it with:")
    print("pip install python-dotenv")
    print("Then try running this script again.")
    sys.exit(1)

# Try to load OpenAI API key from .env file in the writing directory
env_path = Path(os.path.dirname(os.path.dirname(__file__))) / '.env'
if not env_path.exists():
    print(f"Warning: .env file not found at {env_path}")
    print("To use AI features, please create a .env file with your OpenAI API key:")
    print(f"echo 'OPENAI_API_KEY=your_api_key_here' > {env_path}")
    print("You can continue without AI features, but step evaluation will not work.")
    print()

# Load environment variables from .env file if it exists
load_dotenv(dotenv_path=env_path)

@dataclass
class ProcessStep:
    """Represents a single step in a process."""
    step_id: str
    description: str
    decision: str
    success_outcome: str
    failure_outcome: str
    note_id: Optional[str]
    next_step_success: str
    next_step_failure: str
    validation_rules: Optional[str] = None
    error_codes: Optional[str] = None
    retry_logic: Optional[str] = None
    design_feedback: Optional[str] = None

@dataclass
class ProcessNote:
    """Represents a note associated with a process step."""
    note_id: str
    content: str
    related_step_id: str

class ProcessBuilder:
    """Main class for building processes through interactive interviews."""
    
    def __init__(self, process_name: str):
        self.process_name = process_name
        self.steps: List[ProcessStep] = []
        self.notes: List[ProcessNote] = []
        self.current_note_id = 1
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = None
        self.step_count = 0  # To track number of steps for display purposes only
        
        # Initialize OpenAI client if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=api_key)
                # Test the connection
                self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                print("Successfully connected to OpenAI API")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {str(e)}")
                print("AI evaluation features will be disabled.")
                self.openai_client = None
        else:
            self.openai_client = None
            print("Warning: OPENAI_API_KEY not found in environment variables.")
            print("To enable AI features, please set the OPENAI_API_KEY environment variable.")
            print("You can do this by creating a .env file in the writing directory with:")
            print(f"echo 'OPENAI_API_KEY=your_api_key_here' > {env_path}")

    def validate_step_id(self, step_id: str) -> bool:
        """Validate that a step name is unique and non-empty."""
        if not step_id.strip():
            return False
        # Check for uniqueness among existing steps
        return not any(step.step_id == step_id for step in self.steps)

    def validate_next_step(self, next_step: str) -> bool:
        """Validate that a next step reference is valid.
        
        Valid next steps include:
        - 'End' (case-insensitive) to indicate end of process
        - Any non-empty string that will be used as a step identifier
        """
        if next_step.lower() == 'end':
            return True
        # Accept any non-empty string as a valid step reference
        return bool(next_step.strip())

    def validate_process_flow(self) -> List[str]:
        """Validate the entire process flow and return a list of issues."""
        issues = []
        
        # Check for at least one step and end points
        if not self.steps:
            issues.append("Process must have at least one step")
            return issues
            
        has_end = any(step.next_step_success.lower() == 'end' or 
                     step.next_step_failure.lower() == 'end' for step in self.steps)
        
        if not has_end:
            issues.append("Process must have at least one path that leads to 'End'")
        
        # Check all paths for circular references and missing steps
        if self.steps:
            first_step = self.steps[0]
            
            # Helper function to check a path
            def check_path(start_id, path_name):
                visited = set()
                current = start_id
                path = []
                
                while current is not None and current.lower() != 'end':
                    path.append(current)
                    
                    if current in visited:
                        issues.append(f"Circular reference detected in {path_name} path: {' -> '.join(path)}")
                        break
                    
                    visited.add(current)
                    
                    step = next((s for s in self.steps if s.step_id == current), None)
                    if step is None:
                        issues.append(f"Step name '{current}' referenced in {path_name} path not found")
                        break
                    
                    if path_name == "success":
                        current = step.next_step_success
                    else:
                        current = step.next_step_failure
            
            # Check both success and failure paths starting from the first step
            check_path(first_step.step_id, "success")
            check_path(first_step.step_id, "failure")
        
        # Check for disconnected steps
        all_step_ids = {step.step_id for step in self.steps}
        referenced_steps = set()
        
        for step in self.steps:
            if step.next_step_success.lower() != 'end':
                referenced_steps.add(step.next_step_success)
            if step.next_step_failure.lower() != 'end':
                referenced_steps.add(step.next_step_failure)
        
        # Get the first step ID which doesn't need to be referenced
        first_step_id = self.steps[0].step_id if self.steps else ""
        disconnected = all_step_ids - referenced_steps - {first_step_id}  # First step doesn't need to be referenced
        if disconnected:
            issues.append(f"Disconnected step names found: {', '.join(disconnected)}")
        return issues

    def validate_notes(self) -> List[str]:
        """Validate notes and return a list of issues."""
        issues = []
        
        # Check for duplicate note IDs
        note_ids = [note.note_id for note in self.notes]
        if len(note_ids) != len(set(note_ids)):
            issues.append("Duplicate note IDs found")
        
        # Check for orphaned notes
        step_ids = {step.step_id for step in self.steps}
        for note in self.notes:
            if note.related_step_id not in step_ids:
                issues.append(f"Note {note.note_id} references non-existent step name '{note.related_step_id}'")
        
        return issues

    def get_step_input(self, prompt: str) -> str:
        """Get input from user with validation."""
        while True:
            response = input(f"\n{prompt}\n> ").strip()
            if response:
                return response
            print("Please provide a response.")

    def evaluate_step_design(self, step: ProcessStep) -> str:
        """Evaluate a step's design using OpenAI."""
        # Check if OpenAI client is available
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
Retry Logic: {step.retry_logic or 'None'}

Please provide:
1. A brief assessment of the step's design
2. Potential improvements or considerations
3. Any missing elements that should be addressed
4. Specific recommendations for validation, error handling, or retry logic if not provided

Keep the response concise and actionable."""

            try:
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
            except openai.APIError as e:
                return f"OpenAI API Error: {str(e)}"
            except openai.RateLimitError as e:
                return f"OpenAI Rate Limit Error: {str(e)}"
            except openai.APIConnectionError as e:
                return f"OpenAI Connection Error: {str(e)}"
            except Exception as e:
                return f"Error evaluating step design: {str(e)}"
        except Exception as e:
            return f"Unexpected error in evaluate_step_design: {str(e)}"

    def add_step(self) -> None:
        """Add a new step to the process through interactive interview."""
        self.step_count += 1
        print(f"\n=== Step {self.step_count} ===")
        
        # Get step description - this will be used as the step ID
        description = self.get_step_input("What happens in this step?")
        
        # Use the description as the step ID
        step_id = description
        
        # Validate step name is unique and valid
        if not step_id.strip():
            print("Error: Step description cannot be empty.")
            print("Please provide a descriptive name for this step.")
            self.step_count -= 1  # Revert step count since we're not adding this step
            return
        if not self.validate_step_id(step_id):
            print(f"Error: A step with description '{step_id}' already exists.")
            print("Please use a different, unique description for this step.")
            self.step_count -= 1  # Revert step count since we're not adding this step
            return
        decision = self.get_step_input("What decision needs to be made?")
        success_outcome = self.get_step_input("What happens if this step succeeds?")
        failure_outcome = self.get_step_input("What happens if this step fails?")
        
        # Optional note
        add_note = self.get_step_input("Would you like to add a note for this step? (y/n)").lower()
        note_id = None
        if add_note == 'y':
            note_content = self.get_step_input("What's the note content?")
            note_id = f"Note{self.current_note_id}"
            self.notes.append(ProcessNote(note_id, note_content, step_id))
            self.current_note_id += 1
        
        # Get and validate next steps
        while True:
            next_step_success = self.get_step_input("What's the next step if successful? (Enter a descriptive name for the next step or 'End' if final step)")
            if self.validate_next_step(next_step_success):
                break
            print("Please enter a descriptive name for the next step or 'End' to finish the process.")
            print("The name should clearly describe what happens in that step.")
        
        while True:
            next_step_failure = self.get_step_input("What's the next step if failed? (Enter a descriptive name for the next step or 'End' if final step)")
            if self.validate_next_step(next_step_failure):
                break
            print("Please enter a descriptive name for the next step or 'End' to finish the process.")
            print("The name should clearly describe what happens in that step.")
        
        # Enhanced fields
        validation_rules = self.get_step_input("Any validation rules for this step? (Press Enter to skip)")
        error_codes = self.get_step_input("Any specific error codes? (Press Enter to skip)")
        retry_logic = self.get_step_input("Any retry logic? (Press Enter to skip)")
        
        step = ProcessStep(
            step_id=step_id,
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            note_id=note_id,
            next_step_success=next_step_success,
            next_step_failure=next_step_failure,
            validation_rules=validation_rules if validation_rules else None,
            error_codes=error_codes if error_codes else None,
            retry_logic=retry_logic if retry_logic else None
        )
        
        # Evaluate step design
        print("\nEvaluating step design with AI...")
        try:
            design_feedback = self.evaluate_step_design(step)
            step.design_feedback = design_feedback
            print("\n=== Step Design Feedback ===")
            print(design_feedback)
            
            # Ask if user wants to modify the step based on feedback
            modify = self.get_step_input("\nWould you like to modify this step based on the feedback? (y/n)").lower()
            if modify == 'y':
                print("\n=== Suggested Improvements ===")
                try:
                    # Get AI to summarize feedback and suggest a replacement step
                    prompt = f"""Based on the following feedback for a process step:

{design_feedback}

Please:
1. Summarize the key improvements needed in 2-3 bullet points
2. Provide a complete replacement step that addresses these improvements
3. Format the response as:
   SUMMARY:
   - Bullet point 1
   - Bullet point 2
   
   SUGGESTED STEP:
   Description: [new description]
   Decision: [new decision]
   Success Outcome: [new success outcome]
   Failure Outcome: [new failure outcome]
   Validation Rules: [suggested validation rules]
   Error Codes: [suggested error codes]
   Retry Logic: [suggested retry logic]"""

                    response = self.openai_client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": "You are a process design expert. Provide clear, actionable improvements for process steps."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    suggested_improvements = response.choices[0].message.content.strip()
                    print(suggested_improvements)
                    
                    # Ask if user wants to use the suggested step
                    use_suggestion = self.get_step_input("\nWould you like to use this suggested step? (y/n)").lower()
                    if use_suggestion == 'y':
                        # Extract the suggested step details using regex
                        import re
                        description_match = re.search(r'Description: (.*?)(?=\n|$)', suggested_improvements)
                        decision_match = re.search(r'Decision: (.*?)(?=\n|$)', suggested_improvements)
                        success_match = re.search(r'Success Outcome: (.*?)(?=\n|$)', suggested_improvements)
                        failure_match = re.search(r'Failure Outcome: (.*?)(?=\n|$)', suggested_improvements)
                        validation_match = re.search(r'Validation Rules: (.*?)(?=\n|$)', suggested_improvements)
                        error_match = re.search(r'Error Codes: (.*?)(?=\n|$)', suggested_improvements)
                        retry_match = re.search(r'Retry Logic: (.*?)(?=\n|$)', suggested_improvements)
                        
                        # Update step with suggested values
                        if description_match:
                            description = description_match.group(1).strip()
                        if decision_match:
                            decision = decision_match.group(1).strip()
                        if success_match:
                            success_outcome = success_match.group(1).strip()
                        if failure_match:
                            failure_outcome = failure_match.group(1).strip()
                        if validation_match:
                            validation_rules = validation_match.group(1).strip()
                        if error_match:
                            error_codes = error_match.group(1).strip()
                        if retry_match:
                            retry_logic = retry_match.group(1).strip()
                        
                        # Recreate step with updated values
                        step = ProcessStep(
                            step_id=step_id,
                            description=description,
                            decision=decision,
                            success_outcome=success_outcome,
                            failure_outcome=failure_outcome,
                            note_id=note_id,
                            next_step_success=next_step_success,
                            next_step_failure=next_step_failure,
                            validation_rules=validation_rules if validation_rules else None,
                            error_codes=error_codes if error_codes else None,
                            retry_logic=retry_logic if retry_logic else None
                        )
                    else:
                        print("\nPlease re-enter the step details with improvements:")
                        return self.add_step()  # Recursively call to re-enter the step
                except Exception as e:
                    print(f"Error generating suggestions: {str(e)}")
                    print("\nPlease re-enter the step details with improvements:")
                    return self.add_step()  # Recursively call to re-enter the step
        except Exception as e:
            print(f"Error evaluating step design: {str(e)}")
            print("Continuing without AI evaluation...")
        
        # Add the step and validate the process flow
        self.steps.append(step)
        
        # Validate the entire process flow
        flow_issues = self.validate_process_flow()
        note_issues = self.validate_notes()
        
        if flow_issues or note_issues:
            print("\n=== Process Validation Issues ===")
            for issue in flow_issues + note_issues:
                print(f"- {issue}")
            
            fix = self.get_step_input("\nWould you like to fix these issues? (y/n)").lower()
            if fix == 'y':
                self.steps.pop()  # Remove the last step
                return self.add_step()  # Try again

    def setup_output_directory(self, base_dir: str = "testing/output") -> str:
        """Set up the output directory structure for this run.
        
        Creates a directory structure: testing/output/processname/timestamp/
        
        Returns:
            The full path to the output directory
        """
        # Create a timestamped directory under processname
        output_dir = os.path.join(base_dir, self.process_name, self.timestamp)
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        return output_dir

    def generate_csv(self, base_output_dir: str = "testing/output", delimiter: str = ",") -> None:
        """Generate CSV files for the process.
        
        Args:
            base_output_dir: Base directory for output files
            delimiter: Delimiter to use in CSV files (default: comma)
        """
        output_dir = self.setup_output_directory(base_output_dir)
        
        # Process steps CSV
        process_file = os.path.join(output_dir, f"{self.process_name}_process.csv")
        with open(process_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
            writer.writerow([
                "Step ID", "Description", "Decision", "Success Outcome", 
                "Failure Outcome", "Linked Note ID", "Next Step (Success)", 
                "Next Step (Failure)", "Validation Rules", "Error Codes", "Retry Logic"
            ])
            for step in self.steps:
                writer.writerow([
                    step.step_id, step.description, step.decision,
                    step.success_outcome, step.failure_outcome, step.note_id,
                    step.next_step_success, step.next_step_failure,
                    step.validation_rules, step.error_codes, step.retry_logic
                ])
        
        # Notes CSV
        notes_file = None
        if self.notes:
            notes_file = os.path.join(output_dir, f"{self.process_name}_notes.csv")
            with open(notes_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["Note ID", "Content", "Related Step ID"])
                for note in self.notes:
                    writer.writerow([note.note_id, note.content, note.related_step_id])
        
        print(f"\nCSV files generated in {output_dir}/")
        print(f"- Process steps: {process_file}")
        if notes_file:
            print(f"- Notes: {notes_file}")

    def load_from_csv(self, steps_csv_path: str, notes_csv_path: str = None) -> None:
        """Load process steps and notes from CSV files.
        
        This method supports the current CSV format with headers:
        Step ID,Description,Decision,Success Outcome,Failure Outcome,Linked Note ID,Next Step (Success),Next Step (Failure),Validation Rules,Error Codes,Retry Logic
        
        To load the original format, use load_from_original_format() instead.
        
        Args:
            steps_csv_path: Path to the CSV file containing process steps
            notes_csv_path: Optional path to the CSV file containing notes
        
        Raises:
            ValueError: If the CSV structure doesn't match the expected format
        """
        # Reset current state
        self.steps = []
        self.notes = []
        self.step_count = 0
        self.current_note_id = 1
        
        # Load steps from CSV
        try:
            with open(steps_csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Read header row
                
                # Validate headers
                expected_headers = [
                    "Step ID", "Description", "Decision", "Success Outcome", 
                    "Failure Outcome", "Linked Note ID", "Next Step (Success)", 
                    "Next Step (Failure)", "Validation Rules", "Error Codes", "Retry Logic"
                ]
                
                # Check if all expected headers exist
                if not all(header in headers for header in expected_headers):
                    missing = [h for h in expected_headers if h not in headers]
                    raise ValueError(f"Missing required columns in steps CSV: {', '.join(missing)}")
                
                # Get index for each column
                step_id_idx = headers.index("Step ID")
                description_idx = headers.index("Description")
                decision_idx = headers.index("Decision")
                success_outcome_idx = headers.index("Success Outcome")
                failure_outcome_idx = headers.index("Failure Outcome")
                note_id_idx = headers.index("Linked Note ID")
                next_step_success_idx = headers.index("Next Step (Success)")
                next_step_failure_idx = headers.index("Next Step (Failure)")
                validation_idx = headers.index("Validation Rules")
                error_codes_idx = headers.index("Error Codes")
                retry_logic_idx = headers.index("Retry Logic")
                
                # Parse rows
                step_ids = set()
                for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                    try:
                        # Skip empty rows
                        if not any(row):
                            continue
                            
                        # Get step ID as string
                        step_id = row[step_id_idx].strip()
                        
                        # Validate step ID is not empty
                        # Validate step name is not empty
                        if not step_id:
                            raise ValueError(f"Empty step name in row {row_num}")
                        if step_id in step_ids:
                            raise ValueError(f"Duplicate step name in row {row_num}: '{step_id}'")
                        step_ids.add(step_id)
                        
                        # Validate next step references
                        next_step_success = row[next_step_success_idx]
                        next_step_failure = row[next_step_failure_idx]
                        
                        # Validate next step success reference
                        if next_step_success.lower() != 'end':
                            if next_step_success in step_ids:
                                # Valid existing step reference
                                pass
                            elif next_step_success == step_id:
                                # Self-reference - potential loop
                                print(f"Warning: Step '{step_id}' in row {row_num} references itself as the success step. This may create a loop.")
                            else:
                                # Forward reference - will need to be added later
                                print(f"Note: Success path from step '{step_id}' refers to a future step named '{next_step_success}'. Make sure to add this step later.")
                                # Track the referenced ID for future validation
                                step_ids.add(next_step_success)
                        
                        if next_step_failure.lower() != 'end':
                            if next_step_failure in step_ids:
                                # Valid existing step reference
                                pass
                            elif next_step_failure == step_id:
                                # Self-reference - potential loop
                                print(f"Warning: Step '{step_id}' in row {row_num} references itself as the failure step. This may create a loop.")
                            else:
                                # Forward reference - will need to be added later
                                print(f"Note: Failure path from step '{step_id}' refers to a future step named '{next_step_failure}'. Make sure to add this step later.")
                                # Track the referenced ID for future validation
                                step_ids.add(next_step_failure)
                        step = ProcessStep(
                            step_id=step_id,
                            description=row[description_idx],
                            decision=row[decision_idx],
                            success_outcome=row[success_outcome_idx],
                            failure_outcome=row[failure_outcome_idx],
                            note_id=row[note_id_idx] if row[note_id_idx] else None,
                            next_step_success=next_step_success,
                            next_step_failure=next_step_failure,
                            validation_rules=row[validation_idx] if row[validation_idx] else None,
                            error_codes=row[error_codes_idx] if row[error_codes_idx] else None,
                            retry_logic=row[retry_logic_idx] if row[retry_logic_idx] else None
                        )
                        
                        self.steps.append(step)
                    except (ValueError, IndexError) as e:
                        raise ValueError(f"Error parsing row {row_num} in steps CSV: {row}\nError: {str(e)}")
                
                # Update step count for UI display
                self.step_count = len(self.steps)
                
                # Validate the process flow after loading all steps
                flow_issues = self.validate_process_flow()
                if flow_issues:
                    print("\n=== Process Flow Validation Issues ===")
                    for issue in flow_issues:
                        print(f"- {issue}")
                    print("\nThese issues should be fixed in the CSV file.")
        except FileNotFoundError:
            raise ValueError(f"Steps CSV file not found: {steps_csv_path}")
        
        # Load notes from CSV if provided
        if notes_csv_path:
            try:
                with open(notes_csv_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    headers = next(reader)  # Read header row
                    
                    # Validate headers
                    expected_headers = ["Note ID", "Content", "Related Step ID"]
                    if not all(header in headers for header in expected_headers):
                        missing = [h for h in expected_headers if h not in headers]
                        raise ValueError(f"Missing required columns in notes CSV: {', '.join(missing)}")
                    
                    # Get index for each column
                    note_id_idx = headers.index("Note ID")
                    content_idx = headers.index("Content")
                    related_step_idx = headers.index("Related Step ID")
                    # Parse rows
                    max_note_num = 0
                    note_ids = set()
                    for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                        try:
                            # Skip empty rows
                            if not any(row):
                                continue
                                
                            note_id = row[note_id_idx]
                            
                            # Validate note ID
                            if note_id in note_ids:
                                raise ValueError(f"Duplicate Note ID in row {row_num}: {note_id}")
                            note_ids.add(note_id)
                            
                            # Get and validate related step ID
                            related_step_id = row[related_step_idx]
                            
                            # Validate related step ID is not empty and exists
                            if not related_step_id.strip():
                                raise ValueError(f"Empty Related Step ID in row {row_num}")
                            if related_step_id not in step_ids:
                                raise ValueError(f"Related step '{related_step_id}' in row {row_num} does not exist")
                            
                            # Extract note number for tracking max note ID
                            if note_id.startswith("Note"):
                                try:
                                    note_num = int(note_id[4:])
                                    max_note_num = max(max_note_num, note_num)
                                except ValueError:
                                    pass
                            
                            # Create ProcessNote object
                            note = ProcessNote(
                                note_id=note_id,
                                content=row[content_idx],
                                related_step_id=related_step_id
                            )
                            
                            self.notes.append(note)
                            
                            # Link note to the corresponding step
                            for step in self.steps:
                                if step.step_id == related_step_id and step.note_id is None:
                                    step.note_id = note_id
                                    break
                        except (ValueError, IndexError) as e:
                            raise ValueError(f"Error parsing row {row_num} in notes CSV: {row}\nError: {str(e)}")
                    
                    # Update current note ID
                    self.current_note_id = max_note_num + 1
                    
                    # Validate notes after loading all notes
                    note_issues = self.validate_notes()
                    if note_issues:
                        print("\n=== Notes Validation Issues ===")
                        for issue in note_issues:
                            print(f"- {issue}")
                        print("\nThese issues should be fixed in the CSV file.")
            except FileNotFoundError:
                raise ValueError(f"Notes CSV file not found: {notes_csv_path}")
        
        print(f"\nSuccessfully loaded {len(self.steps)} steps and {len(self.notes)} notes from CSV.")

    def load_from_original_format(self, steps_csv_path: str, notes_csv_path: str = None) -> None:
        """Load process steps and notes from the original CSV format.
        
        Original format has headers:
        Step,What happens,What happens next,If conditions are met,If conditions are not met
        
        Args:
            steps_csv_path: Path to the CSV file containing original process steps
            notes_csv_path: Optional path to the CSV file containing notes
        
        Raises:
            ValueError: If the CSV structure doesn't match the expected original format
        """
        # Reset current state
        # Reset current state
        self.steps = []
        self.notes = []
        self.step_count = 0
        self.current_note_id = 1
        # Load steps from original CSV format
        try:
            with open(steps_csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Read header row
                
                # Validate headers for original format
                expected_headers = [
                    "Step", "What happens", "What happens next", 
                    "If conditions are met", "If conditions are not met"
                ]
                
                # Check if all expected headers exist
                if not all(header in headers for header in expected_headers):
                    missing = [h for h in expected_headers if h not in headers]
                    raise ValueError(f"Missing required columns in original format CSV: {', '.join(missing)}")
                
                # Get index for each column
                step_idx = headers.index("Step")
                description_idx = headers.index("What happens")
                decision_idx = headers.index("What happens next")
                success_outcome_idx = headers.index("If conditions are met")
                failure_outcome_idx = headers.index("If conditions are not met")
                
                # Parse rows
                for row in reader:
                    try:
                        # Skip empty rows
                        if not any(row):
                            continue
                            
                        # Extract data from original format
                        description = row[description_idx]
                        decision = row[decision_idx]
                        success_outcome = row[success_outcome_idx]
                        failure_outcome = row[failure_outcome_idx]
                        
                        # Determine next steps based on the content of success/failure outcomes
                        next_step_success = "End"
                        next_step_failure = "End"
                        
                        # Look for patterns like "go to step X" or similar
                        import re
                        
                        # For success path - prioritize descriptive names 
                        # Look for references to step names/descriptions
                        success_step_match = re.search(r'go\s+to\s+(?:the\s+)?"?([^"]+)"?\s+step', success_outcome, re.IGNORECASE)
                        if success_step_match:
                            next_step_success = success_step_match.group(1).strip()
                        # Fallback to legacy numeric pattern, but convert to string
                        elif re.search(r'go\s+to\s+(?:the\s+)?"?([Ss]tep\s+)?(\d+)"?', success_outcome):
                            legacy_match = re.search(r'go\s+to\s+(?:the\s+)?"?([Ss]tep\s+)?(\d+)"?', success_outcome)
                            # Store as string to maintain consistency with string-based step names
                            next_step_success = legacy_match.group(2)
                            
                        # For failure path - same approach
                        failure_step_match = re.search(r'go\s+to\s+(?:the\s+)?"?([^"]+)"?\s+step', failure_outcome, re.IGNORECASE)
                        if failure_step_match:
                            next_step_failure = failure_step_match.group(1).strip()
                        # Fallback to legacy numeric pattern, but convert to string
                        elif re.search(r'go\s+to\s+(?:the\s+)?"?([Ss]tep\s+)?(\d+)"?', failure_outcome):
                            legacy_match = re.search(r'go\s+to\s+(?:the\s+)?"?([Ss]tep\s+)?(\d+)"?', failure_outcome)
                            next_step_failure = legacy_match.group(2)
                            
                        # Use step information from CSV as step_id
                        step_id = row[step_idx].strip()
                        
                        step = ProcessStep(
                            step_id=step_id,
                            description=description,
                            decision=decision,
                            success_outcome=success_outcome,
                            failure_outcome=failure_outcome,
                            note_id=None,  # Will link notes later if they exist
                            next_step_success=next_step_success,
                            next_step_failure=next_step_failure,
                            validation_rules=None,
                            error_codes=None,
                            retry_logic=None
                        )
                        
                        self.steps.append(step)
                    except (ValueError, IndexError) as e:
                        raise ValueError(f"Error parsing row in original format CSV: {row}\nError: {str(e)}")
                
                # Update step count for UI display after loading all steps
                self.step_count = len(self.steps)
                
                # Validate the process flow after loading
                flow_issues = self.validate_process_flow()
                if flow_issues:
                    print("\n=== Process Flow Validation Issues ===")
                    for issue in flow_issues:
                        print(f"- {issue}")
                    print("\nThese issues should be fixed in the CSV file.")
        except FileNotFoundError:
            raise ValueError(f"Original steps CSV file not found: {steps_csv_path}")
        
        # Load notes from CSV if provided
        if notes_csv_path:
            try:
                with open(notes_csv_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    headers = next(reader)  # Read header row
                    
                    # Validate headers
                    expected_headers = ["Note ID", "Content", "Related Step ID"]
                    if not all(header in headers for header in expected_headers):
                        missing = [h for h in expected_headers if h not in headers]
                        raise ValueError(f"Missing required columns in notes CSV: {', '.join(missing)}")
                    
                    # Get index for each column
                    note_id_idx = headers.index("Note ID")
                    content_idx = headers.index("Content")
                    related_step_idx = headers.index("Related Step ID")
                    
                    # Parse rows
                    max_note_num = 0
                    for row in reader:
                        try:
                            # Skip empty rows
                            if not any(row):
                                continue
                                
                            note_id = row[note_id_idx]
                            related_step_id = row[related_step_idx]
                            
                            # Extract note number for tracking max note ID
                            if note_id.startswith("Note"):
                                try:
                                    note_num = int(note_id[4:])
                                    max_note_num = max(max_note_num, note_num)
                                except ValueError:
                                    pass
                            
                            # Create ProcessNote object
                            note = ProcessNote(
                                note_id=note_id,
                                content=row[content_idx],
                                related_step_id=related_step_id
                            )
                            
                            self.notes.append(note)
                            
                            # Link note to the corresponding step - handle both string and numeric references
                            for step in self.steps:
                                # Check for direct match on step_id
                                if step.step_id == related_step_id and step.note_id is None:
                                    step.note_id = note_id
                                    break
                                # Legacy fallback for numeric references
                                elif related_step_id.isdigit() and step.step_id.isdigit() and int(step.step_id) == int(related_step_id) and step.note_id is None:
                                    step.note_id = note_id
                                    break
                        except (ValueError, IndexError) as e:
                            raise ValueError(f"Error parsing row in notes CSV: {row}\nError: {str(e)}")
                    
                    # Update current note ID
                    self.current_note_id = max_note_num + 1
            except FileNotFoundError:
                raise ValueError(f"Notes CSV file not found: {notes_csv_path}")
        
        print(f"\nSuccessfully loaded {len(self.steps)} steps and {len(self.notes)} notes from original format CSV.")

    def sanitize_id(self, id_str: str) -> str:
        """Sanitize a string to make it a valid Mermaid ID.
        
        Creates readable node IDs from descriptive step names while ensuring
        Mermaid diagram compatibility.
        """
        import re
        
        # Keep meaningful characters while ensuring safe node IDs
        safe_id = re.sub(r'[^a-zA-Z0-9_\s-]', '', id_str)
        safe_id = re.sub(r'[\s-]+', '_', safe_id)
        
        # Handle common keywords in step names
        if any(word in safe_id.lower() for word in ['success', 'failure', 'error', 'end']):
            safe_id = f"step_{safe_id}"
        
        # Ensure ID starts with a letter (Mermaid requirement)
        if not safe_id or not safe_id[0].isalpha():
            safe_id = 'node_' + safe_id
            
        return safe_id
    
    def generate_mermaid_diagram(self, base_output_dir: str = "testing/output") -> str:
        """Generate a Mermaid diagram from the process steps."""
        if not self.output_dir:
            output_dir = self.setup_output_directory(base_output_dir)
        else:
            output_dir = self.output_dir
            
        mermaid_file = os.path.join(output_dir, f"{self.process_name}_diagram.mmd")
        
        # Start the diagram
        diagram = "```mermaid\ngraph TD\n"
        
        # Create a mapping from step_id to sanitized Mermaid node ID
        step_id_to_node_id = {}
        for step in self.steps:
            step_id_to_node_id[step.step_id] = f"Step_{self.sanitize_id(step.step_id)}"
        
        # Add nodes and edges
        for step in self.steps:
            # Get the sanitized node ID for this step
            safe_id = step_id_to_node_id[step.step_id]
            
            # Add the main step node
            diagram += f"    {safe_id}[\"{step.description}\"]\n"
            
            # Add decision node if there's a decision
            if step.decision:
                decision_id = f"Decision_{self.sanitize_id(step.step_id)}"
                diagram += f"    {decision_id}{{\"{step.decision}\"}}\n"
                diagram += f"    {safe_id} --> {decision_id}\n"
                
                # Add success path
                if step.next_step_success.lower() != 'end':
                    # Check if this next step already exists in our mapping
                    if step.next_step_success in step_id_to_node_id:
                        next_success = step_id_to_node_id[step.next_step_success]
                        diagram += f"    {decision_id} -->|Yes| {next_success}\n"
                    else:
                        # Reference to a step name that doesn't exist yet - create a placeholder
                        future_id = f"Future_{self.sanitize_id(step.next_step_success)}"
                        # Store this ID in our mapping for future references
                        step_id_to_node_id[step.next_step_success] = future_id
                        diagram += f"    {future_id}[\"{step.next_step_success}\"]\n"
                        diagram += f"    {decision_id} -->|Yes| {future_id}\n"
                else:
                    end_id = "ProcessEnd"
                    diagram += f"    {end_id}[\"Process End\"]\n"
                    diagram += f"    {decision_id} -->|Yes| {end_id}\n"
                
                # Add failure path
                if step.next_step_failure.lower() != 'end':
                    # Check if this next step already exists in our mapping
                    if step.next_step_failure in step_id_to_node_id:
                        next_failure = step_id_to_node_id[step.next_step_failure]
                        diagram += f"    {decision_id} -->|No| {next_failure}\n"
                    else:
                        # Reference to a step name that doesn't exist yet - create a placeholder
                        failure_id = f"Future_{self.sanitize_id(step.next_step_failure)}"
                        # Store this ID in our mapping for future references
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
                note_id = f"Note_{self.sanitize_id(step.step_id)}"
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
        # Directory is already created in setup_output_directory
        with open(mermaid_file, 'w') as f:
            f.write(diagram)
        
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
            if step.retry_logic:
                prompt += f"- Retry Logic: {step.retry_logic}\n"
        
        prompt += """
Please help me:
1. Review this process for completeness
2. Identify any missing steps or edge cases
3. Suggest improvements to the workflow
4. Create a clear, visual representation of the process
"""
        
        return prompt

    def run_interview(self) -> None:
        """Run the interactive interview process."""
        print(f"\n=== Process Builder: {self.process_name} ===\n")
        
        while True:
            self.add_step()
            continue_process = self.get_step_input("Add another step? (y/n)").lower()
            if continue_process != 'y':
                break
        
        # Generate outputs
        self.generate_csv()
        self.generate_mermaid_diagram()
        llm_prompt = self.generate_llm_prompt()
        print("\n=== LLM Prompt ===")
        print(llm_prompt)
        
        # Write LLM prompt to file
        if self.output_dir:
            prompt_file = os.path.join(self.output_dir, f"{self.process_name}_prompt.txt")
            with open(prompt_file, 'w') as f:
                f.write(llm_prompt)
            print(f"LLM prompt saved to: {prompt_file}")


def main():
    """Main entry point for the process builder."""
    parser = argparse.ArgumentParser(description="Process Builder Utility")
    parser.add_argument("--steps-csv", help="Path to CSV file containing process steps")
    parser.add_argument("--notes-csv", help="Path to CSV file containing process notes")
    parser.add_argument("--import-original", action="store_true", 
                        help="Import from original format CSV instead of current format")
    args = parser.parse_args()
    
    # Get process name
    process_name = input("Enter the name of the process: ").strip()
    builder = ProcessBuilder(process_name)
    
    # Determine if we're loading from CSV or running an interview
    if args.steps_csv:
        try:
            if args.import_original:
                builder.load_from_original_format(args.steps_csv, args.notes_csv)
            else:
                builder.load_from_csv(args.steps_csv, args.notes_csv)
            
            # Generate outputs
            builder.generate_csv()
            builder.generate_mermaid_diagram()
            llm_prompt = builder.generate_llm_prompt()
            print("\n=== LLM Prompt ===")
            print(llm_prompt)
            
            # Write LLM prompt to file
            if builder.output_dir:
                prompt_file = os.path.join(builder.output_dir, f"{builder.process_name}_prompt.txt")
                with open(prompt_file, 'w') as f:
                    f.write(llm_prompt)
                print(f"LLM prompt saved to: {prompt_file}")
        except Exception as e:
            print(f"Error loading from CSV: {str(e)}")
            sys.exit(1)
    else:
        # Run the interactive interview
        builder.run_interview()


if __name__ == "__main__":
    main()
