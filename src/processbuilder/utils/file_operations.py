"""
Helper functions for file operations in the Process Builder.
"""
import csv
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..builder import ProcessBuilder

from ..models import ProcessStep, ProcessNote

def load_csv_data(file_path: Path) -> List[Dict[str, str]]:
    """Load data from a CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries with the CSV data
    """
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        handle_file_error(f"File not found: {file_path}")
    except Exception as e:
        handle_file_error(f"Error loading CSV file: {str(e)}")
    
    return []

def save_csv_data(data: List[Dict[str, Any]], filepath: Path) -> bool:
    """Save data to a CSV file.
    
    Args:
        data: List of dictionaries with data to save
        filepath: Path where to save the CSV
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not data:
            print("Warning: No data to save")
            return False
            
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Get fieldnames from first row
        fieldnames = list(data[0].keys())
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return True
    except Exception as e:
        print(f"Error saving CSV: {str(e)}")
        return False

def load_from_csv(builder: 'ProcessBuilder', steps_csv_path: Path, notes_csv_path: Optional[Path] = None) -> List[str]:
    """Load process steps and notes from CSV files.
    
    Args:
        builder: The ProcessBuilder instance
        steps_csv_path: Path to the CSV file with steps
        notes_csv_path: Optional path to the CSV file with notes
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Load steps from CSV
    try:
        with open(steps_csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                step = ProcessStep(
                    step_id=row["Step ID"],
                    description=row["Description"],
                    decision=row["Decision"],
                    success_outcome=row["Success Outcome"],
                    failure_outcome=row["Failure Outcome"],
                    note_id=row["Linked Note ID"] if row["Linked Note ID"] else None,
                    next_step_success=row["Next Step (Success)"],
                    next_step_failure=row["Next Step (Failure)"],
                    validation_rules=row["Validation Rules"] if row["Validation Rules"] else None,
                    error_codes=row["Error Codes"] if row["Error Codes"] else None,
                    retry_logic=row["Retry Logic"] if row["Retry Logic"] else None
                )
                issues = builder.add_step(step)
                if issues:
                    warnings.append(f"Issues found in step {step.step_id}: {', '.join(issues)}")
    except FileNotFoundError:
        handle_file_error(f"Steps CSV file not found: {steps_csv_path}")
    except Exception as e:
        handle_file_error(f"Error loading steps: {str(e)}")
    
    # Load notes from CSV if provided
    if notes_csv_path:
        try:
            with open(notes_csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    note = ProcessNote(
                        note_id=row["Note ID"],
                        content=row["Content"],
                        related_step_id=row["Related Step ID"]
                    )
                    issues = builder.add_note(note)
                    if issues:
                        warnings.append(f"Issues found in note {note.note_id}: {', '.join(issues)}")
        except FileNotFoundError:
            handle_file_error(f"Notes CSV file not found: {notes_csv_path}")
        except Exception as e:
            handle_file_error(f"Error loading notes: {str(e)}")
    
    return warnings

def handle_file_error(message: str) -> None:
    """Handle file operation errors.
    
    Args:
        message: Error message to display
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1) 