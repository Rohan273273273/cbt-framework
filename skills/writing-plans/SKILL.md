---
name: writing-plans
description: Use when you have an approved design spec and need to create a detailed step-by-step implementation plan before coding begins
---

# Writing Plans

## Overview

Create comprehensive implementation plans that a developer with zero codebase context can execute without guessing.

**Core principle:** Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it.

**Announce at start:** "I'm using the writing-plans skill to create an implementation plan."

## When to Use

Use after `superpowers:brainstorming` has produced an approved design spec. Never jump to writing a plan before the design is settled.

## Plan Structure

### 1. Header

```markdown
# Plan: <Feature Name>

**Goal:** <One-sentence description of what this plan accomplishes>
**Architecture:** <Approach — e.g., "event-driven", "REST API with postgres", "CLI tool">
**Tech stack:** <Languages, frameworks, key libraries>
**Spec:** `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
```

### 2. File Map

Before listing tasks, show every file that will be created or modified:

```markdown
## Files

### New files
- `src/feature/handler.ts` — Request handler
- `src/feature/handler.test.ts` — Tests

### Modified files
- `src/index.ts` — Add route registration
- `src/types.ts` — Add FeatureRequest type
```

### 3. Tasks

Each task = one focused unit of work (2-5 minutes).

```markdown
## Task 1: <Task Name>

**Files:** `src/feature/handler.test.ts`, `src/feature/handler.ts`

### Step 1: Write failing test

\`\`\`typescript
// src/feature/handler.test.ts
import { handleFeature } from './handler';

test('returns 200 for valid request', async () => {
  const result = await handleFeature({ id: '123' });
  expect(result.status).toBe(200);
});
\`\`\`

Run: `npm test src/feature/handler.test.ts`
Expected: FAIL — "Cannot find module './handler'"

### Step 2: Implement minimal code

\`\`\`typescript
// src/feature/handler.ts
export async function handleFeature(req: { id: string }) {
  return { status: 200 };
}
\`\`\`

### Step 3: Verify

Run: `npm test src/feature/handler.test.ts`
Expected: PASS

### Step 4: Commit

\`\`\`bash
git add src/feature/handler.ts src/feature/handler.test.ts
git commit -m "Add handleFeature with basic 200 response"
\`\`\`
```

## Task Granularity Rules

**Each task must:**
- Touch 1-3 files maximum
- Follow red-green-refactor (failing test → implementation → pass → commit)
- Have exact file paths (never "the handler file")
- Show complete, runnable code (no `// add error handling here`)
- Include the exact run command and expected output
- End with a commit

**Never:**
- Use placeholder language: "TBD", "TODO", "add appropriate handling"
- Write vague instructions: "implement the feature"
- Bundle multiple behaviors into one task
- Skip the failing test step
- Leave type names inconsistent across tasks

## Plan File Location

Save to: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

Commit the plan before handing it off for execution.

## Self-Review Checklist

After drafting the plan, run this check before saving:

1. **Spec coverage:** Does every requirement from the design spec map to at least one task?
2. **Placeholder scan:** Any "TBD", "TODO", "add X", incomplete steps?
3. **Type consistency:** Do type names and method signatures match across all tasks?
4. **Runnable code:** Can every code block be copy-pasted and executed?
5. **Task size:** Does each task take 2-5 minutes? (If longer, split it)
6. **File paths:** Are all paths exact and consistent?

Fix any issues. Then save and commit.

## Execution Options

After the plan is written, offer two paths:

**Option A — Subagent-driven (recommended):**
> "Plan ready at `<path>`. Use `superpowers:subagent-driven-development` to execute it — dispatches a fresh subagent per task with two-stage review (spec compliance + code quality)."

**Option B — Inline execution:**
> "Or use `superpowers:executing-plans` to execute it in this session with review checkpoints."

Do NOT start execution yourself — offer the choice and let the user or the appropriate skill take over.

## Integration

**Requires:**
- **superpowers:brainstorming** — Creates the design spec this plan implements

**Consumed by:**
- **superpowers:subagent-driven-development** — Executes the plan with subagents
- **superpowers:executing-plans** — Executes the plan inline

## Red Flags

**Never:**
- Start writing a plan before the design is approved
- Use vague language in any step
- Skip the file map section
- Write tasks that take more than 5 minutes
- Omit the expected output of test commands
- Leave method signatures inconsistent across tasks
