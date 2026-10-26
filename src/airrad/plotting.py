"""Figures. Every figure states route, date, profile and the synthetic nature of the data."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import cartopy.crs as ccrs  # noqa: E402
import cartopy.feature as cfeature  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402

from .dosimetry import cumulative_series  # noqa: E402
from .trajectory import SYNTHETIC_LABEL, VIA_LABEL  # noqa: E402

# Validated categorical order (dataviz reference palette, light mode).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# Fixed orders: an entity keeps its colour across figures and studies (new entries are appended).
ROUTE_ORDER = ["SCL-MEL", "SCL-SYD", "SCL-AKL", "SCL-PUQ", "SCL-SYD-FR24"]
PROFILE_ORDER = ["FL330", "FL370", "FL410", "STEP330-390", "FL390"]
DATE_STYLES = [("-", "continua"), ((0, (4, 2)), "discontinua"), ((0, (1, 1.5)), "punteada")]
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
ENGINE_NOTE = "CARI-7 (FAA), sólo radiación cósmica galáctica, promedio mensual"
DATA_NOTES: list[str] = []  # extra trajectory labels (e.g. routes via waypoints), set by the report
PROJ = ccrs.LambertAzimuthalEqualArea(central_longitude=-145, central_latitude=-50)  # trans-Pacific view

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 2.0,
        "font.size": 9,
        "legend.frameon": False,
        "savefig.dpi": 150,
    }
)


def route_color(route: str) -> str:
    return SERIES[ROUTE_ORDER.index(route)] if route in ROUTE_ORDER else SERIES[-1]


def profile_color(profile: str) -> str:
    return SERIES[PROFILE_ORDER.index(profile)] if profile in PROFILE_ORDER else SERIES[-1]


def date_style(date: str, dates) -> tuple:
    """(matplotlib linestyle, Spanish name) by position of `date` in the sorted study dates."""
    return DATE_STYLES[sorted(dates).index(date) % len(DATE_STYLES)]


def route_direction(summary, route, direction=None):
    """Direction shown for a route: the given one, else the one with most scenarios (ties -> outbound)."""
    if direction:
        return direction
    n = summary[summary.route == route].direction.value_counts()
    return max(["outbound", "inbound"], key=lambda d: n.get(d, 0))


def _dir_mask(summary, direction=None) -> pd.Series:
    """Rows in the direction shown for their route (see route_direction)."""
    dirs = {rt: route_direction(summary, rt, direction) for rt in summary.route.unique()}
    return summary.direction == summary.route.map(dirs)


def _dir_label(direction) -> str:
    return "salida SCL" if direction == "outbound" else "llegada a SCL"


def _present(order, values) -> list:
    values = set(values)
    return [v for v in order if v in values] + sorted(values - set(order))


def _footer(fig, extra: str = "") -> None:
    txt = " ".join([f"Datos: {SYNTHETIC_LABEL}.", *DATA_NOTES, f"Motor: {ENGINE_NOTE}."] + ([extra] if extra else []))
    # Below the figure area (bbox_inches="tight" grows the canvas): never overlaps colorbars or axes.
    fig.text(0.01, -0.01, txt, fontsize=6.5, color=INK2, ha="left", va="top", wrap=True)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _projection(lons, lats):
    """Trans-Pacific view (PROJ) for tracks spanning > 60° of longitude; otherwise centred on the tracks."""
    lon, lat = np.radians(np.asarray(lons, dtype=float)), np.asarray(lats, dtype=float)
    clon = float(np.degrees(np.arctan2(np.sin(lon).mean(), np.cos(lon).mean())))
    spread = np.ptp((np.degrees(lon) - clon + 180.0) % 360.0 - 180.0)
    if spread > 60:
        return PROJ, True
    return ccrs.LambertAzimuthalEqualArea(central_longitude=clon, central_latitude=float(lat.mean())), False


def _map_axes(ax, proj, wide, lats, lons):
    # Coastline only: filling Natural Earth land fails in this projection once the
    # pole-containing Antarctic polygon is in view (cartopy/shapely clipping).
    coast = cfeature.COASTLINE if wide else cfeature.COASTLINE.with_scale("50m")
    ax.add_feature(coast, linewidth=0.5, edgecolor=MUTED)
    step = 30 if wide else 10
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color=GRID, xlocs=range(-180, 181, step),
                      ylocs=range(-80, 1, step // 3 if wide else 5), y_inline=wide, x_inline=False)  # fmt: skip
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = {"size": 6.5, "color": INK2}
    gl.ylabel_style = {"size": 6.5, "color": INK2}
    lons, lats = np.asarray(lons, dtype=float), np.asarray(lats, dtype=float)
    if wide:  # fixed context: 25°S to the Antarctic coast at the projection centre
        lons = np.concatenate([lons, [-145.0, -145.0]])
        lats = np.concatenate([lats, [-25.0, -76.0]])
    xy = proj.transform_points(ccrs.PlateCarree(), lons, lats)
    (x0, y0), (x1, y1) = xy[:, :2].min(axis=0), xy[:, :2].max(axis=0)
    pad = 4e5
    if not wide:  # keep some coastline context beside a short, mostly meridional track
        half = max((x1 - x0) / 2, 0.35 * (y1 - y0))
        x0, x1 = (x0 + x1) / 2 - half, (x0 + x1) / 2 + half
        pad = 2e5
    ax.set_xlim(x0 - pad, x1 + pad)
    ax.set_ylim(y0 - pad, y1 + pad)


def _projected_segments(proj, lon, lat):
    # Points are projected individually (no ±180° seam in an azimuthal projection),
    # so consecutive points never produce a line across the whole map.
    xy = proj.transform_points(ccrs.PlateCarree(), np.asarray(lon), np.asarray(lat))[:, :2]
    return np.stack([xy[:-1], xy[1:]], axis=1)


def map_routes(traj: pd.DataFrame, summary: pd.DataFrame, out: Path, profile="FL370", duration="gs470", date="2020-02",
               direction=None):  # fmt: skip
    s = summary[(summary.profile == profile) & (summary.duration == duration) & (summary.date == date)
                & _dir_mask(summary, direction) & (summary.quantity == "E_ICRP103") & (summary.sampling_min == 5)]  # fmt: skip
    proj, wide = _projection(traj["lon"], traj["lat"])
    fig = plt.figure(figsize=(7.5, 4.6) if wide else (4.6, 6.4))
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    _map_axes(ax, proj, wide, traj["lat"], traj["lon"])
    for r in s.itertuples():
        t = traj[traj.scenario_id == r.scenario_id]
        segs = _projected_segments(proj, t["lon"], t["lat"])
        ax.add_collection(LineCollection(segs, colors=route_color(r.route), linewidths=2, label=r.route))
        i = t["lat"].idxmin()
        ax.plot(t.loc[i, "lon"], t.loc[i, "lat"], "o", ms=5, color=route_color(r.route), mec=SURFACE, mew=1.5,
                transform=ccrs.PlateCarree())  # fmt: skip
        ax.text(t.loc[i, "lon"] + (0 if wide else 1.2), t.loc[i, "lat"] - (2.2 if wide else 0), f"{t.loc[i, 'lat']:.1f}°",
                fontsize=7, color=INK2, ha="center" if wide else "left", va="baseline" if wide else "center",
                transform=ccrs.PlateCarree())  # fmt: skip
    ax.legend(loc="lower left", fontsize=8)
    names = ", ".join(r.replace("-", "–") for r in s.route)
    kind = "Trayectorias" if DATA_NOTES else "Geodésicas WGS84"  # DATA_NOTES lists the non-geodesic routes
    ax.set_title(f"{kind} {names} (● latitud más austral)", fontsize=10)
    _footer(fig, "Rutas sin vientos, ETOPS ni restricciones ATC.")
    return _save(fig, out)


def map_dose_rate(traj, steps, summary, out: Path, date: str, profile="FL370", duration="gs470", direction=None):
    s = summary[(summary.profile == profile) & (summary.duration == duration) & (summary.date == date)
                & _dir_mask(summary, direction) & (summary.quantity == "E_ICRP103") & (summary.sampling_min == 5)]  # fmt: skip
    s = s.set_index("route").loc[_present(ROUTE_ORDER, s.route)].reset_index()
    sel = steps[steps.scenario_id.isin(s.scenario_id)]
    norm = Normalize(0, float(np.ceil(sel["rate"].max())))
    proj, wide = _projection(traj["lon"], traj["lat"])
    fig = plt.figure(figsize=(max(12, 4 * len(s)), 4.6) if wide else (4.6 * len(s), 7))
    for k, r in enumerate(s.itertuples()):
        ax = fig.add_subplot(1, len(s), k + 1, projection=proj)
        _map_axes(ax, proj, wide, traj["lat"], traj["lon"])
        st = sel[sel.scenario_id == r.scenario_id].sort_values("step")
        lc = LineCollection(_projected_segments(proj, st["lon"], st["lat"]), cmap=SEQ_BLUE, norm=norm, linewidths=3)
        lc.set_array(st["rate"].to_numpy()[:-1])
        ax.add_collection(lc)
        ax.set_title(f"{r.route} ({_dir_label(r.direction)}) · {profile} · {date}\n{r.total_dose:.1f} µSv en {r.airborne_h:.1f} h", fontsize=9)
    cb = fig.colorbar(lc, ax=fig.axes, orientation="horizontal", fraction=0.05, pad=0.08, shrink=0.5 if wide else 0.9)
    cb.set_label("Tasa de dosis efectiva local, ICRP 103 (µSv/h)")
    _footer(fig, "Tasa evaluada por CARI en el punto medio de cada minuto.")
    return _save(fig, out)


def rate_and_altitude(traj, steps, summary, out: Path, route: str, direction=None, duration="gs470",
                      profiles=("FL370", "STEP330-390"), dates=None):  # fmt: skip
    """Two stacked panels sharing time (no dual axis): local rate on top, altitude below."""
    dates = sorted(summary.date.unique()) if dates is None else list(dates)
    direction = route_direction(summary, route, direction)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.5, 6), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    for p in profiles:
        sid = None
        for d in dates:
            r = summary[(summary.route == route) & (summary.direction == direction) & (summary.profile == p)
                        & (summary.duration == duration) & (summary.date == d) & (summary.quantity == "E_ICRP103")
                        & (summary.sampling_min == 5)]  # fmt: skip
            if r.empty:
                continue
            r = r.iloc[0]
            sid = r.scenario_id
            st = steps[steps.scenario_id == sid].sort_values("step")
            a1.plot(st["t_mid_min"] / 60, st["rate"], color=profile_color(p), ls=date_style(d, dates)[0],
                    label=f"{p} · {d} ({r.total_dose:.1f} µSv)")  # fmt: skip
        if sid is None:
            continue
        tr = traj[traj.scenario_id == sid]  # altitude profile does not depend on the date
        a2.plot(tr["t_min"] / 60, tr["alt_ft"] / 100, color=profile_color(p), label=p)
    a1.set_ylabel("Tasa de dosis efectiva (µSv/h)")
    a1.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))  # outside: never covers the curves
    a2.set_ylabel("Altitud de presión (FL)")
    a2.set_xlabel("Tiempo desde el despegue (h)")
    a2.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    o, t = summary[summary.route == route].query("direction == @direction")[["origin", "destination"]].iloc[0]
    styles = ", ".join(f"{date_style(d, dates)[1]} {d}" for d in dates)
    a1.set_title(f"{route} · {o}→{t} · duración {duration} · línea {styles}", fontsize=9.5)
    _footer(fig)
    return _save(fig, out)


def cumulative_dose(steps, summary, out: Path, direction=None, duration="gs470"):
    dates = sorted(summary.date.unique())
    routes = _present(ROUTE_ORDER, summary.route)
    fig, axes = plt.subplots(len(dates), len(routes), figsize=(max(4.5, 3.7 * len(routes)), 3.2 * len(dates)),
                             sharey=True, squeeze=False)  # fmt: skip
    for i, d in enumerate(dates):
        for j, rt in enumerate(routes):
            ax = axes[i, j]
            d_rt = route_direction(summary, rt, direction)
            s = summary[(summary.route == rt) & (summary.direction == d_rt) & (summary.duration == duration)
                        & (summary.date == d) & (summary.quantity == "E_ICRP103") & (summary.sampling_min == 5)]  # fmt: skip
            for p in _present(PROFILE_ORDER, summary.profile):
                r = s[s.profile == p]
                if r.empty:
                    continue
                c = cumulative_series(steps, r.iloc[0].scenario_id)
                ax.plot(c["t_min"] / 60, c["cum_dose"], color=profile_color(p), label=p)
            ax.set_title(f"{rt} ({_dir_label(d_rt)}) · {d}", fontsize=9)
            if j == 0:
                ax.set_ylabel("Dosis efectiva acumulada (µSv)")
            if i == len(dates) - 1:
                ax.set_xlabel("Tiempo desde el despegue (h)")
    axes[0, -1].legend(fontsize=7.5, loc="upper left")
    _footer(fig, f"Duración {duration}.")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _save(fig, out)


def total_dose_bars(summary, out: Path, direction=None, duration="gs470"):
    dirs = {rt: route_direction(summary, rt, direction) for rt in summary.route.unique()}
    dates = sorted(summary.date.unique())
    routes = _present(ROUTE_ORDER, summary.route)
    profiles = _present(PROFILE_ORDER, summary.profile)
    fig, axes = plt.subplots(1, len(dates), figsize=(max(10, 3.4 * len(dates)), 3.8), sharey=True, squeeze=False)
    w = 0.8 / len(profiles)
    for k, d in enumerate(dates):
        ax = axes[0, k]
        s = summary[_dir_mask(summary, direction) & (summary.duration == duration) & (summary.date == d)
                    & (summary.quantity == "E_ICRP103") & (summary.sampling_min == 5)]  # fmt: skip
        for i, p in enumerate(profiles):
            vals = [s[(s.route == rt) & (s.profile == p)].total_dose.sum() for rt in routes]
            x = np.arange(len(routes)) + (i - (len(profiles) - 1) / 2) * w
            ax.bar(x, vals, width=w * 0.92, color=profile_color(p), label=p)  # gap between adjacent bars
        ax.set_xticks(np.arange(len(routes)), routes)
        if len(set(dirs.values())) > 1:  # mixed directions: say which one each bar group shows
            ax.set_xticks(np.arange(len(routes)), [f"{rt}\n({_dir_label(dirs[rt])})" for rt in routes])
        ax.set_title(d, fontsize=9.5)
        ax.grid(axis="x", visible=False)
    same = f" ({_dir_label(next(iter(dirs.values())))})" if len(set(dirs.values())) == 1 else ""
    fig.suptitle(f"Dosis efectiva por tramo{same}", fontsize=10.5)
    axes[0, 0].set_ylabel("Dosis efectiva por tramo (µSv)")
    axes[0, -1].legend(fontsize=7.5, ncol=2, loc="upper right")
    _footer(fig, f"Duración {duration}. Valores exactos en flights_summary.csv.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, out)


def annual_exposure(annual: pd.DataFrame, out: Path, profile_note: str):
    dates = sorted(annual.date.unique())
    fig, axes = plt.subplots(1, len(dates), figsize=(10, 3.9), sharey=True, squeeze=False)
    for k, d in enumerate(dates):
        ax = axes[0, k]
        a = annual[annual.date == d]
        for rt in _present(ROUTE_ORDER, a[a.kind == "ruta única"].routes):
            r = a[(a.kind == "ruta única") & (a.routes == rt)]
            if r.empty:
                continue
            h_leg = r.annual_hours.iloc[0] / r.legs_total.iloc[0]
            ax.plot(r.legs_per_month, r.annual_dose_mSv, "-o", ms=5, color=route_color(rt), mec=SURFACE, mew=1.5,
                    label=f"{rt} ({h_leg:.1f} h/tramo → {r.annual_hours.min():.0f}–{r.annual_hours.max():.0f} h/año)")  # fmt: skip
        rot = a[a.kind.str.startswith("rotación")]
        top = rot.loc[rot.annual_dose_mSv.idxmax(), "kind"] if not rot.empty else None
        for kind in sorted(rot.kind.unique()):
            r = rot[rot.kind == kind].sort_values("legs_per_month")
            rt = r.routes.iloc[0].split(" + ")[-1].split(" ")[0]  # the return leg's route tells them apart
            ax.plot(r.legs_per_month, r.annual_dose_mSv, "-o", ms=5, color=route_color(rt), mec=SURFACE, mew=1.5,
                    label=kind)  # fmt: skip
            last = r.iloc[-1]  # label the highest point: the upper curve above-left, the lower one below-right
            off, ha = ((-8, 4), "right") if kind == top else ((-4, -12), "left")
            ax.annotate(f"{last.annual_dose_mSv:.2f} mSv · {last.annual_hours:.0f} h", (last.legs_per_month, last.annual_dose_mSv),
                        xytext=off, textcoords="offset points", ha=ha, fontsize=7, color=INK2)  # fmt: skip
        for m in a[a.kind == "mixto"].itertuples():
            ax.plot(m.legs_per_month, m.annual_dose_mSv, "D", ms=6, color=INK2, label=f"{m.calendar}")
            ax.annotate(f"{m.annual_dose_mSv:.2f} mSv, {m.annual_hours:.0f} h", (m.legs_per_month, m.annual_dose_mSv),
                        xytext=(6, -10), textcoords="offset points", fontsize=7, color=INK2)  # fmt: skip
        ax.set_xticks(sorted(a.legs_per_month.unique()))
        ax.set_xlabel("Tramos por mes (1 tramo = ida o vuelta)")
        ax.set_title(f"{d} · {int(a.months.iloc[0])} meses", fontsize=9.5)
    fig.suptitle("Exposición anual hipotética", fontsize=10.5)
    axes[0, 0].set_ylabel("Dosis efectiva anual (mSv)")
    rotations = annual.kind.str.startswith("rotación").any()
    axes[0, 0].legend(fontsize=7.5, loc="lower right" if rotations else "upper left")
    legs = "dosis de cada sentido" if rotations else "media de ambos sentidos"
    _footer(fig, f"APROXIMACIÓN: repite la dosis representativa ({profile_note}, {legs}); "
                 "no simula cada vuelo ni afirma cumplimiento de límites laborales.")  # fmt: skip
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return _save(fig, out)


def _calendar_color(row) -> str:
    if row.kind == "mixto":
        return INK2
    return route_color(row.routes.split(" + ")[-1].split(" ")[0])  # rotations: the return leg's route


def annual_cumulative(annual: pd.DataFrame, out: Path, profile_note: str):
    """Month-by-month accumulation of each hypothetical calendar (linear: every month repeats the same dose)."""
    dates = sorted(annual.date.unique())
    months = int(annual.months.iloc[0])
    rotations = annual.kind.str.startswith("rotación").any()
    fig, axes = plt.subplots(1, len(dates), figsize=(max(10, 3.6 * len(dates)), 4.2), sharey=True, squeeze=False)
    m = np.arange(months + 1)
    for k, d in enumerate(dates):
        ax = axes[0, k]
        a = annual[annual.date == d]
        seen = set()
        for r in a.itertuples():
            name = r.kind if r.kind != "ruta única" else r.routes
            ax.plot(m, r.annual_dose_mSv * m / months, color=_calendar_color(r), lw=2,
                    label=None if name in seen else name)  # fmt: skip
            seen.add(name)
        for n, g in a.groupby("legs_per_month"):  # one end label per calendar size, values in legend order
            unit = f"{n // 2} rot/mes" if rotations else f"{n} tramos/mes"
            vals = " / ".join(f"{v:.2f}" for v in g.annual_dose_mSv)
            ax.annotate(f"{unit}: {vals}", (months, g.annual_dose_mSv.max()), xytext=(-4, 4), textcoords="offset points",
                        ha="right", fontsize=7, color=INK2, bbox=dict(fc=SURFACE, ec="none", pad=1))  # fmt: skip
        ax.set_xticks(range(0, months + 1, 3))
        ax.set_xlabel("Mes del calendario")
        ax.set_title(d, fontsize=9.5)
    fig.suptitle("Acumulación anual hipotética de dosis efectiva", fontsize=10.5)
    axes[0, 0].set_ylabel("Dosis efectiva acumulada (mSv)")
    axes[0, 0].legend(fontsize=7.5, loc="upper left")
    legs = "dosis de cada sentido" if rotations else "media de ambos sentidos"
    _footer(fig, f"APROXIMACIÓN: cada mes repite la dosis representativa ({profile_note}, {legs}) con la condición solar "
                 "de la fecha del panel; por eso la acumulación es lineal. Etiquetas: mSv a 12 meses, en el orden de la "
                 "leyenda. No afirma cumplimiento de límites laborales.")  # fmt: skip
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return _save(fig, out)
