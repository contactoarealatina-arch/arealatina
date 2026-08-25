/* Area Latina Estudio - interacciones del sitio publico */
(function () {
    'use strict';

    /* ----------------------------------------------------------------------
       Fade-in al hacer scroll (Intersection Observer)
       ---------------------------------------------------------------------- */
    function activarFadeIn() {
        var elementos = document.querySelectorAll('.fade-in');
        if (!elementos.length) {
            return;
        }

        if (!('IntersectionObserver' in window)) {
            elementos.forEach(function (el) { el.classList.add('visible'); });
            return;
        }

        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.add('visible');
                    observador.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

        elementos.forEach(function (el, i) {
            el.style.transitionDelay = (i % 6) * 80 + 'ms';
            observador.observe(el);
        });
    }

    /* ----------------------------------------------------------------------
       Sombra de la navbar al hacer scroll
       ---------------------------------------------------------------------- */
    function activarNavbarScroll() {
        var navbar = document.querySelector('.navbar-al');
        if (!navbar) {
            return;
        }
        var alternar = function () {
            navbar.classList.toggle('scrolled', window.scrollY > 40);
        };
        alternar();
        window.addEventListener('scroll', alternar, { passive: true });
    }

    /* ----------------------------------------------------------------------
       Particulas sutiles del hero
       ---------------------------------------------------------------------- */
    function activarParticulas() {
        var canvas = document.getElementById('particulas');
        if (!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        var ctx = canvas.getContext('2d');
        var particulas = [];
        var ancho = 0;
        var alto = 0;

        function dimensionar() {
            ancho = canvas.width = canvas.offsetWidth;
            alto = canvas.height = canvas.offsetHeight;
            var cantidad = Math.min(Math.round(ancho / 22), 70);
            particulas = [];
            for (var i = 0; i < cantidad; i++) {
                particulas.push({
                    x: Math.random() * ancho,
                    y: Math.random() * alto,
                    r: Math.random() * 2 + 0.6,
                    vx: (Math.random() - 0.5) * 0.25,
                    vy: (Math.random() - 0.5) * 0.25,
                    a: Math.random() * 0.4 + 0.15
                });
            }
        }

        function dibujar() {
            ctx.clearRect(0, 0, ancho, alto);
            particulas.forEach(function (p) {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) { p.x = ancho; }
                if (p.x > ancho) { p.x = 0; }
                if (p.y < 0) { p.y = alto; }
                if (p.y > alto) { p.y = 0; }

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255, 138, 101, ' + p.a + ')';
                ctx.fill();
            });
            requestAnimationFrame(dibujar);
        }

        dimensionar();
        window.addEventListener('resize', dimensionar);
        requestAnimationFrame(dibujar);
    }

    document.addEventListener('DOMContentLoaded', function () {
        activarFadeIn();
        activarNavbarScroll();
        activarParticulas();
    });
})();
