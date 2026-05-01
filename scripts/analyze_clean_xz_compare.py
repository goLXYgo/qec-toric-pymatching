from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


Z_CSV = "clean_z_scan.csv"
X_CSV = "clean_x_scan.csv"


def load_rows(path: str, basis: str) -> list[dict]:
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

            # log 圖不能畫 0，所以對 failures=0 用一個上界代理值
            log_plot_rate = rate if failures > 0 else 0.5 / shots

            rows.append(
                {
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
    print("===== Combined Summary =====")
    rows = sorted(rows, key=lambda r: (r["p"], r["basis"], r["distance"]))
    for r in rows:
        print(
            f"basis={r['basis']}, p={r['p']:.3f}, d={r['distance']}, "
            f"failures={r['failures']}/{r['shots']}, "
            f"rate={r['rate']:.6f}, sigma={r['sigma']:.6f}"
        )


def plot_linear(rows: list[dict], outname: str) -> None:
    ps = sorted(set(r["p"] for r in rows))
    bases = sorted(set(r["basis"] for r in rows))

    plt.figure(figsize=(8, 5))
    for p in ps:
        for basis in bases:
            sub = sorted(
                [r for r in rows if r["p"] == p and r["basis"] == basis],
                key=lambda r: r["distance"],
            )
            xs = [r["distance"] for r in sub]
            ys = [r["rate"] for r in sub]
            yerr = [r["sigma"] for r in sub]
            plt.errorbar(
                xs,
                ys,
                yerr=yerr,
                marker="o",
                capsize=4,
                label=f"{basis}, p={p}",
            )

    plt.xlabel("Code distance")
    plt.ylabel("Logical error rate")
    plt.title("Stim-clean X/Z prototypes: logical error rate vs distance")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname, dpi=150)
    plt.close()


def plot_semilogy(rows: list[dict], outname: str) -> None:
    ps = sorted(set(r["p"] for r in rows))
    bases = sorted(set(r["basis"] for r in rows))

    plt.figure(figsize=(8, 5))
    for p in ps:
        for basis in bases:
            sub = sorted(
                [r for r in rows if r["p"] == p and r["basis"] == basis],
                key=lambda r: r["distance"],
            )
            xs = [r["distance"] for r in sub]
            ys = [r["log_plot_rate"] for r in sub]
            plt.semilogy(xs, ys, marker="o", label=f"{basis}, p={p}")

    plt.xlabel("Code distance")
    plt.ylabel("Logical error rate (log scale)")
    plt.title("Stim-clean X/Z prototypes: semilogy distance scaling")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname, dpi=150)
    plt.close()


def plot_by_p(rows: list[dict], p_value: float, outname: str) -> None:
    bases = sorted(set(r["basis"] for r in rows))
    subrows = [r for r in rows if abs(r["p"] - p_value) < 1e-12]

    plt.figure(figsize=(7, 5))
    for basis in bases:
        sub = sorted(
            [r for r in subrows if r["basis"] == basis],
            key=lambda r: r["distance"],
        )
        xs = [r["distance"] for r in sub]
        ys = [r["rate"] for r in sub]
        yerr = [r["sigma"] for r in sub]
        plt.errorbar(
            xs,
            ys,
            yerr=yerr,
            marker="o",
            capsize=4,
            label=f"{basis}",
        )

    plt.xlabel("Code distance")
    plt.ylabel("Logical error rate")
    plt.title(f"X vs Z comparison at p={p_value}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname, dpi=150)
    plt.close()


def main() -> None:
    if not Path(Z_CSV).exists():
        raise FileNotFoundError(f"Missing file: {Z_CSV}")
    if not Path(X_CSV).exists():
        raise FileNotFoundError(f"Missing file: {X_CSV}")

    rows = []
    rows.extend(load_rows(Z_CSV, basis="Z"))
    rows.extend(load_rows(X_CSV, basis="X"))

    print_summary(rows)

    save_combined_csv(rows, "clean_xz_combined.csv")
    plot_linear(rows, "clean_xz_compare_linear.png")
    plot_semilogy(rows, "clean_xz_compare_semilogy.png")

    for p in sorted(set(r["p"] for r in rows)):
        plot_by_p(rows, p, f"clean_xz_compare_p_{str(p).replace('.', '_')}.png")

    print("wrote clean_xz_combined.csv")
    print("wrote clean_xz_compare_linear.png")
    print("wrote clean_xz_compare_semilogy.png")
    print("wrote per-p comparison plots")


if __name__ == "__main__":
    main()