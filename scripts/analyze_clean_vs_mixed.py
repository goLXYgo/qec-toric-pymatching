from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


CLEAN_Z_CSV = "clean_z_scan.csv"
CLEAN_X_CSV = "clean_x_scan.csv"
MIXED_XZ_CSV = "clean_xz_scan.csv"


def load_clean_rows(path: str, basis: str, label: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = float(row["p"])
            distance = int(row["distance"])
            rounds = int(row["rounds"])
            shots = int(row["shots"])
            failures = int(row["failures"])

            rate = failures / shots
            sigma = math.sqrt(rate * (1 - rate) / shots) if shots > 0 else 0.0
            log_plot_rate = rate if failures > 0 else 0.5 / shots

            rows.append(
                {
                    "family": label,
                    "basis": basis,
                    "p": p,
                    "distance": distance,
                    "rounds": rounds,
                    "shots": shots,
                    "failures": failures,
                    "rate": rate,
                    "sigma": sigma,
                    "log_plot_rate": log_plot_rate,
                }
            )
    return rows


def load_mixed_rows(path: str, label: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            basis = row["basis"]
            p = float(row["p"])
            distance = int(row["distance"])
            rounds = int(row["rounds"])
            shots = int(row["shots"])
            failures = int(row["failures"])

            rate = failures / shots
            sigma = math.sqrt(rate * (1 - rate) / shots) if shots > 0 else 0.0
            log_plot_rate = rate if failures > 0 else 0.5 / shots

            rows.append(
                {
                    "family": label,
                    "basis": basis,
                    "p": p,
                    "distance": distance,
                    "rounds": rounds,
                    "shots": shots,
                    "failures": failures,
                    "rate": rate,
                    "sigma": sigma,
                    "log_plot_rate": log_plot_rate,
                }
            )
    return rows


def save_combined_csv(rows: list[dict], path: str) -> None:
    fieldnames = [
        "family",
        "basis",
        "p",
        "distance",
        "rounds",
        "shots",
        "failures",
        "rate",
        "sigma",
        "log_plot_rate",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict]) -> None:
    print("===== Summary =====")
    rows = sorted(rows, key=lambda r: (r["basis"], r["p"], r["family"], r["distance"]))
    for r in rows:
        print(
            f"family={r['family']}, basis={r['basis']}, p={r['p']:.3f}, "
            f"d={r['distance']}, failures={r['failures']}/{r['shots']}, "
            f"rate={r['rate']:.6f}, sigma={r['sigma']:.6f}"
        )


def _subset(rows: list[dict], basis: str, p: float) -> list[dict]:
    return sorted(
        [r for r in rows if r["basis"] == basis and abs(r["p"] - p) < 1e-12],
        key=lambda r: (r["family"], r["distance"]),
    )


def plot_compare_linear(rows: list[dict], basis: str, p: float, outname: str) -> None:
    sub = _subset(rows, basis, p)
    families = sorted(set(r["family"] for r in sub))

    plt.figure(figsize=(7, 5))
    for family in families:
        fam_rows = sorted([r for r in sub if r["family"] == family], key=lambda r: r["distance"])
        xs = [r["distance"] for r in fam_rows]
        ys = [r["rate"] for r in fam_rows]
        yerr = [r["sigma"] for r in fam_rows]
        plt.errorbar(xs, ys, yerr=yerr, marker="o", capsize=4, label=family)

    plt.xlabel("Code distance")
    plt.ylabel("Logical error rate")
    plt.title(f"{basis}-basis: clean vs mixed at p={p}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname, dpi=150)
    plt.close()


def plot_compare_semilogy(rows: list[dict], basis: str, p: float, outname: str) -> None:
    sub = _subset(rows, basis, p)
    families = sorted(set(r["family"] for r in sub))

    plt.figure(figsize=(7, 5))
    for family in families:
        fam_rows = sorted([r for r in sub if r["family"] == family], key=lambda r: r["distance"])
        xs = [r["distance"] for r in fam_rows]
        ys = [r["log_plot_rate"] for r in fam_rows]
        plt.semilogy(xs, ys, marker="o", label=family)

    plt.xlabel("Code distance")
    plt.ylabel("Logical error rate (log scale)")
    plt.title(f"{basis}-basis: clean vs mixed at p={p} (semilogy)")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname, dpi=150)
    plt.close()


def main() -> None:
    for path in [CLEAN_Z_CSV, CLEAN_X_CSV, MIXED_XZ_CSV]:
        if not Path(path).exists():
            raise FileNotFoundError(f"Missing file: {path}")

    rows: list[dict] = []
    rows.extend(load_clean_rows(CLEAN_Z_CSV, basis="Z", label="clean_Z_only"))
    rows.extend(load_clean_rows(CLEAN_X_CSV, basis="X", label="clean_X_only"))
    rows.extend(load_mixed_rows(MIXED_XZ_CSV, label="mixed_XZ"))

    print_summary(rows)
    save_combined_csv(rows, "clean_vs_mixed_combined.csv")

    for basis in ["Z", "X"]:
        for p in [0.001, 0.003]:
            plot_compare_linear(
                rows,
                basis=basis,
                p=p,
                outname=f"compare_{basis}_p_{str(p).replace('.', '_')}_linear.png",
            )
            plot_compare_semilogy(
                rows,
                basis=basis,
                p=p,
                outname=f"compare_{basis}_p_{str(p).replace('.', '_')}_semilogy.png",
            )

    print("wrote clean_vs_mixed_combined.csv")
    print("wrote comparison plots")


if __name__ == "__main__":
    main()