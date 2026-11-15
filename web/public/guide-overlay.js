/* Keep both guides in a closed, accessible dialog without changing their forms. */
window.CardenveilGuideOverlay = {
  mount(root) {
    const dialog = root.querySelector('.guide-dialog');
    const launcher = root.querySelector('.guide-launcher');
    const rules = document.querySelector('.rules-chat');
    const marker = document.createComment('rules-guide-position');
    if (rules) rules.before(marker);
    launcher.addEventListener('click', () => {
      if (rules) dialog.append(rules);
      dialog.showModal();
      launcher.setAttribute('aria-expanded', 'true');
    });
    dialog.querySelector('.guide-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
      if (rules && marker.isConnected) marker.after(rules);
      launcher.setAttribute('aria-expanded', 'false');
      launcher.focus();
    });
  }
};
