# Process Builder

A tool for building, documenting, and improving business processes using AI-powered assistance.

## Overview

The Process Builder helps teams create, document, and improve their business processes through an interactive interview process. It combines human expertise with AI-powered insights to create better processes and documentation.

Key features:
- Interactive process discovery
- AI-powered step evaluation
- Multiple output formats (CSV, Mermaid diagrams, Markdown)
- Continuous improvement through feedback loops

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/process-builder.git
cd process-builder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

Run the process builder:
```bash
python process_builder.py
```

### Command Line Arguments

- `--steps-csv`: Path to CSV file containing process steps
- `--notes-csv`: Path to CSV file containing process notes
- `--import-original`: Import from original format CSV instead of current format

Example:
```bash
python process_builder.py --steps-csv path/to/steps.csv --notes-csv path/to/notes.csv
```

## Security Considerations

1. **API Keys**: 
   - Never commit your `.env` file
   - Keep your OpenAI API key secure
   - The tool will work without an API key, but AI features will be disabled

2. **Data Handling**:
   - The tool processes data locally
   - No data is stored permanently
   - CSV files are handled safely with proper validation

3. **File Operations**:
   - Output files are created in the specified directory
   - Input files are validated before processing
   - Proper error handling for file operations

## Output Formats

The tool generates three types of output:

1. **CSV Files**:
   - Process steps in structured format
   - Optional notes for each step
   - Easy to import into other tools

2. **Mermaid Diagrams**:
   - Visual representation of the process
   - Interactive flow diagrams
   - Easy to share with teams

3. **Markdown Documentation**:
   - Executive summaries
   - Step-by-step instructions
   - Process improvements and notes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository. 