# Provenance: rudakov_just_explore

Source: https://github.com/dolphin-in-a-coma/arc-agi-3-just-explore
commit: c2d98318ecca38c8ee9fb49b5af159e51770bad7
Commit date: 2026-01-07 15:04:54 +0200 ("Fix removed formatting in README"); latest commit on the
default branch when cloned on 2026-09-25.
Paper: E. Rudakov, J. Shock, B. U. Cowley, "Graph-Based Exploration for ARC-AGI-3 Interactive
Reasoning Tasks", arXiv:2512.24156 (2025).

Vendored as plain files (the clone's .git directory removed) so the exact code is in this
repository. No file in this directory has been edited. external/.gitattributes disables line-ending
conversion so the files stay byte-identical to the commit. SHA-256 of the files the E1 adapter
(scripts/e1_rudakov_adapter.py) loads:

    99adfdd811f62ba230c2d48968d911f76b379d4ca38a5698214fa057085c4364  agents/heuristic_agent.py
    b844aa931a2b3fc23d9dc45e0158ec76ac89e5ac617893b18d6d07482b27bdfc  graph_explorer.py
    0cfdc0e6bf3745c694c0c96bb62294ab14dc8aaecc4137b6fed1d63e298ed45e  agents/agent.py
    a5d32c98b6e1f7db66da92f248a3e89e10be2e88a46d0181543c16ece9d2c616  agents/structs.py
    6bc15cbed0030e79b66519e090fbbd2079c9c26170d7102bc5b1aad6e34d712e  agents/swarm.py
    e9fa5a36a14fc9d57ec2e37a97b5a8a9872543ef351b235a8b1ed904579a33a9  agents/tracing.py
    e3bb22cbe67180ee8cf3a207faaada79d836c8a16e4180310ea1a34616ffef9a  agents/recorder.py

Licence: MIT (permits use, copying, modification, publication; condition: keep the copyright and
permission notice). Reuse and modification are permitted, so E1 admissibility A2 is met. Full text
of LICENSE at that commit:

```
MIT License

Copyright (c) 2025 Evgenii Rudakov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Anonymity note: the files contain the original authors' names (their copyright line, README,
citation). They are third-party authors, not the authors of this study; the notice must be kept
under the MIT licence.
