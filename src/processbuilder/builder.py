"""
Main ProcessBuilder class for building and managing processes.
"""

import os
import sys
import time
import logging
import json
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import openai
from datetime import datetime
import io
from typing import List, Optional, Tuple, Dict, Any, Callable
# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # Default log level

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

# Import local modules
from .config import Config
from .models import ProcessStep, ProcessNote
from .utils import (
    sanitize_id,
    validate_process_flow,
    validate_notes,
    write_csv
)
def default_input_handler(prompt: str) -> str:
    """Default input handler that uses the built-in input function.
    This serves as a fallback when get_step_input from cli isn't available."""
    while True:
        response = input(f"\n{prompt}\n> ").strip()
        if response:
            return response

# Function to sanitize strings to prevent issues with quotes
def sanitize_string(text):
    """Sanitize a string to prevent issues with quotes."""
    if not text:
        return text
    return text.replace("'", "\\'")
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
    

def show_loading_animation(message: str, duration: float = 0.5) -> None:
    """Show a simple loading animation while waiting for AI response.
    
    Args:
        message: The message to display while loading
        duration: How long to show each frame in seconds
    """
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    start_time = time.time()
    
    try:
        i = 0
        while True:
            frame = frames[i % len(frames)]
            sys.stdout.write(f"\r{message} {frame}")
            sys.stdout.flush()
            time.sleep(duration)
            i += 1
            
            # Optional timeout to prevent infinite animation
            elapsed = time.time() - start_time
            if elapsed > 30:  # Safety timeout after 30 seconds
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\r\033[K")  # Clear the line
        sys.stdout.flush()
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
        if not self.openai_client:
            return ""
        
        try:
            # Sanitize inputs
            safe_process_name = sanitize_string(self.process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_success = sanitize_string(success_outcome)
            safe_failure = sanitize_string(failure_outcome)
            
            # Build prompt context using string concatenation
            context = (
                f"Process: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Success Outcome: {safe_success}\n"
                f"Failure Outcome: {safe_failure}\n\n"
                "Please suggest error codes for this step that:\n"
                "1. Are specific to potential failure scenarios\n"
                "2. Follow a consistent naming convention\n"
                "3. Include both technical and business error codes\n"
                "4. Are descriptive and meaningful\n"
                "5. Can be used for logging and monitoring\n\n"
                "Format the response as a bulleted list of error codes with brief descriptions."
            )

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
    
    def validate_next_step_id(self, next_step_id: str) -> bool:
        """Validate that a next step ID is either 'End' or an existing step.
        
        Args:
            next_step_id: The next step ID to validate
            
        Returns:
            True if the next step is valid (either 'End' or an existing step ID),
            False otherwise
        """
        # "End" is always a valid next step
        if next_step_id.lower() == 'end':
            return True
            
        # Check if the step ID exists in the current steps
        if any(step.step_id == next_step_id for step in self.steps):
            return True
            
        # Return False for any other value
        return False
            
    def validate_next_step(self, step: ProcessStep) -> List[str]:
        """Validate that the next step IDs in the step are valid.
        
        Args:
            step: The step to validate
            
        Returns:
            List of validation issue messages, empty if all is valid
        """
        issues = []
        
        # Validate next_step_success
        if not self.validate_next_step_id(step.next_step_success):
            issues.append(f"Next step on success path '{step.next_step_success}' does not exist")
            
        # Validate next_step_failure
        if not self.validate_next_step_id(step.next_step_failure):
            issues.append(f"Next step on failure path '{step.next_step_failure}' does not exist")
            
        return issues
        
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
            # Rewrite the prompt with proper string formatting
            parse_prompt = (
                f"Parse the following process step suggestions into specific field updates:\n\n"
                f"{suggestions}\n\n"
                f"Please provide the updates in this exact format:\n"
                f"Description: [new description or None]\n"
                f"Decision: [new decision or None]\n"
                f"Success Outcome: [new success outcome or None]\n"
                f"Failure Outcome: [new failure outcome or None]\n"
                f"Validation Rules: [new validation rules or None]\n"
                f"Error Codes: [new error codes or None]\n\n"
                f"If a field should not be updated, use None."
            )

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
            
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Given the following process context:\n\n"
                f"{context}\n\n"
                f"Suggest a clear and concise description of what happens in this step. The description should:\n"
                f"1. Be specific and actionable\n"
                f"2. Include key activities and inputs\n"
                f"3. Explain the purpose of the step\n"
                f"4. Be between 50-100 words\n"
                f"5. Follow business process documentation best practices\n\n"
                f"Please provide just the description, no additional text."
            )

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
            
            # Sanitize context to prevent syntax errors from unescaped single quotes
            safe_context = sanitize_string(context)
            
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Based on the following process context:\n\n"
                f"{safe_context}\n\n"
                f"Please suggest a clear, specific decision point for this step. The decision should:\n"
                f"1. Be a yes/no question\n"
                f"2. Be directly related to the step's purpose\n"
                f"3. Be specific and actionable\n"
                f"4. Help determine the next step in the process\n\n"
                f"Return only the decision question, without any additional explanation or formatting."
            )

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
            
            # Sanitize context to prevent syntax errors from unescaped single quotes
            safe_context = sanitize_string(context)
            
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Based on the following process context:\n\n"
                f"{safe_context}\n\n"
                f"Please suggest a clear, specific success outcome for this step. The success outcome should:\n"
                f"1. Be a clear yes/no question\n"
                f"2. Directly relate to the step's purpose\n"
                f"3. Be specific and actionable\n"
                f"4. Help determine the next step\n\n"
                f"Format the response as a single question that can be answered with yes/no."
            )

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
            
            # Sanitize context to prevent syntax errors from unescaped single quotes
            safe_context = sanitize_string(context)
            
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Based on the following process context:\n\n"
                f"{safe_context}\n\n"
                f"Please suggest a clear, specific failure outcome for this step. The failure outcome should:\n"
                f"1. Clearly describe what happens when the step fails\n"
                f"2. Be specific about error handling or recovery steps\n"
                f"3. Help determine the next step in the failure path\n"
                f"4. Be actionable and informative\n\n"
                f"Format the response as a clear, concise statement describing the failure outcome."
            )

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
        decision = self.get_input("What decision needs to be made?")
        
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
            for missing_step_id, predecessor_id, path_type in missing_steps:
                # Create the missing step using either interactive or non-interactive mode
                if interactive:
                    print(f"\nFound missing step: {missing_step_id}")
                    print(f"Referenced by step: {predecessor_id} on {path_type} path")
                    new_step = self.create_missing_step(missing_step_id, predecessor_id, path_type)
                else:
                    new_step = self.create_missing_step_noninteractive(missing_step_id, predecessor_id, path_type)
                
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
        if not self.openai_client:
            return "AI evaluation is not available - OPENAI_API_KEY not found or invalid."
            
        try:
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Evaluate the following process step design:\n\n"
                f"Process Name: {self.process_name}\n"
                f"Step ID: {step.step_id}\n"
                f"Description: {step.description}\n"
                f"Decision: {step.decision}\n"
                f"Success Outcome: {step.success_outcome}\n"
                f"Failure Outcome: {step.failure_outcome}\n"
                f"Next Step (Success): {step.next_step_success}\n"
                f"Next Step (Failure): {step.next_step_failure}\n"
                f"Validation Rules: {step.validation_rules or 'None'}\n"
                f"Error Codes: {step.error_codes or 'None'}\n\n"
                f"Please provide:\n"
                f"1. A brief assessment of the step's design\n"
                f"2. Potential improvements or considerations\n"
                f"3. Any missing elements that should be addressed\n"
                f"4. Specific recommendations for validation or error handling if not provided\n\n"
                f"Keep the response concise and actionable."
            )

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
                    if "ProcessEnd" not in diagram:
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
            
            # Add note if present, with error handling for missing notes
            if step.note_id:
                try:
                    note = next(n for n in self.notes if n.note_id == step.note_id)
                    note_id = f"Note_{sanitize_id(step.step_id)}"
                    diagram += f"    {note_id}[\"{note.content}\"]\n"
                    diagram += f"    {safe_id} -.-> {note_id}\n"
                except StopIteration:
                    # Note referenced by step wasn't found, log a warning and continue
                    log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
        diagram += """
    classDef process fill:#E8F5E9,stroke:#66BB6A
    classDef decision fill:#FFF3E0,stroke:#FFB74D
    classDef note fill:#FFFDE7,stroke:#FFF9C4
    classDef end fill:#FFEBEE,stroke:#E57373
    
    class Step_* process
    class Decision_* decision
    class Note_* note
    class ProcessEnd end
```"""
        
        # Save to file
        mermaid_file.write_text(diagram)
        print(f"\nMermaid diagram generated: {mermaid_file}")
        return diagram

    def generate_llm_prompt(self) -> str:
        """Generate a prompt for an LLM to help document the process."""
        prompt = (
            f"I need help documenting the {self.process_name} process. Here's what I know so far:\n\n"
            f"Process Overview:\n"
            f"{self.process_name} is a workflow that handles the following steps:\n\n"
        )
        
        for step in self.steps:
            prompt += f"""
Step {step.step_id}: {step.description}
- Decision: {step.decision}
- Success: {step.success_outcome}
- Failure: {step.failure_outcome}
"""
            if step.note_id:
                try:
                    note = next(n for n in self.notes if n.note_id == step.note_id)
                    prompt += f"\n- Note: {note.content}"
                except StopIteration:
                    log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
                    prompt += f"\n- Note: [Referenced note {step.note_id} not found]"
                
                # Add validation rules if they exist
                if step.validation_rules:
                    prompt += f"\n- Validation: {step.validation_rules}"
                # Add error codes if they exist
                if step.error_codes:
                    prompt += f"\n- Error Codes: {step.error_codes}"
        
        prompt += """

Please help me:
1. Review this process for completeness
2. Identify any missing steps or edge cases
3. Suggest improvements to the workflow
4. Create a clear, visual representation of the process
"""
        return prompt

    def generate_executive_summary(self) -> str:
        """Generate an executive summary for the process using OpenAI."""
        if not self.openai_client:
            return "AI executive summary is not available - OPENAI_API_KEY not found or invalid."
            
        try:
            # Create a detailed prompt for the executive summary
            # Create a detailed prompt for the executive summary
            # Rewrite the prompt with proper string formatting
            prompt = (
                f"Create an executive summary for the {self.process_name} process. Here's the process information:\n\n"
                f"Process Steps:\n"
            )
            
            for step in self.steps:
                prompt += (
                    f"Step {step.step_id}: {step.description}\n"
                    f"- Decision: {step.decision}\n"
                    f"- Success: {step.success_outcome}\n"
                    f"- Failure: {step.failure_outcome}\n"
                )
                
                if step.note_id:
                    try:
                        note = next(n for n in self.notes if n.note_id == step.note_id)
                        prompt += f"\n- Note: {note.content}"
                    except StopIteration:
                        log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
                        prompt += f"\n- Note: [Referenced note {step.note_id} not found]"
            if self.verbose:
                log.debug(f"Sending OpenAI prompt for executive summary: \n{prompt}")
            
            response = self.openai_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a process documentation expert. Create clear, concise executive summaries for business processes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            summary = response.choices[0].message.content.strip()
            if self.verbose:
                log.debug(f"Received OpenAI executive summary response")
            
            return summary
            
        except Exception as e:
            log.error(f"Error generating executive summary: {str(e)}")
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
        try:
            # Create state directory if it doesn't exist
            self.state_dir.mkdir(exist_ok=True)
            
            # Create a state file for this process
            state_file = self.state_dir / f"{self.process_name}.json"
            
            # Build the state dictionary
            state = {
                "process_name": self.process_name,
                "timestamp": self.timestamp,
                "current_note_id": self.current_note_id,
                "step_count": self.step_count,
                "steps": [step.to_dict() for step in self.steps],
                "notes": [note.to_dict() for note in self.notes]
            }
            
            # Write the state to file
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
                
            log.debug(f"Saved process state to {state_file}")
        except Exception as e:
            log.warning(f"Failed to save process state: {str(e)}")
    
    def load_state(self) -> bool:
        """Load process state from a JSON file.
        
        Returns:
            True if state was loaded successfully, False otherwise.
        """
        # Check if state directory and file exist
        state_file = self.state_dir / f"{self.process_name}.json"
        if not state_file.exists():
            log.debug(f"No state file found for process: {self.process_name}")
            return False
            
        try:
            # Read the state from file
            with open(state_file, "r") as f:
                state = json.load(f)
                
            # Load metadata
            self.timestamp = state.get("timestamp", self.timestamp)
            self.current_note_id = state.get("current_note_id", 1)
            self.step_count = state.get("step_count", 0)
            
            # Load steps
            self.steps = []
            for step_data in state.get("steps", []):
                self.steps.append(ProcessStep.from_dict(step_data))
                
            # Load notes
            self.notes = []
            for note_data in state.get("notes", []):
                self.notes.append(ProcessNote.from_dict(note_data))
                
            log.debug(f"Successfully loaded state for process: {self.process_name}")
            return True
        except Exception as e:
            log.warning(f"Failed to load process state: {str(e)}")
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

            
    def generate_validation_rules(self, step_id: str, description: str, decision: str, 
                                success_outcome: str, failure_outcome: str) -> str:
        """Generate suggested validation rules for a step using OpenAI."""
        if not self.openai_client:
            return ""
        
        try:
            # Build context for the prompt
            context = (
                f"Process: {self.process_name}\n"
                f"Step ID: {step_id}\n"
                f"Description: {description}\n"
                f"Decision: {decision}\n"
                f"Success Outcome: {success_outcome}\n"
                f"Failure Outcome: {failure_outcome}\n\n"
                "Please suggest validation rules for this step that:\n"
                "1. Ensure data quality and completeness\n"
                "2. Prevent common errors\n"
                "3. Are specific and actionable\n"
                "4. Follow best practices\n"
                "5. Help maintain process integrity\n\n"
                "Format the response as a bulleted list with brief, clear rules."
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process validation expert. Provide clear, specific validation rules."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # Format the rules
            rules = response.choices[0].message.content.strip().split('\n')
            formatted_rules = []
            for rule in rules:
                if not rule.strip():
                    continue
                    
                # Ensure each rule starts with a bullet point
                if not (rule.strip().startswith('-') or rule.strip().startswith('*')):
                    rule = f"- {rule.strip()}"
                
                # Limit rule length
                words = rule.split()
                if len(words) > 20:
                    rule = ' '.join(words[:20])
                formatted_rules.append(rule)
            
            return '\n'.join(formatted_rules)
        except Exception as e:
            print(f"Error generating validation rules suggestion: {str(e)}")
            return ""

