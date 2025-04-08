"""Process Output Generator module for generating various output formats."""

import os
import csv
import logging
from typing import List, Optional
import requests
from .base import ProcessStep, ProcessNote
from ..utils import sanitize_string, setup_output_directory
import base64

log = logging.getLogger(__name__)

class ProcessOutputGenerator:
    """Handles generation of various output formats."""
    
    def __init__(self, openai_client):
        """Initialize the ProcessOutputGenerator.
        
        Args:
            openai_client: The OpenAI client to use for generation
        """
        self.openai_client = openai_client
    
    def generate_csv(
        self,
        steps: List[ProcessStep],
        notes: List[ProcessNote],
        process_name: str,
        timestamp: str,
        base_output_dir: Optional[str] = None,
        default_output_dir: str = "output"
    ) -> str:
        """Generate a CSV file from process steps and notes.
        
        Args:
            steps: List of ProcessSteps
            notes: List of ProcessNotes
            process_name: Name of the process
            timestamp: Timestamp string
            base_output_dir: Optional base output directory
            default_output_dir: Default output directory name
            
        Returns:
            Path to the generated CSV file
        """
        try:
            # Setup output directory
            output_dir = setup_output_directory(
                process_name=process_name,
                timestamp=timestamp,
                base_dir=base_output_dir,
                default_output_dir=default_output_dir
            )
            
            # Generate CSV file path
            csv_file = os.path.join(output_dir, f"{process_name}_steps.csv")
            
            # Write steps to CSV
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID',
                    'Description',
                    'Decision',
                    'Success Outcome',
                    'Failure Outcome',
                    'Next Step (Success)',
                    'Next Step (Failure)',
                    'Validation Rules',
                    'Error Codes'
                ])
                
                for step in steps:
                    writer.writerow([
                        step.id,
                        step.description,
                        step.decision,
                        step.success_outcome,
                        step.failure_outcome,
                        step.next_step_success,
                        step.next_step_failure,
                        step.validation_rules,
                        step.error_codes
                    ])
                    
            # Write notes to separate CSV
            notes_file = os.path.join(output_dir, f"{process_name}_notes.csv")
            with open(notes_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Step ID', 'Note'])
                for note in notes:
                    writer.writerow([note.step_id, note.text])
                    
            return csv_file
            
        except Exception as e:
            log.error(f"Error generating CSV: {str(e)}")
            return ""
    
    def generate_mermaid_diagram(
        self,
        steps: List[ProcessStep],
        notes: List[ProcessNote],
        process_name: str,
        timestamp: str,
        output_dir: str,
        base_output_dir: Optional[str] = None,
        default_output_dir: str = "output"
    ) -> str:
        """Generate a Mermaid diagram from process steps and notes.
        
        Args:
            steps: List of ProcessSteps
            notes: List of ProcessNotes
            process_name: Name of the process
            timestamp: Timestamp string
            output_dir: Output directory path
            base_output_dir: Optional base output directory
            default_output_dir: Default output directory name
            
        Returns:
            Generated Mermaid diagram as string
        """
        try:
            # Setup output directory
            output_dir = setup_output_directory(
                process_name=process_name,
                timestamp=timestamp,
                base_dir=base_output_dir,
                default_output_dir=default_output_dir
            )
            
            # Create mapping from step IDs to sanitized Mermaid node IDs
            node_ids = {}
            for step in steps:
                # Sanitize the step ID to be Mermaid-safe - replace spaces with underscores
                # and ensure it starts with a letter
                safe_id = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in step.id)
                safe_id = safe_id.replace(' ', '_')
                if not safe_id[0].isalpha():
                    safe_id = 'n' + safe_id
                node_ids[step.id] = safe_id
                
            # Build the diagram
            diagram = ["graph TD"]
            
            # Add Start node
            diagram.append("    Start([Start])")
            
            # Add nodes
            for step in steps:
                safe_id = node_ids[step.id]
                # Escape quotes in description and ensure it's properly formatted
                description = step.description.replace('"', '\\"')
                diagram.append(f'    {safe_id}["{description}"]')
                
            # Add edges
            for step in steps:
                safe_id = node_ids[step.id]
                
                # Add success edge
                if step.next_step_success:
                    safe_success = node_ids[step.next_step_success]
                    success_label = step.success_outcome.replace('"', '\\"')
                    diagram.append(f'    {safe_id} -->|"{success_label}"| {safe_success}')
                
                # Add failure edge
                if step.next_step_failure:
                    safe_failure = node_ids[step.next_step_failure]
                    failure_label = step.failure_outcome.replace('"', '\\"')
                    diagram.append(f'    {safe_id} -.->|"{failure_label}"| {safe_failure}')
                
            # Add notes as subgraphs
            for note in notes:
                if note.step_id in node_ids:
                    safe_id = node_ids[note.step_id]
                    note_text = note.text.replace('"', '\\"')
                    diagram.append(f'    subgraph {safe_id}_notes')
                    diagram.append(f'        {safe_id}_note["{note_text}"]')
                    diagram.append(f'    end')
                    diagram.append(f'    {safe_id} --> {safe_id}_note')
                    
            # Join lines and save to file
            diagram_text = "\n".join(diagram)
            mmd_file = os.path.join(output_dir, f"{process_name}_diagram.mmd")
            with open(mmd_file, 'w') as f:
                f.write(diagram_text)
                
            return diagram_text
            
        except Exception as e:
            log.error(f"Error generating Mermaid diagram: {str(e)}")
            return ""
    
    def generate_png_diagram(
        self,
        mermaid_diagram: str,
        process_name: str,
        timestamp: str,
        output_dir: str,
        base_output_dir: Optional[str] = None,
        default_output_dir: str = "output"
    ) -> str:
        """Generate a PNG image from a Mermaid diagram.
        
        Args:
            mermaid_diagram: Mermaid diagram text
            process_name: Name of the process
            timestamp: Timestamp string
            output_dir: Output directory path
            base_output_dir: Optional base output directory
            default_output_dir: Default output directory name
            
        Returns:
            Path to the generated PNG file
        """
        try:
            # Setup output directory
            output_dir = setup_output_directory(
                process_name=process_name,
                timestamp=timestamp,
                base_dir=base_output_dir,
                default_output_dir=default_output_dir
            )
            
            # Generate PNG file path
            png_file = os.path.join(output_dir, f"{process_name}_diagram.png")
            
            # Encode diagram for URL using base64
            encoded_diagram = base64.b64encode(mermaid_diagram.encode('utf-8')).decode('ascii')
            
            # Generate URL for Mermaid.INK API
            url = f"https://mermaid.ink/img/{encoded_diagram}"
            
            # Download the image
            response = requests.get(url)
            if response.status_code == 200:
                with open(png_file, 'wb') as f:
                    f.write(response.content)
                return png_file
            else:
                log.error(f"Error generating PNG: HTTP {response.status_code}")
                return ""
                
        except Exception as e:
            log.error(f"Error generating PNG: {str(e)}")
            return ""
    
    def generate_llm_prompt(
        self,
        steps: List[ProcessStep],
        notes: List[ProcessNote],
        process_name: str,
        timestamp: str,
        base_output_dir: Optional[str] = None,
        default_output_dir: str = "output"
    ) -> str:
        """Generate a prompt for the LLM.
        
        Args:
            steps: List of ProcessSteps
            notes: List of ProcessNotes
            process_name: Name of the process
            timestamp: Timestamp string
            base_output_dir: Optional base output directory
            default_output_dir: Default output directory name
            
        Returns:
            Path to the generated prompt file
        """
        try:
            # Setup output directory
            output_dir = setup_output_directory(
                process_name=process_name,
                timestamp=timestamp,
                base_dir=base_output_dir,
                default_output_dir=default_output_dir
            )
            
            # Generate prompt
            prompt = [f"Process: {process_name}\n"]
            
            # Add steps
            prompt.append("\nSteps:")
            for step in steps:
                prompt.append(f"\nStep {step.id}:")
                prompt.append(f"Description: {step.description}")
                prompt.append(f"Decision: {step.decision}")
                prompt.append(f"Success Outcome: {step.success_outcome}")
                prompt.append(f"Failure Outcome: {step.failure_outcome}")
                prompt.append(f"Next Step (Success): {step.next_step_success}")
                prompt.append(f"Next Step (Failure): {step.next_step_failure}")
                if step.validation_rules:
                    prompt.append(f"Validation Rules: {step.validation_rules}")
                if step.error_codes:
                    prompt.append(f"Error Codes: {step.error_codes}")
                    
            # Add notes
            if notes:
                prompt.append("\nNotes:")
                for note in notes:
                    prompt.append(f"\nStep {note.step_id}: {note.text}")
                    
            # Write prompt to file
            prompt_file = os.path.join(output_dir, f"{process_name}_prompt.txt")
            with open(prompt_file, 'w') as f:
                f.write('\n'.join(prompt))
                
            return prompt_file
            
        except Exception as e:
            log.error(f"Error generating LLM prompt: {str(e)}")
            return ""
    
    def generate_executive_summary(
        self,
        process_name: str,
        steps: List[ProcessStep],
        notes: List[ProcessNote],
        timestamp: str,
        base_output_dir: Optional[str] = None,
        default_output_dir: str = "output",
        verbose: bool = True
    ) -> str:
        """Generate an executive summary of the process.
        
        Args:
            process_name: Name of the process
            steps: List of ProcessSteps
            notes: List of ProcessNotes
            timestamp: Timestamp string
            base_output_dir: Optional base output directory
            default_output_dir: Default output directory name
            verbose: Whether to include detailed information
            
        Returns:
            Path to the generated summary file
        """
        try:
            # Setup output directory
            output_dir = setup_output_directory(
                process_name=process_name,
                timestamp=timestamp,
                base_dir=base_output_dir,
                default_output_dir=default_output_dir
            )
            
            # Generate summary
            summary = [f"# Executive Summary: {process_name}\n"]
            
            # Add overview
            summary.append("## Process Overview")
            summary.append(f"This process consists of {len(steps)} steps and {len(notes)} notes.\n")
            
            # Add step summaries
            summary.append("## Step Summaries")
            for step in steps:
                summary.append(f"### {step.id}")
                summary.append(f"- **Description**: {step.description}")
                summary.append(f"- **Decision**: {step.decision}")
                summary.append(f"- **Success Path**: {step.next_step_success}")
                summary.append(f"- **Failure Path**: {step.next_step_failure}")
                if verbose:
                    if step.validation_rules:
                        summary.append(f"- **Validation Rules**: {step.validation_rules}")
                    if step.error_codes:
                        summary.append(f"- **Error Codes**: {step.error_codes}")
                summary.append("")
                
            # Add notes if any exist
            if notes:
                summary.append("## Process Notes")
                for note in notes:
                    summary.append(f"### Note for {note.step_id}")
                    summary.append(f"{note.text}\n")
                    
            # Write summary to file
            summary_file = os.path.join(output_dir, f"{process_name}_summary.md")
            with open(summary_file, 'w') as f:
                f.write('\n'.join(summary))
                
            return summary_file
            
        except Exception as e:
            log.error(f"Error generating executive summary: {str(e)}")
            return "" 