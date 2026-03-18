# Global AI Behavior Rules — {{SERVER_NAME}}

## Core Rules
1. All task operations go through `managesim-task` CLI
2. Report progress at every key step using structured format
3. Respect the permission matrix — only communicate with allowed roles
4. Store knowledge with proper provenance (stored_by, visibility)
5. Default visibility is public unless specified otherwise

## Quality Standards
- Verify before reporting completion
- Include evidence/artifacts with task completion
- Follow the assigned pipeline strictly
