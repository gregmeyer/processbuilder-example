"""
Functions for generating various outputs from process steps and notes.
"""

from typing import List, Optional
from ..models.base import ProcessStep, ProcessNote
import os
import logging

log = logging.getLogger(__name__)

def generate_mermaid_diagram(steps: List[ProcessStep], start_step_id: str) -> str:
    """Generate a Mermaid diagram from the process steps."""
    diagram = ["graph TD"]
    
    # Add start node
    diagram.append("    Start([Start])")
    
    # Add all steps as nodes
    for step in steps:
        # Escape special characters in step ID
        safe_id = step.step_id.replace('"', '\\"')
        diagram.append(f'    {step.step_id}["{safe_id}"]')
    
    # Add paths from start to first step
    first_step = next((step for step in steps if step.step_id == start_step_id), None)
    if first_step:
        diagram.append(f"    Start --> {first_step.step_id}")
    
    # Add paths between steps
    for step in steps:
        if step.next_step_success:
            diagram.append(f"    {step.step_id} --> {step.next_step_success}")
        if step.next_step_failure:
            diagram.append(f"    {step.step_id} -.-> {step.next_step_failure}")
    
    return "\n".join(diagram)

def generate_executive_summary(steps: List[ProcessStep], notes: List[ProcessNote]) -> str:
    """Generate an executive summary from process steps and notes.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        
    Returns:
        Executive summary as a markdown string
    """
    summary = ["# Process Executive Summary\n"]
    
    # Add process overview
    summary.append("## Process Overview")
    summary.append(f"This process consists of {len(steps)} steps and {len(notes)} notes.\n")
    
    # Add step summaries
    summary.append("## Step Summaries")
    for step in steps:
        summary.append(f"### {step.step_id}")
        summary.append(f"- **Description**: {step.description}")
        summary.append(f"- **Decision**: {step.decision}")
        summary.append(f"- **Success Path**: {step.next_step_success}")
        summary.append(f"- **Failure Path**: {step.next_step_failure}\n")
    
    # Add notes if any exist
    if notes:
        summary.append("## Process Notes")
        for note in notes:
            summary.append(f"### Note for {note.step_id}")
            summary.append(f"{note.content}\n")
    
    return "\n".join(summary)

def generate_llm_prompt(steps: List[ProcessStep], notes: List[ProcessNote]) -> str:
    """Generate an LLM prompt from process steps and notes.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        
    Returns:
        LLM prompt as a string
    """
    prompt = ["Process Description:"]
    
    # Add step descriptions
    prompt.append("\nSteps:")
    for i, step in enumerate(steps, 1):
        prompt.append(f"{i}. {step.step_id}: {step.description}")
        prompt.append(f"   Decision: {step.decision}")
        prompt.append(f"   Success: {step.success_outcome} -> {step.next_step_success}")
        prompt.append(f"   Failure: {step.failure_outcome} -> {step.next_step_failure}\n")
    
    # Add notes if any exist
    if notes:
        prompt.append("\nAdditional Notes:")
        for note in notes:
            prompt.append(f"- {note.step_id}: {note.content}")
    
    return "\n".join(prompt)

def setup_output_directory(
    process_name: str,
    timestamp: str,
    base_dir: Optional[str] = None,
    default_output_dir: str = "output"
) -> str:
    """Set up the output directory for process files.
    
    Args:
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        base_dir: Optional base directory override
        default_output_dir: Default output directory name
        
    Returns:
        Path to the output directory
    """
    try:
        # Create base output directory if it doesn't exist
        if base_dir:
            output_dir = os.path.join(base_dir, default_output_dir)
        else:
            output_dir = default_output_dir
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Create process directory
        process_dir = os.path.join(output_dir, process_name)
        if not os.path.exists(process_dir):
            os.makedirs(process_dir)
            
        # Create timestamped subfolder
        timestamp_dir = os.path.join(process_dir, timestamp)
        if not os.path.exists(timestamp_dir):
            os.makedirs(timestamp_dir)
            
        return timestamp_dir
        
    except Exception as e:
        log.error(f"Error setting up output directory: {str(e)}")
        return "" 