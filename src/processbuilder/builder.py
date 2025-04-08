"""
Main ProcessBuilder class for building and managing processes.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Dict, Any, Union
import openai
from datetime import datetime
import json

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

# Import local modules
from .config import Config
from .models import (
    ProcessStep,
    ProcessNote,
    ProcessInterviewer,
    ProcessStepGenerator,
    ProcessValidator,
    ProcessOutputGenerator
)
from .models.step_generator import ProcessStepGenerator
from .models.validator import ProcessValidator
from .models.output_generator import ProcessOutputGenerator

# Import utility functions from the reorganized modules
from .utils import (
    # AI generation
    sanitize_string,
    show_loading_animation,
    generate_step_description,
    generate_step_decision,
    generate_step_success_outcome,
    generate_step_failure_outcome,
    generate_step_note,
    generate_validation_rules,
    generate_error_codes,
    generate_executive_summary,
    parse_ai_suggestions,
    evaluate_step_design,
    generate_step_title,
    
    # Process validation
    validate_next_step_id,
    validate_next_step,
    find_missing_steps,
    validate_process_flow,
    validate_notes,
    
    # Output generation
    sanitize_id,
    write_csv,
    setup_output_directory,
    generate_csv,
    generate_mermaid_diagram,
    generate_llm_prompt,
    save_outputs,
    
    # State management
    save_state,
    load_state,
    
    # Input handling
    get_step_input
)

def default_input_handler(prompt: str) -> str:
    """Default input handler that uses the built-in input function.
    This serves as a fallback when get_step_input from cli isn't available."""
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if response:
            return response

# Set log level based on verbose mode
def set_log_level(verbose=False):
    """Set the log level based on verbose mode."""
    logger = logging.getLogger(__name__)
    
    # Set the appropriate log level based on verbose mode
    # Make sure WARNING level is always visible regardless of verbose mode
    logger_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(logger_level)
    
    # Ensure we have at least one handler
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Update log level for all handlers
    # Always set handlers to DEBUG level to ensure warnings are captured
    # regardless of the logger's level
    for handler in logger.handlers:
        handler.setLevel(logging.DEBUG)
    
    # Log a message to confirm level change
    logger.debug(f"Debug logging {'enabled' if verbose else 'disabled'}")
    
    # Log a message to verify warnings are working
    logger.debug("Log levels properly configured")

