# Brand: white / blue

Single source of truth for color across `apps/site/` and `apps/platform/`. Both restyles
must pull from this file rather than inventing their own values, so the two apps read as
one system rather than two unrelated redesigns.

## History — two palettes tried, this is the one that stuck

**First pass:** TU Sofia's own navy (`#1d3b76`), sampled directly from `tu-sofia.bg`'s
live header via `getComputedStyle`. Implemented with hand-rolled CSS, then rebuilt on
Tailwind + shadcn/ui. User's reaction to that whole direction: navy/blue anchored to the
university's own site, "looks terrible like a bootstrap of twitter." Rejected outright,
including the TU-navy anchor itself — see the session record for the full back-and-forth
(several shadcn preset options shown, a blue-forward round, then this).

**This pass — the one in force:** a plain white background with one confident blue
accent, arrived at through a visual concept comparison (a live picker artifact showing
real UI-card mockups in this exact palette), confirmed directly by the user. The blue
below is a **designed choice for this pass**, not re-sampled from an external source —
say so plainly rather than implying a provenance it doesn't have. It sits close to (but
is not identical to) TU Sofia's own CTA blue (`#1447e6`), which is a coincidence of both
being a confident, mid-saturation blue — not a deliberate callback.

## Tokens

```css
/* Brand — the settled palette. White page, one accent, one soft tint. Do not add a
   second brand hue (no purple, no green, no orange) without redoing this file. */
--brand-blue:        #2b62e6;  /* the one accent — reserve for ONE primary action/view */
--brand-blue-dark:   #1f4bc4;  /* hover/active state on --brand-blue */
--brand-blue-tint:   #eaf0ff;  /* soft background shapes, badges, subtle fills */

/* Neutrals — white carries the page, not a tinted neutral. Kept slightly cool so it
   doesn't fight the blue accent. */
--ink:            #0f172a;  /* body text, light mode */
--ink-muted:      #5b6478;
--paper:          #ffffff;  /* page background, light mode — this IS the brand now,
                                not a neutral default; don't tint it */
--paper-sunken:   #f4f7fd;  /* card/section backgrounds one step off white */
--border:         #e3e8f2;

/* Dark mode — white-as-brand has no direct dark equivalent, so dark mode is a
   conventional near-black inversion with the same blue accent lightened for contrast,
   not a literal invert of --paper. Verify contrast before shipping, these are not
   independently re-verified the way the light pairing was. */
--ink-dark:       #e8ecf5;
--ink-muted-dark: #99a2b8;
--paper-dark:     #0b0f1a;
--paper-sunken-dark: #131826;
--border-dark:    #232b3d;
--brand-blue-dark-mode: #6f97f2;  /* lightened so it clears AA on --paper-dark */

/* Semantic — functional, not brand. Never repurpose these for decoration. */
--success:        #176e45;  /* darkened from an earlier #1a7f4f: that measured 4.42:1 on
                                --success-tint, just under AA's 4.5:1 for body text. This
                                measures 5.52:1. */
--success-tint:   #e6f4ec;
--danger:         #c4293a;
--danger-tint:    #fbeaec;
--warning:        #a15c00;
--warning-tint:   #fbf0dc;
```

## Visual stack (decided 2026-09-12, superseding the first hand-rolled-CSS pass)

The first redesign pass (hand-rolled `course.css` custom properties, Django templates
styled by hand) read as dated rather than modern — confirmed by the user directly, not a
guess. Replacing it with the stack the current AI-coding-agent ecosystem has actually
converged on, per a live search on 2026-09-12 (shadcn/ui ~75k GitHub stars, official
Astro support, what Claude/Cursor/v0/Bolt are trained on and default to):

- **`apps/site/`** (Astro + Starlight, one React island): **Tailwind CSS + shadcn/ui**.
  shadcn ships component *source*, not a package — it lands in the repo as ordinary
  editable React/TSX, which is why agents default to it. Use Astro's official Tailwind
  integration and shadcn's Astro install path (check current docs at implementation
  time rather than trusting this file's memory of exact package names — verify, this
  moves fast). Starlight's own design tokens should be bridged to Tailwind's, not
  fought — Starlight ships an official Tailwind pairing for exactly this.
- **`apps/platform/`** (Django + HTMX, server-rendered, no React): **Tailwind CSS +
  DaisyUI**. shadcn doesn't apply here — it's a React source-copy pattern, and there is
  no React in this app, on purpose, per `CLAUDE.md`'s settled Django+HTMX stack
  decision. DaisyUI is the equivalent-tier, similarly-adopted choice for
  framework-agnostic server-rendered HTML: plain class names, no JS framework
  dependency, works directly in Django templates.
- **Both still read `docs/brand.md`'s color tokens above** — the library changes, the
  brand identity (TU Sofia navy, one-accent-per-view discipline) does not. Map the
  `--tu-*`/`--success`/etc. custom properties into each tool's own theming layer
  (Tailwind theme config / shadcn's CSS variables / DaisyUI's theme system) rather than
  hand-writing a second, parallel color system.
- Aim for what actually reads as current in 2026: generous whitespace, a restrained
  neutral base (the brand color does the talking, not five competing tones), soft
  borders and subtle shadows instead of heavy ones, real spacing rhythm, one accent
  color per view. Compare against what shadcn's own component gallery and Starlight's
  official demo sites look like before calling something done — not against what the
  first pass produced.

## Rules

1. **`--brand-blue` is scarce on purpose.** One primary action per view (the join-quiz
   button, "Стартирай" on the variance runner, one hero CTA) — not every button, link,
   and badge. The failure mode that got the first palette rejected was everything
   reading as "blue," not one accent standing out against a quiet page.
2. **White carries the identity now, not a brand color.** The page reads as clean and
   product-first because it's mostly white/near-white with restrained borders — the blue
   earns attention precisely because it's rare. Don't tint `--paper` toward blue "for
   brand consistency"; that's the mistake this pass moved away from.
3. **Imagery matches the discipline too.** Hero/background graphics (see the two concept
   directions under review) stay in this palette only — white ground, blue linework,
   `--brand-blue-tint` fills. No second hue, no photographic/gradient-blob treatment.
4. **Check contrast before shipping a new pairing.** `--ink` on `--paper` and
   `--brand-blue` on `--paper` are the two pairings actually verified; anything new
   (especially in dark mode, which is an inversion, not independently sampled) needs a
   real check against WCAG AA (4.5:1 body text, 3:1 large/bold text) before use.
5. **Semantic colors stay semantic.** `--success`/`--danger`/`--warning` are for pass/fail
   states (autograder results, form validation) — never used as decoration or to imply
   brand.
6. Both apps expose these as CSS custom properties on `:root` (and the dark-mode block),
   named identically, so a value changed here is a value changed in exactly two files,
   not a search-and-replace across templates.
