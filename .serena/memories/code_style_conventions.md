# Code Style and Conventions - Tax Document Renamer System

## Python Code Style

### Naming Conventions
- **Classes**: PascalCase (e.g., `TaxDocumentRenamerV5`, `AutoSplitControlFrame`)
- **Methods/Functions**: snake_case with leading underscore for private methods (e.g., `_create_file_tab`, `_process_pdf_file_v5`)
- **Variables**: snake_case (e.g., `year_month_var`, `files_listbox`, `municipality_sets`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `AUTO_SPLIT_DEFAULT`, `DEBUG_OUTPUT_DEFAULT`)

### Documentation Style
- **Docstrings**: Japanese language docstrings for methods (e.g., `"""ファイル選択タブの作成"""`)
- **Comments**: Mix of Japanese and English, with Japanese for UI-related descriptions
- **Type Hints**: Limited usage, primarily for complex data structures

### File Organization
- **Main application**: Single large class `TaxDocumentRenamerV5` in `main.py` (~1733 lines)
- **Core modules**: Separate files in `core/` directory for specific functionality
- **Helper modules**: `helpers/` directory for policy and configuration management
- **UI components**: Separate modules in `ui/` directory

## GUI Framework Patterns

### tkinter/ttk Usage
- **Modern styling**: Uses `ttk` (themed tkinter) for modern widget appearance
- **Layout management**: Primarily `pack()` and `grid()` geometry managers
- **Frame organization**: Nested frame structure for complex layouts
- **Event handling**: Callback methods with `_` prefix (e.g., `_on_files_dropped`)

### UI Layout Patterns
```python
# Standard frame creation pattern
frame = ttk.Frame(parent)
frame.pack(fill='both', expand=True, pady=(0, 10))

# Label creation with styling
ttk.Label(frame, text="設定・Auto-Split", font=('Arial', 12, 'bold')).pack(pady=(0, 10))

# Button creation with emojis
ttk.Button(frame, text="📁 ファイル選択", command=self._select_files).pack(side='left', padx=(0, 5))
```

### Current UI Structure
- **Left-Right Split**: PanedWindow with 2:1 weight ratio
- **Left Panel**: File selection, drag & drop, file list
- **Right Panel**: Settings, controls, and processing options
- **Tab-based**: Notebook widget with File, Results, and Log tabs

## Architecture Patterns

### JobContext Pattern
```python
@dataclass
class JobContext:
    job_id: str
    confirmed_yymm: Optional[str]
    yymm_source: str
    run_config: Optional[RunConfig]
```

### Processing Pipeline
1. **File Input** → Drag & drop or file selection
2. **YYMM Validation** → UI input validation
3. **OCR Processing** → Text extraction from PDFs
4. **Classification** → Document type identification
5. **Rename Processing** → Final filename generation

## Critical Design Principles

### UI-Forced YYMM System
```python
# Critical documents require UI YYMM input
ui_forced_codes = {"6001", "6002", "6003", "0000"}

if code4 in ui_forced_codes:
    if not self.confirmed_yymm or self.yymm_source not in ("UI", "UI_FORCED"):
        raise ValueError(f"[FATAL][JOB_CONTEXT] UI YYMM required but missing for {code4}")
```

### Always-Enabled Features
```python
# These features are always enabled (no UI controls)
self.auto_split_enabled = True  # Bundle Auto-Split always ON
self.debug_enabled = True       # Debug output always ON
self.v5_mode_enabled = True     # v5 processing mode always ON
```

## Error Handling Patterns

### Logging Integration
```python
def _log(self, message, level='INFO'):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    # Display in UI and log to file
```

### Exception Handling
- **Graceful degradation**: UI remains responsive during processing errors
- **User feedback**: Error messages displayed in results tab
- **Debug information**: Detailed logging for troubleshooting

## Testing Patterns

### Test File Naming
- `test_duplicate_fix.py` - Duplicate processing tests
- `test_receipt_fix.py` - Receipt numbering tests
- `test_municipal_numbering_fix.py` - Municipality numbering tests

### Test Structure
```python
def test_specific_functionality():
    # Setup test data
    # Execute functionality
    # Assert expected results
    # Clean up if necessary
```