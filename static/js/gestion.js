/**
 * Área Latina Estudio — comportamiento del panel de gestión.
 *
 * Todo es progresivo: si el JS no carga, los formularios siguen enviándose
 * y las tablas siguen mostrando sus datos. Nada depende de JS para funcionar.
 */
(function () {
    'use strict';

    window.AL = window.AL || {};

    /* ==================================================================
       Utilidades
       ================================================================== */

    /** Quita tildes y pasa a minúsculas, para buscar sin preocuparse. */
    function normalizar(texto) {
        return (texto || '')
            .toString()
            .toLowerCase()
            .normalize('NFD')
            .replace(/[̀-ͯ]/g, '');
    }

    /** 25000 -> "25.000" */
    function formatoCLP(valor) {
        var n = parseInt(valor, 10);
        if (isNaN(n)) { return ''; }
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    window.AL.normalizar = normalizar;
    window.AL.formatoCLP = formatoCLP;

    /* ==================================================================
       Sidebar en móvil
       ================================================================== */
    function sidebar() {
        var barra = document.getElementById('sidebar');
        var fondo = document.getElementById('sidebarFondo');
        var boton = document.getElementById('abrirMenu');
        if (!barra || !boton) { return; }

        function alternar(abrir) {
            barra.classList.toggle('abierto', abrir);
            if (fondo) { fondo.classList.toggle('visible', abrir); }
        }

        boton.addEventListener('click', function () {
            alternar(!barra.classList.contains('abierto'));
        });

        if (fondo) {
            fondo.addEventListener('click', function () { alternar(false); });
        }

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') { alternar(false); }
        });
    }

    /* ==================================================================
       Toasts
       ================================================================== */
    function toasts() {
        if (!window.bootstrap) { return; }
        document.querySelectorAll('.toast').forEach(function (el) {
            new bootstrap.Toast(el).show();
        });
    }

    /**
     * Muestra un toast desde JS (por ejemplo tras una acción con fetch).
     */
    window.AL.toast = function (mensaje, tipo) {
        var cont = document.getElementById('toasts');
        if (!cont || !window.bootstrap) { return; }
        var el = document.createElement('div');
        el.className = 'toast align-items-center g-toast g-toast-' + (tipo || 'info');
        el.setAttribute('role', 'alert');
        el.innerHTML = '<div class="d-flex"><div class="toast-body"></div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" ' +
            'data-bs-dismiss="toast" aria-label="Cerrar"></button></div>';
        el.querySelector('.toast-body').textContent = mensaje;
        cont.appendChild(el);
        new bootstrap.Toast(el, { delay: 5000 }).show();
        el.addEventListener('hidden.bs.toast', function () { el.remove(); });
    };

    /* ==================================================================
       Buscador en vivo sobre una tabla
       Uso: <input data-buscar="#idTabla">
       ================================================================== */
    function buscadorVivo() {
        document.querySelectorAll('[data-buscar]').forEach(function (input) {
            var tabla = document.querySelector(input.getAttribute('data-buscar'));
            if (!tabla) { return; }
            var cuerpo = tabla.tBodies[0];
            if (!cuerpo) { return; }
            var contador = document.querySelector(input.getAttribute('data-contador') || '');

            function filtrar() {
                var aguja = normalizar(input.value.trim());
                var visibles = 0;

                Array.prototype.forEach.call(cuerpo.rows, function (fila) {
                    if (fila.hasAttribute('data-sin-filtro')) { return; }
                    var texto = normalizar(fila.getAttribute('data-buscable') || fila.textContent);
                    var coincide = !aguja || texto.indexOf(aguja) !== -1;
                    fila.hidden = !coincide;
                    if (coincide) { visibles++; }
                });

                if (contador) { contador.textContent = visibles; }

                var vacio = tabla.parentElement.querySelector('[data-sin-resultados]');
                if (vacio) { vacio.hidden = visibles > 0; }
            }

            input.addEventListener('input', filtrar);
            filtrar();
        });
    }

    /* ==================================================================
       Ordenar tablas al hacer clic en el encabezado
       Uso: <th class="ordenable" data-tipo="texto|numero|fecha">
       ================================================================== */
    function tablasOrdenables() {
        document.querySelectorAll('table[data-ordenable]').forEach(function (tabla) {
            var cuerpo = tabla.tBodies[0];
            if (!cuerpo) { return; }

            tabla.querySelectorAll('th.ordenable').forEach(function (th, indice) {
                // El índice real de la columna, no el de los th ordenables.
                var columna = Array.prototype.indexOf.call(th.parentNode.children, th);

                th.insertAdjacentHTML('beforeend', ' <span class="flecha">▲</span>');

                th.addEventListener('click', function () {
                    var asc = !th.classList.contains('asc');

                    tabla.querySelectorAll('th.ordenable').forEach(function (otro) {
                        otro.classList.remove('asc', 'desc');
                        var f = otro.querySelector('.flecha');
                        if (f) { f.textContent = '▲'; }
                    });

                    th.classList.add(asc ? 'asc' : 'desc');
                    th.querySelector('.flecha').textContent = asc ? '▲' : '▼';

                    var tipo = th.getAttribute('data-tipo') || 'texto';
                    var filas = Array.prototype.slice.call(cuerpo.rows)
                        .filter(function (f) { return !f.hasAttribute('data-sin-filtro'); });

                    filas.sort(function (a, b) {
                        var ca = a.cells[columna];
                        var cb = b.cells[columna];
                        if (!ca || !cb) { return 0; }

                        // data-orden permite ordenar por un valor distinto al
                        // que se muestra (fecha ISO, monto sin puntos, etc.).
                        var va = ca.getAttribute('data-orden');
                        var vb = cb.getAttribute('data-orden');
                        if (va === null) { va = ca.textContent.trim(); }
                        if (vb === null) { vb = cb.textContent.trim(); }

                        if (tipo === 'numero') {
                            var na = parseFloat(String(va).replace(/[^\d.-]/g, '')) || 0;
                            var nb = parseFloat(String(vb).replace(/[^\d.-]/g, '')) || 0;
                            return asc ? na - nb : nb - na;
                        }
                        return asc
                            ? String(va).localeCompare(String(vb), 'es', { numeric: true })
                            : String(vb).localeCompare(String(va), 'es', { numeric: true });
                    });

                    filas.forEach(function (f) { cuerpo.appendChild(f); });
                });
            });
        });
    }

    /* ==================================================================
       RUT chileno: formato y validación de dígito verificador
       ================================================================== */

    /** Calcula el dígito verificador con el algoritmo módulo 11. */
    function digitoVerificador(cuerpo) {
        var suma = 0;
        var multiplo = 2;
        for (var i = cuerpo.length - 1; i >= 0; i--) {
            suma += parseInt(cuerpo.charAt(i), 10) * multiplo;
            multiplo = multiplo === 7 ? 2 : multiplo + 1;
        }
        var resto = 11 - (suma % 11);
        if (resto === 11) { return '0'; }
        if (resto === 10) { return 'K'; }
        return String(resto);
    }

    function limpiarRut(valor) {
        return (valor || '').toString().toUpperCase().replace(/[^0-9K]/g, '');
    }

    /** 123456789 -> "12.345.678-9" */
    function formatearRut(valor) {
        var limpio = limpiarRut(valor);
        if (limpio.length < 2) { return limpio; }
        var cuerpo = limpio.slice(0, -1);
        var dv = limpio.slice(-1);
        return cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + '-' + dv;
    }

    function rutValido(valor) {
        var limpio = limpiarRut(valor);
        if (limpio.length < 8) { return false; }
        var cuerpo = limpio.slice(0, -1);
        var dv = limpio.slice(-1);
        if (!/^\d+$/.test(cuerpo)) { return false; }
        return digitoVerificador(cuerpo) === dv;
    }

    window.AL.rut = { formatear: formatearRut, valido: rutValido, limpiar: limpiarRut };

    function camposRut() {
        document.querySelectorAll('[data-rut]').forEach(function (input) {
            var aviso = document.querySelector(input.getAttribute('data-aviso') || '');

            function revisar(mostrarError) {
                var valor = input.value.trim();
                input.classList.remove('valido', 'invalido');
                if (aviso) { aviso.textContent = ''; }
                if (!valor) { return true; }

                if (rutValido(valor)) {
                    input.classList.add('valido');
                    input.setCustomValidity('');
                    return true;
                }

                input.setCustomValidity('RUT inválido');
                if (mostrarError) {
                    input.classList.add('invalido');
                    if (aviso) {
                        aviso.textContent = 'El RUT no es válido. Revisa el dígito verificador.';
                    }
                }
                return false;
            }

            input.addEventListener('input', function () {
                var cursorAlFinal = input.selectionStart === input.value.length;
                input.value = formatearRut(input.value);
                if (cursorAlFinal) {
                    input.setSelectionRange(input.value.length, input.value.length);
                }
                // Mientras escribe no se le grita: solo al salir del campo.
                revisar(false);
            });

            input.addEventListener('blur', function () { revisar(true); });
            input.form && input.form.addEventListener('submit', function () { revisar(true); });
        });
    }

    /* ==================================================================
       Teléfono chileno: +56 9 XXXX XXXX
       ================================================================== */
    function camposTelefono() {
        document.querySelectorAll('[data-telefono]').forEach(function (input) {
            input.addEventListener('input', function () {
                var digitos = input.value.replace(/\D/g, '');

                // Se normaliza a formato nacional: 56 + 9 dígitos.
                if (digitos.indexOf('56') === 0) { digitos = digitos.slice(2); }
                digitos = digitos.slice(0, 9);

                var salida = '+56';
                if (digitos.length > 0) { salida += ' ' + digitos.slice(0, 1); }
                if (digitos.length > 1) { salida += ' ' + digitos.slice(1, 5); }
                if (digitos.length > 5) { salida += ' ' + digitos.slice(5, 9); }

                input.value = digitos.length ? salida : '';
            });
        });
    }

    /* ==================================================================
       Vista previa de la foto antes de subirla
       ================================================================== */
    function previewFoto() {
        document.querySelectorAll('[data-preview]').forEach(function (input) {
            var destino = document.querySelector(input.getAttribute('data-preview'));
            if (!destino) { return; }

            input.addEventListener('change', function () {
                var archivo = input.files && input.files[0];
                if (!archivo) { return; }

                if (!/^image\//.test(archivo.type)) {
                    window.AL.toast('Ese archivo no es una imagen.', 'error');
                    input.value = '';
                    return;
                }

                var lector = new FileReader();
                lector.onload = function (e) {
                    // Si el destino es un div, se reemplaza por un <img>.
                    if (destino.tagName === 'IMG') {
                        destino.src = e.target.result;
                    } else {
                        var img = document.createElement('img');
                        img.className = destino.className;
                        img.src = e.target.result;
                        img.alt = 'Vista previa';
                        destino.replaceWith(img);
                        destino = img;
                    }
                };
                lector.readAsDataURL(archivo);
            });
        });
    }

    /* ==================================================================
       Tarjetas de opción (checkbox / radio) que se marcan visualmente
       ================================================================== */
    function opcionesVisuales() {
        function sincronizar(contenedor) {
            contenedor.querySelectorAll('.g-opcion, .g-dia').forEach(function (etiqueta) {
                var control = etiqueta.querySelector('input');
                if (!control) { return; }
                var clase = etiqueta.classList.contains('g-dia') ? 'marcado' : 'marcada';
                etiqueta.classList.toggle(clase, control.checked);
            });
        }

        document.querySelectorAll('[data-opciones]').forEach(function (contenedor) {
            sincronizar(contenedor);
            contenedor.addEventListener('change', function () { sincronizar(contenedor); });
        });
    }

    /* ==================================================================
       Formulario por pasos
       ================================================================== */
    function formularioPasos() {
        var form = document.querySelector('[data-pasos]');
        if (!form) { return; }

        var paneles = Array.prototype.slice.call(form.querySelectorAll('.g-panel-paso'));
        var indicadores = Array.prototype.slice.call(document.querySelectorAll('.g-paso'));
        var btnAtras = form.querySelector('[data-paso-atras]');
        var btnSiguiente = form.querySelector('[data-paso-siguiente]');
        var btnEnviar = form.querySelector('[data-paso-enviar]');
        var actual = 0;

        function pintar() {
            paneles.forEach(function (p, i) { p.classList.toggle('visible', i === actual); });

            indicadores.forEach(function (ind, i) {
                ind.classList.toggle('activo', i === actual);
                ind.classList.toggle('completo', i < actual);
            });

            if (btnAtras) { btnAtras.hidden = actual === 0; }
            if (btnSiguiente) { btnSiguiente.hidden = actual === paneles.length - 1; }
            if (btnEnviar) { btnEnviar.hidden = actual !== paneles.length - 1; }

            if (actual === paneles.length - 1) { construirResumen(); }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        /** Valida solo los campos del paso visible, no los de más adelante. */
        function pasoValido() {
            var panel = paneles[actual];
            var campos = panel.querySelectorAll('input, select, textarea');
            var ok = true;

            Array.prototype.forEach.call(campos, function (campo) {
                if (campo.disabled || campo.type === 'hidden') { return; }
                if (!campo.checkValidity()) {
                    if (ok) { campo.reportValidity(); }
                    campo.classList.add('invalido');
                    ok = false;
                } else {
                    campo.classList.remove('invalido');
                }
            });

            return ok;
        }

        /** Arma el resumen del último paso leyendo el propio formulario. */
        function construirResumen() {
            var destino = form.querySelector('[data-resumen]');
            if (!destino) { return; }

            var lineas = [];
            paneles.slice(0, -1).forEach(function (panel) {
                panel.querySelectorAll('[data-resumen-campo]').forEach(function (campo) {
                    var etiqueta = campo.getAttribute('data-resumen-campo');
                    var valor = '';

                    if (campo.type === 'checkbox') {
                        valor = campo.checked ? 'Sí' : 'No';
                    } else if (campo.tagName === 'SELECT') {
                        valor = campo.options[campo.selectedIndex]
                            ? campo.options[campo.selectedIndex].text : '';
                    } else {
                        valor = campo.value;
                    }

                    if (valor) { lineas.push([etiqueta, valor]); }
                });

                // Clases marcadas
                var clases = panel.querySelectorAll('input[name="clases"]:checked');
                if (clases.length) {
                    lineas.push(['Clases', Array.prototype.map.call(clases, function (c) {
                        return c.getAttribute('data-nombre') || c.value;
                    }).join(', ')]);
                }

                var plan = panel.querySelector('input[name="plan"]:checked');
                if (plan) {
                    lineas.push(['Plan', plan.getAttribute('data-nombre') || plan.value]);
                }
            });

            destino.innerHTML = lineas.map(function (par) {
                return '<div class="g-dato"><span class="g-dato-etiqueta">' + par[0] +
                       '</span><span class="g-dato-valor">' + par[1] + '</span></div>';
            }).join('');
        }

        if (btnSiguiente) {
            btnSiguiente.addEventListener('click', function () {
                if (!pasoValido()) { return; }
                actual = Math.min(actual + 1, paneles.length - 1);
                pintar();
            });
        }

        if (btnAtras) {
            btnAtras.addEventListener('click', function () {
                actual = Math.max(actual - 1, 0);
                pintar();
            });
        }

        // Enter no debe saltar al submit desde el paso 1.
        form.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA' &&
                actual < paneles.length - 1) {
                e.preventDefault();
                if (btnSiguiente) { btnSiguiente.click(); }
            }
        });

        pintar();
    }

    /* ==================================================================
       Vencimiento calculado en vivo al elegir plan y fecha
       ================================================================== */
    function vencimientoEnVivo() {
        var contenedor = document.querySelector('[data-vencimiento]');
        if (!contenedor) { return; }

        var inicio = document.querySelector('[name="fecha_inicio"]');
        var salida = document.querySelector('[data-vencimiento-salida]');
        if (!inicio || !salida) { return; }

        function recalcular() {
            var plan = document.querySelector('input[name="plan"]:checked');
            if (!plan || !inicio.value) {
                salida.textContent = 'Elige un plan y una fecha de inicio';
                return;
            }

            var dias = parseInt(plan.getAttribute('data-duracion'), 10) || 30;
            var fecha = new Date(inicio.value + 'T00:00:00');
            fecha.setDate(fecha.getDate() + dias);

            salida.textContent = fecha.toLocaleDateString('es-CL', {
                day: '2-digit', month: 'long', year: 'numeric'
            }) + ' (' + dias + ' días)';
        }

        document.addEventListener('change', function (e) {
            if (e.target.name === 'plan' || e.target === inicio) { recalcular(); }
        });

        recalcular();
    }

    /* ==================================================================
       Mostrar u ocultar un bloque según una casilla
       Uso: <input type="checkbox" data-muestra="#bloque">
       ================================================================== */
    function bloquesCondicionales() {
        document.querySelectorAll('[data-muestra]').forEach(function (control) {
            var destino = document.querySelector(control.getAttribute('data-muestra'));
            if (!destino) { return; }

            function sincronizar() {
                var mostrar = control.type === 'checkbox' ? control.checked : !!control.value;
                destino.hidden = !mostrar;
            }

            control.addEventListener('change', sincronizar);
            sincronizar();
        });
    }

    /* ==================================================================
       Confirmación antes de acciones destructivas
       ================================================================== */
    function confirmaciones() {
        document.querySelectorAll('[data-confirmar]').forEach(function (el) {
            el.addEventListener('submit', function (e) {
                if (!window.confirm(el.getAttribute('data-confirmar'))) {
                    e.preventDefault();
                }
            });
        });
    }

    /* ==================================================================
       Envío automático de filtros al cambiar un select
       ================================================================== */
    function filtrosAuto() {
        document.querySelectorAll('[data-filtro-auto]').forEach(function (select) {
            select.addEventListener('change', function () {
                if (select.form) { select.form.submit(); }
            });
        });
    }

    /* ================================================================== */
    function iniciar() {
        sidebar();
        toasts();
        buscadorVivo();
        tablasOrdenables();
        camposRut();
        camposTelefono();
        previewFoto();
        opcionesVisuales();
        formularioPasos();
        vencimientoEnVivo();
        bloquesCondicionales();
        confirmaciones();
        filtrosAuto();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
