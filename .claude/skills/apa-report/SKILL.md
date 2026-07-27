---
name: apa-report
description: Generate a professional APA 7th edition formatted report or case study as an HTML artifact. Use when creating a task report, delivery document, or case study for a client. Loads template.html as the starting structure — fill in content, never rebuild from scratch.
---

# APA 7th Report Generator

Produces client-facing task reports and case studies formatted to APA 7th edition standards. No academic sections (no Abstract, Methods, References) — just the formatting conventions applied to professional deliverable content.

## When to Use

- Task delivery reports for Jordan / LazySun
- Feature implementation case studies
- Any professional document that needs formal structure

---

## Step 1 — Gather Content

Before opening the template, have ready:
- **Title** of the report
- **Author**: Lebron James D.G. Rodriguez
- **Client**: who it's for (e.g. Jordan Haddadi & Mark Pomykato, Lazy Sun)
- **Date**: current month + year
- **Sections**: the content to fill in (can be from a Google Doc, notes, or conversation context)

**To extract content from a Google Doc:**
```
Navigate the authenticated browser to:
https://docs.google.com/document/d/{DOC_ID}/export?format=txt
The file downloads automatically. Read the .txt file from .playwright-mcp/.
```

---

## Step 2 — Use the Template

Read the template file:
```
C:\Users\HomePC\ljr-dev-os\.claude\skills\apa-report\template.html
```

Fill in all `{{PLACEHOLDER}}` values and add content sections following the heading rules below.

---

## APA 7th Formatting Rules (applied here)

### Headings
```
Level 1 — <h1>: centered, bold         → major sections (e.g. "I. What We Built")
Level 2 — <h2>: flush left, bold       → subsections
Level 3 — <h3>: flush left, bold italic → sub-subsections (e.g. proof case groups)
```

### Body Text
- 0.5" first-line indent on all paragraphs
- No indent on first paragraph after a heading
- Double-spaced line height
- Times New Roman 12pt (16px on screen)

### Figures — APA Format
```html
<div class="figure">
  <span class="fig-label">Figure N</span>
  <span class="fig-title">Descriptive Title in Title Case</span>
  <div class="fig-img">[ Insert: filename.png — 900–1200 px wide ]</div>
  <p class="fig-note"><strong>Note.</strong> One sentence describing what the figure confirms. Context note.</p>
</div>
```
Figures are numbered sequentially throughout the document (1, 2, 3...). No "Exhibit" — always "Figure".

### Appendix
```html
<p class="app-label">Appendix</p>
<p class="app-title">Descriptive Title</p>
<!-- h2 for each appendix section, pre for code blocks -->
```

---

## Step 3 — Publish as Artifact

Write the filled template to the scratchpad, then publish:
```
Artifact(file_path="scratchpad/report_name.html", favicon="📄", description="...")
```

---

## Image Sizes for Figures

| Use case | Width |
|---|---|
| Shopify UI screenshots (cart, PDP, checkout) | 900–1200px, cropped to relevant UI only |
| Full-page screenshots | 1200–1600px |
| Print-ready (300 DPI, 6.5" column) | 1950px |

Crop tight. Show only the relevant area, not the full browser window.
