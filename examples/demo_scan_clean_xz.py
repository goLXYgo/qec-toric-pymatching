from qec_gen import NoiseModel, ToricCodeStimCleanXZGenerator, run_parameter_scan


def toric_circuit(distance: int, rounds: int, p: float, basis: str):
    noise = NoiseModel(
        before_round_data_depolarization=p,
        after_clifford_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )
    return ToricCodeStimCleanXZGenerator(
        distance=distance,
        rounds=rounds,
        noise=noise,
    ).build_memory_experiment(basis=basis)


def main() -> None:
    results = run_parameter_scan(
        toric_circuit,
        code="toric",
        distances=[2, 3],
        physical_error_rates=[0.001, 0.003],
        rounds=3,
        shots=1_000,
        basis="Z",
        seed=1234,
    )
    for point in results:
        print(point)


if __name__ == "__main__":
    main()
