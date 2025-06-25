# Instructions to Remove Claude Code Credits from Git History

Since we cannot run git filter-branch from a subdirectory, please run these commands from the repository root directory (`/home/rinconnect/Code/MCP/Agent-MCP`):

## Step 1: Backup your current branch (already done)
```bash
# Backup branch already created: backup-feature-premium-dashboard-ui
```

## Step 2: Remove Claude Code credits from commit messages

Run this command from the repository root:

```bash
cd /home/rinconnect/Code/MCP/Agent-MCP

# Create the filter script
cat > /tmp/remove_claude.sh << 'EOF'
#!/bin/bash
# Remove Claude Code credits from commit messages
grep -v "🤖 Generated with \[Claude Code\]" | grep -v "Co-Authored-By: Claude <noreply@anthropic.com>" | sed '/^$/N;/^\n$/d'
EOF
chmod +x /tmp/remove_claude.sh

# Run filter-branch to clean the commits
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter '/tmp/remove_claude.sh' feature/premium-dashboard-ui~20..feature/premium-dashboard-ui

# Clean up
rm -f /tmp/remove_claude.sh
```

## Step 3: Verify the changes
```bash
# Check that Claude Code mentions are gone
git log --format="%B" -20 | grep -i "claude code" || echo "Success: No Claude Code mentions found"
```

## Step 4: Force push the cleaned branch
```bash
# Force push to update the remote branch
git push --force-with-lease origin feature/premium-dashboard-ui
```

## Alternative: Using git-filter-repo (if available)

If you have `git-filter-repo` installed, you can use this more modern approach:

```bash
git filter-repo --message-callback '
    import re
    message = message.decode("utf-8")
    message = re.sub(r"🤖 Generated with \[Claude Code\].*\n?", "", message)
    message = re.sub(r"Co-Authored-By: Claude <noreply@anthropic\.com>\n?", "", message)
    return message.encode("utf-8")
' --refs feature/premium-dashboard-ui~20..feature/premium-dashboard-ui
```

## Note
After running these commands, the Claude Code credits will be removed from the commit history. Make sure to coordinate with your team before force-pushing, as this rewrites history.