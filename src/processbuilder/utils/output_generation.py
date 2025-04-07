"""
Functions for generating output files from process steps.
"""
import logging
import csv
from pathlib import Path
from typing import List, Optional, Dict, Any

# Setup logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Add a stream handler if none exists
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

def sanitize_id(id_str: str) -> str:
    """Sanitize a string to make it a valid Mermaid ID.
    
    Args:
        id_str: String to sanitize
        
    Returns:
        A sanitized ID string that is valid for Mermaid diagrams
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

def generate_csv(steps, notes, process_name: str, timestamp: str, 
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

def generate_mermaid_diagram(steps, notes, process_name: str, timestamp: str,
                            output_dir: Optional[Path] = None,
                            base_output_dir: Optional[Path] = None,
                            default_output_dir: Optional[Path] = None) -> str:
    """Generate a Mermaid diagram from the process steps.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        output_dir: Optional existing output directory
        base_output_dir: Optional base directory override
        default_output_dir: Default output directory if base_output_dir is None
        
    Returns:
        The generated Mermaid diagram as a string
    """
    if not output_dir:
        output_dir = setup_output_directory(process_name, timestamp, 
                                          base_output_dir, default_output_dir)
        
    mermaid_file = output_dir / f"{process_name}_diagram.mmd"
    
    # Start the diagram
    diagram = "```mermaid\ngraph TD\n"
    
    # Create a mapping from step_id to sanitized Mermaid node ID
    step_id_to_node_id = {}
    for step in steps:
        step_id_to_node_id[step.step_id] = f"Step_{sanitize_id(step.step_id)}"
    
    # Add nodes and edges
    for step in steps:
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
                note = next(n for n in notes if n.note_id == step.note_id)
                note_id = f"Note_{sanitize_id(step.step_id)}"
                diagram += f"    {note_id}[\"{note.content}\"]\n"
                diagram += f"    {safe_id} -.-> {note_id}\n"
            except StopIteration:
                # Note referenced by step wasn't found, log a warning and continue
                log.warning(f"Note {step.note_id} referenced by step {step.step_id} not found")
    
    # Add styling
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

def generate_llm_prompt(steps, notes, process_name: str) -> str:
    """Generate a prompt for an LLM to help document the process.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        
    Returns:
        A formatted prompt for an LLM
    """
    prompt = (
        f"I need help documenting the {process_name} process. Here's what I know so far:\n\n"
        f"Process Overview:\n"
        f"{process_name} is a workflow that handles the following steps:\n\n"
    )
    
    for step in steps:
        prompt += f"""
Step {step.step_id}: {step.description}
- Decision: {step.decision}
- Success: {step.success_outcome}
- Failure: {step.failure_outcome}
"""
        if step.note_id:
            try:
                note = next(n for n in notes if n.note_id == step.note_id)
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

def save_outputs(steps, notes, process_name: str, timestamp: str, executive_summary: str,
                output_dir: Optional[Path] = None,
                base_output_dir: Optional[Path] = None,
                default_output_dir: Optional[Path] = None) -> Path:
    """Generate and save all outputs for the process.
    
    Args:
        steps: List of ProcessStep objects
        notes: List of ProcessNote objects
        process_name: Name of the process
        timestamp: Timestamp string for uniqueness
        executive_summary: Executive summary text
        output_dir: Optional existing output directory
        base_output_dir: Optional base directory override
        default_output_dir: Default output directory if base_output_dir is None
        
    Returns:
        Path to the output directory containing generated files
    """
    # Ensure we have an output directory
    if not output_dir:
        output_dir = setup_output_directory(process_name, timestamp, 
                                          base_output_dir, default_output_dir)
    
    # Generate CSV files
    generate_csv(steps, notes, process_name, timestamp, output_dir=output_dir)
    
    # Generate Mermaid diagram
    generate_mermaid_diagram(steps, notes, process_name, timestamp, output_dir=output_dir)
    
    # Generate and save LLM prompt
    llm_prompt = generate_llm_prompt(steps, notes, process_name)
    prompt_file = output_dir / f"{process_name}_prompt.txt"
    prompt_file.write_text(llm_prompt)
    print(f"\nLLM prompt saved to: {prompt_file}")
    
    # Save executive summary
    summary_file = output_dir / f"{process_name}_executive_summary.md"
    summary_file.write_text(executive_summary)
    print(f"\nExecutive summary saved to: {summary_file}")
    
    return output_dir
