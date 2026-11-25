/* Lightweight GSAP transitions; all content remains immediately usable without JS animations. */
(() => {
  const root = document.documentElement;
  const theme = document.getElementById('theme-toggle');
  const layout = document.getElementById('layout-toggle');
  const density = document.getElementById('density-toggle');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const gsap = window.gsap;
  let pageAnimation, dialogAnimation;
  function remember(key, value) { try { localStorage.setItem(key, value); } catch {} }
  function sync() {
    const dark = root.dataset.theme === 'dark';
    const comfy = root.dataset.layout === 'comfort';
    theme.setAttribute('aria-checked', String(dark));
    document.querySelector('meta[name="theme-color"]').content = dark ? '#07070f' : '#18191b';
    layout.setAttribute('aria-pressed', String(comfy));
    document.getElementById('layout-label').textContent = comfy ? 'Vista cómoda' : 'Vista clásica';
    layout.setAttribute('aria-label', comfy ? 'Vista cómoda activa. Cambiar a vista clásica' : 'Vista clásica activa. Cambiar a vista cómoda');
  }
  theme.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next; remember('tintastock-theme', next); sync();
  });
  layout.addEventListener('click', () => {
    const next = root.dataset.layout === 'comfort' ? 'classic' : 'comfort';
    root.dataset.layout = next; remember('tintastock-layout', next); sync();
    document.getElementById('nav-more')?.setAttribute('aria-expanded','false');
    document.getElementById('nav-secondary')?.classList.remove('open');
  });
  density.value=root.dataset.density||'compact';
  density.addEventListener('change',()=>{root.dataset.density=density.value;remember('tintastock-density',density.value)});
  sync();
  const clear = (targets) => { if (gsap && targets.length) gsap.set(targets, {clearProps:'opacity,transform'}); };
  function animatePage() {
    if (!gsap || motion.matches || document.hidden) return;
    pageAnimation?.kill();
    const groups = [...document.querySelectorAll('#page .page-head, #page .metric, #page .hero, #page .stock-surface, #page .context-panel, #page .grid > .panel, #page .card-grid > .panel, #page > .panel, #page .label-layout > .panel')].slice(0,12);
    if (!groups.length) return;
    pageAnimation=gsap.timeline();
    pageAnimation.fromTo(groups,{opacity:.65,y:10},{opacity:1,y:0,duration:.3,stagger:.025,ease:'power2.out',clearProps:'opacity,transform'});
    const bars=[...document.querySelectorAll('#page .bar-fill')].slice(0,12);
    if(bars.length)pageAnimation.fromTo(bars,{scaleX:.12},{scaleX:1,duration:.4,stagger:.025,ease:'power2.out',clearProps:'transform'},.12);
  }
  function animateDialog(event) {
    if (!gsap || motion.matches || document.hidden || !event.detail?.first) return;
    dialogAnimation?.kill();
    const panel=document.querySelector('.modal');
    dialogAnimation=gsap.fromTo(panel,{opacity:.75,y:10,scale:.985},{opacity:1,y:0,scale:1,duration:.23,ease:'power2.out',clearProps:'opacity,transform'});
  }
  function settle() {
    pageAnimation?.kill(); dialogAnimation?.kill();
    clear([...document.querySelectorAll('#page .page-head, #page .panel, #page .bar-fill, .modal')]);
  }
  document.addEventListener('tinta:page',animatePage);
  document.addEventListener('tinta:modal',animateDialog);
  motion.addEventListener?.('change',()=>{if(motion.matches)settle()});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)settle()});
  animatePage();
})();
