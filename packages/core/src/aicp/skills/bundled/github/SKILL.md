---
name: github
description: GitHub operations (commit, PR, branch)
allowed-tools: [Bash(git:*)]
when_to_use: When working with GitHub repositories
arguments: [action, message]
context: fork
effort: medium
---

# GitHub Operations Skill

## Available Actions
- commit: Create a git commit
- pr: Create a pull request
- branch: Create a new branch

## Steps for commit
1. Run `git status` to see changes
2. Stage with `git add -A`
3. Commit with `git commit -m "$message"`

## Steps for PR
1. Push current branch
2. Create PR using gh CLI