class ProcessBuilder:
    """Main class for building and managing process workflows."""
    
    # Class-level input handler (allows custom input methods to be injected)
    _input_handler = default_input_handler
    
    # Initialize class variable for verbose mode
    _verbose: bool = False
    
    def __init__(
        self,
        process_name: str,
        config: Optional[Config] = None,
        verbose: bool = False
    ):
        """Initialize the ProcessBuilder.
        
        Args:
            process_name: Name of the process
            config: Optional configuration
            verbose: Whether to enable verbose logging
        """
        self.process_name = process_name
        self.config = config or Config()
        self.verbose = verbose
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(api_key=self.config.openai_api_key)
        
        # Initialize components
        self.interviewer = ProcessInterviewer()(input_handler=self.config.input_handler)
        self.step_generator = ProcessStepGenerator(self.openai_client)
        self.validator = ProcessValidator()
        self.output_generator = ProcessOutputGenerator(self.openai_client)
        
        # Initialize state
        self.steps: List[ProcessStep] = []
        self.notes: List[ProcessNote] = []
        self.start_step_id: Optional[str] = None
        
        # Try to load existing state
        try:
            self.load_state()
            log.debug(f"Loaded existing state for process: {self.process_name}")
        except Exception as e:
            log.debug(f"No existing state found or error loading state: {str(e)}")
        
        # If verbose mode is specified at instance level and different from class level, update the class setting
        if verbose is not None and verbose != self.__class__._verbose:
            self.__class__.set_verbose_mode(verbose)
            log.debug(f"Updated class verbose mode to {verbose}")
        
        # Log the initialization with verbose mode setting
        log.debug(f"ProcessBuilder initialized with verbose={self.verbose}")
        
        # Initialize OpenAI client if API key is available
        try:
            if os.environ.get("OPENAI_API_KEY"):
                self.openai_client = openai.OpenAI()
                log.debug("OpenAI client initialized successfully")
            else:
                self.openai_client = None
                # Always use warning level for missing API key, regardless of verbose mode
                log.warning("No OpenAI API key found. AI features will be disabled.")
                log.debug("Warning about missing API key has been logged")
        except Exception as e:
            self.openai_client = None
            # Always use warning level for errors, regardless of verbose mode
            log.warning(f"Failed to initialize OpenAI client: {str(e)}")

    def __str__(self) -> str:
        """Return a string representation of the ProcessBuilder."""
        return f"ProcessBuilder(name='{self.process_name}', steps={len(self.steps)}, notes={len(self.notes)})"

    def __repr__(self) -> str:
        """Return a detailed string representation of the ProcessBuilder."""
        return f"ProcessBuilder(name='{self.process_name}', steps={len(self.steps)}, notes={len(self.notes)}, start_step='{self.start_step_id}')"

    @property
    def suggested_first_step(self) -> str:
        """Generate a suggested name for the first step when there are 0 steps in the process.
        
        Returns:
            A verb-based, actionable step name or empty string if OpenAI is not available
        """
        if not self.openai_client or len(self.steps) > 0:
            return ""
            
        try:
            # Sanitize process name to prevent syntax errors from unescaped single quotes
            safe_process_name = sanitize_string(self.process_name)
            
            prompt = (
                f"I'm creating a business process called '{safe_process_name}'.\n\n"
                f"Please suggest a name for the first step in this process. The step name should:\n"
                f"1. Start with a strong action verb (e.g., Collect, Review, Analyze)\n"
                f"2. Be clear and descriptive (2-5 words)\n"
                f"3. Be specific to the '{safe_process_name}' process\n"
                f"4. Follow business process naming conventions\n"
                f"5. Be actionable and task-oriented\n\n"
                f"Provide only the step name, nothing else."
            )
            
            if self.verbose:
                log.debug(f"Sending OpenAI prompt for first step suggestion: \n{prompt}")
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Create clear, descriptive step names that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            suggestion = response.choices[0].message.content.strip()
            if self.verbose:
                log.debug(f"Received OpenAI first step suggestion: '{suggestion}'")
            words = suggestion.split()
            if len(words) > 5:
                suggestion = ' '.join(words[:5])
                log.debug(f"Truncated suggestion to: '{suggestion}'")
                
            return suggestion
        except Exception as e:
            log.warning(f"Error generating first step suggestion: {str(e)}")
            return ""
    
    @classmethod
    def set_input_handler(cls, handler: Callable[[str], str]) -> None:
        """Set the input handler for receiving user input.
        
        Args:
            handler: A callable that takes a prompt string and returns user input
                     Must accept a string parameter and return a string
            
        Returns:
            None
            
        Raises:
            TypeError: If the handler is not callable
        """
        # Validate that the handler is callable
        if not callable(handler):
            raise TypeError("Input handler must be callable")
            
        # Update class variable
        cls._input_handler = handler
        log.debug("Input handler updated")
        
    @classmethod
    def set_verbose_mode(cls, verbose: bool) -> None:
        """Set the verbose mode for detailed OpenAI response logging.
        
        Args:
            verbose: If True, OpenAI response details will be logged at DEBUG level
            
        Returns:
            None
        """
        # Store original verbose setting for comparison
        old_verbose = cls._verbose
        
        # Update class variable
        cls._verbose = verbose
        
        # Log the change (use debug if it's a repeat call with same value)
        if old_verbose == verbose:
            log.debug(f"Verbose mode remained {'enabled' if verbose else 'disabled'}")
        else:
            log.info(f"Verbose mode {'enabled' if verbose else 'disabled'}")
        
        # Always update log level to ensure consistency
        set_log_level(verbose)

    @property
    def name(self) -> str:
        """Return the name of the process."""
        return self.process_name
        
    def get_input(self, prompt: str) -> str:
        """Get input from the user with the configured input handler."""
        return self.__class__._input_handler(prompt)

    def generate_error_codes(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str) -> str:
        """Generate suggested error codes for a step using OpenAI."""
        return generate_error_codes(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            decision,
            success_outcome,
            failure_outcome,
            self.verbose
        )
    
    def validate_next_step_id(self, next_step_id: str) -> bool:
        """Validate that a next step ID is either 'End' or an existing step.
        
        Args:
            next_step_id: The next step ID to validate
            
        Returns:
            True if the next step is valid (either 'End' or an existing step ID),
            False otherwise
        """
        return validate_next_step_id(self.steps, next_step_id)
            
    def validate_next_step(self, step_or_id: Union[ProcessStep, str]) -> Union[List[str], bool]:
        """Validate that a next step ID or ProcessStep is valid.
        
        Args:
            step_or_id: Either a ProcessStep object or a string step ID
            
        Returns:
            If step_or_id is a ProcessStep: List of validation issue messages, empty if all is valid
            If step_or_id is a string: True if the step ID is valid, False otherwise
        """
        if isinstance(step_or_id, str):
            return validate_next_step_id(self.steps, step_or_id)
        else:
            return validate_next_step(step_or_id, self.steps)
        
    def create_step_id(self, title: str) -> str:
        """Create a valid, unique step ID from a title.
        
        Args:
            title: The title to convert to a step ID
            
        Returns:
            A valid, unique step ID
        """
        # Convert spaces to underscores and keep only alphanumeric characters and underscores
        step_id = ''.join(c if c.isalnum() else '_' for c in title)
        
        # Remove consecutive underscores
        while '__' in step_id:
            step_id = step_id.replace('__', '_')
            
        # Remove leading/trailing underscores
        step_id = step_id.strip('_')
        
        # Check for duplicates and add a number if needed
        if any(step.step_id == step_id for step in self.steps):
            # Find the highest number suffix for this title
            base_id = step_id
            highest_suffix = 0
            
            for step in self.steps:
                if step.step_id == base_id:
                    highest_suffix = 1
                elif step.step_id.startswith(f"{base_id}_"):
                    try:
                        suffix = int(step.step_id[len(base_id) + 1:])
                        highest_suffix = max(highest_suffix, suffix)
                    except ValueError:
                        pass
            
            # Add suffix to make unique
            step_id = f"{base_id}_{highest_suffix + 1}"
        
        return step_id
        
    def find_missing_steps(self) -> List[Tuple[str, str, str]]:
        """Find steps that are referenced but not yet defined.
        
        Returns:
            A list of tuples (missing_step_id, referencing_step_id, path_type),
            where path_type is either 'success' or 'failure'.
        """
        return find_missing_steps(self.steps)
        
    def parse_ai_suggestions(self, suggestions: str) -> dict:
        """Parse AI suggestions into a structured format.
        
        Args:
            suggestions: The raw AI suggestions text
            
        Returns:
            Dictionary containing suggested updates for each field
        """
        return parse_ai_suggestions(self.openai_client, suggestions)
        
    def generate_step_description(self, step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate an intelligent step description based on context.
        
        Args:
            step_id: The current step ID
            predecessor_id: Optional ID of the step that references this step
            path_type: Optional path type ('success' or 'failure') that led here
        """
        return generate_step_description(
            self.openai_client, 
            self.process_name, 
            step_id, 
            predecessor_id,
            path_type,
            self.steps,
            self.verbose
        )

    def generate_step_decision(self, step_id: str, description: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested decision for a step using OpenAI."""
        return generate_step_decision(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            predecessor_id,
            path_type,
            self.steps,
            self.verbose
        )

    def generate_step_success_outcome(self, step_id: str, description: str, decision: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested success outcome for a step using OpenAI."""
        return generate_step_success_outcome(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            decision,
            predecessor_id,
            path_type,
            self.steps,
            self.verbose
        )

    def generate_step_failure_outcome(self, step_id: str, description: str, decision: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> str:
        """Generate a suggested failure outcome for a step using OpenAI."""
        return generate_step_failure_outcome(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            decision,
            predecessor_id,
            path_type,
            self.steps,
            self.verbose
        )

    def generate_step_note(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str) -> str:
        """Generate a suggested note for a step using OpenAI."""
        return generate_step_note(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            decision,
            success_outcome,
            failure_outcome,
            self.verbose
        )

    def generate_validation_rules(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str) -> str:
        """Generate suggested validation rules for a step using OpenAI."""
        return generate_validation_rules(
            self.openai_client,
            self.process_name,
            step_id,
            description,
            decision,
            success_outcome,
            failure_outcome,
            self.verbose
        )

    def generate_step_title(self, step_id: str, predecessor_id: str, path_type: str) -> str:
        """Generate an intelligent step title based on context.
        
        Args:
            step_id: The current step ID
            predecessor_id: The ID of the step that references this step
            path_type: Either 'success' or 'failure' indicating which path led here
        """
        return generate_step_title(
            self.openai_client,
            self.process_name,
            step_id,
            predecessor_id,
            path_type,
            self.steps,
            self.verbose
        )

    def create_missing_step_noninteractive(self, step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> ProcessStep:
        """Create a missing step with default values without requiring user input.
        
        Args:
            step_id: ID of the step to create
            predecessor_id: Optional ID of the step that references this one
            path_type: Optional path type ('success' or 'failure')
            
        Returns:
            A new ProcessStep with default values
        """
        print(f"\nFound missing step: {step_id}")
        if predecessor_id:
            print(f"Referenced by step: {predecessor_id} on {path_type} path")
        
        # Create default values
        description = f"Automatically generated step for: {step_id}"
        decision = f"Does the {step_id} step complete successfully?"
        success_outcome = "The step completed successfully."
        failure_outcome = "The step failed to complete."
        

        # Create and return the step with default values
        step = ProcessStep(
            step_id=step_id,
            description=description,
            decision=decision,
            success_outcome=success_outcome,
            failure_outcome=failure_outcome,
            next_step_success="end",
            next_step_failure="end",
            validation_rules=None,
            error_codes=None
        )
        return step

    def create_missing_step(self, step_id: str, predecessor_id: Optional[str] = None, path_type: Optional[str] = None) -> ProcessStep:
        """Create a missing step that was referenced by another step."""
        print(f"\nCreating missing step: {step_id}")
        
        # Initial AI confirmation
        use_ai = False
        if self.openai_client:
            use_ai = self.get_input("\nWould you like to use AI suggestions for this step? (y/n)").lower() == 'y'
            if use_ai:
                print("\nI'll ask for your input first, then offer AI suggestions if you'd like.")
        
        # Get step description
        print("\nThe step name is used as a label in the process diagram.")
        description = self.get_input("What happens in this step?")
        
        if use_ai and self.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the description? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating step description")
                    suggested_description = self.generate_step_description(step_id, predecessor_id, path_type)
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
        decision = self.get_decision(step_id, description, predecessor_id, path_type)
        
        if use_ai and self.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the decision? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating decision suggestion")
                    suggested_decision = self.generate_step_decision(step_id, description, predecessor_id, path_type)
                    if suggested_decision:
                        safe_decision = sanitize_string(suggested_decision)
                        print(f"\nAI suggests the following decision: '{safe_decision}'")
                        use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                        if use_suggested == 'y':
                            decision = suggested_decision
                except Exception as e:
                    print(f"Error generating decision suggestion: {str(e)}")
        
        # Get success outcome
        print("\nThe success outcome tells you which step to go to next when the decision is 'yes'.")
        success_outcome = self.get_input("What happens if this step succeeds?")
        
        if use_ai and self.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the success outcome? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating success outcome suggestion")
                    suggested_success = self.generate_step_success_outcome(step_id, description, decision, predecessor_id, path_type)
                    if suggested_success:
                        safe_success = sanitize_string(suggested_success)
                        print(f"\nAI suggests the following success outcome: '{safe_success}'")
                        use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                        if use_suggested == 'y':
                            success_outcome = suggested_success
                except Exception as e:
                    print(f"Error generating success outcome suggestion: {str(e)}")
        
        # Get failure outcome
        print("\nThe failure outcome tells you which step to go to next when the decision is 'no'.")
        failure_outcome = self.get_input("What happens if this step fails?")
        
        if use_ai and self.openai_client:
            want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the failure outcome? (y/n)").lower() == 'y'
            if want_ai_help:
                try:
                    show_loading_animation("Generating failure outcome suggestion")
                    suggested_failure = self.generate_step_failure_outcome(step_id, description, decision, predecessor_id, path_type)
                    if suggested_failure:
                        safe_failure = sanitize_string(suggested_failure)
                        print(f"\nAI suggests the following failure outcome: '{safe_failure}'")
                        use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                        if use_suggested == 'y':
                            failure_outcome = suggested_failure
                except Exception as e:
                    print(f"Error generating failure outcome suggestion: {str(e)}")
        
        # Optional note
        print("\nA note is a brief comment that appears next to the step in the diagram.")
        add_note = self.get_input("Would you like to add a note for this step? (y/n)").lower()
        note_id = None
        if add_note == 'y':
            note_content = self.get_input("What's the note content?")
            
            if use_ai and self.openai_client:
                want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the note? (y/n)").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating note suggestion")
                        suggested_note = self.generate_step_note(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_note:
                            safe_note = sanitize_string(suggested_note)
                            print(f"\nAI suggests the following note: '{safe_note}'")
                            use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                            if use_suggested == 'y':
                                note_content = suggested_note
                    except Exception as e:
                        print(f"Error generating note suggestion: {str(e)}")
            
            note_id = f"Note{self.current_note_id}"
            self.notes.append(ProcessNote(note_id, note_content, step_id))
            self.current_note_id += 1
        
        # Enhanced fields
        print("\nValidation rules help ensure the step receives good input data.")
        add_validation = self.get_input("Would you like to add validation rules? (y/n)").lower()
        validation_rules = None
        if add_validation == 'y':
            validation_rules = self.get_input("Enter validation rules:") or None
            
            if use_ai and self.openai_client:
                want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the validation rules? (y/n)").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating validation rules suggestion")
                        suggested_validation = self.generate_validation_rules(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_validation:
                            print(f"\nAI suggests the following validation rules:\n{suggested_validation}")
                            safe_validation = sanitize_string(suggested_validation)
                            print(f"\nAI suggests the following validation rules:\n{safe_validation}")
                            use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
                            if use_suggested == 'y':
                                validation_rules = suggested_validation
                    except Exception as e:
                        print(f"Error generating validation rules suggestion: {str(e)}")
        
        print("\nError codes help identify and track specific problems that might occur.")
        add_error_codes = self.get_input("Would you like to add error codes? (y/n)").lower()
        error_codes = None
        if add_error_codes == 'y':
            error_codes = self.get_input("Enter error codes:") or None
            
            if use_ai and self.openai_client:
                want_ai_help = self.get_input("\nWould you like to see an AI suggestion for the error codes? (y/n)").lower() == 'y'
                if want_ai_help:
                    try:
                        show_loading_animation("Generating error codes suggestion")
                        suggested_error_codes = self.generate_error_codes(step_id, description, decision, success_outcome, failure_outcome)
                        if suggested_error_codes:
                            safe_error_codes = sanitize_string(suggested_error_codes)
                            print(f"\nAI suggests the following error codes:\n{safe_error_codes}")
                            use_suggested = self.get_input("Use this suggestion? (y/n)").lower()
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
            next_step_success="end",
            next_step_failure="end",
            validation_rules=validation_rules,
            error_codes=error_codes
        )
        
        return step

    def add_step(self, step: Optional[ProcessStep] = None, interactive: bool = False, **kwargs) -> bool:
        """Add a step to the process.
        
        Args:
            step: The ProcessStep to add (optional)
            interactive: Whether this is being called during interactive step creation
            **kwargs: Step attributes if creating a new step
            
        Returns:
            Whether the step was added successfully
        """
        try:
            # If step is not provided, create one from kwargs
            if step is None:
                step = ProcessStep(**kwargs)
                
            # Validate the step
            is_valid, errors = self.validator.validate_step(step, allow_future_steps=interactive)
            if not is_valid:
                log.error(f"Invalid step: {', '.join(errors)}")
                return False
                
            # Add the step
            self.steps.append(step)
            
            # Set as start step if this is the first step
            if len(self.steps) == 1:
                self.start_step_id = step.step_id
                
            return True
            
        except Exception as e:
            log.error(f"Error adding step: {str(e)}")
            return False
            
    def add_note(self, note: ProcessNote) -> bool:
        """Add a note to the process.
        
        Args:
            note: The ProcessNote to add
            
        Returns:
            Whether the note was added successfully
        """
        try:
            # Validate the note
            is_valid, errors = self.validator.validate_note(note)
            if not is_valid:
                log.error(f"Invalid note: {', '.join(errors)}")
                return False
                
            # Add the note
            self.notes.append(note)
            return True
            
        except Exception as e:
            log.error(f"Error adding note: {str(e)}")
            return False
            
    def save_state(self, file_path: Optional[str] = None) -> bool:
        """Save the current state to a file.
        
        Args:
            file_path: Optional path to save the state file
            
        Returns:
            Whether the state was saved successfully
        """
        try:
            # Use default path if none provided
            if not file_path:
                file_path = os.path.join(
                    self.output_dir,
                    f"{self.process_name}_state.json"
                )
                
            # Convert steps and notes to dictionaries
            state = {
                "process_name": self.process_name,
                "timestamp": self.timestamp,
                "start_step_id": self.start_step_id,
                "steps": [step.to_dict() for step in self.steps],
                "notes": [note.to_dict() for note in self.notes]
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
                
            return True
            
        except Exception as e:
            log.error(f"Error saving state: {str(e)}")
            return False
            
    def load_state(self, file_path: str) -> bool:
        """Load state from a file.
        
        Args:
            file_path: Path to the state file
            
        Returns:
            Whether the state was loaded successfully
        """
        try:
            # Read from file
            with open(file_path, 'r') as f:
                state = json.load(f)
                
            # Update process name and timestamp
            self.process_name = state["process_name"]
            self.timestamp = state["timestamp"]
            self.start_step_id = state["start_step_id"]
            
            # Clear existing steps and notes
            self.steps = []
            self.notes = []
            
            # Add steps
            for step_dict in state["steps"]:
                step = ProcessStep.from_dict(step_dict)
                self.steps.append(step)
                
            # Add notes
            for note_dict in state["notes"]:
                note = ProcessNote.from_dict(note_dict)
                self.notes.append(note)
                
            return True
            
        except Exception as e:
            log.error(f"Error loading state: {str(e)}")
            return False
            
    def run_interview(self) -> bool:
        """Run the interactive interview process.
        
        Returns:
            Whether the interview completed successfully
        """
        return self.interviewer.run_interview(
            process_name=self.process_name,
            steps=self.steps,
            notes=self.notes,
            start_step_id=self.start_step_id,
            step_generator=self.step_generator,
            validator=self.validator
        )
        
    def generate_outputs(self) -> Dict[str, str]:
        """Generate all output files.
        
        Returns:
            Dictionary mapping output type to file path
        """
        outputs = {}
        
        try:
            # Generate timestamp for this output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Setup output directory with timestamp
            output_dir = setup_output_directory(
                process_name=self.process_name,
                timestamp=timestamp,
                base_dir=self.config.base_output_dir,
                default_output_dir=self.config.default_output_dir
            )
            
            # Generate CSV
            csv_file = self.output_generator.generate_csv(
                steps=self.steps,
                notes=self.notes,
                process_name=self.process_name,
                timestamp=timestamp,
                base_output_dir=self.config.base_output_dir,
                default_output_dir=self.config.default_output_dir
            )
            if csv_file:
                outputs["csv"] = csv_file
                
            # Generate Mermaid diagram
            mermaid_diagram = self.output_generator.generate_mermaid_diagram(
                steps=self.steps,
                notes=self.notes,
                process_name=self.process_name,
                timestamp=timestamp,
                output_dir=output_dir,
                base_output_dir=self.config.base_output_dir,
                default_output_dir=self.config.default_output_dir
            )
            if mermaid_diagram:
                outputs["mermaid"] = mermaid_diagram
                
                # Generate PNG from Mermaid diagram
                png_file = self.output_generator.generate_png_diagram(
                    mermaid_diagram=mermaid_diagram,
                    process_name=self.process_name,
                    timestamp=timestamp,
                    output_dir=output_dir,
                    base_output_dir=self.config.base_output_dir,
                    default_output_dir=self.config.default_output_dir
                )
                if png_file:
                    outputs["png"] = png_file
                    
            # Generate LLM prompt
            llm_prompt = self.output_generator.generate_llm_prompt(
                steps=self.steps,
                notes=self.notes,
                process_name=self.process_name,
                timestamp=timestamp,
                base_output_dir=self.config.base_output_dir,
                default_output_dir=self.config.default_output_dir
            )
            if llm_prompt:
                outputs["llm_prompt"] = llm_prompt
                
            # Generate executive summary
            executive_summary = self.output_generator.generate_executive_summary(
                process_name=self.process_name,
                steps=self.steps,
                notes=self.notes,
                timestamp=timestamp,
                base_output_dir=self.config.base_output_dir,
                default_output_dir=self.config.default_output_dir,
                verbose=True
            )
            if executive_summary:
                outputs["executive_summary"] = executive_summary
                
            return outputs
            
        except Exception as e:
            log.error(f"Error generating outputs: {str(e)}")
            return {}

    def to_csv(self) -> str:
        """Convert the process to CSV format.
        
        Returns:
            CSV string representation of the process
        """
        try:
            # Create CSV header
            header = [
                "step_id",
                "description",
                "decision",
                "success_outcome",
                "failure_outcome",
                "next_step_success",
                "next_step_failure",
                "note_id",
                "validation_rules",
                "error_codes"
            ]
            
            # Create rows for each step
            rows = []
            for step in self.steps:
                row = [
                    step.step_id,
                    step.description,
                    step.decision,
                    step.success_outcome,
                    step.failure_outcome,
                    step.next_step_success,
                    step.next_step_failure,
                    step.note_id or "",
                    step.validation_rules or "",
                    step.error_codes or ""
                ]
                rows.append(row)
            
            # Convert to CSV string
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)
            
            return output.getvalue()
            
        except Exception as e:
            log.error(f"Error converting process to CSV: {str(e)}")
            raise

    def validate_process_flow(self) -> List[str]:
        """Validate the entire process flow and return a list of issues.
        
        Returns:
            List of validation issue messages, empty if all is valid
        """
        return validate_process_flow(self.steps)

    def validate_step_name(self, step_name: str) -> bool:
        """Validate that a step name is valid.
        
        Args:
            step_name: The step name to validate
            
        Returns:
            True if the name is valid, False otherwise
        """
        if not step_name:
            return False
        # Allow alphanumeric characters, underscores, and hyphens
        return all(c.isalnum() or c in ['_', '-'] for c in step_name)

    def generate_next_step_suggestion(self, step_id: str, description: str, decision: str, 
                                    success_outcome: str, failure_outcome: str, is_success: bool) -> str:
        """Generate an AI suggestion for the next step.
        
        Args:
            step_id: The ID of the current step
            description: The description of the current step
            decision: The decision of the current step
            success_outcome: The success outcome of the current step
            failure_outcome: The failure outcome of the current step
            is_success: Whether this is for success or failure path
            
        Returns:
            Suggested next step ID
        """
        if not self.openai_client:
            return None
            
        try:
            # Get existing step IDs to avoid suggesting duplicates
            existing_steps = [step.step_id for step in self.steps]
            
            # Create a prompt for the AI
            prompt = f"""Given the following step in a process:
            
            Step ID: {step_id}
            Description: {description}
            Decision: {decision}
            Success Outcome: {success_outcome}
            Failure Outcome: {failure_outcome}
            
            Please suggest a logical next step for the {'success' if is_success else 'failure'} path.
            The suggestion should:
            1. Be a clear, concise step name
            2. Follow logically from the current step
            3. Not be one of these existing steps: {', '.join(existing_steps)}
            4. Use underscores instead of spaces
            5. Be between 2-4 words
            
            Return only the suggested step name, nothing else."""
            
            # Get AI response
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a process design expert helping to create logical process flows."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            # Extract and clean the suggestion
            suggestion = response.choices[0].message.content.strip()
            # Convert spaces to underscores and clean up
            suggestion = suggestion.replace(' ', '_').replace('.', '').strip()
            
            return suggestion
            
        except Exception as e:
            print(f"Error generating next step suggestion: {str(e)}")
            return None

