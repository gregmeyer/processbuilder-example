# Process Builder

A Python library for building and documenting process workflows through interactive interviews.

## Features

- Interactive process building through natural language interviews
- Automatic generation of process documentation in multiple formats:
  - Mermaid diagrams (`.mmd` and `.png`)
  - CSV files for steps and notes
  - Executive summaries
  - LLM prompts for process analysis
- Versioned output storage with timestamped directories
- Support for complex process flows with:
  - Success and failure paths
  - Decision points
  - Process notes
  - Validation rules
  - Error handling

## Installation

```bash
pip install processbuilder
```

## Usage

```python
from processbuilder import ProcessBuilder

# Initialize the process builder
builder = ProcessBuilder(process_name="make_a_sandwich")

# Start the interactive interview
builder.interview()

# Generate outputs
outputs = builder.generate_outputs()
```

## Output Structure

Process outputs are organized in timestamped directories:

```
output/
└── process_name/
    └── YYYYMMDD_HHMMSS/
        ├── process_name_steps.csv
        ├── process_name_notes.csv
        ├── process_name_diagram.mmd
        ├── process_name_diagram.png
        ├── process_name_prompt.txt
        └── process_name_summary.md
```

### Output Files

- **CSV Files**:
  - `process_name_steps.csv`: Contains all process steps with their descriptions, decisions, and outcomes
  - `process_name_notes.csv`: Contains all process notes with their associated steps

- **Mermaid Diagrams**:
  - `process_name_diagram.mmd`: Mermaid syntax diagram file
  - `process_name_diagram.png`: Rendered PNG image of the diagram (requires Mermaid.INK API)

- **Documentation**:
  - `process_name_prompt.txt`: LLM prompt for process analysis
  - `process_name_summary.md`: Executive summary of the process

## Mermaid Diagram Features

- Automatic node ID sanitization
- Proper handling of special characters in descriptions
- Support for success and failure paths
- Process notes as subgraphs
- Clean and readable diagram layout

## Requirements

- Python 3.8+
- OpenAI API key (for LLM features)
- Internet connection (for Mermaid.INK API)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 