/* SaeVocalLab — main.js */
(function () {
  'use strict';
  document.documentElement.classList.add('js');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Header shadow on scroll + SP bar hide near footer */
  var header = document.querySelector('.header');
  var spBar = document.querySelector('.sp-bar');
  var footer = document.querySelector('.footer');
  function onScroll() {
    var y = window.scrollY;
    if (header) header.classList.toggle('is-scrolled', y > 10);
    if (spBar && footer) {
      var ft = footer.getBoundingClientRect().top;
      spBar.classList.toggle('is-hidden', ft < window.innerHeight - 40 || y < 200);
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* SP drawer menu */
  var drawer = document.querySelector('.drawer');
  var openBtn = document.querySelector('.menu-btn');
  function setMenu(open) {
    if (!drawer) return;
    drawer.classList.toggle('is-open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    if (openBtn) openBtn.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  }
  if (openBtn) openBtn.addEventListener('click', function () { setMenu(true); });
  document.querySelectorAll('[data-close-menu]').forEach(function (el) {
    el.addEventListener('click', function () { setMenu(false); });
  });
  if (drawer) drawer.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () { setMenu(false); });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });

  /* In-view fade */
  var fades = document.querySelectorAll('.fade');
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    fades.forEach(function (el) { io.observe(el); });
  } else {
    fades.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* Watermark parallax */
  var marks = document.querySelectorAll('.watermark');
  if (marks.length && !reduce) {
    var ticking = false;
    function para() {
      marks.forEach(function (m) {
        var r = m.parentElement.getBoundingClientRect();
        var p = (r.top + r.height / 2 - window.innerHeight / 2) / window.innerHeight;
        var dir = m.classList.contains('watermark--r') ? -1 : 1;
        m.style.transform = 'translateX(' + (p * 120 * dir) + 'px)';
      });
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { requestAnimationFrame(para); ticking = true; }
    }, { passive: true });
    para();
  }

  /* SP carousels with dots */
  document.querySelectorAll('[data-carousel]').forEach(function (track) {
    var dots = document.querySelector('[data-dots="' + track.getAttribute('data-carousel') + '"]');
    if (!dots) return;
    var items = Array.prototype.slice.call(track.children);
    items.forEach(function (item, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', (i + 1) + '枚目へ');
      b.addEventListener('click', function () {
        track.scrollTo({ left: item.offsetLeft - (track.clientWidth - item.clientWidth) / 2, behavior: 'smooth' });
      });
      dots.appendChild(b);
    });
    function update() {
      var c = track.scrollLeft + track.clientWidth / 2, best = 0, d = Infinity;
      items.forEach(function (it, i) {
        var m = Math.abs(it.offsetLeft + it.clientWidth / 2 - c);
        if (m < d) { d = m; best = i; }
      });
      Array.prototype.forEach.call(dots.children, function (b, i) { b.classList.toggle('is-active', i === best); });
    }
    track.addEventListener('scroll', function () { requestAnimationFrame(update); }, { passive: true });
    window.addEventListener('resize', update);
    update();
  });

  /* FAQ accordion */
  document.querySelectorAll('.faq__q').forEach(function (q) {
    q.addEventListener('click', function () {
      var item = q.closest('.faq__item');
      var open = !item.classList.contains('is-open');
      item.classList.toggle('is-open', open);
      q.setAttribute('aria-expanded', String(open));
    });
  });
})();
