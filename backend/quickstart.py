"""
Quick Start Guide for Resume Matcher
Complete setup in 5 minutes
"""

import os
import platform


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_python():
    """Check Python version"""
    print("✓ Checking Python version...")
    version = platform.python_version()
    print(f"  Python {version}")
    
    if version < '3.8':
        print("  ⚠️  Python 3.8+ required")
        return False
    return True


def install_dependencies():
    """Install required packages"""
    print_header("Step 1: Installing Dependencies")
    
    try:
        import subprocess
        print("Installing packages from requirements.txt...")
        result = subprocess.run(['pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ All packages installed successfully\n")
            return True
        else:
            print(f"✗ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def download_spacy_model():
    """Download spaCy NLP model"""
    print_header("Step 2: Downloading spaCy Model")
    
    try:
        import subprocess
        print("Downloading en_core_web_sm model (~50 MB)...")
        result = subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ spaCy model downloaded successfully\n")
            return True
        else:
            print("Note: You can download later with:")
            print("  python -m spacy download en_core_web_sm\n")
            return False
    except Exception as e:
        print(f"Note: Download manually if needed: {str(e)}\n")
        return False


def create_env_file():
    """Create .env file"""
    print_header("Step 3: Creating Environment File")
    
    env_content = """FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Created .env file\n")
        return True
    else:
        print("✓ .env file already exists\n")
        return True


def create_directories():
    """Create required directories"""
    print_header("Step 4: Creating Directories")
    
    directories = ['uploads', 'models', 'logs']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created '{directory}' directory")
        else:
            print(f"✓ '{directory}' directory exists")
    
    print()
    return True


def train_models():
    """Train ML models"""
    print_header("Step 5: Training Models")
    
    print("Initializing and training ML models...")
    print("This may take a minute...\n")
    
    try:
        import subprocess
        result = subprocess.run(['python', 'train_models.py'],
                              capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("✓ Models trained successfully\n")
            return True
        else:
            print("Note: You can train models later with: python train_models.py\n")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Model training timed out\n")
        return False
    except Exception as e:
        print(f"Note: Could not auto-train models: {str(e)}")
        print("Run this later: python train_models.py\n")
        return True  # Don't fail on this


def main():
    """Main setup routine"""
    
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "🚀 AI RESUME MATCHER - QUICK START" + " "*14 + "║")
    print("╚" + "="*58 + "╝")
    
    steps = [
        ("Python Version", check_python),
        ("Install Dependencies", install_dependencies),
        ("Download spaCy Model", download_spacy_model),
        ("Setup Environment", create_env_file),
        ("Create Directories", create_directories),
        ("Train Models", train_models),
    ]
    
    results = {}
    
    for step_name, step_func in steps:
        try:
            results[step_name] = step_func()
        except Exception as e:
            print(f"✗ Error in {step_name}: {str(e)}\n")
            results[step_name] = False
    
    # Summary
    print_header("Setup Summary")
    
    for step_name, result in results.items():
        status = "✓" if result else "⚠️ "
        print(f"{status} {step_name}")
    
    print("\n" + "="*60)
    
    if all(results.values()):
        print("\n✨ Setup complete! You're ready to go!\n")
        print("Start the application with:")
        print("  python run.py\n")
        print("Then open: http://localhost:5000\n")
    else:
        print("\n⚠️  Setup completed with some warnings/issues.\n")
        print("Try running: python run.py\n")
        print("If issues persist, check the error messages above.\n")
    
    print("="*60 + "\n")
    
    return all(results.values())


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
