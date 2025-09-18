# Development Commands - Tax Document Renamer System

## Running the Application

### Development Mode
```bash
python main.py
```

### Using Claude Code MCP Integration
```bash
# The application is integrated with Claude Code via .mcp.json
# Use Claude Code for development workflow automation
```

### Quick Development Workflow (Windows)
```powershell
scripts\run.ps1
```
Note: Initial execution with Claude Code will request approval - select "2. Yes, and don't ask again" to skip future confirmations.

## Building and Packaging

### Create Executable
```bash
python build.py
```

## Testing

### Run All Tests
```bash
cd tests
python -m pytest
```

### Specific Test Files (Related to Recent Fixes)
```bash
# Duplicate processing fix tests
python test_duplicate_fix.py

# Receipt numbering fix tests  
python test_receipt_fix.py

# Municipality numbering tests
python test_municipal_numbering_fix.py

# Tokyo skip logic tests
python test_tokyo_skip_logic_comprehensive.py
python test_tokyo_skip_simple.py
```

## Development Workflow

### AddFunc-BugFix Workflow (6-Phase Process)
The project uses a systematic 6-phase development process via MCP workflow:

1. **1.analyze** - Systematic current state analysis & requirements definition
2. **2.plan** - Architecture design & implementation planning  
3. **3.check** - Quality confirmation & validity evaluation
4. **4.eval** - Risk assessment & Go/No-Go decision
5. **5.do** - Implementation execution & quality assurance
6. **6.fin** - Completion verification & production preparation

## Windows-Specific Commands

### File Operations
```cmd
# List files
dir

# Navigate directories  
cd path\to\directory

# Find files
where filename.py

# Search in files (use ripgrep if available)
rg "search_pattern" 
```

### Git Operations
```bash
git status
git add .
git commit -m "commit message"
git push origin main
```

## System Requirements

### Development Environment
- **OS**: Windows 10/11 (64bit), macOS, Linux
- **Python**: 3.8+ (development & execution environment)
- **Memory**: 4GB+ recommended (8GB+ for enterprise use)
- **Storage**: 200MB+ free space

### Dependencies Management
```bash
# Install dependencies
pip install -r requirements.txt

# Update requirements after adding new packages
pip freeze > requirements.txt
```