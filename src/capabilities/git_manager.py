import sys
import subprocess
import argparse

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing '{cmd}': {e.stderr}")
        return False

def secure_checkpoint(message: str):
    print("Executing Secure Checkpoint...")
    
    # Check status
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        print("Nothing to commit. Working tree is clean.")
        return

    # Stage changes
    print("Staging changes...")
    if not run_cmd("git add ."):
        sys.exit(1)

    # Commit
    print(f"Committing with message: '{message}'")
    # Wrap message in quotes
    safe_msg = message.replace('"', '\\"')
    if not run_cmd(f'git commit -m "{safe_msg}"'):
        sys.exit(1)

    # Push
    print("Pushing to main branch...")
    if not run_cmd("git push origin main"):
        sys.exit(1)

    print("Secure Checkpoint complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Git Manager for Secure Checkpoint")
    parser.add_argument("action", choices=["checkpoint"], help="Action to perform")
    parser.add_argument("message", help="Commit message")
    
    args = parser.parse_args()
    
    if args.action == "checkpoint":
        secure_checkpoint(args.message)
