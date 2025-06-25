#!/bin/bash

# This script removes Claude Code credits from commit messages
# It works by checking out each commit, amending its message, and then rebasing

echo "Starting to remove Claude Code credits from commits..."

# Get the list of commits with Claude Code mentions
commits=$(git log --format="%H" -20 | while read commit; do 
    git show -s --format="%B" $commit | grep -q "Claude Code" && echo $commit
done | tac)  # Reverse order to process from oldest to newest

if [ -z "$commits" ]; then
    echo "No commits found with Claude Code credits"
    exit 0
fi

# Find the parent of the oldest commit we need to fix
oldest_commit=$(echo "$commits" | tail -1)
base_commit=$(git log --format="%H" -1 $oldest_commit^)

echo "Will rebase from commit: $base_commit"
echo "Commits to clean:"
echo "$commits"

# Create a temporary file for the rebase script
cat > /tmp/rebase_script.sh << 'EOF'
#!/bin/bash
# Remove Claude Code credits from the commit message
sed -i '/🤖 Generated with \[Claude Code\]/d' "$1"
sed -i '/Co-Authored-By: Claude <noreply@anthropic.com>/d' "$1"
# Remove any trailing empty lines
sed -i -e :a -e '/^\s*$/d;N;ba' "$1"
EOF

chmod +x /tmp/rebase_script.sh

# Set the editor to our script
export GIT_SEQUENCE_EDITOR="sed -i 's/^pick/reword/'"
export GIT_EDITOR="/tmp/rebase_script.sh"

# Perform the rebase
git rebase -i $base_commit

# Clean up
rm -f /tmp/rebase_script.sh

echo "Finished removing Claude Code credits from commits"