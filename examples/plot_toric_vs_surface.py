from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REQUIRED_COLUMNS = {
    "code",
    "basis",
    "p",
    "distance",
    "rounds",
    "shots",
    "failures",
    "logical_error_rate",
    "num_qubits",
    "num_detectors",
    "num_observables",
    "num_measurements",
}


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    df = df.copy()

    df["code"] = df["code"].astype(str)
    df["basis"] = df["basis"].astype(str)
    df["p"] = df["p"].astype(float)
    df["distance"] = df["distance"].astype(int)
    df["rounds"] = df["rounds"].astype(int)
    df["shots"] = df["shots"].astype(int)
    df["failures"] = df["failures"].astype(int)
    df["logical_error_rate"] = df["logical_error_rate"].astype(float)

    # Avoid issues when plotting log scale if a large-distance low-p run has 0 failures.
    # 0 failures in N shots means the true rate is below roughly O(1/N), so 0.5/N is
    # a common plotting-only pseudo-count.
    df["logical_error_rate_plot"] = df["logical_error_rate"]
    zero_mask = df["logical_error_rate_plot"] <= 0
    df.loc[zero_mask, "logical_error_rate_plot"] = (
        0.5 / df.loc[zero_mask, "shots"]
    )

    return df


def save_summary_csv(
    df: pd.DataFrame,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = (
        df.pivot_table(
            index=["basis", "p", "distance"],
            columns="code",
            values="logical_error_rate",
            aggfunc="first",
        )
        .reset_index()
    )

    if "toric" in summary.columns and "surface" in summary.columns:
        summary["toric_minus_surface"] = summary["toric"] - summary["surface"]
        summary["ratio_toric_over_surface"] = summary["toric"] / summary["surface"]

        summary["better"] = summary.apply(
            lambda row: "toric"
            if row["toric"] < row["surface"]
            else "surface"
            if row["surface"] < row["toric"]
            else "tie",
            axis=1,
        )

    filename = out_dir / "toric_vs_surface_summary.csv"
    summary.to_csv(filename, index=False)
    print(f"wrote {filename}")


def plot_toric_vs_surface_by_basis_and_p(
    df: pd.DataFrame,
    out_dir: Path,
    log_y: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for basis in sorted(df["basis"].unique()):
        for p in sorted(df["p"].unique()):
            sub = df[
                (df["basis"] == basis)
                & (df["p"] == p)
            ].copy()

            if sub.empty:
                continue

            plt.figure()

            for code in sorted(sub["code"].unique()):
                code_df = sub[sub["code"] == code].sort_values("distance")

                y_col = (
                    "logical_error_rate_plot"
                    if log_y
                    else "logical_error_rate"
                )

                plt.plot(
                    code_df["distance"],
                    code_df[y_col],
                    marker="o",
                    label=code,
                )

            if log_y:
                plt.yscale("log")

            plt.xlabel("Distance d")
            plt.ylabel("Logical error rate")
            plt.title(f"Toric vs Surface, basis={basis}, p={p}")
            plt.grid(True, which="both", linestyle="--", alpha=0.5)
            plt.legend()

            filename = out_dir / f"toric_vs_surface_basis_{basis}_p_{p:g}.png"
            plt.savefig(filename, dpi=200, bbox_inches="tight")
            plt.close()

            print(f"wrote {filename}")


def plot_threshold_style(
    df: pd.DataFrame,
    out_dir: Path,
    log_y: bool,
) -> None:
    """
    For each code and basis:
      x-axis: physical error rate p
      y-axis: logical error rate
      one curve per distance

    This is usually the most useful large-scan plot for threshold behavior.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    for code in sorted(df["code"].unique()):
        for basis in sorted(df["basis"].unique()):
            sub = df[
                (df["code"] == code)
                & (df["basis"] == basis)
            ].copy()

            if sub.empty:
                continue

            plt.figure()

            for distance in sorted(sub["distance"].unique()):
                dist_df = sub[sub["distance"] == distance].sort_values("p")

                y_col = (
                    "logical_error_rate_plot"
                    if log_y
                    else "logical_error_rate"
                )

                plt.plot(
                    dist_df["p"],
                    dist_df[y_col],
                    marker="o",
                    label=f"d={distance}",
                )

            if log_y:
                plt.yscale("log")

            plt.xlabel("Physical error rate p")
            plt.ylabel("Logical error rate")
            plt.title(f"{code}, basis={basis}: logical error rate vs p")
            plt.grid(True, which="both", linestyle="--", alpha=0.5)
            plt.legend()

            filename = out_dir / f"threshold_style_{code}_basis_{basis}.png"
            plt.savefig(filename, dpi=200, bbox_inches="tight")
            plt.close()

            print(f"wrote {filename}")


def plot_threshold_overlay_toric_vs_surface(
    df: pd.DataFrame,
    out_dir: Path,
    log_y: bool,
) -> None:
    """
    For each basis and distance:
      x-axis: physical error rate p
      y-axis: logical error rate
      compare toric vs surface directly.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    for basis in sorted(df["basis"].unique()):
        for distance in sorted(df["distance"].unique()):
            sub = df[
                (df["basis"] == basis)
                & (df["distance"] == distance)
            ].copy()

            if sub.empty:
                continue

            plt.figure()

            for code in sorted(sub["code"].unique()):
                code_df = sub[sub["code"] == code].sort_values("p")

                y_col = (
                    "logical_error_rate_plot"
                    if log_y
                    else "logical_error_rate"
                )

                plt.plot(
                    code_df["p"],
                    code_df[y_col],
                    marker="o",
                    label=code,
                )

            if log_y:
                plt.yscale("log")

            plt.xlabel("Physical error rate p")
            plt.ylabel("Logical error rate")
            plt.title(f"Toric vs Surface, basis={basis}, d={distance}")
            plt.grid(True, which="both", linestyle="--", alpha=0.5)
            plt.legend()

            filename = out_dir / f"overlay_basis_{basis}_distance_{distance}.png"
            plt.savefig(filename, dpi=200, bbox_inches="tight")
            plt.close()

            print(f"wrote {filename}")


def plot_all_p_same_basis(
    df: pd.DataFrame,
    out_dir: Path,
    log_y: bool,
) -> None:
    """
    This is similar to your original all-p plot, but made slightly safer for
    large scans. It can become visually crowded when there are many p values.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    for basis in sorted(df["basis"].unique()):
        sub = df[df["basis"] == basis].copy()

        if sub.empty:
            continue

        plt.figure(figsize=(10, 7))

        for code in sorted(sub["code"].unique()):
            for p in sorted(sub["p"].unique()):
                code_p_df = sub[
                    (sub["code"] == code)
                    & (sub["p"] == p)
                ].sort_values("distance")

                if code_p_df.empty:
                    continue

                y_col = (
                    "logical_error_rate_plot"
                    if log_y
                    else "logical_error_rate"
                )

                plt.plot(
                    code_p_df["distance"],
                    code_p_df[y_col],
                    marker="o",
                    label=f"{code}, p={p:g}",
                )

        if log_y:
            plt.yscale("log")

        plt.xlabel("Distance d")
        plt.ylabel("Logical error rate")
        plt.title(f"Toric vs Surface, all p values, basis={basis}")
        plt.grid(True, which="both", linestyle="--", alpha=0.5)
        plt.legend(fontsize=8, ncol=2)

        filename = out_dir / f"all_p_basis_{basis}.png"
        plt.savefig(filename, dpi=200, bbox_inches="tight")
        plt.close()

        print(f"wrote {filename}")


def plot_failure_count(
    df: pd.DataFrame,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for basis in sorted(df["basis"].unique()):
        for p in sorted(df["p"].unique()):
            sub = df[
                (df["basis"] == basis)
                & (df["p"] == p)
            ].copy()

            if sub.empty:
                continue

            plt.figure()

            for code in sorted(sub["code"].unique()):
                code_df = sub[sub["code"] == code].sort_values("distance")

                plt.plot(
                    code_df["distance"],
                    code_df["failures"],
                    marker="o",
                    label=code,
                )

            plt.xlabel("Distance d")
            plt.ylabel("Number of failures")
            plt.title(f"Failure count, basis={basis}, p={p:g}")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend()

            filename = out_dir / f"failures_basis_{basis}_p_{p:g}.png"
            plt.savefig(filename, dpi=200, bbox_inches="tight")
            plt.close()

            print(f"wrote {filename}")


def plot_resource_comparison(
    df: pd.DataFrame,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resource counts do not depend on p for the same code/basis/distance,
    # so drop duplicates before plotting.
    resource_df = df[
        [
            "code",
            "basis",
            "distance",
            "num_qubits",
            "num_detectors",
            "num_measurements",
        ]
    ].drop_duplicates()

    for basis in sorted(resource_df["basis"].unique()):
        sub = resource_df[resource_df["basis"] == basis].copy()

        if sub.empty:
            continue

        for y_col in ["num_qubits", "num_detectors", "num_measurements"]:
            plt.figure()

            for code in sorted(sub["code"].unique()):
                code_df = sub[sub["code"] == code].sort_values("distance")

                plt.plot(
                    code_df["distance"],
                    code_df[y_col],
                    marker="o",
                    label=code,
                )

            plt.xlabel("Distance d")
            plt.ylabel(y_col)
            plt.title(f"{y_col} vs distance, basis={basis}")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend()

            filename = out_dir / f"resource_{y_col}_basis_{basis}.png"
            plt.savefig(filename, dpi=200, bbox_inches="tight")
            plt.close()

            print(f"wrote {filename}")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        type=str,
        default="toric_vs_surface_large_scan.csv",
        help="CSV generated by toric_vs_surface_large_scan.py",
    )

    parser.add_argument(
        "--out-dir",
        type=str,
        default="large_scan_plots",
        help="Directory to save plots and summary CSV",
    )

    parser.add_argument(
        "--linear-y",
        action="store_true",
        help="Use linear y-axis instead of log y-axis.",
    )

    parser.add_argument(
        "--skip-crowded",
        action="store_true",
        help="Skip crowded all-p-vs-distance plots.",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    log_y = not args.linear_y

    df = pd.read_csv(csv_path)
    df = prepare_dataframe(df)

    print("Loaded CSV:")
    print(csv_path)
    print()
    print("Rows:", len(df))
    print("Codes:", sorted(df["code"].unique()))
    print("Bases:", sorted(df["basis"].unique()))
    print("Distances:", sorted(df["distance"].unique()))
    print("p values:", sorted(df["p"].unique()))
    print()

    save_summary_csv(df, out_dir)

    plot_toric_vs_surface_by_basis_and_p(
        df=df,
        out_dir=out_dir / "by_basis_and_p",
        log_y=log_y,
    )

    plot_threshold_style(
        df=df,
        out_dir=out_dir / "threshold_style",
        log_y=log_y,
    )

    plot_threshold_overlay_toric_vs_surface(
        df=df,
        out_dir=out_dir / "overlay_by_distance",
        log_y=log_y,
    )

    if not args.skip_crowded:
        plot_all_p_same_basis(
            df=df,
            out_dir=out_dir / "all_p_same_basis",
            log_y=log_y,
        )

    plot_failure_count(
        df=df,
        out_dir=out_dir / "failure_counts",
    )

    plot_resource_comparison(
        df=df,
        out_dir=out_dir / "resources",
    )

    print()
    print(f"All plots written to: {out_dir}")


if __name__ == "__main__":
    main()
