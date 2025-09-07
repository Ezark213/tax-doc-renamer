#!/usr/bin/env python3
"""
Bundle PDF Auto-Split v5.2 - Demo Script (Simple Version)
束ねPDF限定オート分割のデモンストレーション
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main demo function"""
    print("Bundle PDF Auto-Split v5.2 - Demo")
    print("=" * 50)
    
    try:
        from core.pdf_processor import PDFProcessor
        from core.classification_v5 import DocumentClassifierV5
        
        print("\n1. Configuration Loading Test")
        processor = PDFProcessor()
        config = processor.config
        
        print("Bundle Detection Settings:")
        print(f"  Scan Pages: {config['bundle_detection']['scan_pages']}")
        print(f"  Thresholds: {config['bundle_detection']['thresholds']}")
        
        print("\n2. Document Code Detection Test")
        classifier = DocumentClassifierV5(debug_mode=False)
        
        test_texts = [
            "申告受付完了通知 法人事業税 都道府県 1003",
            "納付区分番号通知 法人税及び地方法人税 0004",
            "受信通知 消費税及び地方消費税 3003",
            "納付情報発行結果 法人市民税 市役所 2004"
        ]
        
        for i, text in enumerate(test_texts, 1):
            code = classifier.detect_page_doc_code(text)
            print(f"  {i}. Text: {text[:40]}...")
            print(f"     Detected Code: {code or 'None'}")
        
        print("\n3. Bundle Preference Test")
        preference_tests = [
            ("受信通知", "national", "0003"),
            ("納付情報", "national", "0004"),
            ("受信通知", "local", "1003"),
            ("納付情報 都道府県", "local", "1004")
        ]
        
        for text, prefer_bundle, expected in preference_tests:
            code = classifier.detect_page_doc_code(text, prefer_bundle)
            status = "[OK]" if code == expected else "[FAIL]"
            print(f"  {status} Text: '{text}', Prefer: {prefer_bundle} -> {code} (expected: {expected})")
        
        print("\nDemo completed successfully!")
        print("\nNext Steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run tests: python tests/run_tests.py") 
        print("3. Launch GUI: python main.py")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to install dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)