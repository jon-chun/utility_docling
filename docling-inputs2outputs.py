#!/usr/bin/env python3
"""
Document Conversion Pipeline with Rotation and Staging

This script provides automated document conversion with file rotation,
staging areas, and comprehensive logging for AI research workflows.

Features:
- Recursive directory processing with structure preservation
- File rotation and staging system
- Config file support (YAML)
- Progress reporting and statistics
- Dry-run mode
- Automatic retry on failures
- Comprehensive error handling and logging
"""

import os
import sys
import shutil
import logging
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import yaml

# Try to import docling, provide helpful error if missing
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("ERROR: docling package not found. Install with: pip install docling")
    sys.exit(1)


# ============================================================================
# Configuration and Constants
# ============================================================================

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

EXPORT_METHODS = {
    'pdf': 'export_to_pdf',
    'docx': 'export_to_docx',
    'txt': 'export_to_text',
    'md': 'export_to_markdown',
    'html': 'export_to_html',
}


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Configure module-level logger with console and file handlers."""
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logging()


# ============================================================================
# Configuration Management
# ============================================================================

def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from YAML file or return defaults.
    
    Args:
        config_path: Path to config.yaml file
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Deep merge for nested dicts
                    for key, value in user_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
                    logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        if config_path:
            logger.info(f"Config file not found at {config_path}, using defaults")
        
    return config


def save_default_config(config_path: str = 'config.yaml'):
    """Save default configuration to YAML file."""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Default configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")


# ============================================================================
# Validation Functions
# ============================================================================

def validate_config(config: Dict) -> None:
    """
    Validate configuration settings.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    input_types = config.get('input_types', [])
    output_types = config.get('output_types', [])
    
    if not input_types or not output_types:
        raise ValueError("Input and output types must not be empty.")
    
    if set(input_types) == set(output_types):
        raise ValueError("Input types cannot be identical to output types.")
    
    # Validate types are supported
    unsupported_inputs = set(input_types) - set(EXPORT_METHODS.keys())
    unsupported_outputs = set(output_types) - set(EXPORT_METHODS.keys())
    
    if unsupported_inputs:
        raise ValueError(f"Unsupported input types: {unsupported_inputs}. "
                        f"Supported: {list(EXPORT_METHODS.keys())}")
    
    if unsupported_outputs:
        raise ValueError(f"Unsupported output types: {unsupported_outputs}. "
                        f"Supported: {list(EXPORT_METHODS.keys())}")
    
    # Validate max file size
    max_size = config.get('max_file_size_mb', 0)
    if max_size <= 0:
        raise ValueError("max_file_size_mb must be positive")
    
    logger.debug("Configuration validated successfully")


# ============================================================================
# Utility Functions
# ============================================================================

def now_stamp() -> str:
    """Generate timestamp string with microseconds to avoid collisions."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def format_bytes(bytes_size: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# ============================================================================
# File Discovery and Processing
# ============================================================================

def get_file_size(filepath: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        logger.warning(f"Could not get size of {filepath}: {e}")
        return 0


def list_input_files(input_dir: str, allowed_types: List[str]) -> List[Tuple[str, str]]:
    """
    Recursively list all files with allowed extensions in input_dir.
    
    Args:
        input_dir: Root directory to scan
        allowed_types: List of allowed file extensions (without dots)
        
    Returns:
        List of tuples (absolute_path, relative_path_from_input_dir)
    """
    files = []
    if not os.path.exists(input_dir):
        logger.warning(f"Input directory does not exist: {input_dir}")
        return files
    
    input_root = Path(input_dir).resolve()
    allowed = {ext.lower() for ext in allowed_types}
    
    # Recursive walk through all subdirectories
    for root, _, filenames in os.walk(input_dir):
        for name in filenames:
            full_path = os.path.join(root, name)
            _, ext = os.path.splitext(name)
            
            if ext:
                ext = ext.lower().lstrip('.')
                if ext in allowed:
                    # Resolve to absolute path first, then compute relative
                    abs_path_obj = Path(full_path).resolve()
                    abs_path = str(abs_path_obj)
                    rel_path = str(abs_path_obj.relative_to(input_root))
                    files.append((abs_path, rel_path))
    
    return sorted(files, key=lambda x: x[1])  # Sort by relative path


def check_file_size(filepath: str, max_size_mb: int) -> Tuple[bool, str]:
    """
    Check if file size is within limits.
    
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        size_bytes = get_file_size(filepath)
        size_mb = size_bytes / (1024 * 1024)
        
        if size_mb > max_size_mb:
            return False, f"File size {format_bytes(size_bytes)} exceeds limit of {max_size_mb}MB"
        
        return True, f"Size: {format_bytes(size_bytes)}"
    except Exception as e:
        return False, f"Could not check file size: {e}"


