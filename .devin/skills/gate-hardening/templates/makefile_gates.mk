# Production Gate Targets
# Each target invokes pytest directly. Non-zero exit = release blocked.
# No runners, no policy engines, no simulation.
#
# Usage:
#   make gate-all          # Run all gates
#   make gate-security     # Run security/tenant isolation gate only
#
# Customize:
#   - Add/remove gate-* targets to match your test directories
#   - Adjust pytest flags as needed (--timeout, -x, etc.)

.PHONY: gate-all gate-security gate-state gate-config gate-chaos gate-smoke gate-agent gate-obs

PYTEST_GATE_FLAGS = -v --tb=short --no-header -p no:randomly

gate-security:
	python3 -m pytest tests/security/ $(PYTEST_GATE_FLAGS)

gate-state:
	python3 -m pytest tests/state/ $(PYTEST_GATE_FLAGS)

gate-config:
	python3 -m pytest tests/config/ $(PYTEST_GATE_FLAGS)

gate-chaos:
	python3 -m pytest tests/chaos/ $(PYTEST_GATE_FLAGS)

gate-smoke:
	python3 -m pytest tests/smoke/ $(PYTEST_GATE_FLAGS)

gate-agent:
	python3 -m pytest tests/evals/ $(PYTEST_GATE_FLAGS)

gate-obs:
	python3 -m pytest tests/obs/ $(PYTEST_GATE_FLAGS)

gate-all: gate-security gate-state gate-config gate-chaos gate-smoke gate-agent gate-obs
	@echo "All gates passed."
