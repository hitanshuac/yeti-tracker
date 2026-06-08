# Git Sync Workflow

**Description**: Automates the process of adding, committing, and pushing code to the repository.

## Pre-conditions
- The user has made code modifications or generated new artifacts.
- The repository must remain under the 10 MB limit (Ensure `data/` and large files are ignored).

## Steps

1. **Status Check**: 
   - Run `git status` to see what files are modified or untracked.
   - Verify that no large files (datasets, `.duckdb`, etc.) are being tracked.
2. **Stage Changes**:
   - Run `git add .` to stage all changes.
3. **Commit**:
   - Run `git commit -m "[Descriptive commit message]"`
4. **Push**:
   - Run `git push origin main`

## Execution Command
To manually execute this quickly from the shell (PowerShell):
```powershell
git add . ; git commit -m "update" ; git push origin main
```