# ============================================================================
# Directory Operations
# ============================================================================

def move_contents(src_dir: str, dst_dir: str, overwrite: bool = True,
                 preserve_metadata: bool = True) -> int:
    """
    Move contents of src_dir into dst_dir with metadata preservation.
    
    Args:
        src_dir: Source directory
        dst_dir: Destination directory
        overwrite: Whether to overwrite existing files
        preserve_metadata: Whether to preserve file metadata
        
    Returns:
        Number of items moved
    """
    if not os.path.exists(src_dir):
        logger.info(f"No directory at {src_dir}; nothing to move.")
        return 0
    
    ensure_dir(dst_dir)
    moved_count = 0
    
    for entry in os.listdir(src_dir):
        src_path = os.path.join(src_dir, entry)
        dst_path = os.path.join(dst_dir, entry)
        
        try:
            if os.path.exists(dst_path):
                if overwrite:
                    if os.path.isdir(dst_path) and not os.path.islink(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                    logger.debug(f"Overwriting existing path at {dst_path}")
                else:
                    logger.debug(f"Skipping existing path (no overwrite): {dst_path}")
                    continue
            
            if preserve_metadata:
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, copy_function=shutil.copy2)
                    shutil.rmtree(src_path)
                else:
                    shutil.copy2(src_path, dst_path)
                    os.remove(src_path)
            else:
                shutil.move(src_path, dst_path)
            
            logger.debug(f"Moved {src_path} -> {dst_path}")
            moved_count += 1
            
        except Exception as e:
            logger.error(f"Failed to move {src_path} to {dst_path}: {e}")
    
    return moved_count


def atomic_write(path: str, content, mode: str = None) -> None:
    """
    Write content atomically with automatic cleanup on failure.
    
    Args:
        path: Destination file path
        content: Content to write (bytes or str)
        mode: Write mode ('wb' or 'w'), auto-detected if None
    """
    dir_name = os.path.dirname(path) or "."
    base_name = os.path.basename(path)
    tmp_path = os.path.join(dir_name, f".{base_name}.tmp")
    
    # Auto-detect mode
    if mode is None:
        mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
    
    try:
        with open(tmp_path, mode, encoding=None if mode == "wb" else "utf-8") as f:
            f.write(content)
        
        # Atomic replace
        os.replace(tmp_path, path)
        
    except Exception as e:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise e


def snapshot_directory(src_dir: str, prefix: str) -> str:
    """
    Create timestamped snapshot copy of directory (non-destructive).
    
    Args:
        src_dir: Source directory to snapshot
        prefix: Prefix for snapshot directory name
        
    Returns:
        Path to created snapshot directory
    """
    stamp = now_stamp()
    dest_dir = f"./{prefix}_{stamp}"
    
    try:
        if os.path.exists(src_dir):
            shutil.copytree(src_dir, dest_dir, copy_function=shutil.copy2)
            logger.info(f"Snapshot created: {src_dir} -> {dest_dir}")
        else:
            os.makedirs(dest_dir, exist_ok=True)
            logger.info(f"Source '{src_dir}' missing; created empty snapshot at {dest_dir}")
            
    except FileExistsError:
        # Handle unlikely timestamp collision
        alt = f"{dest_dir}_1"
        shutil.copytree(src_dir, alt, copy_function=shutil.copy2)
        logger.warning(f"Snapshot destination existed; used {alt} instead")
        dest_dir = alt
        
    return dest_dir


