# Tax Document Renamer System v5.4.6-stable - Project Overview

## Project Purpose
Japanese tax document automatic classification and renaming system with enterprise-grade features. Combines OCR functionality, AI classification engine, dynamic receipt notification numbering system, and prefecture tax return serial numbering system to provide reliable and highly accurate tax document management.

## Tech Stack Used
- **Python 3.13+** (main language)
- **GUI Framework**: tkinter with ttk for modern styling
- **PDF Processing**: PyPDF2 (3.0.1), pypdf (4.0.0), PyMuPDF (1.23.8)
- **OCR Engine**: pytesseract (0.3.10) with Tesseract OCR backend
- **Image Processing**: Pillow (>=10.0)
- **Data Processing**: pandas (2.0.3) for CSV handling
- **Configuration**: PyYAML (6.0.1)
- **Modern UI**: PySide6 (>=6.7) components
- **Build Tool**: PyInstaller (6.15.0) for executable creation

## Main Features
- **23 types of tax documents** automatic classification (0000-7002 numbering system)
- **Bundle PDF Auto-Split**: Automatically detects bundled PDFs and splits them into individual files
- **OCR-based content analysis**: Classification based on actual document content, not just keywords
- **Dynamic municipality numbering**: Automatic detection of prefecture/municipality names with serial numbering
- **CSV journal support**: Special handling for CSV format accounting journals (5006_仕訳帳_YYMM.csv)
- **UI-forced YYMM system**: Ensures critical documents use UI-entered period values
- **Drag & drop interface**: Simple operation through drag & drop
- **Batch processing**: Multiple file processing support

## Current Version Status
- **Latest Stable**: v5.4.6-stable (2025-09-18)
- **Critical Fixes Completed**:
  - ✅ Duplicate processing infinite loop fix (v5.4.4 inherited)
  - ✅ CSV journal support (5006_仕訳帳_YYMM.csv)
  - ✅ Municipality tax numbering fix (2003→2001 base)
  - ✅ Municipality receipt notification numbering fix (Tokyo skip unified)
  - ✅ Bundle split dynamic numbering generation support