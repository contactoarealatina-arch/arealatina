/**
 * Area Latina Estudio - interacciones del sitio publico.
 *
 * Todo lo de aca es liviano y anda en cualquier equipo. Los efectos caros
 * se activan segun el atributo data-nivel que deja capacidades.js:
 *
 *   alto  -> WebGL en el hero + todos los efectos de puntero
 *   medio -> particulas en canvas 2D + efectos de puntero
 *   bajo  -> sin animacion: solo aparece el contenido
 */
(function () {
    'use strict';

    window.AL = window.AL || {};
    var cap = window.AL.capacidades || { nivel: 'bajo', punteroGrueso: true };
    var nivel = cap.nivel;
    var puntero = !cap.punteroGrueso;

    /* ======================================================================
       Aparecer al hacer scroll
       ====================================================================== */
    function revelar() {
        var elementos = document.querySelectorAll('.fade-in, [data-revelar]');
        if (!elementos.length) { return; }

        if (nivel === 'bajo' || !('IntersectionObserver' in window)) {
            elementos.forEach(function (el) { el.classList.add('visible'); });
            return;
        }

        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (!entrada.isIntersecting) { return; }
                var el = entrada.target;
                var retraso = parseInt(el.getAttribute('data-retraso') || '0', 10);
                setTimeout(function () { el.classList.add('visible'); }, retraso);
                observador.unobserve(el);
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

        elementos.forEach(function (el, i) {
            if (!el.hasAttribute('data-retraso')) {
                el.style.transitionDelay = (i % 6) * 80 + 'ms';
            }
            observador.observe(el);
        });
    }

    /* ======================================================================
       Navbar: sombra al bajar, se esconde al scrollear hacia abajo
       ====================================================================== */
    function navbar() {
        var barra = document.querySelector('.navbar-al');
        if (!barra) { return; }

        var ultimo = 0;
        var pendiente = false;

        function actualizar() {
            var y = window.scrollY;
            barra.classList.toggle('scrolled', y > 40);

            // Solo se esconde si el menu movil esta cerrado.
            var menu = document.getElementById('menuPrincipal');
            var menuAbierto = menu && menu.classList.contains('show');
            barra.classList.toggle('oculta', !menuAbierto && y > 300 && y > ultimo);

            ultimo = y;
            pendiente = false;
        }

        window.addEventListener('scroll', function () {
            if (!pendiente) {
                pendiente = true;
                requestAnimationFrame(actualizar);
            }
        }, { passive: true });

        actualizar();
    }

    /* ======================================================================
       Inclinacion 3D siguiendo el cursor
       ====================================================================== */
    function inclinacion() {
        if (!puntero || nivel === 'bajo') { return; }

        document.querySelectorAll('[data-tilt]').forEach(function (el) {
            var fuerza = parseFloat(el.getAttribute('data-tilt')) || 8;
            var marco = null;

            el.addEventListener('pointermove', function (e) {
                if (marco) { return; }
                marco = requestAnimationFrame(function () {
                    var caja = el.getBoundingClientRect();
                    var x = (e.clientX - caja.left) / caja.width - 0.5;
                    var y = (e.clientY - caja.top) / caja.height - 0.5;
                    el.style.transform =
                        'perspective(900px) rotateX(' + (-y * fuerza) + 'deg) ' +
                        'rotateY(' + (x * fuerza) + 'deg) translateZ(6px)';
                    el.style.setProperty('--brillo-x', (x * 100 + 50) + '%');
                    el.style.setProperty('--brillo-y', (y * 100 + 50) + '%');
                    marco = null;
                });
            }, { passive: true });

            el.addEventListener('pointerleave', function () {
                el.style.transform = '';
            }, { passive: true });
        });
    }

    /* ======================================================================
       Botones magneticos
       ====================================================================== */
    function magneticos() {
        if (!puntero || nivel === 'bajo') { return; }

        document.querySelectorAll('[data-iman]').forEach(function (el) {
            var fuerza = parseFloat(el.getAttribute('data-iman')) || 0.25;

            el.addEventListener('pointermove', function (e) {
                var caja = el.getBoundingClientRect();
                var x = e.clientX - caja.left - caja.width / 2;
                var y = e.clientY - caja.top - caja.height / 2;
                el.style.transform = 'translate(' + (x * fuerza) + 'px,' + (y * fuerza) + 'px)';
            }, { passive: true });

            el.addEventListener('pointerleave', function () {
                el.style.transform = '';
            }, { passive: true });
        });
    }

    /* ======================================================================
       Cursor propio (solo mouse real)
       ====================================================================== */
    function cursor() {
        if (!puntero || nivel === 'bajo') { return; }

        var punto = document.createElement('div');
        punto.className = 'cursor-punto';
        var aro = document.createElement('div');
        aro.className = 'cursor-aro';
        document.body.appendChild(punto);
        document.body.appendChild(aro);
        document.body.classList.add('con-cursor-propio');

        var raton = { x: -100, y: -100 };
        var pos = { x: -100, y: -100 };

        window.addEventListener('pointermove', function (e) {
            raton.x = e.clientX;
            raton.y = e.clientY;
            punto.style.transform = 'translate(' + raton.x + 'px,' + raton.y + 'px)';
        }, { passive: true });

        (function seguir() {
            pos.x += (raton.x - pos.x) * 0.18;
            pos.y += (raton.y - pos.y) * 0.18;
            aro.style.transform = 'translate(' + pos.x + 'px,' + pos.y + 'px)';
            requestAnimationFrame(seguir);
        })();

        var seleccion = 'a, button, input, textarea, select, [data-tilt], .filtro-pill';
        document.addEventListener('pointerover', function (e) {
            if (e.target.closest(seleccion)) { aro.classList.add('activo'); }
        });
        document.addEventListener('pointerout', function (e) {
            if (e.target.closest(seleccion)) { aro.classList.remove('activo'); }
        });
    }

    /* ======================================================================
       Contadores animados
       ====================================================================== */
    function contadores() {
        var nodos = document.querySelectorAll('[data-contador]');
        if (!nodos.length) { return; }

        function animar(el) {
            var destino = parseInt(el.getAttribute('data-contador'), 10) || 0;

            if (nivel === 'bajo') {
                el.textContent = destino;
                return;
            }

            var duracion = 1600;
            var inicio = null;

            function paso(ahora) {
                if (inicio === null) { inicio = ahora; }
                var avance = Math.min((ahora - inicio) / duracion, 1);
                // Desaceleracion suave al final.
                var suave = 1 - Math.pow(1 - avance, 3);
                el.textContent = Math.round(destino * suave);
                if (avance < 1) { requestAnimationFrame(paso); }
            }
            requestAnimationFrame(paso);
        }

        if (!('IntersectionObserver' in window)) {
            nodos.forEach(animar);
            return;
        }

        var obs = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    animar(entrada.target);
                    obs.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.5 });

        nodos.forEach(function (el) { obs.observe(el); });
    }

    /* ======================================================================
       Parallax suave por capas
       ====================================================================== */
    function parallax() {
        if (nivel === 'bajo') { return; }

        var capas = document.querySelectorAll('[data-parallax]');
        if (!capas.length) { return; }

        var pendiente = false;

        function mover() {
            var alto = window.innerHeight;
            capas.forEach(function (capa) {
                var caja = capa.getBoundingClientRect();
                if (caja.bottom < 0 || caja.top > alto) { return; }
                var factor = parseFloat(capa.getAttribute('data-parallax')) || 0.15;
                var centro = caja.top + caja.height / 2 - alto / 2;
                capa.style.transform = 'translate3d(0,' + (-centro * factor) + 'px,0)';
            });
            pendiente = false;
        }

        window.addEventListener('scroll', function () {
            if (!pendiente) {
                pendiente = true;
                requestAnimationFrame(mover);
            }
        }, { passive: true });

        mover();
    }

    /* ======================================================================
       Particulas en canvas 2D (respaldo cuando no hay WebGL)
       ====================================================================== */
    function particulas() {
        var canvas = document.getElementById('particulas');
        if (!canvas || nivel === 'bajo') { return; }

        var ctx = canvas.getContext('2d');
        var puntos = [];
        var ancho = 0;
        var alto = 0;
        var raton = { x: -999, y: -999 };

        var contenedor = canvas.parentElement || document.body;

        function dimensionar() {
            // Igual que en el hero WebGL: se mide el contenedor, no el canvas,
            // porque asignar canvas.width cambia su tamano intrinseco y
            // medirse a si mismo genera un bucle de crecimiento.
            ancho = canvas.width = Math.max(1, Math.min(
                contenedor.clientWidth || window.innerWidth || 1, 4096));
            alto = canvas.height = Math.max(1, Math.min(
                contenedor.clientHeight || window.innerHeight || 1, 4096));

            // Menos particulas en pantallas chicas: es donde mas duele.
            var cantidad = Math.min(Math.round(ancho / 26), 60);
            puntos = [];
            for (var i = 0; i < cantidad; i++) {
                puntos.push({
                    x: Math.random() * ancho,
                    y: Math.random() * alto,
                    r: Math.random() * 2 + 0.6,
                    vx: (Math.random() - 0.5) * 0.25,
                    vy: (Math.random() - 0.5) * 0.25,
                    a: Math.random() * 0.4 + 0.15
                });
            }
        }

        canvas.addEventListener('pointermove', function (e) {
            var caja = canvas.getBoundingClientRect();
            raton.x = e.clientX - caja.left;
            raton.y = e.clientY - caja.top;
        }, { passive: true });

        canvas.addEventListener('pointerleave', function () {
            raton.x = raton.y = -999;
        }, { passive: true });

        function dibujar() {
            ctx.clearRect(0, 0, ancho, alto);

            puntos.forEach(function (p) {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) { p.x = ancho; }
                if (p.x > ancho) { p.x = 0; }
                if (p.y < 0) { p.y = alto; }
                if (p.y > alto) { p.y = 0; }

                // El cursor las empuja suavemente.
                var dx = p.x - raton.x;
                var dy = p.y - raton.y;
                var dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 130) {
                    var empuje = (130 - dist) / 130 * 0.9;
                    p.x += (dx / dist) * empuje;
                    p.y += (dy / dist) * empuje;
                }

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

    /* ======================================================================
       Capa WebGL: se descarga SOLO si el equipo da el ancho
       ====================================================================== */
    function cargarWebGL() {
        if (nivel !== 'alto') { return; }
        if (!document.getElementById('hero-webgl')) { return; }
        var url = (window.AL.urls || {}).heroWebgl;
        if (!url) { return; }

        var s = document.createElement('script');
        s.src = url;
        s.defer = true;
        document.head.appendChild(s);
    }

    /* ====================================================================== */
    function iniciar() {
        revelar();
        navbar();
        inclinacion();
        magneticos();
        cursor();
        contadores();
        parallax();

        // El canvas 2D solo cuando NO hay capa WebGL.
        if (nivel === 'medio') { particulas(); }
        cargarWebGL();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