def rotate_inputs(inputs_dir: str, inputs_queue_dir: str, 
                 inputs_staging_dir: str) -> Tuple[str, int, int]:
    """
    Execute input rotation sequence.
    
    Rotation steps:
    1) ./inputs -> ./inputs_old_{timestamp}
    2) Recreate empty ./inputs
    3) Move contents of ./inputs_queue -> ./inputs_staging
    4) Move contents of ./inputs_staging -> ./inputs
    
    Args:
        inputs_dir: Main input directory
        inputs_queue_dir: Queue directory
        inputs_staging_dir: Staging directory
        
    Returns:
        Tuple of (rotated_dir_path, queue_moved_count, staging_moved_count)
    """
    old_inputs_path = ""
    stamp = now_stamp()
    
    logger.info("=" * 70)
    logger.info("ROTATION PHASE: Input staging rotation")
    logger.info("=" * 70)
    
    # Step 1: Rotate old inputs
    if os.path.exists(inputs_dir):
        old_inputs_path = f"./inputs_old_{stamp}"
        try:
            shutil.move(inputs_dir, old_inputs_path)
            logger.info(f"✓ Rotated: {inputs_dir} -> {old_inputs_path}")
        except Exception as e:
            logger.error(f"Failed to rotate {inputs_dir} to {old_inputs_path}: {e}")
            # Best effort: try to clear
            if os.path.isdir(inputs_dir):
                try:
                    shutil.rmtree(inputs_dir)
                except Exception:
                    pass
    else:
        logger.info(f"No existing {inputs_dir} to rotate")
    
    # Step 2: Recreate empty inputs
    ensure_dir(inputs_dir)
    if not os.path.isdir(inputs_dir):
        if os.path.exists(inputs_dir):
            os.remove(inputs_dir)
        ensure_dir(inputs_dir)
    logger.info(f"✓ Created empty: {inputs_dir}")
    
    # Step 3: Queue -> Staging
    queue_count = move_contents(inputs_queue_dir, inputs_staging_dir, overwrite=True)
    if queue_count > 0:
        logger.info(f"✓ Moved {queue_count} items: {inputs_queue_dir} -> {inputs_staging_dir}")
    else:
        logger.info(f"No items in {inputs_queue_dir}")
    
    # Step 4: Staging -> Inputs
    staging_count = move_contents(inputs_staging_dir, inputs_dir, overwrite=True)
    if staging_count > 0:
        logger.info(f"✓ Moved {staging_count} items: {inputs_staging_dir} -> {inputs_dir}")
    else:
        logger.info(f"No items in {inputs_staging_dir}")
    
    # Log final state
    logger.info(f"Empty directories preserved: {inputs_queue_dir}, {inputs_staging_dir}")
    logger.info("=" * 70)
    
    return old_inputs_path, queue_count, staging_count


# ============================================================================
# Document Conversion
# ============================================================================

def generate_output_filename(input_filename: str, input_ext: str, output_ext: str) -> str:
    """
    Generate output filename with source extension to prevent collisions.
    
    Example: 
        report.pdf -> report_from_pdf.md
        report.docx -> report_from_docx.md
    
    Args:
        input_filename: Original filename without extension
        input_ext: Input file extension
        output_ext: Output file extension
        
    Returns:
        Output filename with collision-safe naming
    """
    return f"{input_filename}_from_{input_ext}.{output_ext}"


