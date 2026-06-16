"""
Module for managing secure Git checkpoints and synchronizing upstream.
"""

import argparse
import subprocess
import sys


def run_cmd(cmd: str) -> bool:
    """
    Executes a shell command safely, capturing output.

    Args:
        cmd: The shell command to execute.

    Returns:
        True if the command succeeded, False otherwise.
    """
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing '{cmd}': {e.stderr}")
        return False


def secure_checkpoint(message: str) -> None:
    """
    Automates staging, committing, and pushing changes safely.

    Args:
        message: The commit message.
    """
    print("Executing Secure Checkpoint...")

    # Check status safely
    result = subprocess.run(
        "git status --porcelain",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        print("Nothing to commit. Working tree is clean.")
        return

    # Stage changes
    print("Staging changes...")
    if not run_cmd("git add ."):
        sys.exit(1)

    # Commit
    print(f"Committing with message: '{message}'")
    # Wrap message in quotes safely
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
