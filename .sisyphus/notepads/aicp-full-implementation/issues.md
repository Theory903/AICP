2026-04-05: Perception test failure was not only case-sensitive role matching; Playwright accessibility snapshot access via page.accessibility was missing in this environment, so the provider fell back to a synthetic document node.
- GraphQL adapter tests failed because the stub inherited from a pydantic-backed transport; making the stub a plain test double with url/endpoint/endpoint_url fixed collection/runtime behavior.
- Targeted pytest passed after the stub fix, but the broader core suite still has an unrelated failure in packages/core/tests/integration/test_perception_integration.py::test_perception_signal_extraction.

- 2026-04-05: Workspace build was initially blocked by a non-exhaustive `ProviderKind` match in `crates/mammoth-cli/src/main.rs` and by `crates/tools/Cargo.toml` needing explicit `lsp-types = { workspace = true }` syntax for the unresolved import to link cleanly during full `cargo build`.
