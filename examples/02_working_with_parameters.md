# Example: Working with Parameters

This example shows how to discover, inspect, and understand the custom
Pywr parameter classes that drive the Pywr-DRB simulation.

## List all parameter classes

Ask:
> "What parameter classes exist in Pywr-DRB?"

The LLM calls `get_parameter_list()`, returning classes grouped by module:
```
parameters/ffmp.py:
  - FfmpNycRunningAvgParameter (base: Parameter)
  - VolBalanceNYCDownstreamMRF_step1 (base: Parameter)
  ...

parameters/starfit.py:
  - STARFITReservoirRelease (base: Parameter)
  ...

parameters/general.py:
  - LaggedReservoirRelease (base: Parameter)
  ...
```

## Inspect a specific class

Ask:
> "Show me the STARFITReservoirRelease class details"

The LLM calls `get_parameter_class_info("STARFITReservoirRelease")`:
- Full docstring
- `__init__` signature with parameter types
- All method names and signatures
- Base classes
- Source file location

## Search for how a parameter is used

Ask:
> "Where is STARFITReservoirRelease referenced in the codebase?"

The LLM calls `search_codebase("STARFITReservoirRelease")`, finding:
- The class definition in `parameters/starfit.py`
- Where it's instantiated in `model_builder.py`
- Any test references

## Read the source code

Ask:
> "Show me the value() method of STARFITReservoirRelease"

The LLM calls `get_file_contents("parameters/starfit.py", start_line=X, end_line=Y)`
to show exactly how the parameter computes its value each timestep.

## Add a new parameter (guided prompt)

Ask:
> "Use the how_to_add_parameter prompt"

This invokes a structured walkthrough covering:
1. File placement in `pywrdrb/parameters/`
2. Inheriting from `pywr.parameters.Parameter`
3. Implementing `setup()`, `value()`, `after()`, `reset()`, `load()`
4. Cross-parameter references and ensemble support
5. Registration and integration with `model_builder.py`
