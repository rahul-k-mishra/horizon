# Study 1's agents, copied for HORIZON

Files copied byte for byte from the author's earlier study (the repository of study 1) at its tag prereg-v1.1. Nothing here is edited; .gitattributes keeps git from rewriting line endings. scripts/automation/agents_gvgai.py checks the blob hash of every file under scripts/ before each run and refuses to run on a difference; docs/DESIGN_gvgai_draft.md, Section 4, lists the hashes.

- scripts/: the agents N (g_nav.py on g_agent.py) and R (g_agent.py), their modules g_motion.py and g_control_probe.py, g_nav_run.py (for its MODES) and g_census_table.py (the sixth file of study 1's frozen set), the frame contract and shim env_frame.py, and I1's adapters e1_rudakov_adapter.py and i1_suite_adapter.py.
- external/rudakov_just_explore/: the code of I1 (Rudakov, Shock and Cowley, arXiv:2512.24156), MIT licence, with its LICENSE and PROVENANCE.md as study 1 vendored them; only the six files the adapter loads.
