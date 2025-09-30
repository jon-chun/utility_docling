# Technical Specification
# Document Conversion Pipeline System

**Version**: 2.0.0  
**Date**: 2025-09-30  
**Status**: Implemented  
**Architecture Lead**: Engineering Team  

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Component Specifications](#component-specifications)
4. [Data Models](#data-models)
5. [API Specifications](#api-specifications)
6. [Algorithm Specifications](#algorithm-specifications)
7. [State Machine](#state-machine)
8. [Error Handling](#error-handling)
9. [Performance Specifications](#performance-specifications)
10. [Testing Strategy](#testing-strategy)

---

## System Overview

### Architecture Style
**Monolithic Pipeline Architecture** - Single-process, sequential execution with modular function design.

### Technology Stack
```yaml
Language: Python 3.8+
Core Libraries:
  - docling: Document conversion engine
  - pyyaml: Configuration parsing
  - pathlib: Path operations
  - logging: Logging framework
  - argparse: CLI argument parsing

Built-in Modules:
  - os: File system operations
  - shutil: High-level file operations
  - time/datetime: Timing and timestamps
  - typing: Type annotations
```

### System Context Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                        External User                         │
│                                                              │
│  Actions: Drop files, configure YAML, run CLI commands      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                Document Conversion Pipeline                  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Config Mgmt  │→ │  File System │→ │  Conversion  │     │
│  │   (YAML)     │  │   Manager    │  │    Engine    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                           │                                  │
│                           ▼                                  │
│                  ┌──────────────┐                           │
│                  │   Reporting  │                           │
│                  │   & Logging  │                           │
│                  └──────────────┘                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System Storage                       │
│                                                              │
│  inputs/, outputs/, inputs_queue/, inputs_staging/          │
│  inputs_old_*/, outputs_*/                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Design

### High-Level Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         Main Entry Point                        │
│                         main() function                         │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────┐
              │   Argument Parsing (argparse)   │
              │   parse_arguments()             │
              └────────────┬────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────────┐
              │   Configuration Loading         │
              │   load_config()                 │
              │   validate_config()             │
              └────────────┬────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────────┐
              │   Directory Preparation          │
              │   ensure_dir()                   │
              │   snapshot_directory()           │
              └────────────┬────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────────┐
              │   Conversion Pipeline            │
              │   process_conversions()          │
              │   ├─ File Discovery              │
              │   ├─ Validation Loop             │
              │   ├─ Conversion Loop             │
              │   └─ Statistics Tracking         │
              └────────────┬────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────────┐
              │   Post-Processing Rotation       │
              │   rotate_inputs()                │
              │   ├─ Archive inputs/             │
              │   ├─ Staging → Inputs            │
              │   └─ Queue → Staging             │
              └────────────┬────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────────┐
              │   Report Generation              │
              │   generate_run_report()          │
              │   ConversionStats.summary()      │
              └────────────┬────────────────────┘
                           │
                           ▼
                       Exit (0 or 1)
```

### Module Structure

```python
docling-inputs2outputs.py
│
├─ Global Constants
│  ├─ DEFAULT_CONFIG: Dict
│  └─ EXPORT_METHODS: Dict[str, str]
│
├─ Configuration Module
│  ├─ load_config(path: str) -> Dict
│  ├─ save_default_config(path: str) -> None
│  └─ validate_config(config: Dict) -> None
│
├─ File System Module
│  ├─ list_input_files(dir: str, types: List[str]) -> List[Tuple]
│  ├─ move_contents(src: str, dst: str, ...) -> int
│  ├─ atomic_write(path: str, content: Any) -> None
│  ├─ snapshot_directory(src: str, prefix: str) -> str
│  └─ rotate_inputs(...) -> Tuple[str, int, int]
│
├─ Conversion Module
│  ├─ generate_output_filename(...) -> str
│  ├─ convert_document(...) -> Tuple[bool, str]
│  └─ process_conversions(config: Dict, dry_run: bool) -> ConversionStats
│
├─ Statistics Module
│  └─ ConversionStats (class)
│     ├─ add_success(size: int) -> None
│     ├─ add_failure(file: str, reason: str) -> None
│     └─ summary() -> List[str]
│
├─ Utility Module
│  ├─ now_stamp() -> str
│  ├─ ensure_dir(path: str) -> None
│  ├─ format_bytes(size: int) -> str
│  ├─ format_duration(seconds: float) -> str
│  └─ check_file_size(...) -> Tuple[bool, str]
│
└─ CLI Module
   ├─ parse_arguments() -> Namespace
   └─ main() -> int
```

---

## Component Specifications

### 1. Configuration Manager

**Purpose**: Load, validate, and manage system configuration from YAML and CLI.

**Interface**:
```python
def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration with deep merge of defaults and user config.
    
    Args:
        config_path: Path to config.yaml, None uses defaults
        
    Returns:
        Complete configuration dictionary
        
    Raises:
        yaml.YAMLError: Invalid YAML syntax
    """

def validate_config(config: Dict) -> None:
    """
    Validate configuration integrity and constraints.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: Invalid configuration with detailed message
    """
```

**Implementation Details**:
```python
# Default configuration with all required fields
DEFAULT_CONFIG = {
    'input_types': ['pdf'],
    'output_types': ['md'],
    'max_file_size_mb': 100,
    'retry_attempts': 2,
    'retry_delay_seconds': 1.0,
    'directories': {
        'inputs': './inputs',
        'outputs': './outputs',
        'inputs_queue': './inputs_queue',
        'inputs_staging': './inputs_staging'
    }
}

# Load sequence:
# 1. Start with DEFAULT_CONFIG
# 2. Deep merge user YAML (if exists)
# 3. Apply CLI overrides
# 4. Validate final config
```

**Validation Rules**:
1. `input_types` and `output_types` must be non-empty lists
2. `input_types` ≠ `output_types` (must differ)
3. All types must be in EXPORT_METHODS keys
4. `max_file_size_mb` > 0
5. `retry_attempts` ≥ 0
6. `retry_delay_seconds` > 0
7. All directory paths must be valid strings

**Error Handling**:
- Missing config file: Log warning, use defaults
- Invalid YAML: Raise error with line number
- Invalid config: Raise ValueError with specific issue

### 2. File Discovery System

**Purpose**: Recursively discover input files while filtering by type and computing relative paths.

**Interface**:
```python
def list_input_files(
    input_dir: str,
    allowed_types: List[str]
) -> List[Tuple[str, str]]:
    """
    Discover all files matching allowed types recursively.
    
    Args:
        input_dir: Root directory to scan
        allowed_types: List of extensions (without dots): ['pdf', 'docx']
        
    Returns:
        List of (absolute_path, relative_path) tuples, sorted by relative path
        
    Example:
        [
            ('/full/path/inputs/dir/file.pdf', 'dir/file.pdf'),
            ('/full/path/inputs/file2.pdf', 'file2.pdf')
        ]
    """
```

**Algorithm**:
```python
ALGORITHM: recursive_file_discovery
INPUT: input_dir (Path), allowed_types (Set[str])
OUTPUT: files (List[Tuple[Path, Path]])

1. input_root ← resolve_absolute(input_dir)
2. allowed ← {ext.lower() for ext in allowed_types}
3. files ← []

4. FOR EACH (root, dirs, filenames) IN os.walk(input_dir):
    5. FOR EACH filename IN filenames:
        6. full_path ← join(root, filename)
        7. extension ← extract_extension(filename).lower().strip('.')
        
        8. IF extension IN allowed:
            9. abs_path ← resolve_absolute(full_path)
            10. rel_path ← compute_relative(abs_path, input_root)
            11. files.append((abs_path, rel_path))

12. RETURN sorted(files, key=lambda x: x[1])
```

**Path Resolution**:
```python
# CRITICAL: Both paths must be absolute before computing relative path
input_root = Path(input_dir).resolve()       # /full/path/inputs
full_path = Path(root, name).resolve()       # /full/path/inputs/sub/file.pdf
rel_path = full_path.relative_to(input_root) # sub/file.pdf
```

**Edge Cases**:
- Empty directory: Returns empty list
- No matching files: Returns empty list
- Symbolic links: Followed by default
- Hidden files: Ignored (start with '.')
- Files without extensions: Ignored

### 3. Rotation Manager

**Purpose**: Execute post-conversion file rotation across three tiers.

**Interface**:
```python
def rotate_inputs(
    inputs_dir: str,
    inputs_queue_dir: str,
    inputs_staging_dir: str
) -> Tuple[str, int, int]:
    """
    Execute rotation after conversion completes.
    
    Args:
        inputs_dir: Main inputs directory (./inputs)
        inputs_queue_dir: Queue directory (./inputs_queue)
        inputs_staging_dir: Staging directory (./inputs_staging)
        
    Returns:
        (rotated_archive_path, staging_moved_count, queue_moved_count)
        
    Side Effects:
        - Creates inputs_old_{timestamp}/ directory
        - Moves files between directories
        - Recreates empty directories
    """
```

**State Transitions**:
```python
STATE MACHINE: rotation_cycle

State T0 (Before Rotation):
  inputs/         [file_a.pdf]  # Just processed
  inputs_staging/ [file_b.pdf]  # Ready for next run
  inputs_queue/   [file_c.pdf]  # Future processing

State T1 (During Rotation):
  Step 1: inputs/ → inputs_old_{timestamp}/
  Step 2: Recreate inputs/
  Step 3: inputs_staging/ → inputs/
  Step 4: inputs_queue/ → inputs_staging/

State T2 (After Rotation):
  inputs/         [file_b.pdf]  # Ready for next run
  inputs_staging/ [file_c.pdf]  # Staged
  inputs_queue/   []            # Empty
  inputs_old_T0/  [file_a.pdf]  # Archived
```

**Atomicity Guarantees**:
- Each `shutil.move()` is atomic within same filesystem
- If rotation fails mid-process, files remain in last known good state
- Errors logged but don't halt entire rotation

**Error Recovery**:
- Partial rotation failure: Log error, continue
- Permission denied: Skip that operation, continue
- Disk full: Halt with clear error message

### 4. Conversion Engine

**Purpose**: Convert documents using docling with retry logic and validation.

**Interface**:
```python
def convert_document(
    converter: DocumentConverter,
    input_path: str,
    output_path: str,
    output_ext: str,
    retry_attempts: int = 2,
    retry_delay: float = 1.0
) -> Tuple[bool, str]:
    """
    Convert document with automatic retry on failure.
    
    Args:
        converter: Initialized DocumentConverter instance
        input_path: Absolute path to input file
        output_path: Absolute path for output file
        output_ext: Output extension ('md', 'html', etc.)
        retry_attempts: Number of additional attempts after initial failure
        retry_delay: Seconds to wait between retry attempts
        
    Returns:
        (success: bool, message: str)
        - (True, "Success") on successful conversion
        - (False, "error details") on final failure
        
    Side Effects:
        - Creates output file on success
        - Creates parent directories if needed
        - Logs each attempt
    """
```

**Conversion Pipeline**:
```python
ALGORITHM: document_conversion_with_retry
INPUT: converter, input_path, output_path, output_ext, retry_attempts, retry_delay
OUTPUT: (success: bool, message: str)

1. FOR attempt IN range(0, retry_attempts + 1):
    2. TRY:
        3. IF attempt > 0:
            4. LOG("Retry attempt {attempt}/{retry_attempts}")
            5. SLEEP(retry_delay)
        
        6. result ← converter.convert(input_path)
        
        7. IF result.document IS None:
            8. RETURN (False, "No document in result")
        
        9. export_method_name ← EXPORT_METHODS[output_ext]
        10. export_method ← getattr(result.document, export_method_name)
        
        11. IF NOT callable(export_method):
            12. available ← [m for m in dir(result.document) if m.startswith("export_")]
            13. RETURN (False, f"Missing {export_method_name}, available: {available}")
        
        14. content ← export_method()
        
        15. IF content IS None OR len(content) == 0:
            16. RETURN (False, "Export returned empty content")
        
        17. ensure_dir(parent_dir(output_path))
        18. atomic_write(output_path, content)
        
        19. RETURN (True, "Success")
    
    20. EXCEPT Exception AS e:
        21. IF attempt < retry_attempts:
            22. LOG_WARNING(f"Attempt failed: {e}, will retry")
            23. CONTINUE
        24. ELSE:
            25. LOG_ERROR(f"All attempts failed: {e}")
            26. RETURN (False, str(e))

27. RETURN (False, "Max retries reached")
```

**Validation Stages**:
1. **Pre-conversion**: Check file exists, readable
2. **Post-conversion**: Check result has document
3. **Pre-export**: Check export method exists and callable
4. **Post-export**: Check content not None/empty
5. **Pre-write**: Check parent directory exists/created
6. **Post-write**: (Atomic write guarantees completion)

### 5. Statistics Tracker

**Purpose**: Track and report conversion statistics across entire run.

**Class Specification**:
```python
class ConversionStats:
    """Track conversion statistics for reporting."""
    
    # Attributes
    total_files: int          # Files discovered
    successful: int           # Successful conversions
    failed: int               # Failed conversions
    skipped: int              # Skipped (same-type)
    total_size_bytes: int     # Total data processed
    failed_files: List[Tuple[str, str]]  # (filepath, reason)
    start_time: float         # Epoch time at start
    
    def __init__(self):
        """Initialize counters to zero."""
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.total_size_bytes = 0
        self.failed_files = []
        self.start_time = time.time()
    
    def add_success(self, size_bytes: int = 0) -> None:
        """Record successful conversion."""
        self.successful += 1
        self.total_size_bytes += size_bytes
    
    def add_failure(self, filepath: str, reason: str) -> None:
        """Record failed conversion with reason."""
        self.failed += 1
        self.failed_files.append((filepath, reason))
    
    def add_skip(self) -> None:
        """Record skipped conversion."""
        self.skipped += 1
    
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time
    
    def summary(self) -> List[str]:
        """Generate formatted summary lines."""
        lines = [
            "=" * 70,
            "CONVERSION STATISTICS",
            "=" * 70,
            f"Total files discovered: {self.total_files}",
            f"Successful conversions: {self.successful}",
            f"Failed conversions: {self.failed}",
            f"Skipped (same type): {self.skipped}",
            f"Total data processed: {format_bytes(self.total_size_bytes)}",
            f"Total runtime: {format_duration(self.elapsed_time())}",
        ]
        
        if self.failed_files:
            lines.append("")
            lines.append("Failed Files:")
            for filepath, reason in self.failed_files:
                lines.append(f"  - {filepath}: {reason}")
        
        lines.append("=" * 70)
        return lines
```

---

## Data Models

### Configuration Schema

```python
ConfigSchema = {
    'input_types': List[str],      # File extensions without dots
    'output_types': List[str],     # File extensions without dots
    'max_file_size_mb': int,       # Maximum file size in MB
    'retry_attempts': int,         # Number of retry attempts
    'retry_delay_seconds': float,  # Delay between retries
    'directories': {
        'inputs': str,             # Path to inputs directory
        'outputs': str,            # Path to outputs directory
        'inputs_queue': str,       # Path to queue directory
        'inputs_staging': str      # Path to staging directory
    }
}
```

### File Metadata

```python
FileMetadata = {
    'absolute_path': str,      # Full path: /home/user/inputs/dir/file.pdf
    'relative_path': str,      # Relative: dir/file.pdf
    'filename': str,           # Base: file.pdf
    'name_no_ext': str,        # Name: file
    'extension': str,          # Extension: pdf
    'size_bytes': int,         # File size in bytes
    'discovered_at': float     # Timestamp when discovered
}
```

### Conversion Result

```python
ConversionResult = {
    'input_file': str,         # Input file path
    'output_file': str,        # Output file path
    'input_type': str,         # Input extension
    'output_type': str,        # Output extension
    'success': bool,           # True if successful
    'message': str,            # Success message or error details
    'attempts': int,           # Number of attempts made
    'duration_sec': float,     # Time taken in seconds
    'size_bytes': int          # Output file size
}
```

### Run Report

```python
RunReport = {
    'timestamp': str,          # ISO format timestamp
    'configuration': Dict,     # Config used for run
    'input_files': int,        # Number of files discovered
    'conversions': List[ConversionResult],
    'statistics': {
        'total': int,
        'successful': int,
        'failed': int,
        'skipped': int,
        'total_size_mb': float,
        'runtime_sec': float,
        'throughput_mbps': float
    },
    'rotation': {
        'archive_path': str,
        'staging_moved': int,
        'queue_moved': int
    }
}
```

---

## API Specifications

### Command-Line Interface

```bash
python docling-inputs2outputs.py [OPTIONS]

Options:
  --config PATH           Path to configuration YAML file
                          Default: config.yaml
                          
  --save-config          Generate default config.yaml and exit
                          Exit code: 0
                          
  --dry-run              Preview operations without executing
                          No files created or modified
                          
  --log-level LEVEL      Set logging verbosity
                          Choices: DEBUG, INFO, WARNING, ERROR
                          Default: INFO
                          
  --inputs PATH          Override inputs directory path
                          Overrides config.yaml setting
                          
  --outputs PATH         Override outputs directory path
                          Overrides config.yaml setting
                          
  --inputs-queue PATH    Override inputs_queue directory path
                          Overrides config.yaml setting
                          
  --inputs-staging PATH  Override inputs_staging directory path
                          Overrides config.yaml setting
                          
  -h, --help            Show help message and exit

Exit Codes:
  0  Success - all conversions completed successfully
  1  Failure - configuration error, fatal error, or failed conversions

Examples:
  # Basic usage with defaults
  python docling-inputs2outputs.py
  
  # Dry run with debug logging
  python docling-inputs2outputs.py --dry-run --log-level DEBUG
  
  # Custom configuration
  python docling-inputs2outputs.py --config production.yaml
  
  # Override directories
  python docling-inputs2outputs.py --inputs /data/inputs --outputs /data/outputs
```

### Configuration File API

```yaml
# config.yaml - YAML Configuration File

# Input file types to process (extensions without dots)
# Supported: pdf, docx, txt, md, html
input_types:
  - pdf
  - docx

# Output file types to generate (extensions without dots)
# Supported: pdf, docx, txt, md, html
output_types:
  - md
  - html

# Maximum file size in megabytes (files larger will be skipped)
# Recommended: 50-200 MB depending on available RAM
max_file_size_mb: 100

# Number of retry attempts for failed conversions
# 0 = no retries, 2 = 3 total attempts (initial + 2 retries)
retry_attempts: 2

# Delay in seconds between retry attempts
# Allows transient errors to resolve
retry_delay_seconds: 1.0

# Directory paths (relative or absolute)
directories:
  # Active processing directory
  inputs: ./inputs
  
  # Output directory for converted files
  outputs: ./outputs
  
  # Queue directory for future processing
  inputs_queue: ./inputs_queue
  
  # Staging directory for next run
  inputs_staging: ./inputs_staging
```

---

## Algorithm Specifications

### Collision-Safe Filename Generation

```python
ALGORITHM: generate_collision_safe_filename
INPUT: input_basename (str), input_ext (str), output_ext (str)
OUTPUT: output_filename (str)

FUNCTION generate_output_filename(input_filename, input_ext, output_ext):
    1. name_no_ext ← input_filename WITHOUT extension
    2. safe_input_ext ← input_ext.lower().strip('.')
    3. safe_output_ext ← output_ext.lower().strip('.')
    4. output_filename ← f"{name_no_ext}_from_{safe_input_ext}.{safe_output_ext}"
    5. RETURN output_filename

Examples:
  generate_output_filename("report.pdf", "pdf", "md")
    → "report_from_pdf.md"
  
  generate_output_filename("analysis.docx", "docx", "html")
    → "analysis_from_docx.html"
  
  generate_output_filename("data.v2.xlsx", "xlsx", "csv")
    → "data.v2_from_xlsx.csv"
```

### Atomic Write Operation

```python
ALGORITHM: atomic_write
INPUT: target_path (Path), content (bytes | str)
OUTPUT: None
SIDE_EFFECT: File written atomically to target_path

FUNCTION atomic_write(target_path, content):
    1. dir_path ← parent_directory(target_path)
    2. filename ← basename(target_path)
    3. temp_path ← join(dir_path, f".{filename}.tmp")
    
    4. TRY:
        5. mode ← "wb" IF isinstance(content, bytes) ELSE "w"
        6. encoding ← None IF mode == "wb" ELSE "utf-8"
        
        7. WITH OPEN(temp_path, mode, encoding) AS file:
            8. file.write(content)
        
        9. os.replace(temp_path, target_path)  # Atomic on POSIX and Windows
        
    10. EXCEPT Exception AS e:
        11. IF exists(temp_path):
            12. TRY: remove(temp_path)
            13. EXCEPT: pass
        14. RAISE e

Guarantees:
- Either file is completely written or not at all
- No partial files visible to other processes
- Automatic cleanup of temp files on failure
```

### Directory Structure Mirroring

```python
ALGORITHM: mirror_directory_structure
INPUT: input_rel_path (str), output_root (Path), filename (str)
OUTPUT: output_path (Path)

FUNCTION mirror_structure(input_rel_path, output_root, filename):
    1. rel_dir ← directory_part(input_rel_path)  # "project_a/subdir"
    
    2. IF rel_dir IS NOT empty:
        3. output_dir ← join(output_root, rel_dir)
        4. ensure_dir(output_dir)  # Create if doesn't exist
        5. output_path ← join(output_dir, filename)
    3. ELSE:
        4. output_path ← join(output_root, filename)
    
    5. RETURN output_path

Example:
  input_rel_path = "research/2024/paper.pdf"
  output_root = "/home/user/outputs"
  filename = "paper_from_pdf.md"
  
  Result: "/home/user/outputs/research/2024/paper_from_pdf.md"
  
  Side Effect: Creates /home/user/outputs/research/2024/ if needed
```

---

## State Machine

### Conversion Pipeline State Machine

```
┌─────────┐
│  INIT   │──▶ Load config
└────┬────┘    Validate config
     │         Setup logging
     │
     ▼
┌─────────┐
│ PREPARE │──▶ Ensure directories exist
└────┬────┘    Snapshot outputs
     │         Initialize converter
     │
     ▼
┌──────────┐
│ DISCOVER │──▶ Scan inputs directory
└────┬─────┘    Filter by type
     │           Compute relative paths
     │           Sort files
     │
     ▼
┌──────────┐
│ VALIDATE │──▶ Check file sizes
└────┬─────┘    Check permissions
     │           Log warnings
     │
     ▼
┌──────────┐
│ CONVERT  │──▶ For each file:
└────┬─────┘      ├─ Convert document
     │             ├─ Retry on failure
     │             ├─ Track statistics
     │             └─ Log progress
     │
     ▼
┌─────────┐
│ ROTATE  │──▶ Archive inputs/
└────┬────┘    Move staging → inputs
     │         Move queue → staging
     │
     ▼
┌─────────┐
│ REPORT  │──▶ Generate run report
└────┬────┘    Display statistics
     │         Write report file
     │
     ▼
┌──────────┐
│ COMPLETE │──▶ Exit with status code
└──────────┘    (0 = success, 1 = failure)
```

### File State Transitions

```
File Lifecycle State Machine:

┌─────────────┐
│  UPLOADED   │ User places file
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   QUEUED    │ In inputs_queue/
└──────┬──────┘ Waiting for staging
       │
       │ (After run N completes)
       ▼
┌─────────────┐
│   STAGED    │ In inputs_staging/
└──────┬──────┘ Ready for next run
       │
       │ (After run N+1 completes)
       ▼
┌─────────────┐
│   ACTIVE    │ In inputs/
└──────┬──────┘ Being processed
       │
       │ (During run N+2)
       ▼
┌─────────────┐
│ PROCESSING  │ Being converted
└──────┬──────┘
       │
       ├──▶ Success ───┐
       │               │
       └──▶ Failure ───┤
                       │
                       ▼
              ┌─────────────┐
              │  COMPLETED  │ Conversion done
              └──────┬──────┘
                     │
                     │ (Rotation phase)
                     ▼
              ┌─────────────┐
              │  ARCHIVED   │ In inputs_old_*/
              └─────────────┘ Historical record
```

---

## Error Handling

### Error Classification

```python
class ErrorSeverity(Enum):
    """Error severity levels."""
    FATAL = 1      # Halt execution immediately
    ERROR = 2      # Log error, skip item, continue
    WARNING = 3    # Log warning, continue
    INFO = 4       # Informational message

class ErrorCategory(Enum):
    """Error categories for handling strategy."""
    CONFIGURATION = "config"
    FILE_SYSTEM = "filesystem"
    CONVERSION = "conversion"
    VALIDATION = "validation"
    PERMISSION = "permission"
```

### Error Handling Matrix

| Error Type | Severity | Retry? | Action | Exit Code |
|------------|----------|--------|--------|-----------|
| Invalid config | FATAL | No | Halt | 1 |
| Missing docling | FATAL | No | Halt | 1 |
| Directory creation fails | FATAL | No | Halt | 1 |
| File too large | WARNING | No | Skip file | 0 |
| File not readable | ERROR | No | Skip file | 1 |
| Conversion timeout | ERROR | Yes | Retry, then skip | 1 |
| Corrupt PDF | ERROR | No | Skip file | 1 |
| Disk full | FATAL | No | Halt | 1 |
| Permission denied (read) | ERROR | No | Skip file | 1 |
| Permission denied (write) | FATAL | No | Halt | 1 |
| Export method missing | ERROR | No | Skip file | 1 |
| Network timeout | ERROR | Yes | Retry, then skip | 1 |

### Error Messages

```python
ERROR_MESSAGES = {
    'config_invalid': "Configuration validation failed: {reason}. Please check config.yaml",
    'docling_missing': "ERROR: docling package not found. Install with: pip install docling",
    'file_too_large': "Skipping {file}: File size {size} exceeds limit of {limit}",
    'file_not_found': "Cannot process {file}: File not found or not readable",
    'conversion_failed': "Failed to convert {file} after {attempts} attempts: {error}",
    'disk_full': "FATAL: Disk full. Cannot write to {path}",
    'permission_denied': "Permission denied: Cannot {action} {path}",
    'corrupt_file': "Skipping {file}: File appears to be corrupt ({error})",
    'export_missing': "Document has no method '{method}'. Available: {available}"
}
```

### Exception Handling Pattern

```python
try:
    # Operation
    result = convert_document(file)
    
except FileNotFoundError as e:
    logger.error(f"File not found: {file}")
    stats.add_failure(file, "File not found")
    continue  # Skip to next file
    
except PermissionError as e:
    logger.error(f"Permission denied: {file}")
    stats.add_failure(file, "Permission denied")
    continue  # Skip to next file
    
except MemoryError as e:
    logger.error(f"Out of memory processing: {file}")
    stats.add_failure(file, "Out of memory")
    continue  # Skip to next file
    
except Exception as e:
    logger.exception(f"Unexpected error: {file}")
    stats.add_failure(file, str(e))
    continue  # Skip to next file
    
finally:
    # Cleanup temp files
    cleanup_temp_files()
```

---

## Performance Specifications

### Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| File discovery | <1s per 1000 files | Time to scan and list files |
| Conversion throughput | >0.25 MB/s | Sustained rate over 100 files |
| Memory usage | <2GB per 100 files | Peak RSS during processing |
| Rotation speed | <10s per 1000 files | Time to move/archive files |
| Report generation | <1s | Time to write report file |

### Resource Limits

```python
RESOURCE_LIMITS = {
    'max_file_size_mb': 100,           # Default max file size
    'max_memory_mb': 2000,             # Target max memory usage
    'max_open_files': 100,             # Prevent file descriptor exhaustion
    'max_path_length': 260,            # Windows compatibility
    'max_batch_size': 1000,            # Files per batch
}
```

### Optimization Strategies

1. **Sequential Processing**
   - Process one file at a time
   - Release memory after each file
   - Prevents memory accumulation

2. **Lazy Loading**
   - Don't load all files into memory
   - Process as discovered
   - Generator-based iteration

3. **Efficient Path Operations**
   - Cache resolved paths
   - Use pathlib for cross-platform compatibility
   - Minimize filesystem calls

4. **Atomic Operations**
   - Single system call when possible
   - Reduce context switching
   - Use os.replace() for atomic moves

---

## Testing Strategy

### Unit Tests

```python
# Configuration Tests
test_load_valid_config()
test_load_invalid_yaml()
test_load_missing_config()
test_validate_valid_config()
test_validate_invalid_types()
test_validate_missing_fields()
test_cli_overrides_config()

# File Discovery Tests
test_list_files_flat_directory()
test_list_files_nested_directory()
test_list_files_empty_directory()
test_list_files_filter_by_type()
test_list_files_case_insensitive()
test_list_files_sort_order()

# Rotation Tests
test_rotate_single_file()
test_rotate_multiple_files()
test_rotate_empty_directories()
test_rotate_creates_timestamp()
test_rotate_preserves_structure()

# Conversion Tests
test_convert_pdf_to_md()
test_convert_with_retry()
test_convert_handles_failure()
test_convert_validates_output()
test_collision_safe_naming()

# Statistics Tests
test_stats_tracking()
test_stats_summary_format()
test_stats_failed_files()
```

### Integration Tests

```python
# End-to-End Tests
test_full_pipeline_single_file()
test_full_pipeline_multiple_files()
test_full_pipeline_nested_structure()
test_full_pipeline_with_rotation()

# Error Handling Tests
test_handles_corrupt_file()
test_handles_permission_error()
test_handles_disk_full()
test_handles_large_file()

# Configuration Tests
test_custom_config_file()
test_cli_overrides()
test_environment_specific_configs()
```

### Test Data

```
tests/
├── fixtures/
│   ├── valid_config.yaml
│   ├── invalid_config.yaml
│   ├── sample_files/
│   │   ├── small.pdf (100KB)
│   │   ├── medium.pdf (10MB)
│   │   ├── large.pdf (100MB)
│   │   └── corrupt.pdf
│   └── expected_outputs/
│       └── small_from_pdf.md
├── unit/
│   ├── test_config.py
│   ├── test_discovery.py
│   ├── test_rotation.py
│   └── test_conversion.py
└── integration/
    ├── test_pipeline.py
    └── test_error_handling.py
```

---

## Appendix

### A. File Format Support Matrix

| Format | Extension | Read | Write | Notes |
|--------|-----------|------|-------|-------|
| PDF | .pdf | ✓ | ✓ | Primary format |
| Word | .docx | ✓ | ✓ | Office Open XML |
| Text | .txt | ✓ | ✓ | Plain text |
| Markdown | .md | ✓ | ✓ | CommonMark |
| HTML | .html | ✓ | ✓ | HTML5 |

### B. Platform Compatibility Matrix

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Basic conversion | ✓ | ✓ | ✓ |
| Recursive discovery | ✓ | ✓ | ✓ |
| Atomic writes | ✓ | ✓ | ✓ |
| Path handling | ✓ | ✓ | ✓ |
| File permissions | ✓ | ✓ | Limited |
| Symbolic links | ✓ | ✓ | ✓ |

### C. Dependency Versions

```
Python: >=3.8
docling: >=1.0.0
PyYAML: >=6.0
pathlib: Built-in
logging: Built-in
argparse: Built-in
```

### D. Future Enhancements

**Planned Features**:
1. Parallel processing with multiprocessing
2. Watch mode for automatic processing
3. REST API for remote triggering
4. Progress persistence for resume
5. Cloud storage integration (S3, GCS)
6. WebSocket-based real-time progress
7. Distributed processing across nodes

**Technical Debt**:
1. Duplicate logging (cosmetic issue)
2. No cancellation mechanism
3. Limited error recovery options
4. No progress persistence

---

**Document Status**: Complete  
**Last Updated**: 2025-09-30  
**Next Review**: TBD