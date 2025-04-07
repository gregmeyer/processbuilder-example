"""
Functions for generating AI-powered suggestions for process steps and related content.
"""
import os
import time
import sys
import logging
from typing import Optional, Dict, Any

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

def sanitize_string(text):
    """Sanitize a string to prevent issues with quotes."""
    if not text:
        return text
    return text.replace("'", "\\'")

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

def generate_step_description(openai_client, process_name: str, step_id: str, predecessor_id: Optional[str] = None, 
                             path_type: Optional[str] = None, steps=None, verbose: bool = False) -> str:
    """Generate an intelligent step description based on context.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        predecessor_id: Optional ID of the step that references this step
        path_type: Optional path type ('success' or 'failure') that led here
        steps: List of existing process steps to find predecessors
        verbose: Whether to log detailed responses
        
    Returns:
        A generated step description or empty string if generation fails
    """
    if not openai_client:
        return ""
        
    try:
        # Build context for the prompt
        context = f"Process Name: {process_name}\n"
        context += f"Current Step: {step_id}\n"
        
        if predecessor_id and steps:
            predecessor = next((s for s in steps if s.step_id == predecessor_id), None)
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

        response = openai_client.chat.completions.create(
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
            response = openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a business process expert. Create clear, concise step descriptions that follow best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            description = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated step description for {step_id}: {description[:50]}...")
            
        return description
    except Exception as e:
        log.error(f"Error generating step description: {str(e)}")
        return ""

def generate_step_decision(openai_client, process_name: str, step_id: str, description: str, 
                          predecessor_id: Optional[str] = None, path_type: Optional[str] = None, 
                          steps=None, verbose: bool = False) -> str:
    """Generate a suggested decision for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        predecessor_id: Optional ID of the step that references this step
        path_type: Optional path type ('success' or 'failure') that led here
        steps: List of existing process steps to find predecessors
        verbose: Whether to log detailed responses
        
    Returns:
        A generated decision question or empty string if generation fails
    """
    if not openai_client:
        return ""
    
    try:
        # Build context string
        context = f"Process: {process_name}\n"
        context += f"Current Step: {step_id}\n"
        context += f"Step Description: {description}\n"
        
        if predecessor_id and steps:
            predecessor = next((s for s in steps if s.step_id == predecessor_id), None)
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

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a process design expert. Provide clear, actionable decision points for process steps."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        decision = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated step decision for {step_id}: {decision}")
            
        return decision
    except Exception as e:
        log.error(f"Error generating decision suggestion: {str(e)}")
        return ""

def generate_step_success_outcome(openai_client, process_name: str, step_id: str, description: str, 
                                 decision: str, predecessor_id: Optional[str] = None, 
                                 path_type: Optional[str] = None, steps=None, verbose: bool = False) -> str:
    """Generate a suggested success outcome for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        decision: The decision question for the step
        predecessor_id: Optional ID of the step that references this step
        path_type: Optional path type ('success' or 'failure') that led here
        steps: List of existing process steps to find predecessors
        verbose: Whether to log detailed responses
        
    Returns:
        A generated success outcome or empty string if generation fails
    """
    if not openai_client:
        return ""
        
    try:
        # Build context string
        context = f"Process: {process_name}\n"
        context += f"Current Step: {step_id} - {description}\n"
        context += f"Decision: {decision}\n"
        
        if predecessor_id and steps:
            predecessor = next((s for s in steps if s.step_id == predecessor_id), None)
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
            f"1. Describe what happens when the decision is 'yes'\n"
            f"2. Directly relate to the step's purpose\n"
            f"3. Be specific and actionable\n"
            f"4. Help determine the next step\n\n"
            f"Format the response as a single clear statement describing the success outcome."
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a process design expert. Provide clear, specific success outcomes for process steps."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        success_outcome = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated success outcome for {step_id}: {success_outcome}")
            
        return success_outcome
    except Exception as e:
        log.error(f"Error generating success outcome suggestion: {str(e)}")
        return ""

def generate_step_failure_outcome(openai_client, process_name: str, step_id: str, description: str, 
                                 decision: str, predecessor_id: Optional[str] = None, 
                                 path_type: Optional[str] = None, steps=None, verbose: bool = False) -> str:
    """Generate a suggested failure outcome for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        decision: The decision question for the step
        predecessor_id: Optional ID of the step that references this step
        path_type: Optional path type ('success' or 'failure') that led here
        steps: List of existing process steps to find predecessors
        verbose: Whether to log detailed responses
        
    Returns:
        A generated failure outcome or empty string if generation fails
    """
    if not openai_client:
        return ""
        
    try:
        # Build context string
        context = f"Process: {process_name}\n"
        context += f"Current Step: {step_id} - {description}\n"
        context += f"Decision: {decision}\n"
        
        if predecessor_id and steps:
            predecessor = next((s for s in steps if s.step_id == predecessor_id), None)
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

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a process design expert. Provide clear, specific failure outcomes for process steps."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        failure_outcome = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated failure outcome for {step_id}: {failure_outcome}")
            
        return failure_outcome
    except Exception as e:
        log.error(f"Error generating failure outcome suggestion: {str(e)}")
        return ""

