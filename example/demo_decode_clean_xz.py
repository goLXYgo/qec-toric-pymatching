from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator
import pymatching

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

dem = circuit.detector_error_model(decompose_errors=True)
matching = pymatching.Matching.from_detector_error_model(dem)

sampler = circuit.compile_detector_sampler()
detection_events, observable_flips = sampler.sample(
    shots=shots,
    separate_observables=True,
)

predictions = matching.decode_batch(detection_events)

num_errors = (predictions[:, 0] != observable_flips[:, 0]).sum()
logical_error_rate = num_errors / shots

print("distance:", distance)
print("rounds:", rounds)
print("physical error rate:", p)
print("shots:", shots)
print("logical errors:", num_errors)
print("logical error rate:", logical_error_rate)