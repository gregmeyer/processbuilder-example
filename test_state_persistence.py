#!/usr/bin/env python3
"""
Test script for ProcessBuilder state persistence.

This script tests the automatic state persistence functionality:
1. Creates a ProcessBuilder instance
2. Adds a step
3. Verifies the state is saved
4. Creates a new ProcessBuilder instance
5. Verifies the state is loaded correctly
"""

import os
import json
import shutil
from pathlib import Path
from src.processbuilder.builder import ProcessBuilder
from src.processbuilder.models import ProcessStep

def print_section(title):
    """Print a section title with separator lines."""
    print("\n======================================================================\n")
    print(f"STEP {title}")

def cleanup_test_state():
    """Remove any existing test state files.
    
    This function checks for the .processbuilder directory and deletes
    any TestProcess.json file that exists to ensure a clean testing environment.
    """
    state_dir = Path(".processbuilder")
    if state_dir.exists():
        try:
            test_state_file = state_dir / "TestProcess.json"
            if test_state_file.exists():
                os.remove(test_state_file)
                print(f"Removed existing test state file: {test_state_file}")
        except Exception as e:
            print(f"Error removing test state: {e}")

def main():
    # Clean up any existing test state
    cleanup_test_state()
    
    # STEP 1: Create a ProcessBuilder instance
    print_section("1: Create a ProcessBuilder instance with a test process")
    builder = ProcessBuilder("TestProcess")
    print(f"Created ProcessBuilder instance for process: {builder.process_name}")
    
    # STEP 2: Add a step to the process
    print_section("2: Add a single step to the process")
    test_step = ProcessStep(
        step_id="FirstStep",
        description="This is a test step for state persistence",
        decision="Does this step complete successfully?",
        success_outcome="The step completed successfully",
        failure_outcome="The step failed",
        note_id=None,
        next_step_success="End",
        next_step_failure="End",
        validation_rules=None,
        error_codes=None
    )
    
    # Add the step to the builder
    builder.add_step(test_step, interactive=False)
    print(f"Added step: {test_step.step_id}")
    
    # STEP 3: Verify the state was saved
    print_section("3: Verify the state was saved")
    state_file = Path(".processbuilder/TestProcess.json")
    
    if state_file.exists():
        print(f"State file exists: {state_file}")
        
        # Read the state file
        with open(state_file, "r") as f:
            state_data = json.load(f)
            
        # Verify the state data
        print("State data contains:")
        print(f"  - Process name: {state_data.get('process_name')}")
        print(f"  - Number of steps: {len(state_data.get('steps', []))}")
        print(f"  - Step IDs: {[step.get('step_id') for step in state_data.get('steps', [])]}")
    else:
        print(f"ERROR: State file does not exist: {state_file}")
        return
    
    # STEP 4: Create a new ProcessBuilder instance to test loading
    print_section("4: Create a new ProcessBuilder instance and verify state loading")
    new_builder = ProcessBuilder("TestProcess")
    print(f"Created new ProcessBuilder instance for process: {new_builder.process_name}")
    
    # STEP 5: Verify the loaded state matches the original
    print_section("5: Verify the loaded state matches the original")
    
    if len(new_builder.steps) == len(builder.steps):
        print(f"✅ State loaded successfully! Found {len(new_builder.steps)} steps.")
        
        # Compare the steps in detail
        print("\nComparing original and loaded steps:")
        
        original_step = builder.steps[0]
        loaded_step = new_builder.steps[0]
        
        all_match = True
        
        print(f"Original step ID: {original_step.step_id}")
        print(f"Loaded step ID: {loaded_step.step_id}")
        id_match = original_step.step_id == loaded_step.step_id
        print(f"Match: {id_match}")
        all_match = all_match and id_match
        
        print(f"Original description: {original_step.description}")
        print(f"Loaded description: {loaded_step.description}")
        desc_match = original_step.description == loaded_step.description
        print(f"Match: {desc_match}")
        all_match = all_match and desc_match
        
        print(f"\nAll fields match: {all_match}")
    else:
        print(f"❌ State loading failed. Expected {len(builder.steps)} steps, got {len(new_builder.steps)}.")
    
    print("\n======================================================================\n")
    print("Test completed!")

if __name__ == "__main__":
    main()
