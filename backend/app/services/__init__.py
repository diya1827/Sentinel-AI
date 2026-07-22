"""Service / orchestration layer.

Responsibility: implement application use-cases by coordinating the lower
layers (`scanners`, `agents`, `models`). Services are the only layer allowed
to depend on both scanners and agents. They contain no HTTP or LLM-vendor
specifics.

Planned services:
    ReviewService  — runs a full security review end-to-end:
                     stage code → run scanners → agent triage → build report.
"""
