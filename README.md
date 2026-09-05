# qec-gen

`qec-gen` provides shared noise, decoding, and simulation tools for quantum
error-correcting code experiments built with Stim and PyMatching.

The Toric and nine-qubit Peter Shor memory experiments are implemented. Bacon
Shor has a package boundary that shares the same `NoiseModel`; its circuit
generator is the next implementation to add.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
```

## Toric memory experiment

```python
from qec_gen import (
    NoiseModel,
    ToricCodeStimCleanXZGenerator,
    decode_memory_experiment,
)

noise = NoiseModel(
    before_round_data_depolarization=0.001,
    after_clifford_depolarization=0.001,
    before_measure_flip_probability=0.001,
    after_reset_flip_probability=0.001,
)
generator = ToricCodeStimCleanXZGenerator(
    distance=3,
    rounds=3,
    noise=noise,
)
circuit = generator.build_memory_experiment(basis="Z")
result = decode_memory_experiment(circuit, shots=10_000)

print(result.logical_error_rate)
```

## Package layout

```text
src/qec_gen/
|-- noise.py
|-- decoder.py
|-- simulation.py
|-- toric/
|   |-- layout.py
|   `-- generator.py
|-- peter_shor/
|   `-- generator.py
`-- bacon_shor/
    `-- generator.py
```

Run the current example with:

```powershell
python examples/demo_toric.py
```

## Peter Shor memory experiment

```python
from qec_gen import NoiseModel, PeterShorCodeGenerator, decode_memory_experiment

circuit = PeterShorCodeGenerator(
    rounds=3,
    noise=NoiseModel(before_round_data_depolarization=0.001),
).build_memory_experiment(basis="Z")
result = decode_memory_experiment(circuit, shots=10_000)
```
