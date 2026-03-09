---
name: plan-code-review
description: Post-plan implementation code review and testing. Use this skill AFTER code has been written according to a plan to (1) verify that the implementation matches the plan, (2) find potential bugs or gaps, and (3) design, implement, and run tests based on the code and plan.
---

# Plan-Based Code Review & Testing

This skill is used **after** an implementation has been completed based on a prior plan (e.g. Plan mode). It creates a fresh "review agent mindset" that treats the plan as the source of truth and audits the code against it, then derives tests from both the plan and the code.

## Inputs

When this skill is invoked, first gather:

1. **Plan**  
   - The final agreed plan text, including requirements, constraints, edge cases, and non‑functional needs.
2. **Code changes**  
   - List of relevant files, or diffs, that were implemented according to the plan.
3. **Project testing setup**  
   - Testing framework and typical commands (e.g. `pytest`, `npm test`, `pnpm vitest`, `go test ./...`).
   - Any existing test helpers or patterns if they exist.

If any of these are missing from immediate context, request them explicitly or locate them in the repository.

## Workflow

### 1. Normalize and restate the plan

- Extract from the plan a checklist of **implementation requirements**, including:
  - Functional behaviors and APIs.
  - Data contracts, invariants, and important edge cases.
  - Non‑functional constraints that affect code structure (e.g., performance, security, logging, error handling).
- Rewrite this as a concise **review checklist** that will be used later to assess coverage.

### 2. Map plan to code

- For each item in the checklist:
  - Identify which files / functions / modules are expected to implement it.
  - Note any gaps where the plan calls for behavior that has no obvious implementation.
- Build a table or bullet list like:

  - Requirement → Implementing code locations → Status (`implemented / unclear / missing`).

### 3. Static review for correctness and quality

For the code that implements each requirement:

- Check for **logic bugs and edge cases**:
  - Off‑by‑one errors, null/undefined handling, empty collections, time zone, encoding, rounding, etc.
- Check **error handling and robustness**:
  - Proper propagation or wrapping of errors.
  - Avoiding silent failures and swallowed exceptions.
- Check **state and concurrency** where applicable:
  - Shared mutable state, race conditions, reentrancy problems.
- Check **interfaces and contracts**:
  - Input validation, output guarantees, and alignment with the plan's expectations.
- Note any **code smells** that may not break correctness but are worth fixing:
  - Over‑complex functions, duplication, poor naming, tight coupling, lack of separation of concerns.

Only propose refactors that are clearly beneficial and low‑risk, or call them out as optional improvements.

### 4. Plan–code alignment assessment

- For each checklist item, decide:
  - **Fully satisfied**: implementation clearly matches the plan.
  - **Partially satisfied**: some scenarios or edge cases are missing.
  - **Not satisfied**: no implementation or mismatched behavior.
- If the **plan itself is flawed or incomplete** (e.g., missing required edge cases or constraints), explicitly:
  - Describe the issue.
  - Propose an updated plan item, keeping it minimal and consistent with the user's original intent.

### 5. Test design from plan and code

Design tests **before writing any test code**:

- Derive **test cases** from:
  - Plan requirements (happy paths, edge cases, failure paths).
  - Code structure (branches, conditions, invariants, error paths).
- For each important function/module/endpoint:
  - Enumerate key test scenarios, including:
    - Normal/happy path.
    - Boundary values and edge cases.
    - Invalid input and error paths.
    - Important regressions or previously buggy behaviors (if known).
- Decide the appropriate **test level**:
  - Unit tests for core logic.
  - Integration tests for interactions between components or with external systems.
- Prioritize:
  - Critical correctness.
  - User‑visible behavior.
  - High‑risk or complex branches.

### 6. Implement tests in the project

If the user allows file changes:

1. **Follow existing conventions**:
   - Match the project's existing test directory structure, naming, and frameworks.
2. **Create or update test files**:
   - Add or extend test files in the appropriate locations.
   - Keep tests focused and readable; avoid over‑mocking.
3. **Cover the designed scenarios**:
   - Implement tests for the prioritized scenarios from the previous step.
   - Where full coverage is not feasible, explain which scenarios are covered now and which are left as follow‑ups.
4. Use the usual tooling in this environment:
   - Use repository tools (e.g., `Read`, `ApplyPatch`, `Shell`, `ReadLints`) according to system instructions.
   - Ensure new tests compile/lint cleanly.

If the user does **not** want automatic edits, generate test code snippets and clear file‑placement instructions instead.

### 7. Run tests and iterate

- Run the project's test command(s).
- If any tests fail:
  - Analyze failures.
  - Decide whether the bug is in the **implementation** or the **test** (or both).
  - Propose or apply minimal, targeted fixes, and re‑run tests until they pass or until further changes would be too intrusive for a single review.
- If adding or changing tests reveals weaknesses in the original plan, call that out and suggest updated plan items.

### 8. Output format

Always present results in a concise, structured format:

1. **Plan coverage summary**
   - High‑level verdict: how well the code matches the plan.
   - Table or bullets: requirement → status (`ok / partial / missing`) → key notes.
2. **Bugs and risks**
   - List of concrete issues, each with:
     - Location(s).
     - Impact and severity.
     - Suggested fix or patch idea.
3. **Tests added / proposed**
   - Files and main scenarios covered.
   - How to run the tests (command).
4. **Recommended follow‑ups**
   - Any remaining gaps in plan, implementation, or tests that should be addressed later.

Keep the explanation tight and actionable, focusing on what matters most for correctness, alignment with the plan, and test coverage.

