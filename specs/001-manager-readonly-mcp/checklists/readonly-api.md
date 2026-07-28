# Read-Only & API Contracts Checklist: Manager.io Read-Only MCP Server

**Purpose**: PR-gate validation that read-only/security and tool-contract requirements are complete, clear, consistent, and measurable (unit tests for the English — not for the implementation)
**Created**: 2026-07-28
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/mcp-tools.md](../contracts/mcp-tools.md)

**Depth**: Standard | **Audience**: Reviewer (PR) | **Focus**: Read-only & secrets + tool/API contracts

## Requirement Completeness

- [ ] CHK001 Are both write-fail modes specified (config hard-fail and no-mutate tool-set guarantee), not only one? [Completeness, Spec §FR-005, Clarifications Q3]
- [ ] CHK002 Are canonical write-related env names and near-miss variants listed identically in spec, plan, and contracts? [Completeness, Plan Write-flag policy, Contract §Env]
- [ ] CHK003 Is the full curated collection set enumerated (six names) without open-ended “etc.”? [Completeness, Spec §FR-009, Clarifications Q2]
- [ ] CHK004 Are all required financial snapshot views named as requirements (aged receivables/payables, bank balances, trial balance, P&L, balance sheet, tax summary)? [Completeness, Spec §FR-008]
- [ ] CHK005 Are discovery outputs required to state the read-only boundary explicitly? [Completeness, Spec §FR-006]
- [ ] CHK006 Are auth, not-found, unsupported-operation, and connectivity error classes all required? [Completeness, Spec §FR-013]
- [ ] CHK007 Is Agent Skill read-only boundary language required in the skill description? [Completeness, Spec §FR-014]
- [ ] CHK008 Is GET-only / no mutating client surface stated as a requirement (not only an implementation preference)? [Completeness, Spec §FR-004, Plan Constitution Check]

## Requirement Clarity

- [ ] CHK009 Is “truthy” defined or exemplified for write-flag hard-fail (what values count as enabling writes)? [Clarity, Contract §Safety, Spec §FR-005]
- [ ] CHK010 Is “truncated / has_more / further pages” metadata specified clearly enough that two readers would agree a page response is compliant? [Clarity, Spec §FR-011, Contract `list_records`]
- [ ] CHK011 Is opaque base URL scoping (including `/api2`) stated without implying a separate business-id setting? [Clarity, Spec §FR-002, Clarifications Q4]
- [ ] CHK012 Are date/period rules clear: optional only when live endpoint exposes params; otherwise current/default plus disclosure? [Clarity, Spec §FR-017, Clarifications Q1]
- [ ] CHK013 Is “never log or return the API key” stated as a hard requirement for errors and tool payloads? [Clarity, Spec §FR-002, §FR-013]
- [ ] CHK014 Is bank dual exposure described as two intentional capabilities (snapshot vs collection) rather than vague “also bank”? [Clarity, Spec §FR-018, US4]

## Requirement Consistency

- [ ] CHK015 Do constitution “opt-in write flag” wording and feature “no write opt-in / hard-fail” hardening conflict, and is the feature-local override explicit? [Consistency, Spec Constitution Constraints vs §FR-005]
- [ ] CHK016 Do env variable names match across Clarifications, Plan Write-flag policy, and Contract Env table? [Consistency, Spec Clarifications Q3–Q4, Plan, Contract]
- [ ] CHK017 Is bank_balances vs bank_accounts dual path consistent between user stories, FR-018, and the tools contract? [Consistency, Spec US2/US4, Contract report shortcuts]
- [ ] CHK018 Does “~10 tools” success criterion align with the concrete tool list in the contract (discover + list + get + seven reports)? [Consistency, Spec §SC-007, Contract]
- [ ] CHK019 Are saved-report GUID lookups consistently excluded in out-of-scope, edge cases, and contract non-goals? [Consistency, Spec Out of Scope, Contract Non-goals]

## Acceptance Criteria Quality

- [ ] CHK020 Can SC-005 (write-flag hard-fail + zero mutating tools) be objectively judged pass/fail from the written criteria alone? [Measurability, Spec §SC-005]
- [ ] CHK021 Can SC-004 (truncation signaled on oversized pages) be objectively judged without implementation knowledge? [Measurability, Spec §SC-004]
- [ ] CHK022 Can SC-008 (period unsupported disclosure) be judged without knowing which Manager paths support dates? [Measurability, Spec §SC-008]
- [ ] CHK023 Is “consistent with the instance data” for financial answers bounded enough for acceptance, or still subjective? [Measurability, Spec US1–US2, Ambiguity]

## Scenario & Edge Case Coverage

- [ ] CHK024 Are empty-books / empty-page requirements present (success with empty result, not failure)? [Coverage, Spec Edge Cases]
- [ ] CHK025 Are requirements defined for requesting a period on a view with no date params? [Coverage, Spec §FR-017, Edge Cases]
- [ ] CHK026 Are requirements defined for unknown resource / unsupported capability responses? [Coverage, Spec Edge Cases, FR-006]
- [ ] CHK027 Are multi-instance and multi-business selection explicitly out of scope with a documented caveat (not an underspecified in-scope case)? [Coverage, Spec Out of Scope, Clarifications Q4, Plan Phase Notes]
- [ ] CHK028 Are missing/invalid URL or token configuration failures required before silent partial operation? [Coverage, Spec §FR-003, Edge Cases]

## Dependencies & Assumptions

- [ ] CHK029 Is the assumption that standard report views need no saved-report GUID stated and tied to FR-008? [Assumption, Spec Assumptions, §FR-008]
- [ ] CHK030 Is the multi-business disambiguation caveat marked as unverified / documentation-only rather than implied support? [Assumption, Spec Clarifications Q4, Plan]
- [ ] CHK031 Are exact non-`customers` collection path strings acknowledged as OpenAPI-derived at implement time (not silently assumed)? [Dependency, Research §4, Gap]

## Ambiguities & Conflicts

- [ ] CHK032 Is “truthy” for write env vars free of ambiguity across shells/platforms, or does it need a closed value set? [Ambiguity, Contract §Safety]
- [ ] CHK033 Does Spec §FR-011’s “enough metadata” conflict with Contract’s `truncated`/`has_more` naming by leaving field names optional? [Ambiguity, Spec §FR-011, Contract]
- [ ] CHK034 Is default `page_size` intentionally unspecified (implementer choice) while still requiring truncation signaling in all oversized cases? [Clarity, Spec Assumptions]

## Notes

- Check items off when the **requirements text** satisfies the question; do not use this list as a runtime test plan.
- Existing `requirements.md` covers generic Spec Kit quality; this file is the PR-gate domain checklist for read-only + API contracts.
