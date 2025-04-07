"""
Main ProcessBuilder class for building and managing processes.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Dict, Any
import openai
from datetime import datetime

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
from .models import ProcessStep, ProcessNote

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
    """Main class for building and managing process flows."""
    
    # Class-level input handler (allows custom input methods to be injected)
    _input_handler = default_input_handler
    
    # Initialize class variable for verbose mode
    _verbose: bool = False
    
    def __init__(self, process_name, config=None, verbose=None):
        """Initialize a new ProcessBuilder.
        
        Args:
            process_name: The name of the process to build
            config: Optional Config object, will create default if None
            verbose: Optional boolean to override class-level verbose setting
        """
        self.process_name = process_name
        self.config = config or Config()
        self.steps = []
        self.notes = []
        self.current_note_id = 1
        self.output_dir = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.step_count = 0  # Initialize step counter
        self.state_dir = Path(".processbuilder")
        
        # Try to load existing state
        try:
            self.load_state()
            log.debug(f"Loaded existing state for process: {self.process_name}")
        except Exception as e:
            log.debug(f"No existing state found or error loading state: {str(e)}")
        
        # Set instance-level verbose mode if specified
        self.verbose = verbose if verbose is not None else self.__class__._verbose
        
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
            
    def validate_next_step(self, step: ProcessStep) -> List[str]:
        """Validate that the next step IDs in the step are valid.
        
        Args:
            step: The step to validate
            
        Returns:
            List of validation issue messages, empty if all is valid
        """
        return validate_next_step(step, self.steps)
        
    def create_step_id(self, title: str) -> str:
        """Create a valid, unique step ID from a title.
        
        Args:
            title: The title to convert to a step ID
            
        Returns:
            A valid, unique step ID
        """
        # Start with the title as the step ID
        step_id = title
        
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
            next_step_success="End",
            next_step_failure="End",
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
                
            # Sanitize strings to prevent syntax errors from unescaped single quotes
            safe_process_name = sanitize_string(self.process_name)
            safe_pred_id = sanitize_string(predecessor.step_id)
            safe_pred_desc = sanitize_string(predecessor.description)
            safe_pred_decision = sanitize_string(predecessor.decision)
            safe_path_type = sanitize_string(path_type)
            safe_step_id = sanitize_string(step_id)
            
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Predecessor Step: {safe_pred_id}\n"
                f"Predecessor Description: {safe_pred_desc}\n"
                f"Predecessor Decision: {safe_pred_decision}\n"
                f"Path Type: {safe_path_type}\n"
                f"Current Step ID: {safe_step_id}\n\n"
                f"Suggest an appropriate title for this step that:\n"
                f"1. Follows logically from the predecessor step\n"
                f"2. Is clear and descriptive\n"
                f"3. Starts with a verb\n"
                f"4. Is specific to the process\n"
                f"5. Is concise (2-5 words)\n"
                f"6. Follows business process naming conventions\n\n"
                f"Please provide just the step title, no additional text."
            )

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

    def add_step(self, step=None, interactive: bool = True, **kwargs) -> List[str]:
        """Add a new step to the process and validate it.
        
        This method can be called in two ways:
        1. With a ProcessStep instance: add_step(step, interactive=True)
        2. With keyword arguments: add_step(step_id="Step1", description="...", ...)
        
        Args:
            step: The ProcessStep instance (optional)
            interactive: Whether to use interactive mode for missing steps
                         If False, will auto-generate missing steps without prompts
            **kwargs: Keyword arguments to create a ProcessStep if not provided directly
        
        Returns:
            List of validation issues, or empty list if validation passed
        """
        # If a step wasn't provided directly, create one from kwargs
        if step is None:
            if not kwargs:
                return ["No step provided and no attributes specified"]
            
            # Import here to avoid circular imports
            from .models import ProcessStep
            
            # Make sure required attributes are present
            required_attrs = ["step_id", "description", "decision", "success_outcome", "failure_outcome"]
            missing_attrs = [attr for attr in required_attrs if attr not in kwargs]
            if missing_attrs:
                return [f"Missing required attribute(s): {', '.join(missing_attrs)}"]
            
            # Create the step
            step = ProcessStep(
                step_id=kwargs["step_id"],
                description=kwargs["description"],
                decision=kwargs["decision"],
                success_outcome=kwargs["success_outcome"],
                failure_outcome=kwargs["failure_outcome"],
                note_id=kwargs.get("note_id"),
                next_step_success=kwargs.get("next_step_success", "End"),
                next_step_failure=kwargs.get("next_step_failure", "End"),
                validation_rules=kwargs.get("validation_rules"),
                error_codes=kwargs.get("error_codes"),
                retry_logic=kwargs.get("retry_logic")
            )
        
        # Validate the step
        issues = step.validate()
        
        # Also validate next steps
        next_step_issues = self.validate_next_step(step)
        issues.extend(next_step_issues)
        
        if issues:
            return issues
            
        # Add the step
        self.steps.append(step)
        self.step_count += 1
        
        # Auto-save after adding step
        self.save_state()
        
        # Check for missing steps that need to be created
        missing_steps = self.find_missing_steps()
        while missing_steps:
            for missing_step_id, referencing_step_id, path_type in missing_steps:
                # Create the missing step using either interactive or non-interactive mode
                if interactive:
                    print(f"\nFound missing step: {missing_step_id}")
                    print(f"Referenced by step: {referencing_step_id} on {path_type} path")
                    new_step = self.create_missing_step(missing_step_id, referencing_step_id, path_type)
                else:
                    new_step = self.create_missing_step_noninteractive(missing_step_id, referencing_step_id, path_type)
                
                # Add the new step with the same interactivity setting
                step_issues = self.add_step(new_step, interactive=interactive)
                
                if step_issues:
                    print("\n=== Validation Issues ===")
                    for issue in step_issues:
                        print(f"- {issue}")
                    print("\nPlease fix these issues and try again.")
                    continue
            
            # Check if there are still missing steps
            missing_steps = self.find_missing_steps()
            if not missing_steps:
                break
        
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
                
        # Auto-save after adding note
        self.save_state()
                
        return []
    def evaluate_step_design(self, step: ProcessStep) -> str:
        """Evaluate a step design and provide feedback using OpenAI."""
        return evaluate_step_design(
            self.openai_client,
            self.process_name,
            step
        )
            
    def setup_output_directory(self, base_dir: Optional[Path] = None) -> Path:
        """Set up the output directory structure for this run."""
        output_dir = setup_output_directory(
            process_name=self.process_name,
            timestamp=self.timestamp,
            base_dir=base_dir,
            default_output_dir=self.config.default_output_dir
        )
        self.output_dir = output_dir
        return output_dir

    def generate_csv(self, base_output_dir: Optional[Path] = None) -> None:
        """Generate CSV files for the process."""
        output_dir = generate_csv(
            steps=self.steps,
            notes=self.notes,
            process_name=self.process_name,
            timestamp=self.timestamp,
            base_output_dir=base_output_dir,
            default_output_dir=self.config.default_output_dir
        )
        self.output_dir = output_dir

    def generate_mermaid_diagram(self, base_output_dir: Optional[Path] = None) -> str:
        """Generate a Mermaid diagram from the process steps."""
        diagram = generate_mermaid_diagram(
            steps=self.steps,
            notes=self.notes,
            process_name=self.process_name,
            timestamp=self.timestamp,
            output_dir=self.output_dir,
            base_output_dir=base_output_dir,
            default_output_dir=self.config.default_output_dir
        )
        return diagram

    def generate_llm_prompt(self) -> str:
        """Generate a prompt for an LLM to help document the process."""
        return generate_llm_prompt(
            steps=self.steps,
            notes=self.notes,
            process_name=self.process_name
        )

    def generate_executive_summary(self) -> str:
        """Generate an executive summary for the process using OpenAI."""
        return generate_executive_summary(
            openai_client=self.openai_client,
            process_name=self.process_name,
            steps=self.steps,
            notes=self.notes,
            verbose=self.verbose
        )
    def run_interview(self) -> None:
        """Run the interactive interview process."""
        try:
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
                choice = self.get_input("Enter your choice (1-4):")
                
                if choice == '1':
                    self.view_all_steps()
                    # Always redisplay menu after viewing steps
                    show_menu()
                elif choice == '2':
                    self.edit_step()
                    # Always redisplay menu after editing
                    show_menu()
                elif choice == '3':
                    # Create a new step interactively
                    if len(self.steps) == 0:
                        # For the first step, offer to use the suggested name
                        suggested_id = self.suggested_first_step
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
                    new_step = self.create_missing_step(step_id)
                    
                    # Add the step with validation
                    validation_issues = self.add_step(new_step, interactive=True)
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
                            new_step = self.create_missing_step(step_id)
                            validation_issues = self.add_step(new_step, interactive=True)
                            if validation_issues:
                                print("\n=== Validation Issues ===")
                                for issue in validation_issues:
                                    print(f"- {issue}")
                                print("\nPlease fix these issues and try again.")
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
            
            # Make sure we save state before generating outputs
            self.save_state()
            
            # Check if we have steps before generating outputs
            if not self.steps:
                print("\nCannot generate outputs: Process builder has no steps.")
                return
                
            # Generate outputs
            self.generate_csv()
            self.generate_mermaid_diagram()
            
            # Generate and save LLM prompt
            llm_prompt = self.generate_llm_prompt()
            print("\n=== LLM Prompt ===")
            print(llm_prompt)
            
            if self.output_dir:
                # Create Path object if self.output_dir is a string
                output_dir = Path(self.output_dir) if isinstance(self.output_dir, str) else self.output_dir
                prompt_file = output_dir / f"{self.process_name}_prompt.txt"
                
                # Use write_text if it's a Path object, otherwise use open()
                if hasattr(prompt_file, 'write_text'):
                    prompt_file.write_text(llm_prompt)
                else:
                    with open(prompt_file, 'w') as f:
                        f.write(llm_prompt)
                
                print(f"LLM prompt saved to: {prompt_file}")
            
            # Generate and save executive summary
            executive_summary = self.generate_executive_summary()
            print("\n=== Executive Summary ===")
            print(executive_summary)
            
            if self.output_dir:
                # Create Path object if self.output_dir is a string
                output_dir = Path(self.output_dir) if isinstance(self.output_dir, str) else self.output_dir
                summary_file = output_dir / f"{self.process_name}_executive_summary.md"
                
                # Use write_text if it's a Path object, otherwise use open()
                if hasattr(summary_file, 'write_text'):
                    summary_file.write_text(executive_summary)
                else:
                    with open(summary_file, 'w') as f:
                        f.write(executive_summary)
                
                print(f"Executive summary saved to: {summary_file}")
                
        except Exception as e:
            print(f"An error occurred during interview: {str(e)}")
            print(f"DEBUG: Builder exists: {hasattr(self, 'steps')}")
            print(f"DEBUG: Builder type: {type(self)}")
            print(f"DEBUG: Builder has 'steps' attribute: {hasattr(self, 'steps')}")
            print(f"DEBUG: Error details: {e}")
            print("Cannot generate outputs: Process builder has no steps or is in an invalid state.")

    def save_state(self) -> None:
        """Save the current process state to a JSON file.
        
        This saves all steps, notes, and builder metadata to allow
        resuming work on the process later.
        """
        return save_state(
            process_name=self.process_name,
            timestamp=self.timestamp,
            current_note_id=self.current_note_id,
            step_count=self.step_count,
            steps=self.steps,
            notes=self.notes,
            state_dir=self.state_dir
        )
    
    def to_csv(self) -> List[Dict[str, Any]]:
        """Convert process steps to CSV format for saving.
        
        Returns:
            A list of dictionaries containing step data ready for CSV output
        """
        csv_data = []
        
        for step in self.steps:
            # Prepare step data for CSV format
            step_data = {
                "Step ID": step.step_id,
                "Description": step.description,
                "Decision": step.decision,
                "Success Outcome": step.success_outcome,
                "Failure Outcome": step.failure_outcome,
                "Next Step (Success)": step.next_step_success,
                "Next Step (Failure)": step.next_step_failure,
                "Note ID": step.note_id or "",
                "Validation Rules": step.validation_rules or "",
                "Error Codes": step.error_codes or "",
                "Retry Logic": step.retry_logic or "",
            }
            csv_data.append(step_data)
            
        return csv_data
    
    def load_state(self) -> bool:
        """Load process state from a JSON file.
        
        Returns:
            True if state was loaded successfully, False otherwise.
        """
        result = load_state(
            process_name=self.process_name,
            state_dir=self.state_dir,
            process_step_class=ProcessStep,
            process_note_class=ProcessNote
        )
        
        if result[0]:  # If state was loaded successfully
            metadata, steps, notes = result
            
            # Update builder attributes
            self.timestamp = metadata.get("timestamp", self.timestamp)
            self.current_note_id = metadata.get("current_note_id", 1)
            self.step_count = metadata.get("step_count", 0)
            self.steps = steps
            self.notes = notes
            return True
        else:
            return False

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
                try:
                    note = next(n for n in self.notes if n.note_id == step.note_id)
                    print(f"\nNote: {note.content}")
                except StopIteration:
                    log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
                    print(f"\nNote: [Referenced note {step.note_id} not found]")
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
            choice = int(self.get_input("Enter step number to edit:"))
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
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.description = description_suggestion
                    else:
                        new_desc = self.get_input(f"Description [{step.description}]:")
                        if new_desc:
                            step.description = new_desc
                
                # Decision
                if decision_suggestion:
                    print(f"\nAI suggests decision: '{decision_suggestion}'")
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.decision = decision_suggestion
                    else:
                        new_decision = self.get_input(f"Decision [{step.decision}]:")
                        if new_decision:
                            step.decision = new_decision
                
                # Success Outcome
                if success_suggestion:
                    print(f"\nAI suggests success outcome: '{success_suggestion}'")
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.success_outcome = success_suggestion
                    else:
                        new_success = self.get_input(f"Success Outcome [{step.success_outcome}]:")
                        if new_success:
                            step.success_outcome = new_success
                
                # Failure Outcome
                if failure_suggestion:
                    print(f"\nAI suggests failure outcome: '{failure_suggestion}'")
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.failure_outcome = failure_suggestion
                    else:
                        new_failure = self.get_input(f"Failure Outcome [{step.failure_outcome}]:")
                        if new_failure:
                            step.failure_outcome = new_failure
                
                # Note
                if note_suggestion:
                    print(f"\nAI suggests note: '{note_suggestion}'")
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
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
                        new_note = self.get_input(f"Note [{'None' if not step.note_id else next(n for n in self.notes if n.note_id == step.note_id).content}]:")
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
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.validation_rules = validation_suggestion
                    else:
                        new_validation = self.get_input(f"Validation Rules [{step.validation_rules or 'None'}]:")
                        if new_validation:
                            step.validation_rules = new_validation
                        elif new_validation == '':
                            step.validation_rules = None
                
                # Error Codes
                if error_suggestion:
                    print(f"\nAI suggests error codes: '{error_suggestion}'")
                    use_suggestion = self.get_input("Use this suggestion? (y/n)").lower() == 'y'
                    if use_suggestion:
                        step.error_codes = error_suggestion
                    else:
                        new_errors = self.get_input(f"Error Codes [{step.error_codes or 'None'}]:")
                        if new_errors:
                            step.error_codes = new_errors
                        elif new_errors == '':
                            step.error_codes = None
            else:
                # Manual editing without AI suggestions
                new_desc = self.get_input(f"Description [{step.description}]:")
                if new_desc:
                    step.description = new_desc
                
                new_decision = self.get_input(f"Decision [{step.decision}]:")
                if new_decision:
                    step.decision = new_decision
                
                new_success = self.get_input(f"Success Outcome [{step.success_outcome}]:")
                if new_success:
                    step.success_outcome = new_success
                
                new_failure = self.get_input(f"Failure Outcome [{step.failure_outcome}]:")
                if new_failure:
                    step.failure_outcome = new_failure
                
                new_note = self.get_input(f"Note [{'None' if not step.note_id else next(n for n in self.notes if n.note_id == step.note_id).content}]:")
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
            # Final validation and save
            step_issues = step.validate()
            next_step_issues = self.validate_next_step(step)
            flow_issues = validate_process_flow(self.steps)
            note_issues = validate_notes(self.notes, self.steps)
            all_issues = step_issues + next_step_issues + flow_issues + note_issues

            if all_issues:
                print("\n=== Validation Issues ===")
                for issue in all_issues:
                    print(f"- {issue}")
                print("\nPlease fix these issues.")
                
                save_anyway = self.get_input("Save changes anyway? (y/n)").lower() == 'y'
                if save_anyway:
                    print("\nSaving changes with validation issues...")
                    self.save_state()
                    print("Step updated and saved with validation issues.")
                else:
                    print("\nChanges not saved due to validation issues.")
                    return
            else:
                print("\nStep updated successfully.")
                self.save_state()
                print("Step changes saved successfully.")
        except Exception as e:
            print(f"Error editing step: {str(e)}")
    def generate_step_note(self, step_id: str, description: str, decision: str, success_outcome: str, failure_outcome: str) -> str:
        """Generate a suggested note for a step using OpenAI."""
        if not self.openai_client:
            return ""
            
        try:
            # Sanitize strings to prevent syntax errors from unescaped single quotes
            safe_process_name = sanitize_string(self.process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_success = sanitize_string(success_outcome)
            safe_failure = sanitize_string(failure_outcome)
            
            # Rewrite the context with proper string formatting
            context = (
                f"Process: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Success Outcome: {safe_success}\n"
                f"Failure Outcome: {safe_failure}\n\n"
                f"Please suggest a very concise note (10-20 words) that captures the key point or requirement for this step. The note should be brief and actionable."
            )

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

    def add_step_from_dict(self, data: Dict[str, str]) -> List[str]:
        """Add a new step to the process from dictionary data (e.g., from CSV).
        
        Args:
            data: Dictionary containing step data with keys like 'Step ID', 'Description', etc.
            
        Returns:
            List of validation issues, or empty list if validation passed
        """
        try:
            # Map CSV keys to step attribute names
            step = ProcessStep(
                step_id=data.get("Step ID", ""),
                description=data.get("Description", ""),
                decision=data.get("Decision", ""),
                success_outcome=data.get("Success Outcome", ""),
                failure_outcome=data.get("Failure Outcome", ""),
                note_id=data.get("Note ID", None) if data.get("Note ID") else None,
                next_step_success=data.get("Next Step (Success)", "End"),
                next_step_failure=data.get("Next Step (Failure)", "End"),
                validation_rules=data.get("Validation Rules", None) if data.get("Validation Rules") else None,
                error_codes=data.get("Error Codes", None) if data.get("Error Codes") else None,
                retry_logic=data.get("Retry Logic", None) if data.get("Retry Logic") else None
            )
            
            # Add the step with validation
            return self.add_step(step, interactive=False)
            
        except Exception as e:
            log.warning(f"Error adding step from dictionary: {str(e)}")
            return [f"Error creating step: {str(e)}"]
            
    def add_note_from_dict(self, data: Dict[str, str]) -> List[str]:
        """Add a new note to the process from dictionary data (e.g., from CSV).
        
        Args:
            data: Dictionary containing note data with keys like 'Note ID', 'Content', etc.
            
        Returns:
            List of validation issues, or empty list if validation passed
        """
        try:
            # Map CSV keys to note attribute names
            note = ProcessNote(
                note_id=data.get("Note ID", ""),
                content=data.get("Content", ""),
                related_step_id=data.get("Related Step ID", "")
            )
            
            # Add the note with validation
            return self.add_note(note)
            
        except Exception as e:
            log.warning(f"Error adding note from dictionary: {str(e)}")
            return [f"Error creating note: {str(e)}"]