def convert_document(converter: DocumentConverter, input_path: str, output_path: str,
                    output_ext: str, retry_attempts: int = 2,
                    retry_delay: float = 1.0) -> Tuple[bool, str]:
    """
    Convert document with retry logic and validation.
    
    Args:
        converter: DocumentConverter instance
        input_path: Source file path
        output_path: Destination file path
        output_ext: Output extension (for method lookup)
        retry_attempts: Number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    for attempt in range(retry_attempts + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{retry_attempts} for {input_path}")
                time.sleep(retry_delay)
            
            # Convert
            result = converter.convert(input_path)
            
            # Validate result
            doc = getattr(result, "document", None)
            if doc is None:
                return False, "Conversion result has no 'document' attribute"
            
            # Get export method
            export_method_name = EXPORT_METHODS.get(output_ext)
            if not export_method_name:
                return False, f"No export method mapping for output type: {output_ext}"
            
            export_method = getattr(doc, export_method_name, None)
            if not callable(export_method):
                available = [a for a in dir(doc) if a.startswith("export_to_")]
                return False, f"Document missing method '{export_method_name}'. Available: {available}"
            
            # Export content
            exported_content = export_method()
            
            # Validate content
            if exported_content is None:
                return False, "Export method returned None"
            
            if isinstance(exported_content, (str, bytes)):
                if len(exported_content) == 0:
                    return False, "Export method returned empty content"
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write atomically
            atomic_write(output_path, exported_content)
            
            return True, "Success"
            
        except Exception as e:
            error_msg = f"Conversion error: {e}"
            if attempt < retry_attempts:
                logger.warning(f"{error_msg} (will retry)")
            else:
                logger.error(f"{error_msg} (max retries reached)")
                return False, error_msg
    
    return False, "Max retries reached"


# ============================================================================
# Main Processing Pipeline
# ============================================================================

class ConversionStats:
    """Track conversion statistics."""
    
    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.total_size_bytes = 0
        self.failed_files = []
        self.start_time = time.time()
    
    def add_success(self, size_bytes: int = 0):
        self.successful += 1
        self.total_size_bytes += size_bytes
    
    def add_failure(self, filepath: str, reason: str):
        self.failed += 1
        self.failed_files.append((filepath, reason))
    
    def add_skip(self):
        self.skipped += 1
    
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def summary(self) -> List[str]:
        """Generate summary lines."""
        lines = []
        lines.append("=" * 70)
        lines.append("CONVERSION STATISTICS")
        lines.append("=" * 70)
        lines.append(f"Total files discovered: {self.total_files}")
        lines.append(f"Successful conversions: {self.successful}")
        lines.append(f"Failed conversions: {self.failed}")
        lines.append(f"Skipped (same type): {self.skipped}")
        lines.append(f"Total data processed: {format_bytes(self.total_size_bytes)}")
        lines.append(f"Total runtime: {format_duration(self.elapsed_time())}")
        
        if self.failed_files:
            lines.append("")
            lines.append("Failed Files:")
            for filepath, reason in self.failed_files:
                lines.append(f"  - {filepath}: {reason}")
        
        lines.append("=" * 70)
        return lines


def process_conversions(config: Dict, dry_run: bool = False) -> ConversionStats:
    """
    Main conversion processing pipeline.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, only simulate operations without executing
        
    Returns:
        ConversionStats object with processing results
    """
    stats = ConversionStats()
    
    # Extract config
    dirs = config['directories']
    inputs_dir = dirs['inputs']
    outputs_dir = dirs['outputs']
    input_types = config['input_types']
    output_types = config['output_types']
    max_size_mb = config['max_file_size_mb']
    retry_attempts = config.get('retry_attempts', 2)
    retry_delay = config.get('retry_delay_seconds', 1.0)
    
    # Initialize converter (skip in dry-run)
    converter = None
    if not dry_run:
        try:
            converter = DocumentConverter()
            logger.info("DocumentConverter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentConverter: {e}")
            raise
    
    # Discover input files
    logger.info("=" * 70)
    logger.info("DISCOVERY PHASE: Scanning for input files")
    logger.info("=" * 70)
    
    input_files = list_input_files(inputs_dir, input_types)
    stats.total_files = len(input_files)
    
    logger.info(f"Found {len(input_files)} input files with allowed types")
    logger.info(f"Input types: {input_types}")
    logger.info(f"Output types: {output_types}")
    logger.info(f"Recursive processing: ENABLED")
    logger.info("=" * 70)
    
    if len(input_files) == 0:
        logger.warning("No input files found to process")
        return stats
    
    # Prepare run report
    run_report = []
    run_report.append(f"Document Conversion Run Report")
    run_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_report.append(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    run_report.append(f"")
    run_report.append(f"Configuration:")
    run_report.append(f"  Input types: {input_types}")
    run_report.append(f"  Output types: {output_types}")
    run_report.append(f"  Max file size: {max_size_mb}MB")
    run_report.append(f"  Inputs directory: {inputs_dir}")
    run_report.append(f"  Outputs directory: {outputs_dir}")
    run_report.append(f"  Retry attempts: {retry_attempts}")
    run_report.append(f"")
    run_report.append(f"Files discovered: {len(input_files)}")
    run_report.append(f"")
    
    # Process conversions
    logger.info("=" * 70)
    logger.info("CONVERSION PHASE: Processing documents")
    logger.info("=" * 70)
    
    for idx, (input_abs_path, input_rel_path) in enumerate(input_files, 1):
        # Progress reporting
        progress_pct = (idx / len(input_files)) * 100
        logger.info(f"[{idx}/{len(input_files)} - {progress_pct:.1f}%] Processing: {input_rel_path}")
        
        # Check file size
        is_valid, size_msg = check_file_size(input_abs_path, max_size_mb)
        if not is_valid:
            logger.warning(f"Skipping {input_rel_path}: {size_msg}")
            stats.add_failure(input_rel_path, size_msg)
            run_report.append(f"SKIPPED (size): {input_rel_path} - {size_msg}")
            continue
        else:
            logger.debug(f"  {size_msg}")
        
        # Extract info
        input_filename_no_ext = os.path.splitext(os.path.basename(input_rel_path))[0]
        _, input_ext = os.path.splitext(input_rel_path)
        input_ext = input_ext.lower().lstrip('.')
        
        # Get directory structure for mirroring
        rel_dir = os.path.dirname(input_rel_path)
        
        # Convert to each output type
        for output_ext in output_types:
            if output_ext == input_ext:
                logger.debug(f"  Skipping same-type conversion: {output_ext}")
                stats.add_skip()
                continue
            
            # Generate collision-safe output filename
            output_filename = generate_output_filename(input_filename_no_ext, input_ext, output_ext)
            
            # Mirror directory structure in outputs
            if rel_dir:
                output_path = os.path.join(outputs_dir, rel_dir, output_filename)
            else:
                output_path = os.path.join(outputs_dir, output_filename)
            
            logger.info(f"  Converting to {output_ext}: {output_filename}")
            
            if dry_run:
                logger.info(f"  [DRY RUN] Would create: {output_path}")
                stats.add_success()
                run_report.append(f"[DRY RUN] {input_rel_path} -> {output_path}")
            else:
                success, message = convert_document(
                    converter, input_abs_path, output_path, output_ext,
                    retry_attempts, retry_delay
                )
                
                if success:
                    file_size = get_file_size(input_abs_path)
                    stats.add_success(file_size)
                    logger.info(f"  ✓ Success: {output_path}")
                    run_report.append(f"SUCCESS: {input_rel_path} -> {output_path}")
                else:
                    stats.add_failure(input_rel_path, message)
                    logger.error(f"  ✗ Failed: {message}")
                    run_report.append(f"FAILED: {input_rel_path} -> {output_path} ({message})")
    
    # Add statistics to report
    run_report.append("")
    run_report.extend(stats.summary())
    
    # Save report with timestamp
    report_filename = f"run_report_{now_stamp()}.txt"
    report_path = os.path.join(outputs_dir, report_filename)
    
    try:
        ensure_dir(outputs_dir)
        atomic_write(report_path, "\n".join(run_report))
        logger.info(f"Run report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write run report to {report_path}: {e}")
    
    logger.info("=" * 70)
    
    return stats


# ============================================================================
# CLI and Main Entry Point
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Document Conversion Pipeline with Rotation and Staging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config.yaml
  python script.py
  
  # Dry run to preview operations
  python script.py --dry-run
  
  # Use custom config file
  python script.py --config my_config.yaml
  
  # Generate default config file
  python script.py --save-config
  
  # Override directories via CLI
  python script.py --inputs ./my_inputs --outputs ./my_outputs
  
  # Enable verbose logging
  python script.py --log-level DEBUG
        """
    )
    
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Path to configuration YAML file (default: config.yaml)')
    
    parser.add_argument('--save-config', action='store_true',
                       help='Save default configuration to file and exit')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate operations without executing conversions')
    
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    # Directory overrides
    parser.add_argument('--inputs', type=str,
                       help='Override inputs directory path')
    parser.add_argument('--outputs', type=str,
                       help='Override outputs directory path')
    parser.add_argument('--inputs-queue', type=str,
                       help='Override inputs_queue directory path')
    parser.add_argument('--inputs-staging', type=str,
                       help='Override inputs_staging directory path')
    
    return parser.parse_args()


