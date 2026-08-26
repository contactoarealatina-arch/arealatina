/**
 * Area Latina Estudio - fondo WebGL del hero.
 *
 * Shader propio, sin librerias externas (~6 KB en vez de los ~170 KB que
 * pesaria Three.js). Solo se carga cuando capacidades.js marca nivel "alto".
 *
 * Se apaga solo cuando la pestana esta oculta o el hero sale de pantalla,
 * asi no gasta bateria de fondo.
 */
(function () {
    'use strict';

    var VERTEX = [
        'attribute vec2 a_pos;',
        'void main() {',
        '    gl_Position = vec4(a_pos, 0.0, 1.0);',
        '}'
    ].join('\n');

    var FRAGMENT = [
        'precision mediump float;',
        '',
        'uniform vec2  u_res;',
        'uniform float u_time;',
        'uniform vec2  u_mouse;',
        'uniform float u_activo;',
        '',
        'float hash(vec2 p) {',
        '    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);',
        '}',
        '',
        'float ruido(vec2 p) {',
        '    vec2 i = floor(p);',
        '    vec2 f = fract(p);',
        '    vec2 u = f * f * (3.0 - 2.0 * f);',
        '    float a = hash(i);',
        '    float b = hash(i + vec2(1.0, 0.0));',
        '    float c = hash(i + vec2(0.0, 1.0));',
        '    float d = hash(i + vec2(1.0, 1.0));',
        '    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);',
        '}',
        '',
        'float fbm(vec2 p) {',
        '    float v = 0.0;',
        '    float amp = 0.5;',
        '    for (int i = 0; i < 5; i++) {',
        '        v += amp * ruido(p);',
        '        p *= 2.02;',
        '        amp *= 0.5;',
        '    }',
        '    return v;',
        '}',
        '',
        'void main() {',
        '    float lado = min(u_res.x, u_res.y);',
        '    vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / lado;',
        '    float t = u_time * 0.06;',
        '',
        '    vec2 q = vec2(fbm(p * 1.6 + vec2(t, -t)),',
        '                  fbm(p * 1.6 + vec2(-t, t) + 5.2));',
        '    float f = fbm(p * 2.2 + q * 1.4 + t * 0.5);',
        '',
        '    vec3 col = vec3(0.051, 0.051, 0.051);',
        '    vec3 naranja  = vec3(1.0, 0.341, 0.133);',
        '    vec3 naranjaC = vec3(1.0, 0.541, 0.396);',
        '',
        '    float brillo = smoothstep(0.45, 0.95, f);',
        '    col = mix(col, naranja * 0.55, brillo * 0.55);',
        '    col += naranjaC * pow(brillo, 3.0) * 0.35;',
        '',
        '    vec2 m = (u_mouse * u_res - 0.5 * u_res) / lado;',
        '    float d = length(p - m);',
        '    col += naranja * exp(-d * 2.6) * u_activo * 0.5;',
        '    col += naranjaC * exp(-d * 7.0) * u_activo * 0.35;',
        '',
        '    float vin = smoothstep(1.25, 0.25, length(p));',
        '    col *= mix(0.45, 1.0, vin);',
        '',
        '    col += (hash(gl_FragCoord.xy + u_time) - 0.5) * 0.025;',
        '',
        '    gl_FragColor = vec4(col, 1.0);',
        '}'
    ].join('\n');

    function compilar(gl, tipo, fuente) {
        var sh = gl.createShader(tipo);
        gl.shaderSource(sh, fuente);
        gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
            gl.deleteShader(sh);
            return null;
        }
        return sh;
    }

    function iniciar() {
        var canvas = document.getElementById('hero-webgl');
        if (!canvas) { return; }

        var gl = canvas.getContext('webgl', { antialias: false, alpha: false, depth: false })
              || canvas.getContext('experimental-webgl');
        if (!gl) { return; }

        var vs = compilar(gl, gl.VERTEX_SHADER, VERTEX);
        var fs = compilar(gl, gl.FRAGMENT_SHADER, FRAGMENT);
        if (!vs || !fs) { return; }

        var prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { return; }
        gl.useProgram(prog);

        // Un solo triangulo que cubre toda la pantalla.
        var buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        var loc = gl.getAttribLocation(prog, 'a_pos');
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

        var uRes    = gl.getUniformLocation(prog, 'u_res');
        var uTime   = gl.getUniformLocation(prog, 'u_time');
        var uMouse  = gl.getUniformLocation(prog, 'u_mouse');
        var uActivo = gl.getUniformLocation(prog, 'u_activo');

        /* -------------------------------------------------------------- */
        var raton = { x: 0.5, y: 0.55 };
        var suave = { x: 0.5, y: 0.55 };
        var activo = 0;
        var objetivoActivo = 0;
        var tactil = document.documentElement.getAttribute('data-puntero') === 'grueso';

        var contenedor = canvas.parentElement || document.body;

        function dimensionar() {
            // Tope de densidad en 1.5: mas que eso no se nota y cuesta caro.
            var dpr = Math.min(window.devicePixelRatio || 1, 1.5);

            // Se mide el CONTENEDOR, nunca el propio canvas: asignar
            // canvas.width cambia su tamano intrinseco, asi que medirse a si
            // mismo se realimenta y el buffer crece sin control si el CSS no
            // llega a aplicar.
            var anCss = contenedor.clientWidth || window.innerWidth || 1;
            var alCss = contenedor.clientHeight || window.innerHeight || 1;

            // Tope duro por si acaso: 4096 es el maximo seguro en GPU modestas.
            var an = Math.max(1, Math.min(Math.round(anCss * dpr), 4096));
            var al = Math.max(1, Math.min(Math.round(alCss * dpr), 4096));

            if (canvas.width !== an || canvas.height !== al) {
                canvas.width = an;
                canvas.height = al;
                gl.viewport(0, 0, an, al);
            }
        }

        window.addEventListener('pointermove', function (e) {
            raton.x = e.clientX / window.innerWidth;
            raton.y = 1 - (e.clientY / window.innerHeight);
            objetivoActivo = 1;
        }, { passive: true });

        window.addEventListener('pointerleave', function () {
            objetivoActivo = tactil ? 0.45 : 0;
        }, { passive: true });

        /* -------------------------------------------------------------- */
        var corriendo = true;
        var visible = true;
        var inicio = performance.now();

        document.addEventListener('visibilitychange', function () {
            corriendo = !document.hidden;
            if (corriendo && visible) { requestAnimationFrame(dibujar); }
        });

        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entradas) {
                visible = entradas[0].isIntersecting;
                if (visible && corriendo) { requestAnimationFrame(dibujar); }
            }, { threshold: 0 }).observe(canvas);
        }

        canvas.addEventListener('webglcontextlost', function (e) {
            e.preventDefault();
            corriendo = false;
        });

        function dibujar(ahora) {
            if (!corriendo || !visible) { return; }
            dimensionar();

            // En tactil no hay cursor: la luz orbita sola, muy lento.
            if (tactil) {
                var giro = (ahora - inicio) * 0.00012;
                raton.x = 0.5 + Math.cos(giro) * 0.22;
                raton.y = 0.55 + Math.sin(giro * 0.8) * 0.15;
                objetivoActivo = 0.45;
            }

            suave.x += (raton.x - suave.x) * 0.06;
            suave.y += (raton.y - suave.y) * 0.06;
            activo += (objetivoActivo - activo) * 0.04;

            gl.uniform2f(uRes, canvas.width, canvas.height);
            gl.uniform1f(uTime, (ahora - inicio) * 0.001);
            gl.uniform2f(uMouse, suave.x, suave.y);
            gl.uniform1f(uActivo, activo);
            gl.drawArrays(gl.TRIANGLES, 0, 3);

            requestAnimationFrame(dibujar);
        }

        document.documentElement.setAttribute('data-webgl', 'activo');
        requestAnimationFrame(dibujar);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
