LiteX for ice40 HX8K with SDRAM expansion
====

Quick LiteX project that instantiates a LiteDRAM controller that talks to the Labitat SDRAM expansion for the Lattice HX8K EVB board. It uses the AS4C16M16 SDR SDRAM chip from Alliance.

Ultimo 2019, the project does not synthesize for me without patching LiteDRAM. Yosys fails with an error about conflicting initialization values.

Board files for the expansion available here:

https://github.com/niklasnisbeth/lattice-ice40-hx8kevb-sdram
