# Document Conversion Pipeline

A robust Python-based document conversion system with automated file rotation, staging areas, and comprehensive logging designed for AI research workflows and batch document processing.

## Features

- **Automatic File Rotation**: Intelligent staging system with queue, staging, and processing directories
- **Recursive Processing**: Preserves nested directory structures in output
- **Multiple Format Support**: PDF, DOCX, TXT, Markdown, HTML
- **Collision-Safe Naming**: Prevents filename conflicts with source-aware naming
- **Progress Tracking**: Real-time conversion progress with detailed statistics
- **Configuration Management**: YAML-based configuration with CLI overrides
- **Error Handling**: Automatic retry logic with comprehensive error reporting
- **Dry-Run Mode**: Preview operations without executing conversions
- **Atomic Operations**: Crash-safe file writes with automatic cleanup

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/document-conversion-pipeline.git
cd document-conversion-pipeline

# Install dependencies
pip install docling pyyaml

# Or using uv (recommended)
uv pip install docling pyyaml
```

### Basic Usage

```bash
# Generate default configuration
python docling-inputs2outputs.py --save-config

# Run conversion with default settings
python docling-inputs2outputs.py

# Preview operations without converting
python docling-inputs2outputs.py --dry-run

# Enable verbose logging
python docling-inputs2outputs.py --log-level DEBUG
```

## How It Works

### Directory Structure

```
.
├── inputs_queue/          # Drop new files here (awaits next-next run)
├── inputs_staging/        # Files staged for next run
├── inputs/                # Files being processed in current run
├── inputs_old_TIMESTAMP/  # Archived processed files
└── outputs/               # Converted documents
    ├── file1_from_pdf.md
    └── run_report_TIMESTAMP.txt
```

### Processing Flow

Each execution follows this sequence:

1. **Conversion Phase**: Process all files currently in `./inputs/`
2. **Rotation Phase** (after conversion):
   - Move `./inputs/` → `./inputs_old_{timestamp}/`
   - Move `./inputs_staging/` → `./inputs/`
   - Move `./inputs_queue/` → `./inputs_staging/`
   - Recreate empty directories

### Example Workflow

```bash
# Initial setup - place files in queue
cp document1.pdf inputs_queue/
cp document2.pdf inputs_staging/
cp document3.pdf inputs/

# First run: Processes document3.pdf
python docling-inputs2outputs.py
# Result: document3_from_pdf.md in outputs/
# document3.pdf moved to inputs_old_*/
# document2.pdf moved to inputs/
# document1.pdf moved to inputs_staging/

# Second run: Processes document2.pdf
python docling-inputs2outputs.py
# Result: document2_from_pdf.md in outputs/
# document2.pdf moved to inputs_old_*/
# document1.pdf moved to inputs/
```

## Configuration

### config.yaml

```yaml
# Input/output file types
input_types:
  - pdf
  - docx
output_types:
  - md
  - html

# Processing limits
max_file_size_mb: 100
retry_attempts: 2
retry_delay_seconds: 1.0

# Directory paths
directories:
  inputs: ./inputs
  outputs: ./outputs
  inputs_queue: ./inputs_queue
  inputs_staging: ./inputs_staging
```

### CLI Options

```bash
# Use custom configuration
python docling-inputs2outputs.py --config my_config.yaml

# Override directories
python docling-inputs2outputs.py --inputs ./my_inputs --outputs ./my_outputs

# Dry run with debug logging
python docling-inputs2outputs.py --dry-run --log-level DEBUG

# Save default configuration
python docling-inputs2outputs.py --save-config
```

## Output Format

### Collision-Safe Naming

Files are renamed to prevent collisions when multiple sources have the same basename:

```
report.pdf  → report_from_pdf.md
report.docx → report_from_docx.md
```

### Run Reports

Each execution generates a timestamped report in `outputs/`:

```
run_report_20250930_161031_118.txt
```

Contains:
- Configuration used
- Files processed
- Success/failure status
- Conversion statistics
- Runtime metrics

## Use Cases

### AI Research Workflows

- Batch convert research papers (PDF → Markdown) for LLM training data
- Process documentation for RAG systems
- Convert datasets while preserving directory structure

### Document Management

- Archive legacy documents with format migration
- Batch convert company documentation
- Automate document intake pipelines

### Benchmarking

- Process test datasets with consistent naming
- Track conversion statistics across runs
- Maintain audit trails with timestamped reports

## Advanced Features

### Recursive Processing

Automatically enabled - preserves nested directory structures:

```
inputs/
  ├── project_a/
  │   └── report.pdf
  └── project_b/
      └── analysis.pdf

outputs/
  ├── project_a/
  │   └── report_from_pdf.md
  └── project_b/
      └── analysis_from_pdf.md
```

### File Size Validation

Configure maximum file size to prevent memory issues:

```yaml
max_file_size_mb: 100  # Skip files larger than 100MB
```

### Automatic Retry

Failed conversions are automatically retried:

```yaml
retry_attempts: 2
retry_delay_seconds: 1.0
```

## Troubleshooting

### No files found

**Issue**: "Found 0 input files with allowed types"

**Solution**: Check that:
- Files are in `./inputs/` directory
- File extensions match `input_types` in config
- Directory names are correct (plural: `inputs_queue` not `input_queue`)

### Import errors

**Issue**: "ERROR: docling package not found"

**Solution**:
```bash
pip install docling
```

### Path errors

**Issue**: "'file.pdf' is not in the subpath"

**Solution**: Ensure you're running the script from the project root directory.

### Double logging

**Issue**: Each log line appears twice

**Solution**: This is a known cosmetic issue and doesn't affect functionality.

## Requirements

- Python 3.8+
- docling
- PyYAML
- pathlib (built-in)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/document-conversion-pipeline/issues)
- **Documentation**: See `USER_GUIDE.md` for detailed usage
- **Technical Details**: See `TECHNICAL_DOCS.md` for architecture

## Changelog

### v2.0.0 (2025-09-30)
- Complete rewrite with rotation system
- Added YAML configuration support
- Recursive processing with structure preservation
- Collision-safe filename generation
- Comprehensive error handling and retry logic
- Dry-run mode
- Progress reporting and statistics
- Timestamped reports and archives