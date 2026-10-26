# CARI-7 (no incluido)

Este directorio recibe la instalación local de CARI-7 de la FAA. Los binarios y datos **no se
redistribuyen** en este repositorio: el paquete no declara una licencia de redistribución para
ellos (ver `docs/cari7_verificacion.md` §7).

Instalación:

```bash
uv run python scripts/install_cari7.py            # descarga de la FAA + verificación SHA-256
uv run airrad check                               # ejecuta el ejemplo oficial y lo compara
```

El instalador deja aquí `CARI_7_DVD/` e `INSTALL_PROVENANCE.json`, ambos ignorados por git.
