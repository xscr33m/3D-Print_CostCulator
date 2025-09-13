#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D Print CostCulator - Language Manager

xscr33mLabs © 2025
Version: 1.0
"""

import json
import os
import sys
from typing import Dict, Callable, Any


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class LanguageManager:
    """Manages translations and language switching"""
    
    def __init__(self, translations_dir: str = "translations"):
        # Use the resource path function for PyInstaller compatibility
        self.translations_dir = get_resource_path(translations_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.current_language = "de"  # Default: German
        self.update_callbacks: list[Callable] = []
        
        # Create translations folder if it doesn't exist (development mode)
        if not os.path.exists(self.translations_dir):
            # Try to create the directory only if we're not in a PyInstaller bundle
            try:
                if not hasattr(sys, '_MEIPASS'):
                    os.makedirs(self.translations_dir)
            except OSError:
                pass  # Ignore if we can't create it (e.g., in PyInstaller bundle)
        
        # Load available translations
        self.load_translations()
    
    def load_translations(self):
        """Loads all available translations"""
        try:
            # Load German translation
            de_path = os.path.join(self.translations_dir, "de.json")
            if os.path.exists(de_path):
                with open(de_path, 'r', encoding='utf-8') as f:
                    self.translations["de"] = json.load(f)
            
            # Load English translation
            en_path = os.path.join(self.translations_dir, "en.json")
            if os.path.exists(en_path):
                with open(en_path, 'r', encoding='utf-8') as f:
                    self.translations["en"] = json.load(f)
                    
        except Exception as e:
            print(f"Error loading translations: {e}")
    
    def get_available_languages(self) -> Dict[str, str]:
        """Returns available languages"""
        return {
            "de": "Deutsch",
            "en": "English"
        }
    
    def set_language(self, language_code: str):
        """Sets the current language"""
        if language_code in self.translations:
            self.current_language = language_code
            self.notify_update()
        else:
            print(f"Language '{language_code}' not available")
    
    def get_current_language(self) -> str:
        """Returns the current language code"""
        return self.current_language
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translates a text key
        
        Args:
            key: Translation key (e.g. "gui.window_title")
            **kwargs: Parameters for string formatting
            
        Returns:
            Translated text or key if not found
        """
        try:
            # Navigate through nested keys (e.g. "gui.window_title")
            keys = key.split('.')
            value = self.translations.get(self.current_language, {})
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return f"[{key}]"  # Show key if not found
            
            # Format string with parameters if provided
            if isinstance(value, str) and kwargs:
                return value.format(**kwargs)
            
            return str(value)
            
        except Exception as e:
            print(f"Translation error for '{key}': {e}")
            return f"[{key}]"
    
    def register_update_callback(self, callback: Callable):
        """Registers a callback function for language changes"""
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)
    
    def unregister_update_callback(self, callback: Callable):
        """Removes a callback function"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    def notify_update(self):
        """Notifies all registered callbacks about language changes"""
        for callback in self.update_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error executing update callback: {e}")
    
    def save_language_preference(self):
        """Saves the language preference to a configuration file"""
        try:
            config = {"language": self.current_language}
            with open("language_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving language preference: {e}")
    
    def load_language_preference(self):
        """Loads the saved language preference"""
        try:
            if os.path.exists("language_config.json"):
                with open("language_config.json", 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "language" in config and config["language"] in self.translations:
                        self.current_language = config["language"]
        except Exception as e:
            print(f"Error loading language preference: {e}")


# Global instance of the LanguageManager
language_manager = LanguageManager()