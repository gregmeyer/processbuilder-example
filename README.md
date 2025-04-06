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

## Installation

```bash
pip install processbuilder
```

## Usage

### Interactive Mode

1. Run the process builder:
   ```bash
   processbuilder
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
   processbuilder --steps-csv path/to/steps.csv --notes-csv path/to/notes.csv
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

## Dependencies

- Python 3.8+
- OpenAI API (for AI suggestions)
- python-dotenv (for environment variables)
- pandas (for CSV handling)
- mermaid-cli (for diagram generation)

## License

MIT License 