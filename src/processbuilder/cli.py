"""
Command-line interface for the Process Builder.
"""
import argparse
import os
import sys
import time
from pathlib import Path

from .builder import ProcessBuilder
from .config import Config
from .utils.interview_process import run_interview
from .utils.input_handlers import get_step_input, prompt_for_confirmation
from .utils.ui_helpers import clear_screen, print_header, show_loading_animation, show_startup_animation
from .utils.file_operations import load_csv_data, save_csv_data
from .utils.process_management import view_all_steps, edit_step, generate_outputs

def main() -> None:
    """Main entry point for the process builder."""
    parser = argparse.ArgumentParser(description="Process Builder Utility")
    parser.add_argument("--steps-csv", help="Path to CSV file containing process steps")
    parser.add_argument("--notes-csv", help="Path to CSV file containing process notes")
    args = parser.parse_args()
    
    # Show startup animation at the beginning
    show_startup_animation(in_menu=False)
    
    print("Welcome to Process Builder! 🚀\n")
    
    # Get process name
    process_name = get_step_input("Enter the name of the process:")
    
    # Initialize builder with configuration
    config = Config(env_path=None)
    
    # Create ProcessBuilder with proper initialization
    builder = ProcessBuilder(process_name, config)
    
    # Determine if we're loading from CSV
    if args.steps_csv:
        steps_path = Path(args.steps_csv)
        notes_path = Path(args.notes_csv) if args.notes_csv else None
        load_from_csv(builder, steps_path, notes_path)
    
    # Main menu loop
    while True:
        try:
            # Show menu with process header
            clear_screen()
            print_header(f"Process Builder: {process_name}")
            
            choice = get_step_input("Choose an option:\n1. View all steps\n2. Edit a step\n3. Add steps\n4. Generate outputs\n5. Exit")
            
            if choice == "1":
                clear_screen()
                print_header(f"Process Builder: {process_name} - View Steps")
                view_all_steps(builder)
                input("\nPress Enter to return to menu...")
                
            elif choice == "2":
                clear_screen()
                print_header(f"Process Builder: {process_name} - Edit Step")
                edit_step(builder)
                input("\nPress Enter to return to menu...")
                
            elif choice == "3":
                # run_interview handles its own screen clearing and headers
                run_interview(builder)
                input("\nPress Enter to return to menu...")
                
            elif choice == "4":
                clear_screen()
                print_header(f"Process Builder: {process_name} - Generate Outputs")
                generate_outputs(builder)
                input("\nPress Enter to return to menu...")
                
            elif choice == "5":
                # Exit
                clear_screen()
                
                # Ask if they want to save before exiting
                save_before_exit = prompt_for_confirmation("Would you like to save your process before exiting?")
                if save_before_exit:
                    output_dir = get_step_input("Enter the output directory for saving the CSV file:")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"{builder.name}.csv")
                    
                    try:
                        # Convert the process to CSV format
                        csv_data = builder.to_csv()
                        if not csv_data:
                            print("Warning: No data to save. Process may be empty.")
                        else:
                            # Save the data
                            saved = save_csv_data(csv_data, output_path)
                            if saved:
                                print(f"Process saved to {output_path}")
                            else:
                                print("Failed to save the process.")
                    except AttributeError as e:
                        print(f"Error: Unable to save process. {str(e)}")
                        print("This may be due to a missing method or attribute. Please contact support.")
                    except Exception as e:
                        print(f"Error while saving: {str(e)}")
                
                print("\nExiting Process Builder. Thank you for using our tool!")
                break
                
            else:
                # Invalid choice - show error and wait
                clear_screen()
                print_header(f"Process Builder: {process_name}")
                print("\nInvalid choice. Please try again.")
                input("\nPress Enter to return to menu...")
                
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            clear_screen()
            print("\nOperation interrupted. Returning to main menu...")
            time.sleep(1)  # Brief pause to show the message


def load_from_csv(builder: ProcessBuilder, steps_csv_path: Path, notes_csv_path: Path = None) -> None:
    """Load process data from CSV files into the builder.
    
    Args:
        builder: The ProcessBuilder instance to load data into
        steps_csv_path: Path to the steps CSV file
        notes_csv_path: Optional path to the notes CSV file
    """
    try:
        # Load steps from CSV
        steps_data = load_csv_data(steps_csv_path)
        if steps_data:
            for row in steps_data:
                # Add steps to the builder
                issues = builder.add_step_from_dict(row)
                if issues:
                    print(f"\nWarning: Issues found in step {row.get('Step ID', 'Unknown')}:")
                    for issue in issues:
                        print(f"- {issue}")
        else:
            print(f"Error: Could not load data from steps CSV file: {steps_csv_path}")
            sys.exit(1)
        
        # Load notes from CSV if provided
        if notes_csv_path:
            notes_data = load_csv_data(notes_csv_path)
            if notes_data:
                for row in notes_data:
                    # Add notes to the builder
                    issues = builder.add_note_from_dict(row)
                    if issues:
                        print(f"\nWarning: Issues found in note {row.get('Note ID', 'Unknown')}:")
                        for issue in issues:
                            print(f"- {issue}")
            else:
                print(f"Error: Could not load data from notes CSV file: {notes_csv_path}")
                sys.exit(1)
    
    except Exception as e:
        print(f"Error loading CSV data: {str(e)}")
        sys.exit(1)
