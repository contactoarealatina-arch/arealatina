/**
 * Area Latina Estudio - deteccion de capacidades del dispositivo.
 *
 * Corre ANTES de pintar la pagina y marca <html> con:
 *   data-nivel   = "alto" | "medio" | "bajo"
 *   data-puntero = "fino" | "grueso"
 *
 * El resto del CSS y del JS se apoya en esos atributos, asi que un equipo
 * lento nunca llega a descargar ni a ejecutar los efectos pesados.
 */
(function () {
    'use strict';

    var raiz = document.documentElement;

    /* ------------------------------------------------------------------
       Senales del dispositivo
       ------------------------------------------------------------------ */
    function consulta(mq) {
        return window.matchMedia && window.matchMedia(mq).matches;
    }

    var reduceMovimiento = consulta('(prefers-reduced-motion: reduce)');
    var punteroGrueso = consulta('(pointer: coarse)') || !consulta('(hover: hover)');

    // Memoria y nucleos: no todos los navegadores los exponen.
    var memoria = navigator.deviceMemory || 0;
    var nucleos = navigator.hardwareConcurrency || 0;

    // Conexion: si el usuario pidio ahorro de datos o va con red lenta,
    // no le mandamos efectos caros.
    var conexion = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    var redLenta = false;
    var ahorroDatos = false;
    if (conexion) {
        ahorroDatos = conexion.saveData === true;
        redLenta = /(^|-)2g$/.test(conexion.effectiveType || '');
    }

    /* ------------------------------------------------------------------
       WebGL: se prueba de verdad creando un contexto, no por user agent
       ------------------------------------------------------------------ */
    function soporteWebGL() {
        try {
            var lienzo = document.createElement('canvas');
            var ctx = lienzo.getContext('webgl2');
            if (ctx) { return 2; }
            ctx = lienzo.getContext('webgl') || lienzo.getContext('experimental-webgl');
            return ctx ? 1 : 0;
        } catch (e) {
            return 0;
        }
    }

    var webgl = soporteWebGL();

    /* ------------------------------------------------------------------
       Veredicto
       ------------------------------------------------------------------ */
    var nivel;

    if (reduceMovimiento || ahorroDatos || redLenta || (memoria && memoria <= 2)) {
        // Equipo justo, red mala o el usuario pidio menos animacion.
        nivel = 'bajo';
    } else if (webgl >= 1 && (memoria === 0 || memoria >= 4) && (nucleos === 0 || nucleos >= 4)) {
        // Da el ancho para la capa WebGL.
        nivel = 'alto';
    } else {
        // Anda bien, pero sin WebGL o con menos musculo: solo efectos CSS.
        // Ojo: no tener WebGL NO baja a "bajo". Un equipo potente con WebGL
        // desactivado en el navegador igual mueve sin problema el canvas 2D
        // y los efectos de puntero.
        nivel = 'medio';
    }

    raiz.setAttribute('data-nivel', nivel);
    raiz.setAttribute('data-puntero', punteroGrueso ? 'grueso' : 'fino');

    // Queda disponible para el resto de los scripts.
    window.AL = window.AL || {};
    window.AL.capacidades = {
        nivel: nivel,
        webgl: webgl,
        punteroGrueso: punteroGrueso,
        reduceMovimiento: reduceMovimiento,
        memoria: memoria,
        nucleos: nucleos
    };
})();
