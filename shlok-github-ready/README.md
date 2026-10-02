# Shlok Polymers Website

Next.js application for the SHLOK polymer grade book, price list and competitive mapping.

## Important
- Do not commit `.env` files or secrets.
- Original PDFs, Excel uploads and intermediate extraction files are excluded.
- The application dataset used by the website remains in `public/data/dataset.json`.

## Local development
From this directory, with Bun 1.3.4 installed:

```sh
bun install --frozen-lockfile
bunx --no-install tsc --noEmit
bun run lint
bun run dev
```

Stop development before starting production on the same port:

```sh
bun run build
bun run start
```

The production build validates TypeScript and copies public/static assets into Next.js standalone output.
The start command binds to `0.0.0.0` and honors `PORT` (default 3000).
No database, migrations, application secrets or `/home/z/` paths are needed to run the website.

## Deployment
Use the repository-root `render.yaml` as the Render Blueprint. It selects this directory,
the Node runtime with pinned Bun/Node versions, a frozen Bun installation and the package's
build/start commands. Render supplies `PORT`; application credentials are not required.
The build downloads Google Fonts from `fonts.googleapis.com` and `fonts.gstatic.com`.
In Codex cloud, export `NEXT_TURBOPACK_EXPERIMENTAL_USE_SYSTEM_TLS_CERTS=1` to use the
platform certificate trust store. Keep TLS verification enabled.

The Order view intentionally embeds the existing Google Form and retains its "Open in new tab"
link. Codex network restrictions can block `docs.google.com`; verify form loading and the link
from a normal browser after deployment. Do not submit enquiries during smoke tests.
The favicon uses the existing local `public/shlok-logo.png` asset.

## Legacy data-processing scripts

The scripts in `scripts/` were retained unchanged. Their `/home/z/my-project` references
are legacy offline PDF/Excel processing paths, not production or development-server
requirements. Running these scripts requires the excluded source documents and a separate
path/configuration update. They are not invoked by install, build or start.

The original archive installer outside the checkout remains useful for reproducing the
historical archive. Render builds the checked-in source directly and does not invoke it.
