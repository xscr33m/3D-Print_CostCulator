#!/usr/bin/env python3
"""
Build configuration script for creating executable
"""
import subprocess
import sys
import os
import shutil

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")

def create_executable():
    """Create the executable using PyInstaller"""
    # Get the current working directory for absolute paths
    project_root = os.getcwd()
    src_path = os.path.join(project_root, "src")
    main_py_path = os.path.join(src_path, "main.py")
    translations_path = os.path.join(src_path, "translations")
    language_manager_path = os.path.join(src_path, "language_manager.py")
    icon_path = os.path.join(project_root, "assets", "icon.ico")
    
    # Verify required files exist
    if not os.path.exists(main_py_path):
        print(f"❌ Error: main.py not found at {main_py_path}")
        return False
    
    if not os.path.exists(translations_path):
        print(f"❌ Error: translations folder not found at {translations_path}")
        return False
    
    if not os.path.exists(language_manager_path):
        print(f"❌ Error: language_manager.py not found at {language_manager_path}")
        return False
    
    print(f"✓ Found main.py at: {main_py_path}")
    print(f"✓ Found translations at: {translations_path}")
    print(f"✓ Found language_manager.py at: {language_manager_path}")
    
    # Check for icon file (optional)
    has_icon = os.path.exists(icon_path)
    if has_icon:
        print(f"✓ Found icon at: {icon_path}")
    else:
        print(f"⚠️  No icon found at: {icon_path} (using default)")
    
    # PyInstaller command with all necessary options
    cmd = [
        sys.executable, "-m", "PyInstaller",  # Use python -m PyInstaller instead of direct pyinstaller
        "--onefile",                    # Single executable file
        "--windowed",                   # No console window (GUI app)
        "--name=3D-Print_CostCulator",  # Name of the executable
        "--distpath=release",           # Output directory
        "--workpath=build_temp",        # Temporary build directory
        "--specpath=build_config",      # Spec file location
    ]
    
    # Add icon if available
    if has_icon:
        cmd.append(f"--icon={icon_path}")
        
        # Add all other options
        cmd.extend([
        # Include hidden imports that might not be detected automatically
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.lib",
        "--hidden-import=reportlab.platypus",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.lib.styles",
        "--hidden-import=reportlab.lib.units",
        "--hidden-import=reportlab.lib.colors",
        
        # Include PIL for icon support
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        
        # Include data files with absolute paths
        f"--add-data={translations_path};translations",
        f"--add-data={language_manager_path};.",
    ])
    
    # Add icon as data file if it exists
    if has_icon:
        assets_path = os.path.join(project_root, "assets")
        cmd.append(f"--add-data={assets_path};assets")
    
    # Add exclude modules and main file
    cmd.extend([
        # Exclude unnecessary modules to reduce size
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=scipy",
        "--exclude-module=pandas",
        
        main_py_path  # Use full path to main.py in src folder
    ])
    
    print("Building executable...")
    print("Command:", " ".join(cmd))
    
    try:
        subprocess.check_call(cmd)
        print("✓ Executable created successfully!")
        print("📁 Location: release/3D-Print_CostCulator.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False


def cleanup_build_folders():
    """Clean up temporary build folders"""
    folders_to_clean = ["build_temp", "build_config"]
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"🧹 Cleaned up: {folder}/")
            except Exception as e:
                print(f"⚠️  Warning: Could not remove {folder}/: {e}")
        
    print("✨ Cleanup completed!")


def main():
    """Main build process"""
    print("🔨 Building 3D-Print CostCulator executable...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/main.py"):
        print("❌ Error: src/main.py not found. Please run this script from the project root.")
        return
    
    # Install PyInstaller if needed
    install_pyinstaller()
    
    # Create the executable
    if create_executable():
        print("\n🎉 Build completed successfully!")
        print("Your executable is ready for distribution:")
        print("📦 File: release/3D-Print_CostCulator.exe")
        print("💾 Size: ~20-50MB (includes Python + all dependencies)")
        print("🚀 Ready for distribution - no Python installation required!")
        
        # Clean up temporary build folders
        print("\n🧹 Cleaning up temporary build files...")
        cleanup_build_folders()
    else:
        print("\n❌ Build failed. Please check the error messages above.")
        # Still clean up even if build failed
        cleanup_build_folders()

if __name__ == "__main__":
    main()