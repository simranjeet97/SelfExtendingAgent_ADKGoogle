---
name: git-workflow
description: >
  Guide developers through Git operations, branching strategies,
  commit conventions, merge/rebase decisions, and pull request
  workflows. Use when the user asks about Git commands, branching,
  commits, merging, rebasing, resolving conflicts, or setting up
  a Git workflow for a team or project.
metadata:
  author: your-github-username
  version: "1.0"
---

# Git Workflow

## Core philosophy
Prefer clarity over cleverness. Every Git operation should leave
the repository history more understandable, not less.

## Commit message convention
Follow Conventional Commits: `type(scope): description`
Types: feat, fix, docs, style, refactor, test, chore
Example: `feat(auth): add OAuth2 login flow`

## Branching strategy
- `main`: always deployable, protected
- `develop`: integration branch for features
- `feature/name`: one feature per branch
- `hotfix/name`: production fixes only

## When to merge vs rebase
- Merge: preserving history of a feature branch into main
- Rebase: cleaning up local commits before a PR
- Never rebase public branches that others are using

## Conflict resolution process
1. `git status` to see all conflicted files
2. Open each file and resolve the `<<<<<<<` markers
3. `git add` each resolved file
4. `git commit` to complete the merge
5. Verify with `git log --oneline --graph`
