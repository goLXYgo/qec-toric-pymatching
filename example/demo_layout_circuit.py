from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import stim

from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator
from toric_gen.layout import ToricCodeLayout


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def save_svg(path: Path, diagram: object) -> None:
    path.write_text(str(diagram), encoding="utf-8")
    print(f"wrote {path}")


def plot_layout(distance: int, output_path: Path) -> None:
    layout = ToricCodeLayout(distance)

    qubit_coords = layout.qubit_coords()

    data_qids = {layout.data_qid(e) for e in layout.data_order}
    x_anc_qids = {layout.x_anc_qid(v) for v in layout.x_anc_order}
    z_anc_qids = {layout.z_anc_qid(p) for p in layout.z_anc_order}

    logical_z1_qids = set(layout.logical_z_loops()["Z1"])
    logical_x1_qids = set(layout.logical_x_loops()["X1"])

    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw X-check support lines.
    for v in layout.x_anc_order:
        a = layout.x_anc_qid(v)
        ax_x, ax_y = qubit_coords[a]

        for e in layout.x_check_support(v):
            d = layout.data_qid(e)
            dx, dy = qubit_coords[d]
            ax.plot([ax_x, dx], [ax_y, dy], linewidth=0.8, alpha=0.25)

    # Draw Z-check support lines.
    for p in layout.z_anc_order:
        a = layout.z_anc_qid(p)
        ax_x, ax_y = qubit_coords[a]

        for e in layout.z_check_support(p):
            d = layout.data_qid(e)
            dx, dy = qubit_coords[d]
            ax.plot([ax_x, dx], [ax_y, dy], linewidth=0.8, alpha=0.25)

    # Draw qubits.
    for q, (x, y) in qubit_coords.items():
        if q in data_qids:
            marker = "o"
            label = "data"
            size = 80
        elif q in x_anc_qids:
            marker = "s"
            label = "X ancilla"
            size = 90
        elif q in z_anc_qids:
            marker = "^"
            label = "Z ancilla"
            size = 90
        else:
            marker = "x"
            label = "unknown"
            size = 80

        # Avoid duplicate legend labels.
        existing_labels = [t.get_text() for t in ax.get_legend().texts] if ax.get_legend() else []
        show_label = label if label not in existing_labels else None

        ax.scatter(x, y, marker=marker, s=size, label=show_label)

        # qid label
        ax.text(x + 0.04, y + 0.04, str(q), fontsize=7)

    # Highlight logical Z1 loop.
    for q in logical_z1_qids:
        x, y = qubit_coords[q]
        ax.scatter(
            x,
            y,
            marker="o",
            s=260,
            facecolors="none",
            linewidths=2.0,
            label="logical Z1" if q == next(iter(logical_z1_qids)) else None,
        )

    # Highlight logical X1 loop.
    for q in logical_x1_qids:
        x, y = qubit_coords[q]
        ax.scatter(
            x,
            y,
            marker="x",
            s=220,
            linewidths=2.5,
            label="logical X1" if q == next(iter(logical_x1_qids)) else None,
        )

    ax.set_title(f"Toric code layout, d={distance}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="best")
    fig.tight_layout()

    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    print(f"wrote {output_path}")


def build_and_save_circuit(
    basis: str,
    distance: int,
    rounds: int,
    output_dir: Path,
) -> None:
    gen = ToricCodeStimCleanXZGenerator(
        distance=distance,
        rounds=rounds,
        noise=NoiseModel(
            before_round_data_depolarization=0.0,
            after_clifford_depolarization=0.0,
            before_measure_flip_probability=0.0,
            after_reset_flip_probability=0.0,
        ),
    )

    circuit = gen.build_memory_experiment(basis=basis)

    stim_path = output_dir / f"toric_d{distance}_r{rounds}_basis_{basis}.stim"
    dem_path = output_dir / f"toric_d{distance}_r{rounds}_basis_{basis}.dem"
    svg_path = output_dir / f"toric_d{distance}_r{rounds}_basis_{basis}_timeline.svg"

    dem = circuit.detector_error_model(decompose_errors=True)

    save_text(stim_path, str(circuit))
    save_text(dem_path, str(dem))

    # Stim timeline SVG. Open this SVG in browser.
    save_svg(svg_path, circuit.diagram("timeline-svg"))

    print()
    print(f"basis={basis}")
    print(f"num_qubits       = {circuit.num_qubits}")
    print(f"num_detectors    = {circuit.num_detectors}")
    print(f"num_observables  = {circuit.num_observables}")
    print(f"num_measurements = {circuit.num_measurements}")
    print()

    print("First 80 lines of circuit:")
    print("-" * 80)
    lines = str(circuit).splitlines()
    for line in lines[:80]:
        print(line)
    if len(lines) > 80:
        print("...")
    print("-" * 80)
    print()


def main() -> None:
    distance = 3
    rounds = distance

    output_dir = Path("demo_outputs")
    output_dir.mkdir(exist_ok=True)

    plot_layout(
        distance=distance,
        output_path=output_dir / f"toric_layout_d{distance}.png",
    )

    for basis in ["Z", "X"]:
        build_and_save_circuit(
            basis=basis,
            distance=distance,
            rounds=rounds,
            output_dir=output_dir,
        )


if __name__ == "__main__":
    main()