def main():
    """Main entry point for the conversion pipeline."""
    args = parse_arguments()
    
    # Setup logging
    global logger
    logger = setup_logging(args.log_level)
    
    # Handle save-config
    if args.save_config:
        save_default_config(args.config)
        return 0
    
    logger.info("=" * 70)
    logger.info("DOCUMENT CONVERSION PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        logger.info("MODE: DRY RUN (no actual conversions will be performed)")
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Apply CLI overrides
        if args.inputs:
            config['directories']['inputs'] = args.inputs
        if args.outputs:
            config['directories']['outputs'] = args.outputs
        if args.inputs_queue:
            config['directories']['inputs_queue'] = args.inputs_queue
        if args.inputs_staging:
            config['directories']['inputs_staging'] = args.inputs_staging
        
        # Validate configuration
        validate_config(config)
        
        # Extract directories
        dirs = config['directories']
        inputs_dir = dirs['inputs']
        outputs_dir = dirs['outputs']
        inputs_queue_dir = dirs['inputs_queue']
        inputs_staging_dir = dirs['inputs_staging']
        
        # Ensure base directories exist
        ensure_dir(outputs_dir)
        ensure_dir(inputs_queue_dir)
        ensure_dir(inputs_staging_dir)
        
        # Snapshot outputs (before conversion, preserves previous run)
        if not args.dry_run:
            outputs_snapshot = snapshot_directory(outputs_dir, "outputs")
            logger.info(f"Previous outputs preserved at: {outputs_snapshot}")
        
        # Execute input rotation
        rotated_input, queue_moved, staging_moved = rotate_inputs(
            inputs_dir, inputs_queue_dir, inputs_staging_dir
        )
        
        # Process conversions
        stats = process_conversions(config, dry_run=args.dry_run)
        
        # Final summary
        logger.info("")
        for line in stats.summary():
            logger.info(line)
        
        logger.info("")
        logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        # Return appropriate exit code
        return 0 if stats.failed == 0 else 1
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())