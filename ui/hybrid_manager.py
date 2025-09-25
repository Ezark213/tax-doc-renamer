#!/usr/bin/env python3
"""
Hybrid Migration Manager for Modern UI Transition
Phase 5: Implementation Execution - Modern UI Migration

Manages seamless transition from tkinter to PySide6 Modern UI
with environment variable switching and feature flag management.
"""

import os
import sys
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import logging

# Environment variable for UI mode switching
UI_MODE_ENV = "TAX_DOC_UI_MODE"  # Values: "legacy" | "modern" | "auto"
FEATURE_FLAGS_ENV = "TAX_DOC_FEATURES"  # Comma-separated feature flags

class UIMode:
    """UI Mode constants"""
    LEGACY = "legacy"    # tkinter-based UI
    MODERN = "modern"    # PySide6-based Modern UI
    AUTO = "auto"        # Automatic detection

class FeatureFlags:
    """Feature flag constants for gradual migration"""
    MODERN_DRAG_DROP = "modern_drag_drop"
    MATERIAL_DESIGN = "material_design"
    ACCESSIBILITY = "accessibility"
    ANIMATIONS = "animations"
    DARK_MODE = "dark_mode"
    ENHANCED_OCR_UI = "enhanced_ocr_ui"

class HybridMigrationManager:
    """
    Manages the hybrid migration between tkinter and PySide6 UIs
    Provides seamless switching and feature flag management
    """
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.ui_mode = self._detect_ui_mode()
        self.feature_flags = self._parse_feature_flags()
        self.compatibility_checks = {}
        
        self.logger.info(f"Hybrid Migration Manager initialized - Mode: {self.ui_mode}")
        self.logger.info(f"Active feature flags: {list(self.feature_flags.keys())}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for migration manager"""
        logger = logging.getLogger("HybridMigrationManager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _detect_ui_mode(self) -> str:
        """Detect UI mode from environment or auto-detect"""
        env_mode = os.getenv(UI_MODE_ENV, UIMode.AUTO).lower()
        
        if env_mode in [UIMode.LEGACY, UIMode.MODERN]:
            return env_mode
        
        # Auto-detection logic
        try:
            import PySide6
            # Check if PySide6 is properly available
            from PySide6.QtWidgets import QApplication
            return UIMode.MODERN
        except ImportError:
            self.logger.warning("PySide6 not available, falling back to legacy mode")
            return UIMode.LEGACY
    
    def _parse_feature_flags(self) -> Dict[str, bool]:
        """Parse feature flags from environment"""
        flags_env = os.getenv(FEATURE_FLAGS_ENV, "")
        active_flags = [flag.strip() for flag in flags_env.split(",") if flag.strip()]
        
        return {
            FeatureFlags.MODERN_DRAG_DROP: FeatureFlags.MODERN_DRAG_DROP in active_flags,
            FeatureFlags.MATERIAL_DESIGN: FeatureFlags.MATERIAL_DESIGN in active_flags,
            FeatureFlags.ACCESSIBILITY: FeatureFlags.ACCESSIBILITY in active_flags,
            FeatureFlags.ANIMATIONS: FeatureFlags.ANIMATIONS in active_flags,
            FeatureFlags.DARK_MODE: FeatureFlags.DARK_MODE in active_flags,
            FeatureFlags.ENHANCED_OCR_UI: FeatureFlags.ENHANCED_OCR_UI in active_flags,
        }
    
    def is_modern_ui_enabled(self) -> bool:
        """Check if modern UI should be used"""
        return self.ui_mode == UIMode.MODERN
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if specific feature flag is enabled"""
        return self.feature_flags.get(feature, False)
    
    def get_ui_factory(self):
        """Get appropriate UI factory based on current mode"""
        if self.is_modern_ui_enabled():
            try:
                from .modern_ui_factory import ModernUIFactory
                return ModernUIFactory(self)
            except ImportError as e:
                self.logger.error(f"Modern UI factory not available: {e}")
                # Fallback to legacy
                from .legacy_ui_factory import LegacyUIFactory
                return LegacyUIFactory(self)
        else:
            from .legacy_ui_factory import LegacyUIFactory
            return LegacyUIFactory(self)
    
    def run_compatibility_checks(self) -> Dict[str, bool]:
        """Run compatibility checks for migration"""
        checks = {
            "pyside6_available": self._check_pyside6(),
            "system_requirements": self._check_system_requirements(),
            "tesseract_compatibility": self._check_tesseract_compatibility(),
            "pdf_processing": self._check_pdf_processing(),
        }
        
        self.compatibility_checks = checks
        
        # Log results
        for check, result in checks.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"Compatibility check {check}: {status}")
        
        return checks
    
    def _check_pyside6(self) -> bool:
        """Check PySide6 availability and version"""
        try:
            import PySide6
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QDragEnterEvent, QDropEvent
            return True
        except ImportError:
            return False
    
    def _check_system_requirements(self) -> bool:
        """Check system requirements for modern UI"""
        # Python version check
        if sys.version_info < (3, 8):
            return False
        
        # Memory check (simplified)
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.available > 512 * 1024 * 1024  # 512MB minimum
        except ImportError:
            # If psutil not available, assume OK
            return True
    
    def _check_tesseract_compatibility(self) -> bool:
        """Check if Tesseract works with modern UI"""
        try:
            import pytesseract
            # Basic test - if this doesn't crash, it's compatible
            return True
        except ImportError:
            return False
    
    def _check_pdf_processing(self) -> bool:
        """Check PDF processing library compatibility"""
        try:
            import PyPDF2
            import pypdf
            return True
        except ImportError:
            return False
    
    def enable_feature(self, feature: str):
        """Enable a specific feature flag"""
        self.feature_flags[feature] = True
        self.logger.info(f"Feature enabled: {feature}")
    
    def disable_feature(self, feature: str):
        """Disable a specific feature flag"""
        self.feature_flags[feature] = False
        self.logger.info(f"Feature disabled: {feature}")
    
    def switch_to_modern(self):
        """Switch to modern UI mode"""
        if self._check_pyside6():
            self.ui_mode = UIMode.MODERN
            self.logger.info("Switched to modern UI mode")
        else:
            self.logger.error("Cannot switch to modern UI: PySide6 not available")
            raise RuntimeError("PySide6 not available for modern UI")
    
    def switch_to_legacy(self):
        """Switch to legacy UI mode"""
        self.ui_mode = UIMode.LEGACY
        self.logger.info("Switched to legacy UI mode")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        return {
            "ui_mode": self.ui_mode,
            "feature_flags": self.feature_flags,
            "compatibility_checks": self.compatibility_checks,
            "modern_ui_available": self._check_pyside6(),
        }

# Singleton instance
_migration_manager = None

def get_migration_manager() -> HybridMigrationManager:
    """Get singleton migration manager instance"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = HybridMigrationManager()
    return _migration_manager

# Convenience functions
def is_modern_ui() -> bool:
    """Check if modern UI is enabled"""
    return get_migration_manager().is_modern_ui_enabled()

def is_feature_enabled(feature: str) -> bool:
    """Check if feature is enabled"""
    return get_migration_manager().is_feature_enabled(feature)

def set_ui_mode_env(mode: str):
    """Set UI mode via environment variable"""
    os.environ[UI_MODE_ENV] = mode

def set_feature_flags_env(flags: list):
    """Set feature flags via environment variable"""
    os.environ[FEATURE_FLAGS_ENV] = ",".join(flags)