# CLAUDE.md - AI Assistant Guidelines

This document provides context and guidelines for AI assistants working with this codebase.

## Repository Overview

**Repository Name:** test
**Current State:** Initial setup - minimal repository structure
**Primary Branch:** main

This repository is in its early stages with minimal content. The structure and guidelines below will evolve as the project develops.

## Current Structure

```
/home/user/test/
├── .git/           # Git version control
├── README.md       # Project readme (placeholder)
└── CLAUDE.md       # This file - AI assistant guidelines
```

## Development Workflow

### Git Conventions

1. **Branch Naming:**
   - Feature branches: `feature/<description>`
   - Bug fixes: `fix/<description>`
   - Documentation: `docs/<description>`

2. **Commit Messages:**
   - Use clear, descriptive commit messages
   - Start with a verb in present tense (Add, Fix, Update, Remove)
   - Keep the first line under 72 characters
   - Example: `Add user authentication module`

3. **Before Committing:**
   - Ensure all files are properly formatted
   - Verify no sensitive data (credentials, API keys) is included
   - Test changes locally when applicable

### Code Style Guidelines

As the project develops, specific style guidelines will be added here. General principles:

- Write clean, readable code with meaningful variable names
- Include comments for complex logic
- Follow the principle of least surprise
- Keep functions focused and single-purpose

## Key Files to Know

| File | Purpose |
|------|---------|
| `README.md` | Project overview and setup instructions |
| `CLAUDE.md` | AI assistant context and guidelines (this file) |

## Common Tasks

### Setting Up the Project

```bash
# Clone the repository
git clone <repository-url>
cd test
```

### Making Changes

1. Create a feature branch
2. Make your changes
3. Commit with a descriptive message
4. Push and create a pull request

## Important Notes for AI Assistants

1. **Read Before Modifying:** Always read existing files before suggesting changes
2. **Minimal Changes:** Make only the changes necessary to complete the task
3. **Preserve Existing Patterns:** Follow established conventions in the codebase
4. **Security First:** Never commit sensitive data or introduce vulnerabilities
5. **Test Changes:** Verify changes work as expected before committing

## Future Sections

As this project grows, the following sections will be added:

- [ ] Build and test commands
- [ ] Architecture overview
- [ ] API documentation
- [ ] Dependency management
- [ ] Deployment procedures
- [ ] Troubleshooting guide

---

*Last updated: 2025-12-05*
