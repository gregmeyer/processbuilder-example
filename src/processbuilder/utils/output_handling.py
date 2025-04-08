"""Output handling utilities for ProcessBuilder."""

import logging
import json
import csv
import base64
import requests
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from ..models import ProcessStep, ProcessNote

log = logging.getLogger(__name__)

def write_csv(data: List[Dict[str, Any]], filepath: Path, fieldnames: List[str]) -> None:
    """Write data to a CSV file.
    
    Args:
        data: List of dictionaries with data to write
        filepath: Path to output CSV file
        fieldnames: List of column headers
    """
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def sanitize_id(id_str: str) -> str:
    """Sanitize a string to make it a valid Mermaid ID.
    
    Args:
        id_str: String to sanitize
        
    Returns:
        A sanitized ID string that is valid for Mermaid diagrams
    """
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

def setup_output_directory(process_name: str, timestamp: str, base_dir: Optional[Path] = None, 
                          default_output_dir: Optional[Path] = None) -> Path:
    """Set up the output directory structure for this run.
    
    Args:
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        base_dir: Optional base directory override
        default_output_dir: Default output directory to use if base_dir is None
        
    Returns:
        Path to the created output directory
    """
    base_dir = base_dir or default_output_dir or Path("output")
    output_dir = base_dir / process_name / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def generate_mermaid_diagram(steps: List[ProcessStep]) -> str:
    """Generate a Mermaid flowchart diagram from process steps.
    
    Args:
        steps: List of ProcessSteps
        
    Returns:
        Mermaid diagram as a string
    """
    diagram = ["graph TD"]
    
    # Add Start node
    diagram.append("    Start[Start]")
    
    # Add each step
    for step in steps:
        # Add step node
        diagram.append(f"    {step.step_id}[{step.description}]")
        
        # Add success path
        if step.next_step_success:
            diagram.append(f"    {step.step_id} -->|{step.success_outcome}| {step.next_step_success}")
        else:
            diagram.append(f"    {step.step_id} -->|{step.success_outcome}| End")
            
        # Add failure path
        if step.next_step_failure:
            diagram.append(f"    {step.step_id} -->|{step.failure_outcome}| {step.next_step_failure}")
        else:
            diagram.append(f"    {step.step_id} -->|{step.failure_outcome}| End")
    
    # Add End node
    diagram.append("    End[End]")
    
    return "\n".join(diagram)

def export_to_json(steps: List[ProcessStep], notes: List[ProcessNote], file_path: str) -> None:
    """Export process data to JSON file.
    
    Args:
        steps: List of ProcessSteps
        notes: List of ProcessNotes
        file_path: Path to save JSON file
    """
    try:
        data = {
            "steps": [step.to_dict() for step in steps],
            "notes": [note.to_dict() for note in notes]
        }
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
        log.info(f"Exported process data to {file_path}")
        
    except Exception as e:
        log.error(f"Error exporting to JSON: {str(e)}")
        raise

def export_to_csv(steps: List[ProcessStep], notes: List[ProcessNote], file_path: str) -> None:
    """Export process data to CSV file.
    
    Args:
        steps: List of ProcessSteps
        notes: List of ProcessNotes
        file_path: Path to save CSV file
    """
    try:
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Write steps
            writer.writerow(["Step ID", "Description", "Decision", "Success Outcome", "Failure Outcome", "Next Step Success", "Next Step Failure"])
            for step in steps:
                writer.writerow([
                    step.step_id,
                    step.description,
                    step.decision,
                    step.success_outcome,
                    step.failure_outcome,
                    step.next_step_success,
                    step.next_step_failure
                ])
            
            # Write notes
            writer.writerow([])  # Blank line
            writer.writerow(["Note ID", "Step ID", "Content"])
            for note in notes:
                writer.writerow([note.note_id, note.step_id, note.content])
            
        log.info(f"Exported process data to {file_path}")
        
    except Exception as e:
        log.error(f"Error exporting to CSV: {str(e)}")
        raise

