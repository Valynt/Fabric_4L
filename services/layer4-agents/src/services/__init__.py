"""Layer 4 agents services package.

Provides flat-namespace `services.*` imports used internally by Layer 4
modules (e.g. `from services.llm_output_parser import parse_llm_json`).

Marker file required so that during OpenAPI schema export the layer4 `src/`
path resolves `services` as a regular package and Python does not aggregate
other layers' `services/` directories via namespace-package resolution.
"""
