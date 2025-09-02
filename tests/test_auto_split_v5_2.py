#!/usr/bin/env python3
"""
Test suite for Bundle PDF Auto-Split functionality v5.2
束ねPDF限定オート分割機能のテストスイート
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pdf_processor import PDFProcessor, BundleDetectionResult
from core.classification_v5 import DocumentClassifierV5


class TestBundleDetection(unittest.TestCase):
    """Bundle PDF detection tests"""
    
    def setUp(self):
        """Test setup"""
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_processor = PDFProcessor()
        
    def tearDown(self):
        """Test cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_mock_pdf_pages(self, page_texts: list) -> Mock:
        """Create mock PDF with specified page texts"""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=len(page_texts))
        mock_doc.pages = []
        
        for i, text in enumerate(page_texts):
            mock_page = Mock()
            mock_page.get_text.return_value = text
            mock_doc.pages.append(mock_page)
        
        return mock_doc
    
    @patch('fitz.open')
    def test_local_tax_bundle_detection(self, mock_fitz_open):
        """Test local tax bundle detection"""
        # Mock PDF content for local tax bundle
        sample_texts = [
            "申告受付完了通知 都道府県民税 法人事業税 1003",
            "納付情報発行結果 法人事業税 都道府県 1004", 
            "申告受付完了通知 法人市民税 市役所 2003",
            "納付情報 法人市民税 市町村 2004"
        ]
        
        mock_doc = self.create_mock_pdf_pages(sample_texts)
        mock_fitz_open.return_value = mock_doc
        
        result = self.pdf_processor._detect_bundle_type("mock_local_bundle.pdf")
        
        self.assertTrue(result.is_bundle)
        self.assertEqual(result.bundle_type, "local")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertGreater(len(result.matched_elements["receipt"]), 0)
        self.assertGreater(len(result.matched_elements["payment"]), 0)
    
    @patch('fitz.open')
    def test_national_tax_bundle_detection(self, mock_fitz_open):
        """Test national tax bundle detection"""
        # Mock PDF content for national tax bundle
        sample_texts = [
            "受信通知 法人税及び地方法人税 0003 送信されたデータを受け付けました",
            "納付区分番号通知 法人税 0004 納付内容を確認し",
            "受信通知 消費税及び地方消費税 3003 申告データを受付けました", 
            "納付情報 消費税 3004 納付区分番号"
        ]
        
        mock_doc = self.create_mock_pdf_pages(sample_texts)
        mock_fitz_open.return_value = mock_doc
        
        result = self.pdf_processor._detect_bundle_type("mock_national_bundle.pdf")
        
        self.assertTrue(result.is_bundle)
        self.assertEqual(result.bundle_type, "national")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertGreater(len(result.matched_elements["receipt"]), 0)
        self.assertGreater(len(result.matched_elements["payment"]), 0)
    
    @patch('fitz.open')
    def test_non_bundle_detection(self, mock_fitz_open):
        """Test non-bundle PDF detection (should not split)"""
        # Mock PDF content for normal document (not a bundle)
        sample_texts = [
            "法人税申告書 内国法人の確定申告",
            "貸借対照表 損益計算書",
            "総勘定元帳 会計年度"
        ]
        
        mock_doc = self.create_mock_pdf_pages(sample_texts)
        mock_fitz_open.return_value = mock_doc
        
        result = self.pdf_processor._detect_bundle_type("mock_normal_doc.pdf")
        
        self.assertFalse(result.is_bundle)
        self.assertIsNone(result.bundle_type)
        self.assertEqual(result.confidence, 0.0)
    
    @patch('fitz.open')
    def test_ambiguous_document_detection(self, mock_fitz_open):
        """Test detection of ambiguous documents (edge cases)"""
        # Mock PDF with only partial keywords
        sample_texts = [
            "受信通知 何らかの内容",  # Has receipt keyword but no tax category
            "その他の文書内容",
            ""
        ]
        
        mock_doc = self.create_mock_pdf_pages(sample_texts)
        mock_fitz_open.return_value = mock_doc
        
        result = self.pdf_processor._detect_bundle_type("mock_ambiguous.pdf")
        
        self.assertFalse(result.is_bundle)  # Should not be detected as bundle
        self.assertIsNone(result.bundle_type)