def generate_mermaid_image(diagram: str, api_key: str) -> bytes:
    """Generate a Mermaid diagram image using the Mermaid API.
    
    Args:
        diagram: Mermaid diagram as a string
        api_key: Mermaid API key
        
    Returns:
        Image data as bytes
    """
    try:
        # Encode diagram for URL
        encoded_diagram = base64.b64encode(diagram.encode()).decode()
        
        # Make API request
        response = requests.post(
            "https://mermaid.ink/img",
            json={
                "code": encoded_diagram,
                "mermaid": {"theme": "default"}
            },
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.text}")
            
        return response.content
        
    except Exception as e:
        log.error(f"Error generating Mermaid image: {str(e)}")
        raise

def generate_csv(steps: List[ProcessStep], notes: List[ProcessNote], process_name: str, timestamp: str, 
                base_output_dir: Optional[Path] = None, 
                default_output_dir: Optional[Path] = None) -> Path:
    """Generate CSV files for the process.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        base_output_dir: Optional base directory override
        default_output_dir: Default output directory if base_output_dir is None
        
    Returns:
        Path to the output directory containing generated files
    """
    output_dir = setup_output_directory(process_name, timestamp, 
                                       base_output_dir, default_output_dir)
    
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
        for step in steps
    ]
    
    steps_file = output_dir / f"{process_name}_process.csv"
    write_csv(steps_data, steps_file, list(steps_data[0].keys()) if steps_data else [])
    
    # Notes CSV
    if notes:
        notes_data = [
            {
                "Note ID": note.note_id,
                "Content": note.content,
                "Related Step ID": note.related_step_id
            }
            for note in notes
        ]
        
        notes_file = output_dir / f"{process_name}_notes.csv"
        write_csv(notes_data, notes_file, list(notes_data[0].keys()))
    
    print(f"\nCSV files generated in {output_dir}/")
    print(f"- Process steps: {steps_file}")
    if notes:
        print(f"- Notes: {notes_file}")
    
    return output_dir

def generate_llm_prompt(steps: List[ProcessStep], notes: List[ProcessNote], process_name: str) -> str:
    """Generate a prompt for LLM-based process analysis.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        
    Returns:
        A formatted prompt string for LLM analysis
    """
    prompt = f"""Analyze the following business process: {process_name}

Process Steps:
"""
    
    # Add each step
    for step in steps:
        prompt += f"""
Step ID: {step.step_id}
Description: {step.description}
Decision: {step.decision}
Success Outcome: {step.success_outcome}
Failure Outcome: {step.failure_outcome}
Next Step (Success): {step.next_step_success}
Next Step (Failure): {step.next_step_failure}
"""
        if step.validation_rules:
            prompt += f"Validation Rules: {step.validation_rules}\n"
        if step.error_codes:
            prompt += f"Error Codes: {step.error_codes}\n"
    
    # Add notes if any
    if notes:
        prompt += "\nProcess Notes:\n"
        for note in notes:
            prompt += f"""
Note ID: {note.note_id}
Related Step: {note.related_step_id}
Content: {note.content}
"""
    
    prompt += """
Please analyze this process and provide:
1. A summary of the process flow
2. Potential bottlenecks or inefficiencies
3. Suggestions for improvement
4. Any missing steps or unclear transitions
"""
    
    return prompt 

def save_outputs(steps: List[ProcessStep], notes: List[ProcessNote], process_name: str, timestamp: str,
                base_output_dir: Optional[Path] = None, 
                default_output_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Save all output files for the process.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        base_output_dir: Optional base directory override
        default_output_dir: Default output directory if base_output_dir is None
        
    Returns:
        Dictionary mapping output type to file path
    """
    output_dir = setup_output_directory(process_name, timestamp, 
                                       base_output_dir, default_output_dir)
    
    outputs = {}
    
    # Generate and save CSV files
    csv_dir = generate_csv(steps, notes, process_name, timestamp, 
                          base_output_dir, default_output_dir)
    outputs['csv'] = csv_dir
    
    # Generate and save Mermaid diagram
    mermaid_diagram = generate_mermaid_diagram(steps)
    mermaid_file = output_dir / f"{process_name}_diagram.mmd"
    mermaid_file.write_text(mermaid_diagram)
    outputs['mermaid'] = mermaid_file
    
    # Generate and save JSON
    json_file = output_dir / f"{process_name}_process.json"
    export_to_json(steps, notes, str(json_file))
    outputs['json'] = json_file
    
    return outputs 