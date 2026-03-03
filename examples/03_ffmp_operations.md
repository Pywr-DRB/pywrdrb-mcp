# Example: FFMP Operations and NYC Reservoir Rules

This example shows how to query and understand the Flexible Flow Management
Program (FFMP) rules that govern NYC reservoir operations in Pywr-DRB.

## Get an overview of FFMP data

Ask:
> "Show me the FFMP operational data"

The LLM calls `get_ffmp_data()` (default category="all"), returning a summary table:

| Category | Description |
|---|---|
| `constants` | MRF baselines, delivery limits, flood max releases |
| `storage_zones` | Daily storage zone threshold profiles (6 drought levels x 366 days) |
| `mrf_daily` | Daily MRF release factors per reservoir and drought level |
| `mrf_monthly` | Monthly MRF factors for Montague/Trenton |
| `lower_basin` | DRBC lower basin reservoir policies |

## Drill into a specific category

Ask:
> "Show me the FFMP storage zone profiles"

The LLM calls `get_ffmp_data("storage_zones")`, returning monthly-sampled
threshold values for each drought level (L1b through L5). Values are storage
fractions (0-1) that define the boundaries between drought levels.

## Understand the full FFMP rule set (resource)

Ask:
> "Explain the FFMP rules in detail"

The LLM reads the `pywrdrb://domain/ffmp-rules-summary` resource, which is
a hand-written guide covering:
- Drought level definitions and transitions
- NYC reservoir release rules
- Montague/Trenton MRF targets
- Delivery constraints (NYC 800 MGD, NJ 100 MGD)
- Flood operations

## Modify FFMP rules for a scenario (guided prompt)

Ask:
> "Use the how_to_modify_ffmp_rules prompt"

This walks through modifying FFMP parameters via `NYCOperationsConfig`:
1. Create a config from defaults
2. Update storage zones, MRF targets, delivery constraints, or flood limits
3. Pass the config to `ModelBuilder`
4. Run the scenario

## Inspect the NYCOperationsConfig class

Ask:
> "Show me the NYCOperationsConfig class"

The LLM calls `get_parameter_class_info("NYCOperationsConfig")` to see
all available configuration methods and their signatures.
