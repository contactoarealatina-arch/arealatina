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
# 3 procesos: alcanza de sobra para un estudio y entra en el plan chico.
# --preload comparte memoria entre ellos.
exec gunicorn config.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 60 \
    --preload \
    --access-logfile - \
    --error-logfile -
