# Branch Inventory

This file is generated from live GitHub branch, pull-request, protection, and comparison data by the
weekly `Repository Hygiene` workflow. The workflow publishes the populated version as the
`branch-inventory` artifact and in the workflow summary; scheduled runs are report-only and do not
commit, close, or delete anything.

Run the workflow manually with `operation=report` for an on-demand signed snapshot. Every generated
row includes owner, head SHA, age, last commit date, ahead/behind counts relative to `main`, associated
pull request, disposition, and reason.

Do not hand-edit branch rows here. Cleanup decisions belong in the generated inventory and must be
applied through the exact-branch manual confirmation flow documented in
[`branch-hygiene.md`](branch-hygiene.md).
