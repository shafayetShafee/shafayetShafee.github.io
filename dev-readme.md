# Dev Notes — shafayetShafee.github.io

Personal reference for updating and maintaining the Quarto personal website.

## Local Preview & Rendering

Preview the site locally with live reload:

```bash
quarto preview
```

Render everything without serving:

```bash
quarto render
```

## Publishing

### Full workflow before publishing

1. Make your changes on a feature/working branch
2. Commit your changes:
   ```bash
   git add .
   git commit -m "describe your changes"
   ```
3. Merge into `main`:
   ```bash
   git checkout main
   git merge your-branch-name
   ```
4. Push `main` to remote:
   ```bash
   git push origin main
   ```
5. Publish to GitHub Pages:
   ```bash
   quarto publish gh-pages --no-prompt
   ```

> [!NOTE]
> #### What `quarto publish gh-pages` does
>
> - Renders all `.qmd` files to HTML
> - Checks out the `gh-pages` branch in a hidden worktree (without disturbing your `main` files)
> - Commits the rendered HTML there as `"Built site for gh-pages"`
> - Pushes `gh-pages` to GitHub, which triggers deployment
>
> Your `main` branch always holds **source files** (`.qmd`, `.bib`, `.py`, etc.).
> The `gh-pages` branch holds only **rendered HTML** — managed entirely by Quarto.
>
> GitHub Pages uses caching. If changes don't appear immediately, do a hard refresh
> (`Ctrl+Shift+R` or `Cmd+Shift+R`) in your browser.


## Freeze

The publications page has `freeze: false` in its YAML front matter because it
runs Python code that must re-execute on every render (to pick up new `.bib` entries).

Other pages use `freeze: true` (set globally in `_quarto.yml`). To force re-execution
of a frozen page after editing it:

```bash
# Delete that page's freeze cache, e.g. for about.qmd:
rm -rf _freeze/about/

# Then render/preview normally — it will re-execute and re-freeze
quarto preview
```

Or to re-run everything at once:

```bash
quarto render --no-freeze
```

## Adding a New Publication

### Step 1 — Add the BibTeX entry to `publications.bib`

```bibtex
@article{yourkey2026,
  title   = {Your Paper Title},
  author  = {Shafee, Shafayet Khan AND Coauthor, Name},
  year    = 2026,
  journal = {Journal Name},
  volume  = 1,
  number  = 1,
  pages   = {1--10},
  doi     = {10.xxxx/xxxxxx},
}
```

For arXiv preprints:

```bibtex
@misc{yourkey2026,
  title        = {Your Preprint Title},
  author       = {Shafayet Khan Shafee and Coauthor Name},
  year         = 2026,
  eprint       = {2606.XXXXX},
  archivePrefix = {arXiv},
  primaryClass = {stat.ME},
  url          = {https://arxiv.org/abs/2606.XXXXX},
}
```

> [!IMPORTANT]
> The BibTeX key (e.g. `yourkey2026`) is what ties everything together.
> Use it consistently across the `.bib` file and the YAML links file.

### Step 2 — Add extra links to `pubs_additional_links.yml`

```yaml
yourkey2026:
  - link: https://arxiv.org/pdf/2606.XXXXX
    icon: fa fa-file-pdf
    text: PDF
  - link: https://doi.org/10.6084/m9.figshare.XXXXXXX
    icon: ai ai-open-data
    text: Paper Data
  - link: https://github.com/shafayetShafee/your-repo
    icon: fa-brands fa-github
    text: Paper Code
```

If there are no extra links for an entry, you can omit it from the YAML entirely.

### Step 3 — Update the one-liner on the homepage

In `index.qmd`, update the Research & Publications section to reflect the new count:

```markdown
I have [**two**](publications/index.qmd) peer-reviewed publications ...
```

### Step 4 — Preview and publish

```bash
quarto preview
git add .
git commit -m "add new publication"
git checkout main
git merge your-branch-name
git push origin main
quarto publish gh-pages --no-prompt
```

## Adding a New Blog Post

```bash
# Create a new post folder and file
mkdir posts/your-post-slug
touch posts/your-post-slug/index.qmd
```

Add YAML front matter to the new file:

```yaml
---
title: "Your Post Title"
date: 2026-06-17
categories: [statistics, R]
---
```

Then preview, commit, and publish as usual.


## Updating Homepage Content

All homepage content lives in `index.qmd`. Sections are clearly headed with `##`.

