# Technical Documentation

## Architecture Overview

This document provides technical details for developers working with or extending the document conversion pipeline.

## System Architecture

### High-Level Design

```
┌─────────────────┐
│  Configuration  │
│   (YAML/CLI)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   Main Pipeline │─────▶│  Validation  │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  File Discovery │
│   (Recursive)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   Conversion    │─────▶│ DocConverter │
│     Loop        │      │   (docling)  │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│   Rotation &    │
│   Archiving     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Report & Stats │
└─────────────────┘
```

### Core Components

#### 1. Configuration Management

**File**: Lines 88-135

**Functions**:
- `load_config(config_path)` - Loads YAML configuration with deep merge
- `save_default_config(config_path)` - Generates default config file
- `validate_config(config)` - Validates configuration integrity

**Configuration Schema**:
```python
{
    'input_types': List[str],      # ['pdf', 'docx', ...]
    'output_types': List[str],     # ['md', 'html', ...]
    'max_file_size_mb': int,       # File size limit
    'retry_attempts': int,         # Retry count for failures
    'retry_delay_seconds': float,  # Delay between retries
    'directories': {
        'inputs': str,
        'outputs': str,
        'inputs_queue': str,
        'inputs_staging': str
    }
}
```

#### 2. File Discovery System

**File**: Lines 237-266

**Function**: `list_input_files(input_dir, allowed_types)`

**Algorithm**:
1. Resolve input directory to absolute path
2. Recursively walk directory tree with `os.walk()`
3. Filter files by extension against allowed types
4. Compute relative paths for structure preservation
5. Return sorted list of (absolute_path, relative_path) tuples

**Path Resolution**:
```python
input_root = Path(input_dir).resolve()  # /full/path/to/inputs
full_path = os.path.join(root, name)    # root/subdir/file.pdf
abs_path = Path(full_path).resolve()    # /full/path/to/inputs/subdir/file.pdf
rel_path = abs_path.relative_to(input_root)  # subdir/file.pdf
```

**Critical Fix**: Both `full_path` and `input_root` must be resolved to absolute paths before computing `relative_to()` to avoid ValueError on mixed relative/absolute paths.

#### 3. Directory Operations

**File**: Lines 268-325

**Core Functions**:

```python
def move_contents(src_dir, dst_dir, overwrite=True, preserve_metadata=True)
```
- Moves directory contents (not the directory itself)
- Preserves file metadata (timestamps, permissions)
- Handles overwrites and conflicts
- Returns count of items moved

```python
def atomic_write(path, content, mode=None)
```
- Writes to `.{filename}.tmp` first
- Uses `os.replace()` for atomic operation
- Cleans up temp file on failure
- Auto-detects binary vs text mode

```python
def snapshot_directory(src_dir, prefix)
```
- Creates timestamped non-destructive copy
- Uses `shutil.copytree()` with `copy_function=shutil.copy2`
- Handles collision with suffix increment

#### 4. Rotation System

**File**: Lines 327-397

**Function**: `rotate_inputs(inputs_dir, inputs_queue_dir, inputs_staging_dir)`

**Execution Timing**: Called **AFTER** conversion completes

**Rotation Sequence**:
```python
# Step 1: Archive processed files
./inputs/ → ./inputs_old_{timestamp}/

# Step 2: Prepare for next run
./inputs_staging/ → ./inputs/

# Step 3: Stage for run after next
./inputs_queue/ → ./inputs_staging/
```

**State Diagram**:
```
Run N:
  inputs/        [file_a.pdf] ────▶ Convert ────▶ outputs/file_a_from_pdf.md
  staging/       [file_b.pdf]                     
  queue/         [file_c.pdf]                     

Rotation:
  inputs/        [file_a.pdf] ────▶ inputs_old_N/
  staging/       [file_b.pdf] ────▶ inputs/
  queue/         [file_c.pdf] ────▶ staging/

Run N+1:
  inputs/        [file_b.pdf] ────▶ Convert ────▶ outputs/file_b_from_pdf.md
  staging/       [file_c.pdf]
  queue/         []
```

#### 5. Document Conversion

**File**: Lines 399-493

**Function**: `convert_document(converter, input_path, output_path, output_ext, retry_attempts, retry_delay)`

**Conversion Pipeline**:
```python
1. DocumentConverter.convert(input_path)
   └─▶ Returns ConversionResult

2. result.document
   └─▶ Document object with export methods

3. getattr(document, export_method_name)()
   └─▶ export_to_markdown(), export_to_html(), etc.
   └─▶ Returns str or bytes

4. atomic_write(output_path, content)
   └─▶ Safe write with temp file
```

**Export Method Mapping**:
```python
EXPORT_METHODS = {
    'pdf': 'export_to_pdf',
    'docx': 'export_to_docx',
    'txt': 'export_to_text',
    'md': 'export_to_markdown',
    'html': 'export_to_html',
}
```

