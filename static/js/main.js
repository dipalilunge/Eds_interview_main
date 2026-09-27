document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('faq-toggle');
  const panel = document.getElementById('faq-panel');
  const closeBtn = document.getElementById('faq-close');

  if (!toggle || !panel) return;

  const openPanel = () => {
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    const input = document.getElementById('faq-input');
    if (input) input.focus();
  };

  const closePanel = () => {
    panel.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
  };

  toggle.addEventListener('click', () => {
    panel.hidden ? openPanel() : closePanel();
  });

  if (closeBtn) closeBtn.addEventListener('click', closePanel);
});
