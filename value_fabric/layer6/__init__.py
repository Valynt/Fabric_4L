"""Neutralized Layer 6 compatibility namespace.

Canonical Layer 6 runtime code lives under
``services/layer6-benchmarks/src/layer6_benchmarks``. New code must import
``layer6_benchmarks.*`` directly.

This package is retained only as an empty namespace placeholder for stale-path
detection and shim-removal governance. It must not append service paths, export
runtime symbols, or contain implementation logic.
"""
