# Documentation site and repository discoverability

This site renders the repository's English and Chinese Markdown as static HTML. Source documents remain the authority; edit them rather than generated HTML. The build includes public framework guides and example READMEs, while research notes, binaries and local state stay out of the site artifact.

## Free project hosting

The documentation is published through **GitHub Pages for this repository** at [reverse-cli-anything documentation](https://leileqithu.github.io/reverse-cli-anything/). It uses a project path, not an account-level `username.github.io` repository. Initial deployment and public asset checks passed on 2026-10-15.

Public repositories can use GitHub Pages on GitHub Free. Each repository can have a project site, so this does not consume the account's single user/organization site. No purchased domain, server, paid API, analytics service or other hosting account is required. GitHub's service limits still apply; see [Pages availability and project sites](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and [usage limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## Build and verify

From the repository root, using Python 3.11+:

```text
python -m pip install -r site/requirements.txt
python tools/build-site.py
python tools/check-site.py
```

The output is `outputs/site/`. For local preview, build with `--base-url http://localhost:8765/` and run `python -m http.server 8765 --directory outputs/site --bind 127.0.0.1`. Pass the same base URL to the checker. Rebuild with the production URL before manually uploading preview output.

On this workstation, the site virtual environment is `.local/site-venv/` on D:, and pip cache is `D:/Caches/pip`. It reuses the existing base Python installation on C: without relocating it. Do not commit the environment or generated output.

## Publish

1. Commit and push the reviewed source changes to the repository's `main` branch.
2. In this repository's **Settings → Pages**, choose **GitHub Actions** as the build source.
3. Run **Actions → Documentation site → Run workflow**. Later relevant changes on `main` rebuild automatically; there is no scheduled polling or idle server.
4. Verify the deployment URL returned by GitHub and check the homepage, Chinese homepage, FAQ and `/sitemap.xml`.

The workflow gets the actual base URL from `actions/configure-pages`, including a configured custom domain if one is added later. It does not purchase a domain or create a user-level Pages repository. Deployment requires the repository's Pages setting to be enabled and a public repository for free hosting. Build and deploy permissions are restricted to their respective jobs.

The generator uses tracked Markdown files, plus explicitly listed new FAQ, automation guide and native example pages. Add other new documentation to Git before building it. Removed or renamed pages should be built into a fresh output directory, as in CI; the generator deliberately does not recursively delete user directories.

## Repository About fields

Applied repository description:

> Reverse-engineer closed-source desktop software into CLI tools for AI agents. Verified CapCut, Axure RP and Shapr3D workflows.

Applied topics (this repository only, retaining its existing agent-skills topic):

```text
reverse-engineering ai-agents cli desktop-automation automation
agent-tools command-line capcut axure shapr3d python agent-skills
```

The About website points to the verified deployment URL. These settings were applied through the repository API; editing this document alone does not update GitHub settings. [GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics) support repository discovery.

## SEO and generative search

See the [audience, task and query analysis](search-intent.md) for the evidence behind content changes, discovery hypotheses and post-publication evaluation. The CapCut search failure motivates broader problem-based entry points, not a change to a CapCut-only product.

The site provides unique page titles, descriptions, canonical URLs, reciprocal English/Chinese alternates, Open Graph metadata, visible evidence links, source-code/article structured data and a sitemap. The README introduces the project before video content; the FAQs answer real setup, scope and verification questions. There are no fabricated testimonials or unverified platform claims.

Project Pages live below a path and cannot set the host's root `/robots.txt`. Do not claim a project-level robots file controls crawlers. The builder emits robots.txt only for a root-domain base URL. Submit the deployed sitemap URL directly in Google Search Console if ownership verification is available; Search Console is optional for public deployment.

Google says standard SEO and useful original content remain the basis for generative search, and that it does not use `llms.txt` for ranking. See [Google's generative search guidance](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide). No ranking or AI citation gains are claimed before measurement.

After publication, record a baseline for GitHub traffic/referrers and search queries such as “closed-source software automation”, “reverse engineering CLI for AI agents”, “CapCut CLI”, “Axure automation” and “闭源软件 AI Agent 自动化”. Check actual indexed pages and source citations over time. Avoid treating a single personalized AI response as a ranking measurement. No monitoring service or recurring automation is created by this change.

The [2026-10-16 keyword audit](search-keywords.md) and [48-query CSV](search-keywords.csv) preserve the reported queries, two expansion stages, audience mappings and evaluation set. These maintainer records are not additional search landing pages.
