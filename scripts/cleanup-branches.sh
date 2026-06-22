#!/bin/bash

# Ensure we have the latest remote information
git fetch -p

# Set the default branch name
DEFAULT_BRANCH="main"

echo "Finding branches merged into $DEFAULT_BRANCH..."

# List branches merged into the default branch, excluding the default branch itself
MERGED_BRANCHES=$(git branch -r --merged "origin/$DEFAULT_BRANCH" | grep -v "$DEFAULT_BRANCH" | grep -v "HEAD" | sed 's/origin\///')

if [ -z "$MERGED_BRANCHES" ]; then
  echo "No merged branches to clean up!"
  exit 0
fi

echo "The following branches have been merged and will be deleted:"
echo "$MERGED_BRANCHES"
echo ""
read -p "Do you want to delete these branches remotely? (y/N): " CONFIRM

if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
  for BRANCH in $MERGED_BRANCHES; do
    echo "Deleting $BRANCH..."
    # Delete the remote branch
    git push origin --delete "$BRANCH" || echo "Failed to delete remote branch: $BRANCH"
    # Delete the local branch if it exists
    git branch -d "$BRANCH" 2>/dev/null || true
  done
  echo "Cleanup complete!"
else
  echo "Operation cancelled."
fi
