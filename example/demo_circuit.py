from __future__ import annotations

from pathlib import Path

from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator


def main() -> None:
    distance = 2
    rounds = 1
    basis = "Z"   
    p = 0.00

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    noise = NoiseModel(
        before_round_data_depolarization=p,
        after_clifford_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )

    gen = ToricCodeStimCleanXZGenerator(
        distance=distance,
        rounds=rounds,
        noise=noise,
    )

    circuit = gen.build_memory_experiment(basis=basis)

    stim_path = out_dir / f"toric_d{distance}_r{rounds}_memory_{basis}.stim"
    txt_path = out_dir / f"toric_d{distance}_r{rounds}_memory_{basis}.txt"
    svg_path = out_dir / f"toric_d{distance}_r{rounds}_memory_{basis}_timeline.svg"
    dem_path = out_dir / f"toric_d{distance}_r{rounds}_memory_{basis}.dem"

    circuit_text = str(circuit)

    # 1. 印出 Stim 文字電路
    print()
    print("=" * 80)
    print("STIM TEXT CIRCUIT")
    print("=" * 80)
    print(circuit_text)

    # 2. 存文字電路
    txt_path.write_text(circuit_text, encoding="utf-8")

    # 3. 用 Stim 產生 timeline SVG
    svg = circuit.diagram("timeline-svg")
    svg_path.write_text(str(svg), encoding="utf-8")



    print()
    print("=" * 80)
    print(f"Toric code generated: d={distance}, rounds={rounds}, basis={basis}")
    print("=" * 80)
    print("num_qubits:     ", circuit.num_qubits)
    print("num_detectors:  ", circuit.num_detectors)
    print("num_observables:", circuit.num_observables)
    print()
    print("Saved:")
    print("  Stim circuit:        ", stim_path)
    print("  Text circuit:        ", txt_path)
    print("  SVG circuit diagram: ", svg_path)
    print("  DEM file:            ", dem_path)
    print()
    print("用瀏覽器打開這個看圖：")
    print(f"  {svg_path}")


if __name__ == "__main__":
    main()