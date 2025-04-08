"""Process Step Generator module for AI-powered step generation."""

from typing import Optional, Tuple
import openai
import logging
from ..utils import sanitize_string, show_loading_animation

log = logging.getLogger(__name__)

class ProcessStepGenerator:
    """Handles AI-powered step generation and suggestions."""
    
    def __init__(self, openai_client: openai.OpenAI):
        """Initialize the ProcessStepGenerator.
        
        Args:
            openai_client: The OpenAI client to use for generation
        """
        self.openai_client = openai_client
    
    def generate_step_description(
        self,
        process_name: str,
        step_id: str,
        predecessor_id: Optional[str] = None,
        path_type: Optional[str] = None
    ) -> str:
        """Generate a step description using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            predecessor_id: Optional ID of the predecessor step
            path_type: Optional path type ('success' or 'failure')
            
        Returns:
            Generated description
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_pred_id = sanitize_string(predecessor_id) if predecessor_id else ""
            safe_path_type = sanitize_string(path_type) if path_type else ""
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Predecessor Step: {safe_pred_id}\n"
                f"Path Type: {safe_path_type}\n\n"
                f"Please suggest a clear, concise description for this step that:\n"
                f"1. Explains what happens in this step\n"
                f"2. Is specific to the process\n"
                f"3. Is actionable and clear\n"
                f"4. Follows logically from the predecessor (if any)\n"
                f"5. Is appropriate for the path type (if specified)\n\n"
                f"Provide just the description, no additional text."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Create clear, concise step descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log.error(f"Error generating step description: {str(e)}")
            return ""
    
    def generate_step_decision(
        self,
        process_name: str,
        step_id: str,
        description: str,
        predecessor_id: Optional[str] = None,
        path_type: Optional[str] = None
    ) -> str:
        """Generate a step decision using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            description: Description of the step
            predecessor_id: Optional ID of the predecessor step
            path_type: Optional path type ('success' or 'failure')
            
        Returns:
            Generated decision
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_pred_id = sanitize_string(predecessor_id) if predecessor_id else ""
            safe_path_type = sanitize_string(path_type) if path_type else ""
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Predecessor Step: {safe_pred_id}\n"
                f"Path Type: {safe_path_type}\n\n"
                f"Please suggest a clear, concise decision for this step that:\n"
                f"1. Is a yes/no question\n"
                f"2. Determines the next step in the process\n"
                f"3. Is specific to the step description\n"
                f"4. Follows logically from the predecessor (if any)\n"
                f"5. Is appropriate for the path type (if specified)\n\n"
                f"Provide just the decision question, no additional text."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Create clear, concise decision questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log.error(f"Error generating step decision: {str(e)}")
            return ""
    
    def generate_step_outcomes(
        self,
        process_name: str,
        step_id: str,
        description: str,
        decision: str,
        predecessor_id: Optional[str] = None,
        path_type: Optional[str] = None
    ) -> Tuple[str, str]:
        """Generate success and failure outcomes using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            description: Description of the step
            decision: Decision question
            predecessor_id: Optional ID of the predecessor step
            path_type: Optional path type ('success' or 'failure')
            
        Returns:
            Tuple of (success_outcome, failure_outcome)
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_pred_id = sanitize_string(predecessor_id) if predecessor_id else ""
            safe_path_type = sanitize_string(path_type) if path_type else ""
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Predecessor Step: {safe_pred_id}\n"
                f"Path Type: {safe_path_type}\n\n"
                f"Please suggest two clear, concise outcomes for this step:\n"
                f"1. Success Outcome: What happens when the answer to the decision is 'yes'\n"
                f"2. Failure Outcome: What happens when the answer to the decision is 'no'\n\n"
                f"Each outcome should:\n"
                f"- Be specific to the step\n"
                f"- Follow logically from the decision\n"
                f"- Be appropriate for the path type (if specified)\n"
                f"- Be actionable and clear\n\n"
                f"Provide the outcomes in this format:\n"
                f"Success: [success outcome]\n"
                f"Failure: [failure outcome]"
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process design expert. Create clear, concise outcomes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # Parse the response to extract success and failure outcomes
            content = response.choices[0].message.content.strip()
            success_outcome = ""
            failure_outcome = ""
            
            for line in content.split("\n"):
                if line.startswith("Success:"):
                    success_outcome = line[8:].strip()
                elif line.startswith("Failure:"):
                    failure_outcome = line[8:].strip()
            
            return success_outcome, failure_outcome
            
        except Exception as e:
            log.error(f"Error generating step outcomes: {str(e)}")
            return "", ""
    
    def generate_step_note(
        self,
        process_name: str,
        step_id: str,
        description: str,
        decision: str,
        outcomes: Tuple[str, str]
    ) -> str:
        """Generate a step note using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            description: Description of the step
            decision: Decision question
            outcomes: Tuple of (success_outcome, failure_outcome)
            
        Returns:
            Generated note
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_success = sanitize_string(outcomes[0])
            safe_failure = sanitize_string(outcomes[1])
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Success Outcome: {safe_success}\n"
                f"Failure Outcome: {safe_failure}\n\n"
                f"Please suggest a very concise note (10-20 words) that:\n"
                f"1. Captures the key point or requirement for this step\n"
                f"2. Is brief and actionable\n"
                f"3. Provides important context or constraints\n"
                f"4. Is specific to the step\n\n"
                f"Provide just the note, no additional text."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process documentation expert. Provide very concise, actionable notes."},
                    {"role": "user", "content": prompt}
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
            log.error(f"Error generating step note: {str(e)}")
            return ""
    
    def generate_validation_rules(
        self,
        process_name: str,
        step_id: str,
        description: str,
        decision: str,
        outcomes: Tuple[str, str]
    ) -> str:
        """Generate validation rules using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            description: Description of the step
            decision: Decision question
            outcomes: Tuple of (success_outcome, failure_outcome)
            
        Returns:
            Generated validation rules
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_success = sanitize_string(outcomes[0])
            safe_failure = sanitize_string(outcomes[1])
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Success Outcome: {safe_success}\n"
                f"Failure Outcome: {safe_failure}\n\n"
                f"Please suggest validation rules for this step that:\n"
                f"1. Ensure the step receives good input data\n"
                f"2. Are specific to the step's requirements\n"
                f"3. Are clear and actionable\n"
                f"4. Cover both success and failure paths\n"
                f"5. Are appropriate for the process\n\n"
                f"Provide the rules in a clear, bullet-point format."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process validation expert. Create clear, actionable validation rules."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log.error(f"Error generating validation rules: {str(e)}")
            return ""
    
    def generate_error_codes(
        self,
        process_name: str,
        step_id: str,
        description: str,
        decision: str,
        outcomes: Tuple[str, str]
    ) -> str:
        """Generate error codes using AI.
        
        Args:
            process_name: Name of the process
            step_id: ID of the step
            description: Description of the step
            decision: Decision question
            outcomes: Tuple of (success_outcome, failure_outcome)
            
        Returns:
            Generated error codes
        """
        try:
            # Sanitize strings to prevent syntax errors
            safe_process_name = sanitize_string(process_name)
            safe_step_id = sanitize_string(step_id)
            safe_description = sanitize_string(description)
            safe_decision = sanitize_string(decision)
            safe_success = sanitize_string(outcomes[0])
            safe_failure = sanitize_string(outcomes[1])
            
            prompt = (
                f"Given the following process context:\n"
                f"Process Name: {safe_process_name}\n"
                f"Step ID: {safe_step_id}\n"
                f"Description: {safe_description}\n"
                f"Decision: {safe_decision}\n"
                f"Success Outcome: {safe_success}\n"
                f"Failure Outcome: {safe_failure}\n\n"
                f"Please suggest error codes for this step that:\n"
                f"1. Identify specific problems that might occur\n"
                f"2. Are unique and meaningful\n"
                f"3. Are appropriate for the step\n"
                f"4. Cover both success and failure paths\n"
                f"5. Are easy to understand and use\n\n"
                f"Provide the error codes in a clear, bullet-point format."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a process error handling expert. Create clear, meaningful error codes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log.error(f"Error generating error codes: {str(e)}")
            return "" 