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
