#!/usr/bin/env bash
# Lo que corre Railway cada vez que levanta el servidor.
#
# Las migraciones van aca y no a mano porque despues nadie del estudio va
# a entrar por consola: si un despliegue trae una tabla nueva, tiene que
# quedar aplicada sola o el sitio se cae con "relation does not exist".
set -e

echo "==> Migraciones"
python manage.py migrate --noinput

echo "==> Tabla de cache (la usa el freno de intentos de login)"
python manage.py createcachetable

echo "==> Archivos estaticos"
python manage.py collectstatic --noinput

echo "==> Arriba"
# 2 procesos con 4 hilos cada uno, en vez de 3 procesos sueltos.
#
# Railway cobra por la memoria que se ocupa de verdad, y cada proceso
# de gunicorn se lleva su propia copia de Django (~120 MB). Los hilos
# la comparten. Asi atiende la misma cantidad de gente ocupando cerca
# de la mitad: son ~8 peticiones a la vez, de sobra para un estudio.
exec gunicorn config.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --timeout 60 \
    --preload \
    --access-logfile - \
    --error-logfile -
