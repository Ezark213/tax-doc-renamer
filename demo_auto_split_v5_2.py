#!/usr/bin/env python3
"""
Bundle PDF Auto-Split v5.2 - Demo Script
束ねPDF限定オート分割のデモンストレーション
"""

import sys
import os
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.pdf_processor import PDFProcessor
    from core.classification_v5 import DocumentClassifierV5
    
    def demo_bundle_detection():
        """Bundle detection demo"""
        print("Bundle Detection Demo")
        print("-" * 30)
        
        processor = PDFProcessor()
        classifier = DocumentClassifierV5(debug_mode=True)
        
        # Test document code detection
        print("\n📄 Document Code Detection Tests:")
        test_texts = [
            "申告受付完了通知 法人事業税 都道府県 1003",
            "納付区分番号通知 法人税及び地方法人税 0004",
            "受信通知 消費税及び地方消費税 3003",
            "納付情報発行結果 法人市民税 市役所 2004",
            "受信通知 (no specific tax info)",
            "納付情報 (no specific tax info)"
        ]
        
        for i, text in enumerate(test_texts, 1):
            code = classifier.detect_page_doc_code(text)
            print(f"  {i}. Text: {text[:50]}...")
            print(f"     Detected Code: {code or 'None'}")
        
        # Test with bundle preferences
        print("\n🎯 Bundle Preference Tests:")
        preference_tests = [
            ("受信通知", "national", "0003"),
            ("納付情報", "national", "0004"),
            ("受信通知", "local", "1003"),
            ("納付情報 都道府県", "local", "1004"),
            ("納付情報 市町村", "local", "2004")
        ]
        
        for text, prefer_bundle, expected in preference_tests:
            code = classifier.detect_page_doc_code(text, prefer_bundle)
            status = "✅" if code == expected else "❌"
            print(f"  {status} Text: '{text}', Prefer: {prefer_bundle} → {code} (expected: {expected})")
    
    def demo_config_loading():
        """Configuration loading demo"""
        print("\n⚙️ Configuration Loading Demo")
        print("-" * 30)
        
        processor = PDFProcessor()
        config = processor.config
        
        print("Bundle Detection Settings:")
        print(f"  Scan Pages: {config['bundle_detection']['scan_pages']}")
        print(f"  Thresholds: {config['bundle_detection']['thresholds']}")
        
        print("\nTarget Codes:")
        local_codes = config['target_codes']['local_tax']
        national_codes = config['target_codes']['national_tax']
        print(f"  Local Receipt: {local_codes['receipt_notifications']}")
        print(f"  Local Payment: {local_codes['payment_info']}")
        print(f"  National Receipt: {national_codes['receipt_notifications']}")
        print(f"  National Payment: {national_codes['payment_info']}")
        
        print("\nKeywords:")
        keywords = config['keywords']
        print(f"  Receipt Keywords: {keywords['receipt_notification'][:3]}...")
        print(f"  Payment Keywords: {keywords['payment_info'][:3]}...")
    
    def demo_mock_bundle_detection():
        """Mock bundle detection demo"""
        print("\n🎭 Mock Bundle Detection Demo")
        print("-" * 30)
        
        processor = PDFProcessor()
        
        # Simulate different document types
        mock_documents = [
            {
                "name": "local_tax_bundle.pdf",
                "pages": [
                    "申告受付完了通知 都道府県民税 法人事業税 1003",
                    "納付情報発行結果 都道府県 法人事業税 1004",
                    "申告受付完了通知 法人市民税 市役所 2003", 
                    "納付情報 市町村 法人市民税 2004"
                ]
            },
            {
                "name": "national_tax_bundle.pdf",
                "pages": [
                    "受信通知 法人税及び地方法人税 0003 送信されたデータを受け付けました",
                    "納付区分番号通知 法人税 0004 納付内容を確認し",
                    "受信通知 消費税及び地方消費税 3003 申告データを受付けました",
                    "納付情報 消費税 3004 納付区分番号"
                ]
            },
            {
                "name": "normal_document.pdf",
                "pages": [
                    "法人税申告書 内国法人の確定申告",
                    "貸借対照表 損益計算書",
                    "総勘定元帳 会計年度"
                ]
            }
        ]
        
        for doc in mock_documents:
            print(f"\n📄 Testing: {doc['name']}")
            
            # Simulate bundle detection logic
            combined_text = " ".join(doc['pages'])
            
            # Check receipt notifications
            receipt_keywords = ["受信通知", "申告受付完了通知", "申告受付完了"]
            receipt_matches = [kw for kw in receipt_keywords if kw in combined_text]
            
            # Check payment info
            payment_keywords = ["納付情報", "納付区分番号通知", "納付書"]
            payment_matches = [kw for kw in payment_keywords if kw in combined_text]
            
            # Check codes
            local_codes = ["1003", "1013", "1023", "1004", "2003", "2013", "2023", "2004"]
            national_codes = ["0003", "0004", "3003", "3004"]
            
            local_code_matches = [code for code in local_codes if code in combined_text]
            national_code_matches = [code for code in national_codes if code in combined_text]
            
            print(f"  Receipt matches: {receipt_matches}")
            print(f"  Payment matches: {payment_matches}")
            print(f"  Local codes: {local_code_matches}")
            print(f"  National codes: {national_code_matches}")
            
            # Determine bundle type
            has_receipt = len(receipt_matches) > 0
            has_payment = len(payment_matches) > 0
            
            if has_receipt and has_payment and len(national_code_matches) >= 2:
                bundle_type = "national"
                is_bundle = True
            elif has_receipt and has_payment and len(local_code_matches) >= 2:
                bundle_type = "local"
                is_bundle = True
            else:
                bundle_type = None
                is_bundle = False
            
            result_icon = "✅" if is_bundle else "❌"
            print(f"  {result_icon} Result: {'Bundle' if is_bundle else 'Not Bundle'} ({bundle_type or 'N/A'})")
    
    def main():
        """Main demo function"""
        print("🚀 Bundle PDF Auto-Split v5.2 - Demo")
        print("=" * 50)
        
        try:
            demo_config_loading()
            demo_bundle_detection()
            demo_mock_bundle_detection()
            
            print("\n🎉 Demo completed successfully!")
            print("\n💡 Next Steps:")
            print("1. Run 'python tests/run_tests.py' for comprehensive testing")
            print("2. Launch 'python main.py' for the full GUI application")
            print("3. Try uploading bundle PDFs to test auto-split functionality")
            
        except Exception as e:
            print(f"\n❌ Demo error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)