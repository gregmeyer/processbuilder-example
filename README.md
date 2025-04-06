# Process Builder

A tool for building structured process definitions through interactive interviews. Generates both CSV output and LLM prompts for process documentation.

## Features

- Interactive interview process for building step-by-step workflows
- AI-powered step design evaluation
- CSV export for process steps and notes
- Mermaid diagram generation for visual process flow
- LLM prompt generation for process documentation
- Step title management and step selection
- Validation of process flow and step references

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/processbuilder.git
cd processbuilder

# Install the package
pip install -e .
```

## Usage

### Interactive Mode

Run the process builder in interactive mode:

```bash
processbuilder
```

The tool will guide you through:
1. Entering the process name
2. For each step:
   - Step title (e.g., "User Authentication", "Data Validation")
   - Step description
   - Decision point
   - Success and failure outcomes
   - Optional notes
   - Next step selection (choose from existing steps or create new)
   - Optional validation rules, error codes, and retry logic
3. AI evaluation of step design
4. Option to modify steps based on feedback
5. Generation of outputs (CSV, Mermaid diagram, LLM prompt)

### CSV Import Mode

Import process steps and notes from CSV files:

```bash
processbuilder --steps-csv path/to/steps.csv --notes-csv path/to/notes.csv
```

## Output Files

The tool generates the following files in a timestamped directory:

- `{process_name}_process.csv`: Process steps in CSV format
- `{process_name}_notes.csv`: Process notes in CSV format
- `{process_name}_diagram.mmd`: Mermaid diagram of the process flow
- `{process_name}_prompt.txt`: LLM prompt for process documentation

## CSV Format

### Process Steps CSV

```csv
Step ID,Description,Decision,Success Outcome,Failure Outcome,Linked Note ID,Next Step (Success),Next Step (Failure),Validation Rules,Error Codes,Retry Logic
```

### Notes CSV

```csv
Note ID,Content,Related Step ID
```

## Step Selection

When defining next steps in the process, you can:
1. Enter a number corresponding to an existing step
2. Enter a new step name
3. Enter 'End' to finish the process

The tool will show a numbered list of existing steps to help with selection.

## Requirements

- Python 3.8+
- OpenAI API key (for AI evaluation features)

## Configuration

Create a `.env` file in the project root with your OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
```

## License

MIT License 