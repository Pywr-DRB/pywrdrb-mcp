# Example: Exploring the River Network

This example shows how to use the pywrdrb-mcp tools to explore the
Delaware River Basin network topology, reservoirs, and node relationships.

## List all nodes

Ask:
> "What nodes are in the Pywr-DRB model?"

The LLM will call `get_node_list()`, which returns nodes grouped by type:
- **Reservoir nodes**: NYC (cannonsville, pepacton, neversink), STARFIT, Lower Basin
- **Major flow nodes**: delMontague, delTrenton, etc.
- **Flood monitoring nodes**: USGS gages downstream of NYC reservoirs

## Get reservoir details

Ask:
> "Tell me about the Cannonsville reservoir"

The LLM will call `get_reservoir_details("cannonsville")`, returning:
- Type: NYC
- Downstream node
- USGS/NHM/NWM gage IDs
- List memberships (NYC list, reservoir list, etc.)

## Trace the network topology

Ask:
> "What's upstream of the Montague node?"

The LLM calls `get_node_topology("delMontague", include_flood_topology=True)`:
```
Upstream nodes: [delLordville, lackawaxen, ...]
Downstream node: delDRCanal
Travel time lag: 0 days
USGS gage: 01438500
Flood monitoring: yes (Montague is a key compliance point)
```

## Use the prompt for a deep dive

Ask:
> "Use the how_to_understand_node prompt for delTrenton"

This invokes the `how_to_understand_node` prompt with `node_name="delTrenton"`,
which guides the LLM through a structured multi-tool investigation:
1. Pull topology via `get_node_topology`
2. Search for parameter references via `search_codebase`
3. Check if it's a reservoir via `get_reservoir_details`
4. Look up available observation data
5. Check applicable operational constraints

## Browse the full network graph (resource)

For a complete picture, the LLM can read the `pywrdrb://topology/network-graph`
resource, which contains the full adjacency data (upstream nodes, downstream
nodes, and travel time lags for every node).
