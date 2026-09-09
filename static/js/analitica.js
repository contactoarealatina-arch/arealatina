/* Aviso de cookies y medición con Google Analytics.
 *
 * La medición NO arranca sola. El sitio le promete al visitante, en el
 * aviso y en la política de privacidad, que puede quedarse solo con las
 * cookies técnicas; cargar Analytics igual haría falsa esa promesa.
 *
 * Por eso el orden es: primero la persona elige, después (y solo si
 * aceptó) se trae el script de Google.
 */
(function () {
    'use strict';

    var CLAVE = 'al-consentimiento';   // 'todo' | 'basico'
    var CLAVE_VIEJA = 'al-cookies';    // el aviso anterior, sin opciones

    window.AL = window.AL || {};

    // El codigo de medicion viene en el atributo data-ga de esta misma
    // etiqueta. Se lee ahora y no despues porque document.currentScript
    // solo apunta acá mientras el archivo se esta ejecutando.
    var etiquetaPropia = document.currentScript;
    window.AL.ga = (etiquetaPropia && etiquetaPropia.dataset.ga) || '';

    // -----------------------------------------------------------------
    // Memoria de la decisión
    // -----------------------------------------------------------------
    // Todo lo que toca localStorage va en try/catch: en ventana privada
    // el navegador lanza una excepción al leerlo y sin esto se cae la
    // página entera por un aviso de cookies.
    function leerDecision() {
        try {
            var valor = localStorage.getItem(CLAVE);
            if (valor === 'todo' || valor === 'basico') { return valor; }
            // Quien ya había apretado "Entendido" en el aviso viejo nunca
            // aceptó medición: se le respeta como "solo lo necesario" en
            // vez de darlo por aceptado.
            if (localStorage.getItem(CLAVE_VIEJA) === 'ok') { return 'basico'; }
        } catch (e) {}
        return null;
    }

    function guardarDecision(valor) {
        try { localStorage.setItem(CLAVE, valor); } catch (e) {}
    }

    // -----------------------------------------------------------------
    // Google Analytics
    // -----------------------------------------------------------------
    var gaListo = false;
    var pendientes = [];   // eventos disparados antes de que cargue

    function cargarAnalytics() {
        var id = window.AL.ga;
        if (!id || gaListo) { return; }
        gaListo = true;

        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag('js', new Date());
        window.gtag('config', id);

        var etiqueta = document.createElement('script');
        etiqueta.async = true;
        etiqueta.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
        document.head.appendChild(etiqueta);

        // Los clics que ocurrieron mientras el visitante leía el aviso no
        // se pierden: quedan guardados y salen ahora.
        pendientes.forEach(function (p) { window.gtag('event', p[0], p[1]); });
        pendientes = [];
    }

    /* Registra un evento. Si el visitante no aceptó medición, no hace
     * nada: es una función que se puede llamar siempre sin preguntar. */
    window.AL.evento = function (nombre, datos) {
        if (!nombre) { return; }
        if (!window.AL.ga) { return; }
        if (!gaListo) {
            if (leerDecision() === 'todo') { cargarAnalytics(); }
            else { pendientes.push([nombre, datos || {}]); return; }
        }
        window.gtag('event', nombre, datos || {});
    };

    // -----------------------------------------------------------------
    // Eventos declarados en el HTML
    // -----------------------------------------------------------------
    // Un solo escuchador para toda la página en vez de uno por botón:
    // así un botón nuevo solo necesita su atributo data-evento y no hay
    // que acordarse de venir a tocar este archivo.
    document.addEventListener('click', function (ev) {
        var origen = ev.target.closest('[data-evento]');
        if (!origen) { return; }

        var datos = {};
        var crudos = origen.getAttribute('data-evento-datos');
        if (crudos) {
            try { datos = JSON.parse(crudos); } catch (e) {}
        }
        window.AL.evento(origen.getAttribute('data-evento'), datos);
    });

    // -----------------------------------------------------------------
    // El aviso
    // -----------------------------------------------------------------
    function iniciarAviso() {
        var aviso = document.getElementById('avisoCookies');
        if (!aviso) { return; }

        var decision = leerDecision();
        if (decision) {
            if (decision === 'todo') { cargarAnalytics(); }
            return;
        }

        aviso.hidden = false;
        requestAnimationFrame(function () { aviso.classList.add('visible'); });

        function responder(valor) {
            guardarDecision(valor);
            aviso.classList.remove('visible');
            setTimeout(function () { aviso.hidden = true; }, 300);
            if (valor === 'todo') { cargarAnalytics(); }
        }

        var aceptar = document.getElementById('aceptarCookies');
        var soloBasico = document.getElementById('rechazarCookies');
        if (aceptar) {
            aceptar.addEventListener('click', function () { responder('todo'); });
        }
        if (soloBasico) {
            soloBasico.addEventListener('click', function () { responder('basico'); });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciarAviso);
    } else {
        iniciarAviso();
    }
})();
