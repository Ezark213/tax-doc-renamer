# Suggested Commands - Tax Document Renamer System

## Essential Development Commands

### Application Execution
```bash
# Run main application
python main.py

# Quick development workflow (Windows)
scripts\run.ps1
```

### Testing Commands
```bash
# Run all tests
cd tests && python -m pytest

# Run specific critical tests
python test_duplicate_fix.py
python test_receipt_fix.py
python test_municipal_numbering_fix.py
python test_tokyo_skip_logic_comprehensive.py
```

### Build and Package
```bash
# Create executable
python build.py

# Install dependencies
pip install -r requirements.txt
```

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit changes
git commit -m "descriptive message"

# Push to remote
git push origin main
```

### File Operations (Windows)
```cmd
# List directory contents
dir

# Navigate to project directory
cd C:\Users\mayum\tax-doc-renamer

# Find files
where /R . *.py

# Search in files (if ripgrep available)
rg "search_pattern"
```

### Development Utilities
```bash
# Export keyword dictionary (from within application)
# Use UI button: "📤 キーワード辞書をエクスポート"

# Check Python version
python --version

# List installed packages
pip list

# Create requirements file
pip freeze > requirements.txt
```

## Claude Code MCP Integration

### MCP Server Configuration
```json
{
  "mcpServers": {
    "tax-document-analyzer": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "C:\\Users\\mayum\\tax-doc-renamer"
    },
    "serena-workflow": {
      "command": "python", 
      "args": ["-c", "from workflows.workflow_manager import WorkflowManager; WorkflowManager().run_mcp_server()"],
      "cwd": "C:\\Users\\mayum\\tax-doc-renamer"
    }
  }
}
```

### AddFunc-BugFix Workflow Commands
```bash
# Access via Claude Code MCP integration
# 6-phase systematic development process:
# 1.analyze → 2.plan → 3.check → 4.eval → 5.do → 6.fin
```

## Emergency Commands

### System Recovery
```bash
# If application crashes or hangs
taskkill /f /im python.exe

# Clean up temporary files
del /s /q *.tmp

# Reset to last known good version
git reset --hard HEAD~1
```

### Backup and Restore
```bash
# Create backup of current version
xcopy /s /e /h . ..\tax-doc-renamer-backup\

# Restore from backup
xcopy /s /e /h ..\tax-doc-renamer-backup\* .
```

## Performance and Monitoring

### Performance Testing
```bash
# Time application startup
python -c "import time; start=time.time(); import main; print(f'Startup time: {time.time()-start:.2f}s')"

# Memory usage monitoring (install psutil if needed)
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

### Log Analysis
```bash
# View recent logs (if logging to file)
tail -f logs\application.log

# Search for errors in logs
findstr "ERROR" logs\*.log
```

## Quick Reference Commands

### Most Used Development Commands
1. `python main.py` - Run application
2. `cd tests && python -m pytest` - Run tests
3. `python build.py` - Build executable
4. `git add . && git commit -m "message" && git push` - Git workflow
5. `scripts\run.ps1` - Quick development (Windows)

### Troubleshooting Commands
1. `python --version` - Check Python version
2. `pip list` - Check installed packages
3. `where python` - Find Python installation
4. `tasklist | findstr python` - Check running Python processes
5. `dir /s *.py` - Find all Python files in project