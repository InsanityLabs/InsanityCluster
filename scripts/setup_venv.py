#!/usr/bin/env python3
"""
Setup script to create virtual environment and install dependencies
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Setup virtual environment and install dependencies"""
    project_root = Path(__file__).parent.parent
    venv_path = project_root / "venv"
    
    print("🚀 Setting up Insanity Cluster development environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Error: Python 3.11 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Create virtual environment
    if not venv_path.exists():
        print(f"\n📦 Creating virtual environment at {venv_path}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        print("✅ Virtual environment created")
    else:
        print(f"\n✅ Virtual environment already exists at {venv_path}")
    
    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Upgrade pip
    print("\n📦 Upgrading pip...")
    subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install requirements
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print("\n📦 Installing dependencies from requirements.txt...")
        subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], check=True)
        print("✅ Dependencies installed")
    else:
        print("⚠️  Warning: requirements.txt not found")
    
    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    env_template = project_root / ".env.template"
    if not env_file.exists() and env_template.exists():
        print("\n📝 Creating .env file from template...")
        env_file.write_text(env_template.read_text())
        print("✅ .env file created - please update with your configuration")
    
    print("\n✨ Setup complete!")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Update .env with your configuration")
    print("3. Start infrastructure services: docker-compose up -d")
    print("4. Run the application: uvicorn insanity_cluster.surface.api:app --reload")


if __name__ == "__main__":
    main()