**Retry Logic**:
- Attempts: `retry_attempts + 1` (includes initial attempt)
- Delay: Exponential or fixed based on `retry_delay`
- Failure handling: Logs error, returns `(False, error_message)`

**Validation Checks**:
1. Result has `document` attribute
2. Document has export method
3. Export method is callable
4. Exported content is not None/empty
5. Output directory exists

#### 6. Collision-Safe Naming

**File**: Lines 402-420

**Function**: `generate_output_filename(input_filename, input_ext, output_ext)`

**Algorithm**:
```python
Input:  "report.pdf"
Parse:  filename="report", ext="pdf"
Output: "report_from_pdf.md"

Input:  "report.docx"
Parse:  filename="report", ext="docx"
Output: "report_from_docx.md"
```

**Rationale**: Multiple input files with same basename (report.pdf, report.docx) would collide when converted to same output type (report.md). The `_from_{ext}` suffix ensures uniqueness.

#### 7. Statistics Tracking

**File**: Lines 495-530

**Class**: `ConversionStats`

**Attributes**:
```python
total_files: int         # Files discovered
successful: int          # Successful conversions
failed: int              # Failed conversions
skipped: int             # Same-type conversions skipped
total_size_bytes: int    # Total data processed
failed_files: List[Tuple[str, str]]  # (filepath, reason)
start_time: float        # Epoch time at start
```

**Methods**:
- `add_success(size_bytes)` - Increment success counter
- `add_failure(filepath, reason)` - Track failure with reason
- `add_skip()` - Increment skip counter
- `elapsed_time()` - Calculate runtime
- `summary()` - Generate formatted summary lines

#### 8. Main Processing Pipeline

**File**: Lines 532-715

**Function**: `process_conversions(config, dry_run=False)`

**Execution Flow**:
```python
1. Initialize DocumentConverter (skip if dry_run)
2. Discover input files recursively
3. Log discovery phase statistics
4. FOR EACH input file:
   a. Check file size against limit
   b. FOR EACH output type:
      - Skip if same as input type
      - Generate collision-safe filename
      - Mirror directory structure in outputs
      - Convert document (or simulate if dry_run)
      - Track statistics
5. Generate run report with timestamp
6. Return ConversionStats object
```

**Progress Reporting**:
```python
progress_pct = (idx / total_files) * 100
logger.info(f"[{idx}/{total_files} - {progress_pct:.1f}%] Processing: {file}")
```

**Directory Structure Mirroring**:
```python
rel_dir = os.path.dirname(input_rel_path)  # "project_a/"
if rel_dir:
    output_path = os.path.join(outputs_dir, rel_dir, filename)
else:
    output_path = os.path.join(outputs_dir, filename)
```

## Data Flow

### Input Processing

```
inputs_queue/
  └─ file1.pdf ──┐
                 │
inputs_staging/  │
  └─ file2.pdf ──┼─────▶ Rotation ────▶ inputs/
                 │                        ├─ file2.pdf
inputs/          │                        └─ file3.pdf
  └─ file3.pdf ──┘                             │
                                               │
                                               ▼
                                         Conversion
                                               │
                                               ▼
                                          outputs/
                                            ├─ file2_from_pdf.md
                                            └─ file3_from_pdf.md
```

### Rotation Cycle

```
Time T0: User drops files
  inputs_queue/      [A.pdf]
  inputs_staging/    [B.pdf]
  inputs/            [C.pdf]

Time T1: Run 1 starts
  → Convert C.pdf → outputs/C_from_pdf.md
  
Time T1 end: Rotation
  inputs_queue/      [A.pdf] ──────┐
  inputs_staging/    [B.pdf] ──┐   │
  inputs/            [C.pdf] ──┼───┼──▶ inputs_old_T1/
                               │   │
  After rotation:              │   │
  inputs_queue/      []        │   │
  inputs_staging/    [A.pdf] ◀─┘   │
  inputs/            [B.pdf] ◀─────┘

Time T2: Run 2 starts
  → Convert B.pdf → outputs/B_from_pdf.md
```

## Error Handling

### Error Hierarchy

```
1. Fatal Errors (exit code 1)
   - Configuration validation failure
   - DocumentConverter initialization failure
   - Missing required directories

2. Recoverable Errors (logged, continue processing)
   - File size exceeds limit (skip file)
   - Conversion failure (retry, then skip)
   - Individual file read/write errors

3. Warnings (logged, no impact)
   - Empty directories during rotation
   - Missing optional config parameters
```

### Retry Strategy

```python
for attempt in range(retry_attempts + 1):
    try:
        # Conversion attempt
        if success:
            return (True, "Success")
    except Exception as e:
        if attempt < retry_attempts:
            time.sleep(retry_delay)
            continue
        else:
            return (False, f"Max retries: {e}")
```

## Performance Considerations

### Memory Management

- **File Reading**: Docling loads entire PDF into memory
- **Large Files**: Set `max_file_size_mb` appropriately
- **Batch Processing**: Processes files sequentially (not parallel)

