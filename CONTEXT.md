# System Context: Forge Autonomous Operations with Solari

## Domain & Mission
This system implements the core mission of **Forge (forgeaicore.com)**: connecting fragmented tools across an engineering and operations stack into a unified agentic layer. It eliminates intelligence gaps between tools by autonomously sensing changes, reasoning across systems, and executing verified actions without manual handoffs.

## Infrastructure Primitives (Solari)
- **Cloud Browser**: Stealth Chromium sessions with residential proxy routing, persistent auth profiles, and DOM-level rrweb NDJSON recording.
- **MicroVM Sandbox**: Headless Linux VM booting in ~1s from memory snapshots, supporting stateful Python code execution, isolated commands, and public port previews (*.preview.getsolari.com).
- **Managed Desktop**: Linux desktop environment with X11, live VNC streams, mouse/keyboard interaction, and screenshot capture.

## Architectural Boundaries
- `infrastructure/`: Direct wrappers for Solari SDKs and offline deterministic simulation drivers.
- `services/`: Pure domain logic for signal correlation, discrepancy detection, and patch management.
- `agents/`: LangGraph state machine orchestrating `Sense`, `Decide`, `Execute`, `Verify`, and `Approve` nodes.
- `eval/`: Benchmark suite measuring detection accuracy and false positive rates across 10 multi-tool scenarios.
- `web/`: Local cockpit interface streaming execution traces and audit telemetry.
