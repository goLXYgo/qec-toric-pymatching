from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_one_basis(
    rows: list[dict[str, str]],
    basis: str,
    output_dir: Path,
) -> None:
    data: dict[int, list[tuple[float, float]]] = defaultdict(list)

    for row in rows:
        if row["basis"] != basis:
            continue

        distance = int(row["distance"])
        p = float(row["p"])
        logical_error_rate = float(row["logical_error_rate"])

        if p <= 0:
            continue

        # log plot 不能畫 0，所以 0 failure 的點先跳過
        # 如果想保留，可以改成 logical_error_rate = 0.5 / shots
        if logical_error_rate <= 0:
            continue

        data[distance].append((p, logical_error_rate))

    plt.figure(figsize=(10, 7))

    for distance in sorted(data):
        points = sorted(data[distance])
        ps = [x[0] for x in points]
        rates = [x[1] for x in points]

        plt.plot(
            ps,
            rates,
            marker="o",
            linewidth=2,
            label=f"d={distance}",
        )

    plt.xscale("log")
    plt.yscale("log")

    plt.xlabel("Physical error rate p", fontsize=14)
    plt.ylabel("Logical error rate", fontsize=14)
    plt.title(f"toric, basis={basis}: logical error rate vs p", fontsize=18)

    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.legend(fontsize=12)
    plt.tight_layout()

    output_path = output_dir / f"toric_basis_{basis}_low_p.png"
    plt.savefig(output_path, dpi=200)
    plt.close()

    print(f"wrote {output_path}")


def main() -> None:
    input_csv = "clean_xz_scan_low_p.csv"
    output_dir = Path("plots")
    output_dir.mkdir(exist_ok=True)

    rows = read_csv(input_csv)

    for basis in ["Z", "X"]:
        plot_one_basis(rows, basis, output_dir)


if __name__ == "__main__":
    main()