# Tax Document Renamer System - Codebase Structure

## Project Architecture

```
tax-doc-renamer/
├── 🎯 main.py                 # Main application entry point (TaxDocumentRenamerV5 class)
├── 🔧 build.py                # Build script for executable creation
├── 🤖 mcp_server.py           # Tax document analysis MCP server for Claude Code integration
├── 📋 .mcp.json               # Claude Code MCP configuration
├── 🏗️ core/                  # Core processing modules (NEVER MODIFY)
│   ├── classification_v5.py   # AI classification engine (v5.3.5 enhanced)
│   ├── rename_engine.py        # Rename processing (JobContext integrated)
│   ├── pre_extract.py          # Snapshot generation
│   ├── ocr_engine.py          # OCR processing engine
│   ├── pdf_processor.py       # PDF processing engine
│   ├── csv_processor.py       # CSV processing for journals
│   └── yymm_resolver.py       # YYMM resolution system
├── 🛠️ helpers/               # Advanced helper systems
│   ├── yymm_policy.py         # UI-forced YYMM policy
│   ├── run_config.py          # RunConfig central management
│   └── job_context.py         # JobContext unified management
├── 🎨 ui/                     # User interface components
│   └── drag_drop.py           # Drag & drop UI implementation
├── 🔄 workflows/              # AddFunc-BugFix Workflow
├── 🧪 tests/                  # Comprehensive test suite
├── 📚 docs/                   # Technical documentation
├── 📦 resources/              # Resource files
└── 📄 requirements.txt        # Python dependencies
```

## Key Classes and Components

### Main Application (main.py)
- **TaxDocumentRenamerV5**: Main application class with tkinter GUI
  - 45+ methods handling UI, file processing, and workflow
  - Key UI methods: `_create_file_tab()`, `_create_ui()`
  - Core processing: `_process_pdf_file_v5()`, `_folder_batch_processing_background()`

### Core Processing Modules (core/)
- **classification_v5.py**: Document classification engine
- **pdf_processor.py**: PDF manipulation and splitting
- **ocr_engine.py**: OCR text extraction with Tesseract
- **csv_processor.py**: CSV journal file handling
- **rename_engine.py**: File renaming with JobContext integration

### UI Structure (Current Implementation)
- **Left Panel**: File selection area with drag & drop
  - File/folder selection buttons
  - Selected files listbox
  - Clear functionality
- **Right Panel**: Settings and controls
  - Auto-Split control frame
  - YYMM (year-month) input
  - Municipality settings
  - Export settings

## Design Constraints
- **Core modules (core/)**: MUST NEVER BE MODIFIED - contains critical processing logic
- **UI-only changes**: Only layout changes and UI element removal/movement allowed
- **Bundle Auto-Split**: Always enabled (UI setting removed)
- **OCR Enhanced**: Always enabled (UI setting removed)
- **v5 Mode**: Always enabled (UI setting removed)