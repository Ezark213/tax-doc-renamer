# Task Completion Checklist - Tax Document Renamer System

## When a Development Task is Completed

### 1. Code Quality Verification
- [ ] **Core modules untouched**: Verify no changes made to `core/` directory files
- [ ] **UI-only changes**: Confirm modifications are limited to layout and UI elements
- [ ] **Bundle Auto-Split preserved**: Ensure always-enabled functionality remains intact
- [ ] **YYMM policy maintained**: UI-forced YYMM system for critical documents (6001, 6002, 6003, 0000)

### 2. Testing Requirements
- [ ] **Run existing test suite**: Execute all tests in `tests/` directory
  ```bash
  cd tests
  python -m pytest
  ```
- [ ] **Critical functionality tests**: Run specific test files for recent fixes
  ```bash
  python test_duplicate_fix.py
  python test_receipt_fix.py
  python test_municipal_numbering_fix.py
  ```
- [ ] **Manual UI testing**: Verify all UI elements function correctly
- [ ] **End-to-end workflow**: Test complete document processing workflow

### 3. Build and Package Verification
- [ ] **Build executable**: Run build script to ensure no compilation errors
  ```bash
  python build.py
  ```
- [ ] **Executable testing**: Test the generated executable with sample files
- [ ] **Dependencies check**: Verify all requirements are properly listed in `requirements.txt`

### 4. Documentation Updates
- [ ] **Update README.md**: If functionality changes affect user experience
- [ ] **Update CHANGELOG.md**: Document changes made
- [ ] **Update version info**: Increment version in `version_info.py` if needed
- [ ] **Claude Code session log**: Update `CLAUDE.md` with development notes

### 5. Code Review Checklist
- [ ] **No hardcoded paths**: Ensure all file paths are properly handled
- [ ] **Error handling**: Verify proper exception handling and user feedback
- [ ] **Memory management**: Check for potential memory leaks in file processing
- [ ] **Thread safety**: Ensure background processing doesn't interfere with UI

### 6. Git Operations
- [ ] **Stage changes**: Add modified files to git staging
  ```bash
  git add .
  ```
- [ ] **Commit with descriptive message**: Include issue reference if applicable
  ```bash
  git commit -m "UI改善: 左右レイアウト最適化とBundle Auto-Split設定除去"
  ```
- [ ] **Push to repository**: Update remote repository
  ```bash
  git push origin main
  ```

### 7. Deployment Preparation
- [ ] **Version stability**: Confirm this version is stable for production use
- [ ] **Backup current version**: Ensure previous stable version is preserved
- [ ] **Migration notes**: Document any changes that affect existing installations
- [ ] **User guide updates**: Update documentation for any UI changes

## Special Considerations for UI Improvements

### Layout Changes Verification
- [ ] **Right-side consolidation**: Verify all functionality moved to right panel
- [ ] **Left-side preparation**: Confirm left panel is prepared for future rename functionality
- [ ] **Responsive design**: Check layout behavior with different window sizes
- [ ] **Font and styling**: Ensure consistent Japanese font usage (Yu Gothic UI)

### Removed UI Elements Verification
- [ ] **Bundle Auto-Split UI removed**: Confirm setting UI is removed but functionality preserved
- [ ] **File selection simplification**: Verify streamlined file selection process
- [ ] **Settings consolidation**: Check that essential settings remain accessible

### Performance Impact Assessment
- [ ] **Processing speed**: Verify UI changes don't negatively impact processing performance
- [ ] **Memory usage**: Check that UI simplification reduces memory footprint
- [ ] **User experience**: Confirm improved workflow efficiency

## Final Sign-off
- [ ] **All tests pass**: Complete test suite execution successful
- [ ] **No regressions**: All existing functionality works as expected
- [ ] **UI improvements verified**: New layout provides better user experience
- [ ] **Documentation complete**: All changes properly documented
- [ ] **Ready for production**: Version is stable and deployment-ready