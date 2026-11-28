/* FrameForge V2 mobile navigation for compact Android and phone browsers. */
(() => {
  'use strict';
  const root = document;
  const destinations = {
    assets: '#ffv2AssetsPanel',
    timeline: '#ffv2TimelineSection',
    director: '#ffv2DirectorPanel',
    production: '#ffv2ProductionPanel',
    render: '#ffv2RenderQueuePanel'
  };
  function navigate(target, button) {
    const node = root.querySelector(destinations[target] || '');
    if (!node) return;
    if (target === 'assets') {
      const tab = root.querySelector('[data-panel="ffv2AssetsPanel"]');
      if (tab) tab.click();
    } else if (target === 'director' || target === 'production' || target === 'render') {
      const details = node.querySelector('details');
      if (details) details.open = true;
    }
    root.querySelectorAll('#ffv2MobileNav [data-mobile-target]').forEach(item => {
      if (item === button) item.setAttribute('aria-current', 'location');
      else item.removeAttribute('aria-current');
    });
    node.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }
  function bind() {
    const nav = root.getElementById('ffv2MobileNav');
    if (!nav || nav.dataset.bound === 'true') return;
    nav.dataset.bound = 'true';
    nav.addEventListener('click', event => {
      const button = event.target.closest('[data-mobile-target]');
      if (button) navigate(button.dataset.mobileTarget, button);
    });
  }
  if (root.readyState === 'loading') root.addEventListener('DOMContentLoaded', bind, { once: true });
  else bind();
  window.FFV2Mobile = { navigate };
})();