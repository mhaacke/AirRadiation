"""Generate notebooks/analisis_inicial.ipynb and execute it against a run directory.

Usage: uv run python scripts/build_notebook.py runs/matrix_v1
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell


def build(run_dir: str) -> nbformat.NotebookNode:
    cells = [
        md(
            "# Análisis inicial: radiación cósmica galáctica en rutas australes (CARI-7)\n\n"
            "**Estudio de escenarios.** Trayectorias geodésicas sintéticas, perfiles y duraciones supuestos, "
            "condiciones promedio mensuales de CARI-7, sólo radiación cósmica galáctica (sin eventos solares). "
            "No reconstruye vuelos reales ni es una herramienta operacional. Las dosis no se convierten en "
            "riesgos individuales ni se extraen conclusiones clínicas.\n\n"
            "Todas las cifras de este notebook se leen de los archivos de la ejecución; ninguna está escrita a mano."
        ),
        code(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n\n"
            f"ROOT = Path({str(ROOT)!r})\nRUN = ROOT / {run_dir!r}\nREP = RUN / 'report'\n"
            "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)\n"
            "pd.set_option('display.float_format', lambda x: f'{x:,.4g}')\n"
            "manifest = json.loads((RUN / 'manifest.json').read_text())\n"
            "summary = pd.read_csv(REP / 'flights_summary.csv')\n"
            "comp = pd.read_csv(REP / 'comparisons.csv')\n"
            "try:\n    annual = pd.read_csv(REP / 'annual_calendars.csv')\n"
            "except pd.errors.EmptyDataError:  # estudio sin calendarios anuales\n    annual = pd.DataFrame()\n"
            "checks = pd.read_csv(REP / 'validation_checks.csv')\n"
            "validation = json.loads((REP / 'validation_summary.json').read_text())"
        ),
        md("## 1. Procedencia de la ejecución"),
        code(
            "eng = manifest['engine']\n"
            "print('run_id        :', manifest['run_id'], '| estado:', manifest['status'])\n"
            "print('motor         :', eng['engine'], eng['executable'], '| banner:', eng['embedded_banner'])\n"
            "print('sha256 binario:', eng['executable_sha256'], '|', eng['executable_arch'])\n"
            "print('runner        :', eng['runner'], eng['docker_image'], eng['docker_platform'])\n"
            "print('MV-DATES.L99  :', eng['data_files']['SOLARMOD/MV-DATES.L99'])\n"
            "print('paquete CARI  :', (manifest['cari_install_provenance'] or {}).get('package_sha256'))\n"
            "print('código        :', manifest['git'])\n"
            "print('config sha256 :', manifest['config_sha256'])\n"
            "for a in manifest['assumptions']: print('-', a)"
        ),
        md(
            "## 2. Fechas y modulación solar\n\n"
            "El potencial heliocéntrico es el dato de modulación que CARI-7 usa. No se presupone el sentido "
            "del efecto: lo determina el modelo."
        ),
        code(
            "pd.DataFrame([{**{'fecha': k}, **{x: v[x] for x in ('label', 'justification')}} "
            "for k, v in manifest['config']['dates'].items()])\n"
        ),
        code(
            "summary.groupby('date')['heliocentric_potential_MV'].first()"
        ),
        md("## 3. Dosis por tramo: matriz principal (dosis efectiva ICRP 103, µSv)"),
        code(
            "main = summary[summary.blocks.str.contains('principal')]\n"
            "main.pivot_table(index=['route', 'direction'], columns=['date', 'profile'], values='total_dose').round(1)"
        ),
        md("Tasa media temporal, tasa máxima y dosis por hora de vuelo (µSv/h). La dosis por hora es la dosis de CARI dividida por el tiempo en el aire; la tasa media es el promedio temporal de las tasas locales; deben coincidir."),
        code(
            "cols = ['route', 'direction', 'profile', 'date', 'airborne_h', 'total_dose', 'dose_per_flight_hour',\n"
            "        'mean_rate', 'cruise_mean_rate', 'max_rate', 'max_rate_lat', 'southernmost_lat']\n"
            "main[cols].sort_values(['route', 'direction', 'date', 'profile'])"
        ),
        md("## 4. Diferencias entre escenarios\n\nDiferencias absolutas (µSv) y porcentuales, siempre dentro de una misma magnitud. Son variaciones entre escenarios definidos por el usuario, no incertidumbre del modelo."),
        code(
            "for k, g in comp.groupby('comparison'):\n"
            "    print(f'\\n=== {k} ===')\n"
            "    print(g.groupby('value')[['diff_abs', 'diff_pct', 'dose_per_h_diff_pct']].describe().round(2)"
            "[[('diff_abs', 'min'), ('diff_abs', 'max'), ('diff_pct', 'min'), ('diff_pct', 'max'), "
            "('dose_per_h_diff_pct', 'min'), ('dose_per_h_diff_pct', 'max')]].to_string())"
        ),
        md("### Sensibilidad a la duración (supuesto ilustrativo de asimetría por viento)"),
        code(
            "comp[comp.varied == 'duration'][['route', 'direction', 'date', 'airborne_min_ref', 'airborne_min', "
            "'dose_ref', 'dose', 'diff_pct', 'dose_per_h_diff_pct']]"
        ),
        md("## 5. Magnitudes distintas para el mismo vuelo\n\nDosis efectiva, H*(10) y dosis absorbida **no son intercambiables**. Se muestran lado a lado; el cociente H*(10)/E es solo descriptivo."),
        code("pd.read_csv(REP / 'quantities_same_flight.csv')"),
        md("## 6. Validación"),
        code(
            "print(json.dumps({k: v for k, v in validation.items() if k != 'convergence'}, indent=1))\n"
            "pd.DataFrame(validation['convergence'])"
        ),
        code("checks.describe().T[['min', 'max']]"),
        md("## 7. Exposición anual con calendarios hipotéticos\n\n"
           "**Aproximación:** repite la dosis de un tramo representativo (media de ambos sentidos o, en las rotaciones, la dosis de cada sentido). No simula las "
           "condiciones de cada vuelo del año. Un tramo es un vuelo de ida o de vuelta. No se afirma que estos "
           "calendarios cumplan límites laborales u operacionales."),
        code(
            "if annual.empty:\n    print(manifest['config']['annual']['note'])\n"
            "else:\n    display(annual[['calendar', 'date', 'legs_per_month', 'legs_total', 'rotations_equivalent', "
            "'annual_hours', 'annual_dose_mSv']])\n"
            "    for f in ['acumulacion_anual', 'exposicion_anual']:\n"
            "        display(Image(filename=str(REP / 'figures' / f'{f}.png'), width=900))"
        ),
        md("## 8. Figuras"),
        code(
            "for p in sorted(p for p in (REP / 'figures').glob('*.png') if 'anual' not in p.stem):  # anuales: sección 7\n"
            "    print(p.name)\n"
            "    display(Image(filename=str(p), width=900))"
        ),
        md(
            "## 9. Limitaciones\n\n"
            "- Geodésicas sintéticas: las rutas reales dependen de vientos, ETOPS y ATC.\n"
            "- Promedio mensual: no incluye decrecimientos Forbush ni tormentas geomagnéticas concretas.\n"
            "- CARI-7 usa la rejilla de rigidez de corte IGRF2010 para fechas posteriores a 2010.\n"
            "- Sin SPE/GLE. Sin blindaje del fuselaje.\n"
            "- La incertidumbre global que declara CARI (~30 % a altitudes comerciales, `HELP.TXT`) no es un "
            "intervalo de confianza por escenario. Este análisis no calcula intervalos de confianza."
        ),
    ]
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


def main() -> None:
    run_dir = sys.argv[1] if len(sys.argv) > 1 else "runs/matrix_v1"
    nb = build(run_dir)
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    out = ROOT / "notebooks" / "analisis_inicial.ipynb"
    out.parent.mkdir(exist_ok=True)
    nbformat.write(nb, out)
    print(f"Notebook ejecutado: {out}")


if __name__ == "__main__":
    main()
