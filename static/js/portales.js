/**
 * Área Latina Estudio — comportamiento común de los portales de profesoras
 * y alumnos. Todo es opcional: sin JS los formularios siguen funcionando.
 */
(function () {
    'use strict';

    /* Los mensajes del servidor se desvanecen solos después de unos segundos,
       salvo los de error, que conviene que la persona alcance a leer. */
    function mensajesTemporales() {
        document.querySelectorAll('.p-mensaje').forEach(function (aviso) {
            if (aviso.classList.contains('error')) { return; }
            setTimeout(function () {
                aviso.style.transition = 'opacity .4s ease, transform .4s ease';
                aviso.style.opacity = '0';
                aviso.style.transform = 'translateY(-8px)';
                setTimeout(function () { aviso.remove(); }, 420);
            }, 5000);
        });
    }

    /* Cuenta regresiva hasta la próxima clase. */
    function cuentaRegresiva() {
        var nodo = document.querySelector('[data-cuenta]');
        if (!nodo) { return; }

        var objetivo = new Date(nodo.getAttribute('data-cuenta'));
        if (isNaN(objetivo.getTime())) { return; }

        function pintar() {
            var faltan = objetivo - new Date();
            if (faltan <= 0) {
                nodo.textContent = 'Está empezando';
                return;
            }
            var dias = Math.floor(faltan / 86400000);
            var horas = Math.floor(faltan / 3600000) % 24;
            var minutos = Math.floor(faltan / 60000) % 60;

            if (dias > 0) {
                nodo.textContent = 'En ' + dias + ' día' + (dias !== 1 ? 's' : '') +
                                   ' y ' + horas + ' h';
            } else if (horas > 0) {
                nodo.textContent = 'En ' + horas + ' h ' + minutos + ' min';
            } else {
                nodo.textContent = 'En ' + minutos + ' minuto' + (minutos !== 1 ? 's' : '');
            }
        }

        pintar();
        setInterval(pintar, 30000);
    }

    /* Confirmaciones antes de acciones que no se pueden deshacer. */
    function confirmaciones() {
        document.querySelectorAll('[data-confirmar]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                if (!window.confirm(form.getAttribute('data-confirmar'))) {
                    e.preventDefault();
                }
            });
        });
    }

    function iniciar() {
        mensajesTemporales();
        cuentaRegresiva();
        confirmaciones();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
