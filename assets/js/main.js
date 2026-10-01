/* Navigation, category filtering, accessible project dialogs and mail drafts. */
(() => {
  'use strict';
  const uiCopy = JSON.parse(document.getElementById('site-ui-copy').textContent);
  document.body.classList.add('enhanced');
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#navigation');
  const closeMenu = () => {
    nav.classList.remove('is-open');
    menu.setAttribute('aria-expanded', 'false');
    menu.querySelector('span').textContent = '＋';
  };
  menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    nav.classList.toggle('is-open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.querySelector('span').textContent = open ? '−' : '＋';
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
      closeMenu(); menu.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.header')) closeMenu();
  });
  const projects = [...document.querySelectorAll('.project[data-category]')];
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      const filter = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      let count = 0;
      projects.forEach(project => {
        const show = filter === 'all' || project.dataset.category.split(',').map(s => s.trim()).includes(filter);
        project.hidden = !show;
        if (show) count++;
      });
      document.querySelector('.result-count').textContent = (count === 1 ? uiCopy.count_one : uiCopy.count_many).replace('{count}', String(count));
    });
  });
  const dialog = document.querySelector('.modal');
  if (dialog && typeof dialog.showModal === 'function') {
    let trigger = null;
    const openProject = (id, source) => {
      const detail = document.getElementById(id);
      if (!detail || !detail.classList.contains('project-detail')) return;
      trigger = source || document.querySelector(`[data-project="${CSS.escape(id)}"]`);
      const clone = detail.cloneNode(true);
      clone.id = `modal-${id}`;
      const heading = clone.querySelector('h2');
      heading.id = `modal-title-${id}`;
      clone.setAttribute('aria-labelledby', heading.id);
      dialog.setAttribute('aria-labelledby', heading.id);
      dialog.querySelector('.modal-content').replaceChildren(clone);
      if (!dialog.open) dialog.showModal();
      dialog.scrollTop = 0;
      document.body.classList.add('modal-open');
    };
    document.querySelectorAll('[data-project]').forEach(anchor => {
      anchor.addEventListener('click', event => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        history.pushState(null, '', '#' + anchor.dataset.project);
        openProject(anchor.dataset.project, anchor);
      });
    });
    const readHash = () => {
      let id;
      try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
      if (id) openProject(id);
      else if (dialog.open) dialog.close();
    };
    dialog.querySelector('.modal-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => {
      document.body.classList.remove('modal-open');
      if (location.hash) history.replaceState(null, '', location.pathname + location.search);
      if (trigger && !trigger.closest('[hidden]')) trigger.focus({preventScroll:true});
    });
    window.addEventListener('hashchange', readHash);
    readHash();
  } else if (dialog) {
    document.querySelector('.project-details').style.display = 'block';
  }
  const form = document.querySelector('[data-mail-form]');
  if (form) {
    if (new URLSearchParams(location.search).get('type') === 'speaking') form.elements.type.selectedIndex = 1;
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const to = form.dataset.mailTo;
      const feedback = form.querySelector('.form-feedback');
      feedback.hidden = false;
      if (!to) { feedback.textContent = uiCopy.mail_unset; return; }
      const values = new FormData(form);
      const value = key => String(values.get(key) || '').trim();
      const fillCopy = template => template.replace(/\{(name|company|email|type|message)\}/g, (_, key) => value(key));
      const subject = fillCopy(uiCopy.mail_subject);
      const body = fillCopy(uiCopy.mail_body);
      feedback.textContent = uiCopy.mail_help;
      location.href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    });
  }
})();

/* Motion is progressive enhancement: content remains visible without JS. */
(() => {
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  if (!Element.prototype.animate) return;
  const running = new Set();
  const play = (element, keyframes, options) => {
    const animation = element.animate(keyframes, options);
    running.add(animation);
    animation.finished.catch(() => {}).finally(() => running.delete(animation));
    return animation;
  };
  // Separate the oversized title lines without changing their accessible text.
  document.querySelectorAll('.page-intro h1').forEach(heading => {
    [...heading.childNodes].forEach(node => {
      if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) return;
      const line = document.createElement('span');
      line.className = 'motion-line';
      node.replaceWith(line);
      line.append(node);
    });
  });
  const targets = new Map();
  const register = (selector, type) => document.querySelectorAll(selector).forEach((element, index) => {
    if (!element.closest('.project-details, .modal')) targets.set(element, {type, index});
  });
  register('.hero-copy, .hero-topline, .hero-bottom, .section-heading > .eyebrow, .speaking-copy > p, .lecture-intro-copy > p, .topic, .approach-row, .steps li, .faq details, .about-home > div, .profile > div, .fields li, .contact-layout > *, .project-caption, .contact-band-top, .contact-band-bottom, .page-intro-description', 'soft');
  register('.project-image, .lecture-photo, .about-home figure, .profile figure, .event-entry figure', 'photo');
  register('.section-heading h2, .speaking-copy h3, .lecture-intro-copy h2', 'heading');
  register('.hero-display > span:not(.hero-asterisk), .page-intro h1 > span, .contact-large', 'display');
  const reveal = (element, {type, index}) => {
    if (preference.matches) return;
    const delay = type === 'display' ? index % 3 * 180 : type === 'soft' ? index % 3 * 70 : 0;
    const start = type === 'display'
      ? {opacity:0, transform:'translateY(100px) rotate(4deg) scale(.92)', filter:'blur(8px)'}
      : type === 'heading'
      ? {opacity:0, transform:'translateY(65px) rotate(1.5deg)', filter:'blur(3px)'}
      : type === 'photo'
      ? {opacity:0, transform:'translateY(55px) scale(.96)', filter:'blur(2px)'}
      : {opacity:0, transform:'translateY(24px)', filter:'blur(0px)'};
    play(element, [start, {opacity:1,transform:'translateY(0) rotate(0) scale(1)',filter:'blur(0px)'}], {
      duration: type === 'display' ? 2400 : type === 'photo' ? 2200 : type === 'heading' ? 1900 : 1500,
      delay, easing:'cubic-bezier(.16,1,.3,1)', fill:'backwards'
    });
  };
  let observer;
  if (!preference.matches && 'IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        reveal(entry.target, targets.get(entry.target));
        observer.unobserve(entry.target);
      });
    }, {threshold:0.08});
    targets.forEach((motion, element) => observer.observe(element));
  }
  // Fade out before a local page navigation; same-page anchors and project
  // dialogs retain their normal behavior. No interception of mail/external links.
  let navigating = false;
  const reset = () => {
    navigating = false;
    running.forEach(animation => animation.cancel());
    running.clear();
  };
  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || preference.matches) return;
    const anchor = event.target.closest('a[href]');
    if (!anchor || anchor.hasAttribute('download') || (anchor.target && anchor.target !== '_self')) return;
    const destination = new URL(anchor.href, location.href);
    if (destination.origin !== location.origin || !/\.html$/.test(destination.pathname) || (destination.pathname === location.pathname && destination.search === location.search)) return;
    event.preventDefault();
    if (navigating) return;
    navigating = true;
    const animation = play(document.querySelector('main'), [
      {opacity:1,transform:'translateY(0)'},
      {opacity:0,transform:'translateY(-18px)'}
    ], {duration:450,easing:'ease-in',fill:'forwards'});
    animation.finished.catch(() => {}).then(() => location.assign(destination.href));
  });
  window.addEventListener('pageshow', event => { if (event.persisted) reset(); });
  preference.addEventListener('change', () => {
    if (preference.matches) { observer?.disconnect(); reset(); }
  });
})();