class TestDocumentCodeDetection(unittest.TestCase):
    """Document code detection tests"""
    
    def setUp(self):
        """Test setup"""
        self.classifier = DocumentClassifierV5(debug_mode=False)
    
    def test_strong_code_pattern_detection(self):
        """Test strong code pattern detection"""
        test_cases = [
            ("申告受付完了通知 1003 都道府県", "1003"),
            ("納付区分番号通知 0004 法人税", "0004"),
            ("受信通知 3003 消費税", "3003"),
            ("納付情報発行 2004 市町村税", "2004"),
            ("その他の文書 1013 受信通知", "1013"),
            ("強制分割テスト 2023 地方税", "2023")
        ]
        
        for text, expected_code in test_cases:
            with self.subTest(text=text):
                result = self.classifier.detect_page_doc_code(text)
                self.assertEqual(result, expected_code)
    
    def test_keyword_combination_detection(self):
        """Test keyword combination detection"""
        test_cases = [
            ("受信通知 法人税及び地方法人税", None, "0003"),
            ("納付情報 法人税", None, "0004"),
            ("受信通知 消費税及び地方消費税", None, "3003"),
            ("納付区分番号通知 消費税", None, "3004"),
            ("申告受付完了通知 都道府県民税 事業税", None, "1003"),
            ("納付情報 都道府県 法人事業税", None, "1004"),
            ("受信通知 法人市民税 市役所", None, "2003"),
            ("納付情報 市町村 法人市民税", None, "2004")
        ]
        
        for text, prefer_bundle, expected_code in test_cases:
            with self.subTest(text=text):
                result = self.classifier.detect_page_doc_code(text, prefer_bundle)
                self.assertEqual(result, expected_code)
    
    def test_bundle_preference_heuristics(self):
        """Test bundle preference heuristics"""
        # National bundle preferences
        result = self.classifier.detect_page_doc_code("受信通知", "national")
        self.assertEqual(result, "0003")
        
        result = self.classifier.detect_page_doc_code("納付情報", "national")
        self.assertEqual(result, "0004")
        
        # Local bundle preferences
        result = self.classifier.detect_page_doc_code("受信通知", "local")
        self.assertEqual(result, "1003")
        
        result = self.classifier.detect_page_doc_code("納付情報 都道府県", "local")
        self.assertEqual(result, "1004")
        
        result = self.classifier.detect_page_doc_code("納付情報 市町村", "local")
        self.assertEqual(result, "2004")
    
    def test_no_detection_cases(self):
        """Test cases where no code should be detected"""
        test_cases = [
            "",
            "通常の申告書類",
            "決算書 貸借対照表",
            "総勘定元帳 仕訳帳",
            "その他の書類"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                result = self.classifier.detect_page_doc_code(text)
                self.assertIsNone(result)


class TestAutoSplitIntegration(unittest.TestCase):
    """Auto-split integration tests"""
    
    def setUp(self):
        """Test setup"""
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_processor = PDFProcessor()
        
    def tearDown(self):
        """Test cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('fitz.open')
    @patch('pypdf.PdfReader')
    @patch('pypdf.PdfWriter')
    def test_bundle_split_execution(self, mock_writer, mock_reader, mock_fitz_open):
        """Test complete bundle split execution"""
        # Setup mocks
        mock_detection_result = BundleDetectionResult(
            is_bundle=True,
            bundle_type="local",
            confidence=0.9,
            matched_elements={"receipt": ["受信通知"], "payment": ["納付情報"], "codes": ["1003"]},
            debug_info=["Test bundle detected"]
        )
        
        # Mock PDF reader with 4 pages
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [Mock(), Mock(), Mock(), Mock()]
        mock_reader.return_value = mock_reader_instance
        
        # Mock writer
        mock_writer_instance = Mock()
        mock_writer.return_value = mock_writer_instance
        
        with patch.object(self.pdf_processor, '_detect_bundle_type', return_value=mock_detection_result):
            result = self.pdf_processor.maybe_split_pdf(
                "test_bundle.pdf", 
                self.temp_dir, 
                force=False,
                processing_callback=None
            )
        
        self.assertTrue(result)
    
    def test_force_split_mode(self):
        """Test force split mode (should split regardless of detection)"""
        with patch('fitz.open'), patch('pypdf.PdfReader') as mock_reader, patch('pypdf.PdfWriter'):
            # Mock non-bundle detection
            mock_detection_result = BundleDetectionResult(
                is_bundle=False,
                bundle_type=None,
                confidence=0.0,
                matched_elements={"receipt": [], "payment": [], "codes": []},
                debug_info=["Not a bundle"]
            )
            
            mock_reader_instance = Mock()
            mock_reader_instance.pages = [Mock(), Mock()]
            mock_reader.return_value = mock_reader_instance
            
            with patch.object(self.pdf_processor, '_detect_bundle_type', return_value=mock_detection_result):
                # Force split should work even for non-bundles
                result = self.pdf_processor.maybe_split_pdf(
                    "test_force.pdf", 
                    self.temp_dir, 
                    force=True,
                    processing_callback=None
                )
            
            self.assertTrue(result)  # Should succeed with force=True
    
    def test_non_bundle_skip(self):
        """Test that non-bundle PDFs are skipped (not split)"""
        with patch('fitz.open'):
            mock_detection_result = BundleDetectionResult(
                is_bundle=False,
                bundle_type=None,
                confidence=0.0,
                matched_elements={"receipt": [], "payment": [], "codes": []},
                debug_info=["Not a bundle"]
            )
            
            with patch.object(self.pdf_processor, '_detect_bundle_type', return_value=mock_detection_result):
                result = self.pdf_processor.maybe_split_pdf(
                    "test_normal.pdf", 
                    self.temp_dir, 
                    force=False,
                    processing_callback=None
                )
            
            self.assertFalse(result)  # Should not split


class TestConfigurationLoading(unittest.TestCase):
    """Configuration loading tests"""
    
    def test_default_config_fallback(self):
        """Test that default config is used when file is missing"""
        pdf_processor = PDFProcessor()
        config = pdf_processor.config
        
        # Check that essential config keys exist
        self.assertIn("bundle_detection", config)
        self.assertIn("target_codes", config)
        self.assertIn("keywords", config)
        
        # Check specific values
        self.assertEqual(config["bundle_detection"]["scan_pages"], 10)
        self.assertIn("local_tax", config["target_codes"])
        self.assertIn("national_tax", config["target_codes"])
    
    def test_config_values(self):
        """Test that configuration values are correctly structured"""
        pdf_processor = PDFProcessor()
        config = pdf_processor.config
        
        # Bundle detection config
        bundle_config = config["bundle_detection"]
        self.assertIsInstance(bundle_config["scan_pages"], int)
        self.assertIn("thresholds", bundle_config)
        
        # Target codes config  
        target_codes = config["target_codes"]
        self.assertIn("receipt_notifications", target_codes["local_tax"])
        self.assertIn("payment_info", target_codes["local_tax"])
        self.assertIn("receipt_notifications", target_codes["national_tax"])
        self.assertIn("payment_info", target_codes["national_tax"])
        
        # Keywords config
        keywords = config["keywords"]
        self.assertIn("receipt_notification", keywords)
        self.assertIn("payment_info", keywords)
        self.assertIn("tax_categories", keywords)


class TestErrorHandling(unittest.TestCase):
    """Error handling tests"""
    
    def setUp(self):
        """Test setup"""
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_processor = PDFProcessor()
        
    def tearDown(self):
        """Test cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_invalid_pdf_handling(self):
        """Test handling of invalid PDF files"""
        with patch('fitz.open', side_effect=Exception("Invalid PDF")):
            result = self.pdf_processor._detect_bundle_type("invalid.pdf")
            
            self.assertFalse(result.is_bundle)
            self.assertIn("Detection error", str(result.debug_info))
    
    def test_split_execution_error_handling(self):
        """Test error handling during split execution"""
        with patch('pypdf.PdfReader', side_effect=Exception("Read error")):
            result = self.pdf_processor._execute_bundle_split(
                "error.pdf", self.temp_dir, "local", None
            )
            
            self.assertFalse(result)
    
    def test_empty_file_list_handling(self):
        """Test handling of empty or invalid file lists"""
        classifier = DocumentClassifierV5(debug_mode=False)
        
        # Empty text
        result = classifier.detect_page_doc_code("")
        self.assertIsNone(result)
        
        # None input
        result = classifier.detect_page_doc_code(None)
        self.assertIsNone(result)


def run_test_suite():
    """Run the complete test suite"""
    print("Running Bundle PDF Auto-Split Test Suite v5.2")
    print("=" * 60)
    
    # Create test suite
    test_modules = [
        TestBundleDetection,
        TestDocumentCodeDetection,
        TestAutoSplitIntegration,
        TestConfigurationLoading,
        TestErrorHandling
    ]
    
    suite = unittest.TestSuite()
    
    for test_module in test_modules:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_module)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 All tests passed! Bundle PDF Auto-Split v5.2 is ready for production.")
    elif success_rate >= 80:
        print("⚠️ Most tests passed. Review failures before deployment.")
    else:
        print("❌ Multiple test failures. Further development required.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the test suite
    success = run_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)