# RFCs

AICP uses Request for Comments (RFCs) for protocol changes.

## When to Submit an RFC

RFCs are required for:
- New capability kinds
- Policy contract changes
- Workflow model changes
- Breaking schema changes
- New adapter contract behavior
- New render types

## RFC Process

1. Create a new RFC file: `rfcs/XXXX-descriptive-title.md`
2. Include:
   - Summary of the change
   - Motivation and use cases
   - Detailed specification
   - Backwards compatibility analysis
3. Submit as PR for discussion
4. After approval, implement in `/spec`

## RFC Template

```markdown
# RFC: [Title]

## Summary
[One paragraph explanation]

## Motivation
[Why is this needed?]

## Detailed Specification
[Technical details]

## Backwards Compatibility
[Impact analysis]

## Open Questions
[Things to resolve]
```

## Accepted RFCs

| Number | Title | Status |
|--------|-------|--------|
