#!/usr/bin/env python3
"""
Configuration Manager for Hybrid UI System
Phase 5: Implementation Execution - Feature Flag Management

Manages UI configuration, feature flags, and runtime settings
with YAML-based configuration and environment variable support.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

class ConfigManager:
    """Manages application configuration and feature flags"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("ConfigManager")
        
        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "ui_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                self.config = self._get_default_config()
                self.save_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.config = self._get_default_config()
    
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'ui_mode': 'auto',
            'feature_flags': {
                'modern_drag_drop': True,
                'material_design': True,
                'accessibility': True,
                'animations': True,
                'dark_mode': False,
                'enhanced_ocr_ui': True,
                'progress_animations': True,
                'bulk_operations': True,
            },
            'ui_behavior': {
                'animation_duration': 200,
                'animation_easing': 'ease_out',
                'keyboard_navigation': True,
                'screen_reader_support': True,
                'focus_indicators': True,
            },
            'theme': {
                'light': {
                    'primary_color': '#1976D2',
                    'secondary_color': '#388E3C',
                    'surface_color': '#FAFAFA',
                    'background_color': '#FFFFFF',
                },
                'dark': {
                    'primary_color': '#90CAF9',
                    'secondary_color': '#A5D6A7',
                    'surface_color': '#303030',
                    'background_color': '#121212',
                }
            },
            'advanced': {
                'migration_mode': 'hybrid',
                'fallback_enabled': True,
                'compatibility_checks': True,
            }
        }
    
    def get_ui_mode(self) -> str:
        """Get UI mode with environment variable override"""
        # Environment variable takes precedence
        env_mode = os.getenv('TAX_DOC_UI_MODE')
        if env_mode:
            return env_mode.lower()
        
        return self.config.get('ui_mode', 'auto')
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags with environment variable override"""
        # Start with config flags
        flags = self.config.get('feature_flags', {}).copy()
        
        # Override with environment variable
        env_flags = os.getenv('TAX_DOC_FEATURES', '')
        if env_flags:
            # Parse comma-separated flags
            active_flags = [flag.strip() for flag in env_flags.split(',') if flag.strip()]
            
            # Reset all flags to False, then enable specified ones
            for flag in flags:
                flags[flag] = flag in active_flags
        
        return flags
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled"""
        return self.get_feature_flags().get(feature, False)
    
    def enable_feature(self, feature: str, save: bool = True):
        """Enable a feature flag"""
        if 'feature_flags' not in self.config:
            self.config['feature_flags'] = {}
        
        self.config['feature_flags'][feature] = True
        
        if save:
            self.save_config()
        
        self.logger.info(f"Feature enabled: {feature}")
    
    def disable_feature(self, feature: str, save: bool = True):
        """Disable a feature flag"""
        if 'feature_flags' not in self.config:
            self.config['feature_flags'] = {}
        
        self.config['feature_flags'][feature] = False
        
        if save:
            self.save_config()
        
        self.logger.info(f"Feature disabled: {feature}")
    
    def get_theme_config(self, theme_name: str = 'light') -> Dict[str, str]:
        """Get theme configuration"""
        themes = self.config.get('theme', {})
        return themes.get(theme_name, themes.get('light', {}))
    
    def get_ui_behavior(self) -> Dict[str, Any]:
        """Get UI behavior settings"""
        return self.config.get('ui_behavior', {})
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration"""
        return self.config.get('advanced', {})
    
    def get_platform_config(self) -> Dict[str, Any]:
        """Get platform-specific configuration"""
        platform_config = self.config.get('platform', {})
        
        # Get current platform settings
        import sys
        if sys.platform == 'win32':
            return platform_config.get('windows', {})
        elif sys.platform == 'darwin':
            return platform_config.get('macos', {})
        else:
            return platform_config.get('linux', {})
    
    def get_tax_system_config(self) -> Dict[str, Any]:
        """Get tax system specific configuration"""
        return self.config.get('tax_system', {})
    
    def get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration"""
        return self.config.get('fallback', {})
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv('TAX_DOC_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    def is_safe_mode(self) -> bool:
        """Check if safe mode is enabled"""
        fallback_config = self.get_fallback_config()
        return fallback_config.get('safe_mode', False)
    
    def should_force_legacy(self) -> bool:
        """Check if legacy mode should be forced"""
        fallback_config = self.get_fallback_config()
        return fallback_config.get('force_legacy', False)
    
    def is_modern_ui_disabled(self) -> bool:
        """Check if modern UI is completely disabled"""
        fallback_config = self.get_fallback_config()
        return fallback_config.get('disable_modern_ui', False)
    
    def update_config(self, updates: Dict[str, Any], save: bool = True):
        """Update configuration with dictionary"""
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self.config, updates)
        
        if save:
            self.save_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'ui_mode': self.get_ui_mode(),
            'feature_flags': self.get_feature_flags(),
            'debug_mode': self.is_debug_mode(),
            'safe_mode': self.is_safe_mode(),
            'force_legacy': self.should_force_legacy(),
            'modern_ui_disabled': self.is_modern_ui_disabled(),
            'config_path': str(self.config_path),
            'config_exists': self.config_path.exists(),
        }
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required sections
        required_sections = ['ui_mode', 'feature_flags', 'ui_behavior', 'theme']
        for section in required_sections:
            if section not in self.config:
                issues.append(f"Missing required section: {section}")
        
        # Validate UI mode
        valid_ui_modes = ['legacy', 'modern', 'auto']
        ui_mode = self.get_ui_mode()
        if ui_mode not in valid_ui_modes:
            issues.append(f"Invalid UI mode: {ui_mode}. Must be one of {valid_ui_modes}")
        
        # Validate feature flags
        feature_flags = self.get_feature_flags()
        for flag, value in feature_flags.items():
            if not isinstance(value, bool):
                issues.append(f"Feature flag '{flag}' must be boolean, got {type(value).__name__}")
        
        # Validate theme colors
        themes = self.config.get('theme', {})
        for theme_name, theme_config in themes.items():
            for color_name, color_value in theme_config.items():
                if not isinstance(color_value, str) or not color_value.startswith('#'):
                    issues.append(f"Invalid color '{color_name}' in theme '{theme_name}': {color_value}")
        
        return issues
    
    def reset_to_defaults(self, save: bool = True):
        """Reset configuration to defaults"""
        self.config = self._get_default_config()
        
        if save:
            self.save_config()
        
        self.logger.info("Configuration reset to defaults")

# Singleton instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get singleton configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager