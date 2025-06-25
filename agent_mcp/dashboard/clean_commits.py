#!/usr/bin/env python3
import subprocess
import sys
import re

def get_commits_with_claude():
    """Get list of commits that contain Claude Code credits"""
    result = subprocess.run(
        ["git", "log", "--format=%H", "-30"],
        capture_output=True, text=True
    )
    
    commits_with_claude = []
    for commit in result.stdout.strip().split('\n'):
        msg_result = subprocess.run(
            ["git", "show", "-s", "--format=%B", commit],
            capture_output=True, text=True
        )
        if "Claude Code" in msg_result.stdout:
            commits_with_claude.append(commit)
    
    return list(reversed(commits_with_claude))  # Return in chronological order

def clean_commit_message(message):
    """Remove Claude Code credits from commit message"""
    # Remove the Claude Code line and the Co-Authored-By line
    lines = message.split('\n')
    cleaned_lines = []
    skip_next = False
    
    for line in lines:
        if "🤖 Generated with [Claude Code]" in line:
            skip_next = True
            continue
        if skip_next and line.strip() == "":
            skip_next = False
            continue
        if "Co-Authored-By: Claude <noreply@anthropic.com>" in line:
            continue
        cleaned_lines.append(line)
    
    # Remove trailing empty lines
    while cleaned_lines and cleaned_lines[-1].strip() == "":
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def main():
    commits = get_commits_with_claude()
    
    if not commits:
        print("No commits found with Claude Code credits")
        return
    
    print(f"Found {len(commits)} commits with Claude Code credits")
    
    # Find the parent of the oldest commit
    oldest_commit = commits[0]
    parent_result = subprocess.run(
        ["git", "rev-parse", f"{oldest_commit}^"],
        capture_output=True, text=True
    )
    parent_commit = parent_result.stdout.strip()
    
    print(f"Will rebase from commit: {parent_commit}")
    
    # Create the rebase todo list
    todo_content = []
    
    # Get all commits from parent to HEAD
    all_commits_result = subprocess.run(
        ["git", "rev-list", "--reverse", f"{parent_commit}..HEAD"],
        capture_output=True, text=True
    )
    all_commits = all_commits_result.stdout.strip().split('\n')
    
    for commit in all_commits:
        if commit in commits:
            todo_content.append(f"reword {commit}")
        else:
            todo_content.append(f"pick {commit}")
    
    # Save the todo list
    with open("/tmp/rebase-todo", "w") as f:
        f.write('\n'.join(todo_content))
    
    print("Rebase todo list created. Run the following command:")
    print(f"GIT_SEQUENCE_EDITOR='cp /tmp/rebase-todo' git rebase -i {parent_commit}")
    print("\nThen for each 'reword' commit, manually remove the Claude Code credits.")

if __name__ == "__main__":
    main()