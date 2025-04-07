# Process Builder

A tool for building structured process definitions through interactive interviews. Generates both CSV output and LLM prompts for process documentation.

## Features

- Interactive process building with AI-powered suggestions
- AI suggestions for:
  - Step titles and descriptions
  - Step decisions and outcomes
  - Success and failure paths
  - Validation rules and error codes
  - Concise step notes (10-20 words)
- Process validation and flow checking
- Multiple output formats:
  - CSV files for process steps and notes
  - Mermaid diagrams for visual representation
  - LLM prompts for documentation
  - Executive summaries
- Interactive menu system for:
  - Viewing all steps with flow connections
  - Editing existing steps
  - Adding new steps
  - Managing process flow
- Debug and verbose mode:
  - Toggle detailed logging for troubleshooting
  - View OpenAI API responses and request details
  - Monitor API key validation and warnings

## Project Structure

The ProcessBuilder application is organized in a modular architecture:

```
src/processbuilder/
├── __init__.py        # Package exports
├── builder.py         # Main ProcessBuilder class
├── models.py          # ProcessStep and ProcessNote models
├── config.py          # Configuration settings
└── utils/             # Utility modules
    ├── __init__.py    # Utility exports
    ├── ai_generation.py            # AI-related functionality
    ├── file_operations.py          # File handling utilities
    ├── input_handlers.py           # User input processing
    ├── interview_process.py        # Step creation workflow
    ├── output_generation.py        # Output file generation
    ├── process_management.py       # Process flow management
    ├── process_validation.py       # Step validation functions
    ├── state_management.py         # Process state persistence
    └── ui_helpers.py               # UI display functions
```

### Core Components

- **ProcessBuilder**: Orchestrates the process building workflow and delegates to utility functions
- **ProcessStep**: Represents individual steps in the process with validation logic
- **ProcessNote**: Represents notes attached to process steps
- **Config**: Handles configuration settings

### Utility Modules

- **ai_generation**: Handles OpenAI API interactions for generating suggestions
- **process_validation**: Validates process flow, steps, and connections
- **output_generation**: Generates CSV, Mermaid diagrams, and other outputs
- **state_management**: Persists and loads process state
- **input_handlers**: Manages user input collection and validation
- **ui_helpers**: Provides console UI functionality
- **file_operations**: Manages file I/O operations
- **interview_process**: Implements the interactive step creation workflow

## Configuration

### Verbose Mode

Process Builder includes a verbose mode for detailed logging and debugging:

```python
# Enable verbose mode at the class level
from processbuilder import ProcessBuilder
ProcessBuilder.set_verbose_mode(True)

# Enable verbose mode for a specific instance
builder = ProcessBuilder("My Process", verbose=True)
```

When verbose mode is enabled:

- Debug-level logs are displayed, showing detailed process information
- OpenAI API request and response details are logged
- Warning messages are always displayed regardless of verbose mode
- API key validation is logged and visible in the console

Example debug output with verbose mode enabled:

```
DEBUG - ProcessBuilder initialized with verbose=True
WARNING - No OpenAI API key found. AI features will be disabled.
DEBUG - Warning about missing API key has been logged
DEBUG - Sending OpenAI prompt for first step suggestion
DEBUG - Received OpenAI first step suggestion: 'Collect Customer Information'
```

## Installation

```bash
pip install processbuilder
```

## Usage

### Interactive Mode

1. Run the process builder:
   ```bash
   # Basic usage
   processbuilder
   
   # Run with verbose mode enabled
   processbuilder --verbose
   ```

2. Enter the process name when prompted.
3. For each step, you'll be guided through:
   - Step title (with AI suggestion for first step)
   - Step description (with AI suggestion)
   - Decision point (with AI suggestion)
   - Success outcome (with AI suggestion)
   - Failure outcome (with AI suggestion)
   - Next steps for both paths (with AI suggestions)
   - Optional note (with AI suggestion)
   - Optional validation rules (with AI suggestion)
   - Optional error codes (with AI suggestion)

4. After completing the process, you'll enter the interactive menu where you can:
   - View all steps with their flow connections
   - Edit any step's properties
   - Add new steps
   - Exit the process builder

### Step Viewing

When viewing steps, you'll see:
- Step title and description
- Decision and outcomes
- Predecessor steps (steps that lead to this step)
- Successor steps (next steps for both success and failure paths)
- Concise notes (10-20 words), validation rules, and error codes
- Clear visual separation between steps

Example step view:
```
Step 1: Verify Customer Information
Description: Check customer details against database
Decision: Is the customer information valid?
Success Outcome: Customer information is verified
Failure Outcome: Customer information is invalid

Predecessors: None (Start of process)

Successors:
  - Process Payment (Success)
  - Request Additional Information (Failure)

Note: Verify email and phone format
Validation Rules: Email format, phone number format
Error Codes: INVALID_EMAIL, INVALID_PHONE
--------------------------------------------------------------------------------
```

### Step Editing

You can edit any step's properties:
1. Title
2. Description
3. Decision
4. Success Outcome
5. Failure Outcome
6. Note
7. Validation Rules
8. Error Codes
9. Next Step (Success)
10. Next Step (Failure)

The process flow is validated after each edit to ensure consistency.

### CSV Import Mode

1. Prepare your CSV files:
   - One file for process steps
   - Optional file for process notes

2. Run the process builder with CSV files:
   ```bash
   # Basic import
   processbuilder --steps-csv path/to/steps.csv --notes-csv path/to/notes.csv
   
   # Import with verbose mode enabled
   processbuilder --steps-csv path/to/steps.csv --notes-csv path/to/notes.csv --verbose
   ```

3. The process will be loaded and you'll enter the interactive menu where you can:
   - View all steps
   - Edit steps as needed
   - Add new steps
   - Generate outputs

## Output Files

The process builder generates several output files in a structured directory format:

```
output/
└── process_name/
    └── YYYYMMDD_HHMMSS/
        ├── process_name_process.csv
        ├── process_name_notes.csv
        ├── process_name_diagram.mmd
        ├── process_name_prompt.txt
        └── process_name_executive_summary.md
```

### CSV Format

The process steps CSV includes:
- Step ID
- Description
- Decision
- Success Outcome
- Failure Outcome
- Linked Note ID
- Next Step (Success)
- Next Step (Failure)
- Validation Rules
- Error Codes
- Retry Logic

### Validation Rules

The process builder enforces several validation rules:
1. Step names must be unique
2. Next step references must be valid
3. Process must have at least one path to 'End'
4. No circular references allowed
5. All referenced steps must exist

### Error Codes

Common error codes include:
- INVALID_INPUT
- VALIDATION_FAILED
- PROCESS_ERROR
- TIMEOUT
- RETRY_EXCEEDED

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/processbuilder.git
cd processbuilder

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## Dependencies
- Python 3.8+
- OpenAI API (for AI suggestions)
- python-dotenv (for environment variables)
- pandas (for CSV handling)
- mermaid-cli (for diagram generation)
- logging (for verbose mode and debug output)

## License

MIT License 