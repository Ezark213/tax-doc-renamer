#!/usr/bin/env python3
"""
Simple test for classification fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_classification_fixes():
    """Test the highest priority keyword functionality"""
    print("=== Classification Test Results ===")
    
    classifier = DocumentClassifier(debug_mode=False)
    
    test_cases = [
        ("納付税額一覧表", "納付税額一覧表.pdf", "0000_納付税額一覧表"),
        ("総勘定元帳", "総勘定元帳.pdf", "5002_総勘定元帳"),
        ("課税期間分の消費税及び", "消費税申告.pdf", "3001_消費税及び地方消費税申告書"),
        ("内国法人の確定申告(青色)", "内国法人確定申告.pdf", "0001_法人税及び地方法人税申告書")
    ]
    
    results = []
    for text, filename, expected in test_cases:
        result = classifier.classify_document(text, filename)
        success = result.document_type == expected
        results.append(success)
        
        status = "PASS" if success else "FAIL"
        print(f"{status}: {text[:20]}... -> {result.document_type}")
        if result.classification_method == "highest_priority_keyword":
            print(f"      Method: highest_priority (SUCCESS!)")
        else:
            print(f"      Method: {result.classification_method}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    test_classification_fixes()