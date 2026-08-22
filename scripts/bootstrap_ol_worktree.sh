#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/bootstrap_ol_worktree.sh <worktree-path> <feature-branch>
# Example:
#   bash scripts/bootstrap_ol_worktree.sh /home/ubuntu/ZIC_ol_product feature/ol-product

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <worktree-path> <feature-branch>" >&2
  exit 2
fi

WORKTREE_PATH=$1
FEATURE_BRANCH=$2
REPO_PATH=${ZIC_REPO_PATH:-/home/ubuntu/ZIC_git}
REMOTE_URL=${ZIC_REMOTE_URL:-git@github.com:MohamadKamardin1/ZIC.git}
SSH_KEY=${ZIC_SSH_KEY:-/home/ubuntu/.ssh/id_ed25519_zic}

if [ -f "$SSH_KEY" ]; then
  export GIT_SSH_COMMAND="ssh -i ${SSH_KEY}"
fi

if [ ! -d "$REPO_PATH/.git" ] && [ ! -f "$REPO_PATH/.git" ]; then
  if [ -e "$REPO_PATH" ]; then
    echo "Repository path exists but is not a Git repository: $REPO_PATH" >&2
    echo "Set ZIC_REPO_PATH to an empty path or provide the mounted repository." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$REPO_PATH")"
  git clone "$REMOTE_URL" "$REPO_PATH"
fi

cd "$REPO_PATH"
git fetch origin sultan

if git worktree list --porcelain | grep -Fq "worktree ${WORKTREE_PATH}"; then
  actual_branch=$(git -C "$WORKTREE_PATH" branch --show-current)
  if [ "$actual_branch" != "$FEATURE_BRANCH" ]; then
    echo "Existing worktree has branch '$actual_branch', expected '$FEATURE_BRANCH': $WORKTREE_PATH" >&2
    exit 1
  fi
else
  if [ -e "$WORKTREE_PATH" ]; then
    echo "Worktree path exists but is not registered: $WORKTREE_PATH" >&2
    exit 1
  fi

  if git show-ref --verify --quiet "refs/heads/${FEATURE_BRANCH}"; then
    git worktree add "$WORKTREE_PATH" "$FEATURE_BRANCH"
  elif git ls-remote --exit-code --heads origin "$FEATURE_BRANCH" >/dev/null 2>&1; then
    git worktree add "$WORKTREE_PATH" "$FEATURE_BRANCH"
  else
    git worktree add -b "$FEATURE_BRANCH" "$WORKTREE_PATH" origin/sultan
  fi
fi

actual_branch=$(git -C "$WORKTREE_PATH" branch --show-current)
actual_commit=$(git -C "$WORKTREE_PATH" rev-parse --short HEAD)
if [ "$actual_branch" != "$FEATURE_BRANCH" ]; then
  echo "Branch verification failed: $actual_branch" >&2
  exit 1
fi
if [ -n "$(git -C "$WORKTREE_PATH" status --porcelain)" ]; then
  echo "Worktree is not clean: $WORKTREE_PATH" >&2
  exit 1
fi

printf 'Ready\n  repository: %s\n  worktree:  %s\n  branch:    %s\n  baseline:  %s\n' "$REPO_PATH" "$WORKTREE_PATH" "$actual_branch" "$actual_commit"
