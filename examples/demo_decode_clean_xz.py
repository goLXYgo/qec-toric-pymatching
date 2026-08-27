from qec_gen import (
    NoiseModel,
    ToricCodeStimCleanXZGenerator,
    decode_memory_experiment,
)

distance = 3
rounds = 3
p = 0.001
shots = 10000

gen = ToricCodeStimCleanXZGenerator(
    distance=distance,
    rounds=rounds,
    noise=NoiseModel(
        before_round_data_depolarization=p,
        after_clifford_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    ),
)

circuit = gen.build_memory_experiment(basis="Z")

result = decode_memory_experiment(circuit, shots)

print("distance:", distance)
print("rounds:", rounds)
print("physical error rate:", p)
print("shots:", shots)
print("logical errors:", result.logical_errors)
print("logical error rate:", result.logical_error_rate)