def generate_step_note(openai_client, process_name: str, step_id: str, description: str, 
                      decision: str, success_outcome: str, failure_outcome: str, verbose: bool = False) -> str:
    """Generate a suggested note for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        decision: The decision question for the step
        success_outcome: The success outcome description
        failure_outcome: The failure outcome description
        verbose: Whether to log detailed responses
        
    Returns:
        A generated note or empty string if generation fails
    """
    if not openai_client:
        return ""
        
    try:
        # Sanitize strings to prevent syntax errors from unescaped single quotes
        safe_process_name = sanitize_string(process_name)
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

        response = openai_client.chat.completions.create(
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
            
        if verbose:
            log.debug(f"Generated note for {step_id}: {note}")
            
        return note
    except Exception as e:
        log.error(f"Error generating note suggestion: {str(e)}")
        return ""

def generate_validation_rules(openai_client, process_name: str, step_id: str, description: str, 
                             decision: str, success_outcome: str, failure_outcome: str, verbose: bool = False) -> str:
    """Generate suggested validation rules for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        decision: The decision question for the step
        success_outcome: The success outcome description
        failure_outcome: The failure outcome description
        verbose: Whether to log detailed responses
        
    Returns:
        A generated set of validation rules or empty string if generation fails
    """
    if not openai_client:
        return ""
    
    try:
        # Build context for the prompt
        context = (
            f"Process: {process_name}\n"
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

        response = openai_client.chat.completions.create(
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
        
        validation_rules = '\n'.join(formatted_rules)
        
        if verbose:
            log.debug(f"Generated validation rules for {step_id}: {validation_rules[:50]}...")
            
        return validation_rules
    except Exception as e:
        log.error(f"Error generating validation rules suggestion: {str(e)}")
        return ""

def generate_error_codes(openai_client, process_name: str, step_id: str, description: str, 
                        decision: str, success_outcome: str, failure_outcome: str, verbose: bool = False) -> str:
    """Generate suggested error codes for a step using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        description: The description of the step
        decision: The decision question for the step
        success_outcome: The success outcome description
        failure_outcome: The failure outcome description
        verbose: Whether to log detailed responses
        
    Returns:
        A generated set of error codes or empty string if generation fails
    """
    if not openai_client:
        return ""
    
    try:
        # Sanitize inputs
        safe_process_name = sanitize_string(process_name)
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

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a process error handling expert. Provide clear, specific error codes for process steps."},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        error_codes = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated error codes for {step_id}: {error_codes[:50]}...")
            
        return error_codes
    except Exception as e:
        log.error(f"Error generating error codes suggestion: {str(e)}")
        return ""

def generate_executive_summary(openai_client, process_name: str, steps, notes, verbose: bool = False) -> str:
    """Generate an executive summary for the process using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        verbose: Whether to log detailed responses
        
    Returns:
        A generated executive summary or error message if generation fails
    """
    if not openai_client:
        return "AI executive summary is not available - OPENAI_API_KEY not found or invalid."
        
    try:
        # Create a detailed prompt for the executive summary
        prompt = (
            f"Create an executive summary for the {process_name} process. Here's the process information:\n\n"
            f"Process Steps:\n"
        )
        
        for step in steps:
            prompt += (
                f"Step {step.step_id}: {step.description}\n"
                f"- Decision: {step.decision}\n"
                f"- Success: {step.success_outcome}\n"
                f"- Failure: {step.failure_outcome}\n"
            )
            
            if step.note_id:
                try:
                    note = next(n for n in notes if n.note_id == step.note_id)
                    prompt += f"\n- Note: {note.content}"
                except StopIteration:
                    log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
                    prompt += f"\n- Note: [Referenced note {step.note_id} not found]"
                    
        if verbose:
            log.debug(f"Sending OpenAI prompt for executive summary: \n{prompt[:200]}...")
        
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a process documentation expert. Create clear, concise executive summaries for business processes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        summary = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Received OpenAI executive summary response")
        
        return summary
        
    except Exception as e:
        log.error(f"Error generating executive summary: {str(e)}")
        return f"Error generating executive summary: {str(e)}"

def parse_ai_suggestions(openai_client, suggestions: str) -> dict:
    """Parse AI suggestions into a structured format.
    
    Args:
        openai_client: The OpenAI client instance
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

        response = openai_client.chat.completions.create(
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
        log.error(f"Error parsing AI suggestions: {str(e)}")
        return suggested_updates

def evaluate_step_design(openai_client, process_name: str, step) -> str:
    """Evaluate a step design and provide feedback using OpenAI.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step: The ProcessStep object to evaluate
        
    Returns:
        A design evaluation or error message if evaluation fails
    """
    if not openai_client:
        return "AI evaluation is not available - OPENAI_API_KEY not found or invalid."
        
    try:
        # Rewrite the prompt with proper string formatting
        prompt = (
            f"Evaluate the following process step design:\n\n"
            f"Process Name: {process_name}\n"
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

        response = openai_client.chat.completions.create(
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

def generate_step_title(openai_client, process_name: str, step_id: str, predecessor_id: str, 
                       path_type: str, steps, verbose: bool = False) -> str:
    """Generate an intelligent step title based on context.
    
    Args:
        openai_client: The OpenAI client instance
        process_name: The name of the process
        step_id: The current step ID
        predecessor_id: The ID of the step that references this step
        path_type: Either 'success' or 'failure' indicating which path led here
        steps: List of ProcessStep objects
        verbose: Whether to log detailed responses
        
    Returns:
        A generated step title or the original step_id if generation fails
    """
    if not openai_client:
        return step_id
        
    try:
        # Get predecessor step details
        predecessor = next((s for s in steps if s.step_id == predecessor_id), None)
        if not predecessor:
            return step_id
            
        # Sanitize strings to prevent syntax errors from unescaped single quotes
        safe_process_name = sanitize_string(process_name)
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

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a business process expert. Create clear, concise step titles that follow best practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        title = response.choices[0].message.content.strip()
        
        if verbose:
            log.debug(f"Generated step title: {title}")
            
        return title
    except Exception as e:
        log.error(f"Error generating step title: {str(e)}")
        return step_id
