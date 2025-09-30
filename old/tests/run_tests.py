#!/usr/bin/env python3
"""
Simple test runner for Bundle PDF Auto-Split v5.2
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from test_auto_split_v5_2 import run_test_suite
    
    print("Bundle PDF Auto-Split v5.2 - Test Runner")
    print("=" * 50)
    
    success = run_test_suite()
    
    if success:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Check output above for details.")
    
    sys.exit(0 if success else 1)
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"Test execution error: {e}")
    sys.exit(1)