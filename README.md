# Toric Code Memory Experiment Progress

This repository currently contains three working toric-code memory prototypes built to interface cleanly with **Stim** and **PyMatching**.

# toric-gen

Commands after cloning

This is the most typical workflow after cloning the repository.

Windows PowerShell
```powershell
git clone <your-repo-url>
cd toric-gen
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest -q
python examples/demo_decode_clean_xz.py
```

macOS / Linux
```bash
git clone <your-repo-url>
cd toric-gen
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
python examples/demo_decode_clean_xz.py
```

If you only want the minimal install

Windows PowerShell
```powershell
git clone <your-repo-url>
cd toric-gen
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python examples/demo_decode_clean_xz.py
```

macOS / Linux
```bash
git clone <your-repo-url>
cd toric-gen
python -m venv .venv
source .venv/bin/activate
pip install -e .
python examples/demo_decode_clean_xz.py
```


## How to use toric-gen

`toric-gen` provides a Stim-compatible toric code memory experiment generator.  
It can generate a quantum circuit, convert the circuit into a detector error model, and decode detection events using PyMatching.

### Basic usage

```python
from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator
import pymatching

gen = ToricCodeStimCleanXZGenerator(
    distance=3,
    rounds=3,
    noise=NoiseModel(
        before_round_data_depolarization=0.001,
        after_clifford_depolarization=0.001,
        before_measure_flip_probability=0.001,
        after_reset_flip_probability=0.001,
    ),
)

circuit = gen.build_memory_experiment(basis="Z")

print(circuit)
```

### Decode with PyMatching

```python
from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator
import pymatching

distance = 3
rounds = 3
p = 0.001
shots = 1000

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
```

### Run the included example

After installation, you can run the example script:

```bash
python examples/demo_decode_clean_xz.py
```

### Main parameters

- `distance`: code distance of the toric code.
- `rounds`: number of syndrome extraction rounds.
- `basis`: memory experiment basis. Use `"X"` or `"Z"`.
- `before_round_data_depolarization`: depolarizing noise applied to data qubits before each round.
- `after_clifford_depolarization`: depolarizing noise applied after Clifford gates.
- `before_measure_flip_probability`: measurement flip probability before measurement.
- `after_reset_flip_probability`: reset flip probability after reset.

### Typical workflow

1. Create a `NoiseModel`.
2. Create a `ToricCodeStimCleanXZGenerator`.
3. Build a memory experiment circuit with `build_memory_experiment`.
4. Convert the circuit to a detector error model.
5. Build a PyMatching decoder from the detector error model.
6. Sample detection events from the Stim circuit.
7. Decode the detection events with PyMatching.
8. Compare the prediction with the observable flips to estimate the logical error rate.