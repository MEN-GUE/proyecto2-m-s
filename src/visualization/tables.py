import csv
from pathlib import Path

TAB_DIR = Path(__file__).resolve().parents[2] / "results/tables"


def _fmt(x):
    if isinstance(x, float):
        return f"{x:.3f}".rstrip("0").rstrip(".")
    return str(x).replace("%", "\\%").replace("_", "\\_").replace("&", "\\&")


def save(name, header, rows):
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    with open(TAB_DIR / f"{name}.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([header, *rows])
    tex = ["\\begin{tabular}{" + "l" + "r" * (len(header) - 1) + "}", "\\toprule",
           " & ".join(map(_fmt, header)) + " \\\\", "\\midrule"]
    tex += [" & ".join(_fmt(x) for x in r) + " \\\\" for r in rows]
    tex += ["\\bottomrule", "\\end{tabular}"]
    (TAB_DIR / f"{name}.tex").write_text("\n".join(tex) + "\n")
    return TAB_DIR / f"{name}.csv"


def model_parameters():
    from ..model import params as P
    rows = [
        ["Paso de tiempo", "$\\Delta t$", P.DT, "s", "Enunciado"],
        ["Masa", "$m$", P.MASS, "kg", "Helbing et al. (2000)"],
        ["Radio", "$R_\\alpha$", f"U({P.RADIUS_MIN}, {P.RADIUS_MAX})", "m", "Helbing et al. (2000)"],
        ["Rapidez deseada", "$v^0_\\alpha$", f"N({P.V0_MEAN}, {P.V0_SD}) en [{P.V0_MIN:.2f}, {P.V0_MAX:.2f}]", "m/s",
         "Helbing y Molnár (1995)"],
        ["Rapidez máxima", "", f"{P.V_CAP} $v^0_\\alpha$", "m/s", "Helbing y Molnár (1995)"],
        ["Tiempo de relajación", "$\\tau$", P.TAU, "s", "Se calibra con Jülich"],
        ["Repulsión entre personas", "$A_p$, $B_p$", f"{P.A_P:.0f}, {P.B_P}", "N, m", "Helbing et al. (2000)"],
        ["Repulsión de muros", "$A_w$, $B_w$", f"{P.A_W:.0f}, {P.B_W}", "N, m", "Helbing et al. (2000)"],
        ["Probabilidad de compra", "$p$", P.P_BUY, "", "Enunciado"],
        ["Atención (media, CV)", "", f"LogNormal({P.SERVICE_MEAN}, {P.SERVICE_CV})", "s", "Enunciado; CV estimado"],
        ["Puntos de atención por barra", "", P.SERVERS_PER_BAR, "", "Estimación"],
        ["Separación en fila", "", P.QUEUE_SPACING, "m", "Reposo con $A_p$, $B_p$"],
        ["Kernel de densidad", "$\\sigma$", P.DENS_SIGMA, "m", "Helbing et al. (2007)"],
        ["Celda de densidad", "", P.DENS_H, "m", "Elección"],
    ]
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    with open(TAB_DIR / "parametros_modelo.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["Parámetro", "Símbolo", "Valor", "Unidad", "Fuente"], *rows])
    tex = ["\\begin{tabular}{llllp{4cm}}", "\\toprule", "Parámetro & Símbolo & Valor & Unidad & Fuente \\\\",
           "\\midrule"] + [" & ".join(str(x) for x in r) + " \\\\" for r in rows] + ["\\bottomrule", "\\end{tabular}"]
    (TAB_DIR / "parametros_modelo.tex").write_text("\n".join(tex) + "\n")
    return TAB_DIR / "parametros_modelo.csv"
