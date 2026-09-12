/**
 * Scroll-driven parallax for the homepage hero (tilted browser frame + glow) and the
 * floating product-fragment cards scattered further down the page. One rAF-throttled
 * scroll listener drives every `[data-parallax-*]` element on the page.
 *
 * Deliberately NOT IntersectionObserver-driven: this only ever computes a continuous
 * value per frame (translateY proportional to distance from a fixed reference point —
 * `window.scrollY` for the hero, viewport-centre distance via `getBoundingClientRect`
 * for the floating cards). There is no "snap to nearest of N discrete things" logic
 * here, which is the specific pattern that produces stale/desynced state under fast
 * scrolling — see the card comment below for the one spot that could be mistaken for
 * that pattern and isn't.
 *
 * Respects `prefers-reduced-motion`: when it's on (or the viewport is narrow enough
 * that the floating cards don't render at all, see course.css's breakpoint), every
 * element is left at its CSS-authored rest transform and no scroll listener runs.
 */

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
/* Keep in sync with the breakpoint in course.css that hides `.home-floating-cards`
 * and disables the hero's own tilt/position shift on narrow viewports (see the "Narrow
 * screens" section of course.css). */
const NARROW_VIEWPORT_QUERY = '(max-width: 48rem)';

function initHomeParallax(): void {
  const heroFrame = document.querySelector<HTMLElement>('[data-parallax-frame]');
  const heroGlow = document.querySelector<HTMLElement>('[data-parallax-glow]');
  const cards = Array.from(document.querySelectorAll<HTMLElement>('[data-parallax-card]'));

  if (!heroFrame && !heroGlow && cards.length === 0) return;

  const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY);
  const narrowViewport = window.matchMedia(NARROW_VIEWPORT_QUERY);

  let scrollHandlerAttached = false;
  let frameRequested = false;

  function motionAllowed(): boolean {
    return !reducedMotion.matches && !narrowViewport.matches;
  }

  function resetTransforms(): void {
    heroFrame?.style.removeProperty('transform');
    heroGlow?.style.removeProperty('transform');
    for (const card of cards) card.style.removeProperty('transform');
  }

  /** One continuous update per frame — no discrete-state tracking anywhere in here. */
  function update(): void {
    frameRequested = false;
    if (!motionAllowed()) return;

    const scrollY = window.scrollY;

    if (heroFrame) {
      // Capped so the tilt settles once the hero has scrolled well past, rather than
      // drifting indefinitely on a long page.
      const progress = Math.min(scrollY, 640) / 640;
      const baseRotateX = 6;
      const baseRotateY = -3;
      const rotateX = baseRotateX - progress * 5;
      const rotateY = baseRotateY + progress * 2.5;
      const translateY = progress * 26;
      heroFrame.style.transform =
        `perspective(1400px) rotateX(${rotateX.toFixed(2)}deg) ` +
        `rotateY(${rotateY.toFixed(2)}deg) translateY(${translateY.toFixed(1)}px)`;
    }

    if (heroGlow) {
      const translateY = Math.min(scrollY, 640) * 0.18;
      heroGlow.style.transform = `translate3d(0, ${translateY.toFixed(1)}px, 0)`;
    }

    // Continuous parallax offset per card: each card's own distance from the vertical
    // centre of the viewport, scaled by that card's speed and its fixed rotation. This
    // is a plain function of scroll position re-evaluated every frame — not a "which
    // card is active" decision — so it can't go stale the way discrete-threshold
    // IntersectionObserver logic can under fast scrolling.
    const viewportCenter = window.innerHeight / 2;
    for (const card of cards) {
      const speed = Number(card.dataset.parallaxCard) || 0.08;
      const rotate = Number(card.dataset.parallaxRotate) || 0;
      const rect = card.getBoundingClientRect();
      const distanceFromCenter = viewportCenter - (rect.top + rect.height / 2);
      const translateY = distanceFromCenter * speed;
      card.style.transform = `translate3d(0, ${translateY.toFixed(1)}px, 0) rotate(${rotate}deg)`;
    }
  }

  function onScroll(): void {
    if (frameRequested) return;
    frameRequested = true;
    requestAnimationFrame(update);
  }

  function syncMotionState(): void {
    if (motionAllowed()) {
      if (!scrollHandlerAttached) {
        window.addEventListener('scroll', onScroll, { passive: true });
        scrollHandlerAttached = true;
      }
      update();
    } else {
      if (scrollHandlerAttached) {
        window.removeEventListener('scroll', onScroll);
        scrollHandlerAttached = false;
      }
      resetTransforms();
    }
  }

  syncMotionState();
  reducedMotion.addEventListener('change', syncMotionState);
  narrowViewport.addEventListener('change', syncMotionState);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initHomeParallax);
} else {
  initHomeParallax();
}
