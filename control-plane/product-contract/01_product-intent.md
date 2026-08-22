# 01 — Product Intent

Source: Master Product Intent §1 (S1). Status: Proposed canonical version 1.0. Code baseline: `76f21bdc2fc277d0fdddf546c32ac75a5ded7e42` (`bmsull560/Fabric_4L`).

## Vision

- ValuePilot turns tenant-scoped account information, customer evidence, validated benchmarks, explicit assumptions, and human judgment into a defensible financial value case.
- It MUST preserve the reasoning path from original source through operational signal, value driver, formula, scenario, financial result, narrative claim, approval, export, and realized outcome.
- Success condition: the account team and customer can jointly inspect, challenge, revise, approve, and reuse the model without trusting a black box or reconstructing the calculation outside the platform.

## Product promise

> "An authorized value engineer can move from account evidence to a defensible, versioned, decision-ready value case without losing tenant scope, financial traceability, human judgment, or provenance."

## North-star outcome

> "A value engineer can start or resume an account, inspect source-to-signal reasoning, validate hypotheses, create a driver-based financial model, generate an evidence-linked narrative from an immutable snapshot, obtain approval, export the exact approved version, and track realized value."

## Principles

Derived from the master intent statement:

> "ValuePilot earns trust by making value reasoning inspectable, calculations reproducible, evidence challengeable, decisions reviewable, and published commitments immutable. The product is complete only when that trust survives every route, service, fallback, version, and export."

- P: value reasoning is inspectable.
- P: calculations are reproducible.
- P: evidence is challengeable.
- P: decisions are reviewable.
- P: published commitments are immutable.
- Trust MUST survive every route, service, fallback, version, and export.

## Non-goals

1. ValuePilot is **not** an autonomous mechanism for making financial commitments or publishing unreviewed AI claims.
2. ValuePilot is **not** a generic proposal writer disconnected from a durable value model.
3. ValuePilot is **not** a mechanism for inventing plausible financial inputs when customer data is missing.
4. ValuePilot is **not** a collection of unrelated tab payloads, browser-local drafts, or route-specific systems of record.
5. ValuePilot is **not** a one-time calculator. It connects discovery, modeling, evidence, approval, export, and realization.

## Normative rules R-1..R-8

Normative vocabulary: **MUST** = required for customer-ready release; **SHOULD** = expected unless an approved exception exists; **MAY** = optional behavior that cannot weaken a MUST.

ID mapping note: the source document numbers these rules 1–8; the downstream manifest ID mapping is rule N → **R-n** by convention (confirmed by the S3 manifest example `rules: [R2, R4]`, written here as `R-2`, `R-4`). The statements below are verbatim.

## R-1

Every customer-facing statement and number MUST be classified as a verified fact, human-approved inference, external benchmark, explicit assumption, or deterministic calculation.

## R-2

The authoritative model MUST be server-persisted, tenant-scoped, account-scoped, versioned, and recoverable. Browser storage MAY cache non-authoritative preferences only.

## R-3

Consequential AI output MUST support Accept, Edit, and Reject. AI output MUST NOT become verified, approved, or customer-facing without the required human and evidence gates.

## R-4

Financial math MUST be deterministic and reproducible. An LLM MAY explain or narrate a result but MUST NOT silently replace a formula, invent an input, or alter an approved calculation.

## R-5

Synthetic, benchmark-derived, fallback, and demo inputs MUST remain visibly labeled through calculation, narrative, approval, and export. Materially degraded outputs MUST NOT be publishable.

## R-6

Authorization, tenant, account, case, model, evidence, and version uncertainty MUST fail closed.

## R-7

An approved or published version MUST be immutable. Any later edit creates a new draft with explicit lineage.

## R-8

Every quantitative claim MUST expose a provenance path from claim to calculation, formula, inputs, driver, signal or evidence, and original source.
