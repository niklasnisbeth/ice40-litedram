LiteX for ice40 HX8K with SDRAM expansion
====

Quick LiteX project that instantiates a LiteDRAM controller that talks to the Labitat SDRAM expansion for the Lattice HX8K EVB board. It uses the AS4C16M16 SDR SDRAM chip from Alliance.

Ultimo 2019, the project does not synthesize for me without patching LiteDRAM with the included patch. Yosys fails with an error about conflicting initialization values. See below for more information.

Board files for the expansion available here:

https://github.com/niklasnisbeth/lattice-ice40-hx8kevb-sdram

Error
----

Yosys gives a strange synthesize error for me:

```
$ python3 ice40hx8k_litedram_nn.py 
lxbuildenv: v2019.8.19.1 (run ice40hx8k_litedram_nn.py --lx-help for help)
<__main__.Platform object at 0x7fb78610b7f0>
{'cpu_type': None, 'cpu_variant': None, 'integrated_rom_size': 0, 'integrated_sram_size': 0}
ERROR: Conflicting init values for signal 1'1 (\soc_sdram_master_p0_act_n = 1'1, \soc_sdram_choose_req_want_activates = 1'0).
Traceback (most recent call last):
  File "ice40hx8k_litedram_nn.py", line 224, in <module>
    main()
  File "ice40hx8k_litedram_nn.py", line 220, in main
    vns = builder.build()
  File "/home/niklas/hack/litex/notbuildenv/deps/litex/litex/soc/integration/builder.py", line 185, in build
    toolchain_path=toolchain_path, **kwargs)
  File "/home/niklas/hack/litex/notbuildenv/deps/litex/litex/soc/integration/soc_core.py", line 452, in build
    return self.platform.build(self, *args, **kwargs)
  File "/home/niklas/hack/litex/notbuildenv/deps/litex/litex/build/lattice/platform.py", line 34, in build
    return self.toolchain.build(self, *args, **kwargs)
  File "/home/niklas/hack/litex/notbuildenv/deps/litex/litex/build/lattice/icestorm.py", line 189, in build
    _run_script(script)
  File "/home/niklas/hack/litex/notbuildenv/deps/litex/litex/build/lattice/icestorm.py", line 121, in _run_script
    raise OSError("Subprocess failed")
OSError: Subprocess failed
```

The Minispartan6 example uses mostly the same chip with the same setup, and synthesizes fine for me with ISE.

I'm using Yosys 0.9+932 (git sha1 9e6632c4, clang 9.0.0 -fPIC -Os), self-compiled.

```
$ git submodule 
 8dae0c0c7fe5f9476214bc6e63d91884781378b2 deps/litedram (heads/master)
 ffa7ca8f0b44b0e560c58e6f9e72c64d78669e64 deps/litex (heads/master)
 48476be9e2fd6d4bb5751c1aa786a30b62197eed deps/litex_boards (heads/master)
 bee558c8cb04720fb695f63d3597f2aefa55e8e4 deps/migen (0.6.dev-316-gbee558c)
```
