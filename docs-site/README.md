# ValuePact Public Documentation Site

This directory is the **only** public ValuePact documentation site. It is a self-contained
MkDocs (Material theme) project and is independent of the internal Fabric4L engineering docs in
the repository's `/docs` tree, which are not built or published here.

## Local development

```bash
# from docs-site/
python -m pip install -r requirements-docs.txt

# refresh the OpenAPI spec used by the API reference (gitignored copy)
python scripts/sync-openapi.py

# serve with live reload at http://127.0.0.1:8000
mkdocs serve

# strict production build (fails on broken links / missing nav)
mkdocs build --strict
```

## Structure

- `docs/` — public ValuePact product documentation (top-level sections).
- `docs/fabric4l/` — namespaced internal engineering documentation.
- `docs/api/generated.md` — interactive OpenAPI reference rendered via `swagger-ui-tag`.
- `docs/api/openapi/` — generated spec copy (gitignored); produced by `scripts/sync-openapi.py`.
- `mkdocs.yml` — site configuration and navigation.
- `requirements-docs.txt` — documentation build dependencies.

## API reference

The API reference is generated from the canonical contract at
`../contracts/openapi/fabric-4l-api.json`. Do not hand-edit endpoint shapes in Markdown; update
the contract and re-run `scripts/sync-openapi.py` (CI does this automatically before building).

## Page metadata

Durable pages carry `owner`, `status` (`draft` | `active` | `deprecated`), and `last_reviewed`
front matter. Update `status` to `active` once a page's content is verified and maintained.

## CI / deployment

`.github/workflows/public-docs.yml` builds the site with `mkdocs build --strict` on every PR
touching `docs-site/**` or the API gateway spec, and deploys to GitHub Pages on pushes to
`main`. Enable publishing by setting the repository's **Pages** source to **GitHub Actions**.