### Disk I/O

- **Atomic Writes**: Additional write for temp file
- **Snapshots**: Full directory copies (use hardlinks if needed)
- **Rotations**: Move operations are fast (same filesystem)

### Optimization Opportunities

1. **Parallel Processing**: Add concurrent.futures for multi-file batches
2. **Incremental Snapshots**: Use hardlinks or rsync-style copying
3. **Progress Persistence**: Save state to resume interrupted runs
4. **Streaming Writes**: For very large output files

## Extension Points

### Adding New Export Formats

```python
# 1. Update EXPORT_METHODS dictionary
EXPORT_METHODS = {
    'pdf': 'export_to_pdf',
    'newformat': 'export_to_newformat',  # Add this
}

# 2. Update config.yaml
output_types:
  - md
  - newformat  # Add this

# 3. Ensure docling.document has export_to_newformat() method
```

### Custom Validation Logic

```python
def validate_config(config: Dict) -> None:
    # Existing validation
    ...
    
    # Add custom validation
    if 'custom_setting' in config:
        custom_value = config['custom_setting']
        if not meets_requirements(custom_value):
            raise ValueError("Custom validation failed")
```

### Hooks for Pre/Post Processing

```python
def process_conversions(config, dry_run=False):
    # Add hook before conversion
    if hasattr(config, 'pre_conversion_hook'):
        config.pre_conversion_hook(input_files)
    
    # Conversion loop
    ...
    
    # Add hook after conversion
    if hasattr(config, 'post_conversion_hook'):
        config.post_conversion_hook(stats)
```

## Testing Considerations

### Unit Test Targets

1. **Configuration**
   - `load_config()` with valid/invalid YAML
   - `validate_config()` with edge cases
   - Deep merge functionality

2. **File Operations**
   - `list_input_files()` with nested structures
   - `atomic_write()` with failures mid-write
   - `move_contents()` with overwrites

3. **Rotation**
   - `rotate_inputs()` with empty directories
   - Timestamp collision handling
   - Partial rotation failures

4. **Conversion**
   - `convert_document()` with various formats
   - Retry logic with mock failures
   - Collision-safe naming edge cases

### Integration Test Scenarios

1. **End-to-End Pipeline**
   - Place files in queue/staging/inputs
   - Run conversion
   - Verify outputs and rotation
   - Run again to test next cycle

2. **Error Recovery**
   - Corrupt PDF file
   - Out of disk space
   - Permission denied errors

3. **Configuration Variations**
   - Different input/output type combinations
   - CLI overrides
   - Missing config file

### Mock Objects

```python
from unittest.mock import Mock, patch

# Mock DocumentConverter
mock_converter = Mock()
mock_result = Mock()
mock_result.document.export_to_markdown = Mock(return_value="# Content")
mock_converter.convert = Mock(return_value=mock_result)

# Mock file system
with patch('os.path.exists', return_value=True):
    with patch('os.listdir', return_value=['file1.pdf']):
        # Test file discovery
```

## Debugging

### Log Levels

```python
# DEBUG: Detailed operation logs
logger.debug(f"Moving {src} to {dst}")

# INFO: Major phase transitions
logger.info("CONVERSION PHASE: Processing documents")

# WARNING: Recoverable issues
logger.warning("Skipping large file: 500MB > 100MB limit")

# ERROR: Failures that affect results
logger.error("Conversion failed: {error}")
```

### Common Debug Patterns

```bash
# Enable debug logging
python docling-inputs2outputs.py --log-level DEBUG

# Dry run to trace execution
python docling-inputs2outputs.py --dry-run --log-level DEBUG

# Check configuration loading
python docling-inputs2outputs.py --save-config
cat config.yaml
```

### Troubleshooting Path Issues

```python
# Add temporary debug logging
logger.debug(f"Input root resolved: {input_root}")
logger.debug(f"Full path: {full_path}")
logger.debug(f"Full path resolved: {Path(full_path).resolve()}")
logger.debug(f"Relative path: {rel_path}")
```

## Dependencies

### Required Packages

```
docling>=1.0.0          # Document conversion engine
PyYAML>=6.0            # Configuration parsing
```

### Built-in Modules

```
os, sys, shutil        # File system operations
logging                # Logging framework
argparse               # CLI argument parsing
time, datetime         # Timing and timestamps
pathlib                # Path manipulation
typing                 # Type hints
```

### Optional Dependencies

```
concurrent.futures     # For parallel processing (future)
watchdog              # For file system monitoring (future)
```

## Version History

### v2.0.0 (2025-09-30)
- Complete rewrite with rotation system
- Post-conversion rotation timing
- Recursive processing with structure preservation
- YAML configuration support
- Collision-safe filename generation
- Comprehensive error handling
- Dry-run mode
- Statistics tracking

### v1.0.0 (Original)
- Basic PDF to Markdown conversion
- Simple input/output directories
- No rotation system