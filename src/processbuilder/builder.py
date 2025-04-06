"""
Main ProcessBuilder class for building and managing processes.
"""
import os
from pathlib import Path
from typing import List, Optional
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
                print("Successfully connected to OpenAI API")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {str(e)}")
                print("AI evaluation features will be disabled.")
                self.openai_client = None
        else:
            self.openai_client = None

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
Retry Logic: {step.retry_logic or 'None'}

Please provide:
1. A brief assessment of the step's design
2. Potential improvements or considerations
3. Any missing elements that should be addressed
4. Specific recommendations for validation, error handling, or retry logic if not provided

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
                "Error Codes": step.error_codes,
                "Retry Logic": step.retry_logic
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
                if step.retry_logic:
                    prompt += f"- Retry Logic: {step.retry_logic}\n"
            
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
        
        while True:
            self.add_step()
            continue_process = self.get_step_input("Add another step? (y/n)").lower()
            if continue_process != 'y':
                break
        
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