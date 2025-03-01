#!/usr/bin/env python
"""
Git repository cleanup script.
This script helps clean up any large files or sensitive data that may have been
staged before the .gitignore was properly set up.
"""

import os
import subprocess
import sys

def run_command(command):
    """Run a shell command and return the output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("Error: Not a git repository. Run this script from the root of your git repo.")
        return 1
    
    print("Git Repository Cleanup Utility")
    print("==============================")
    
    # Check status of the repository
    status = run_command('git status --porcelain')
    if not status:
        print("Repository is clean. No files are staged or modified.")
        return 0
    
    print("\nCurrent repository status:")
    print(run_command('git status'))
    
    # Reset any staged files to follow the new .gitignore
    print("\nResetting staged changes to apply the new .gitignore rules...")
    run_command('git reset')
    
    # List files that would be committed with current .gitignore
    print("\nFiles that would be committed with current .gitignore:")
    clean_status = run_command('git status --porcelain')
    ignored_files = run_command('git ls-files --others --ignored --exclude-standard')
    
    tracked_files = run_command('git ls-files')
    
    if tracked_files:
        print("\nFiles currently tracked by git:")
        for file in tracked_files.split('\n'):
            print(f"  {file}")
    
    if ignored_files:
        print("\nFiles properly ignored by .gitignore:")
        for file in ignored_files.split('\n'):
            if file.strip():
                print(f"  {file}")
    
    # List large files that might need special handling
    print("\nChecking for large files (>10MB) that should probably be ignored:")
    large_files = run_command('find . -type f -size +10M -not -path "./.git/*" | sort')
    
    if large_files:
        print("Large files found that might need special handling:")
        for file in large_files.split('\n'):
            if file.strip():
                size_mb = int(run_command(f'du -m "{file}" | cut -f1').strip())
                print(f"  {file} ({size_mb}MB)")
                
                # Check if file is tracked by git
                is_tracked = run_command(f'git ls-files --error-unmatch "{file}" 2>/dev/null')
                if is_tracked:
                    print(f"    WARNING: This large file is tracked by git. Consider removing it with:")
                    print(f"    git rm --cached \"{file}\"")
    else:
        print("No large files found outside of .git directory.")
    
    print("\nCleanup complete! You can now stage and commit your files with:")
    print("  git add .")
    print("  git commit -m \"Initial commit with proper .gitignore\"")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 