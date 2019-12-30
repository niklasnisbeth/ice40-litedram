#!/usr/bin/env python3
# This variable defines all the external programs that this module
# relies on.  lxbuildenv reads this variable in order to ensure
# the build will finish without exiting due to missing third-party
# programs.
#LX_DEPENDENCIES = ["riscv", "yosys", "icestorm"]
LX_DEPENDENCIES = ["yosys", "icestorm"]

# Import lxbuildenv to integrate the deps/ directory
import lxbuildenv

# Disable pylint's E1101, which breaks completely on migen
#pylint:disable=E1101

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.lattice.programmer import IceStormProgrammer
from litex.build.lattice.platform import LatticePlatform
from litex.build.generic_platform import *

from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import AS4C16M16
from litedram.phy import GENSDRPHY

from litex.soc.cores.uart import UARTWishboneBridge 

from gateware import spi_flash

_io = [
    # ("user_led", 0, Pins("B5"), IOStandard("LVCMOS33")),
    # ("user_led", 1, Pins("B4"), IOStandard("LVCMOS33")),
    # ("user_led", 2, Pins("A2"), IOStandard("LVCMOS33")),
    # ("user_led", 3, Pins("A1"), IOStandard("LVCMOS33")),
    # ("user_led", 4, Pins("C5"), IOStandard("LVCMOS33")),
    # ("user_led", 5, Pins("C4"), IOStandard("LVCMOS33")),
    # ("user_led", 6, Pins("B3"), IOStandard("LVCMOS33")),
    # ("user_led", 7, Pins("C3"), IOStandard("LVCMOS33")),

    ("serial", 0,
        Subsignal("rx", Pins("B10")),
        Subsignal("tx", Pins("B12"), Misc("PULLUP")),
        Subsignal("rts", Pins("B13"), Misc("PULLUP")),
        Subsignal("cts", Pins("A15"), Misc("PULLUP")),
        Subsignal("dtr", Pins("A16"), Misc("PULLUP")),
        Subsignal("dsr", Pins("B14"), Misc("PULLUP")),
        Subsignal("dcd", Pins("B15"), Misc("PULLUP")),
        IOStandard("LVCMOS33"),
    ),

    ("spiflash", 0,
        Subsignal("cs_n", Pins("R12"), IOStandard("LVCMOS33")),
        Subsignal("clk", Pins("R11"), IOStandard("LVCMOS33")),
        Subsignal("mosi", Pins("P12"), IOStandard("LVCMOS33")),
        Subsignal("miso", Pins("P11"), IOStandard("LVCMOS33")),
    ),

    ("sdram_clock", 0, Pins("P10"), IOStandard("LVCMOS33")),
    ("sdram", 0,
        Subsignal("a", Pins("B4 B3 A2 A1 T6 R6 T7 R9 T9 P9 C3 P8 R10")),
        Subsignal("dq", Pins("B11 A10 C9 A9 B9 B8 A7 B7 M11 N10 P13 N12 T14 T13 T16 T15")),
        Subsignal("we_n", Pins("A6")),
        Subsignal("ras_n", Pins("B6")),
        Subsignal("cas_n", Pins("C6")),
        Subsignal("cs_n", Pins("C5")),
        Subsignal("cke", Pins("T10")),
        Subsignal("ba", Pins("C4 B5")),
        Subsignal("dm", Pins("T11 C7")),
        IOStandard("LVCMOS33"),
    ),

    ("clk12", 0, Pins("J3"), IOStandard("LVCMOS33")),
]

class Platform(LatticePlatform):
    default_clk_name = "clk12"
    default_clk_period = 83.333

    gateware_size = 0x28000

    # FIXME: Create a "spi flash module" object in the same way we have SDRAM
    spiflash_model = "n25q32"
    spiflash_read_dummy_bits = 8
    spiflash_clock_div = 2
    spiflash_total_size = int((32/8)*1024*1024) # 32Mbit
    spiflash_page_size = 256
    spiflash_sector_size = 0x10000

    def __init__(self):
        LatticePlatform.__init__(self, "ice40-hx8k-ct256", _io, toolchain="icestorm")

    def create_programmer(self):
        return IcestormProgrammer()

class _CRG(Module):
    def __init__(self, platform):
        clk12 = platform.request("clk12")

        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        self.cd_sys.clk.attr.add("keep")
        self.cd_sys_ps.clk.attr.add("keep")

        self.reset = Signal()

        # FIXME: Use PLL, increase system clock to 32 MHz, pending nextpnr
        # fixes.
        self.comb += self.cd_sys.clk.eq(clk12)
        self.comb += self.cd_sys_ps.clk.eq(clk12)

        self.comb += platform.request("sdram_clock").eq(self.cd_sys_ps.clk)

        # POR reset logic- POR generated from sys clk, POR logic feeds sys clk
        # reset.
        self.clock_domains.cd_por = ClockDomain()
        reset_delay = Signal(12, reset=4095)
        self.comb += [
            self.cd_por.clk.eq(self.cd_sys.clk),
            self.cd_sys.rst.eq(reset_delay != 0)
        ]
        self.sync.por += \
            If(reset_delay != 0,
                reset_delay.eq(reset_delay - 1)
            )
        self.specials += AsyncResetSynchronizer(self.cd_por, self.reset)

def csr_map_update(csr_map, csr_peripherals):
    csr_map.update(dict((n, v)
        for v, n in enumerate(csr_peripherals, start=(max(csr_map.values()) + 1) if csr_map else 0)))

class BaseSoC(SoCSDRAM):
    csr_peripherals = (
        "spiflash",
        "sdrphy",
        "cas",
    )
    csr_map_update(SoCSDRAM.csr_map, csr_peripherals)

    mem_map = {
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }
    mem_map.update(SoCSDRAM.mem_map)

    def __init__(self, platform, **kwargs):
        if 'integrated_rom_size' not in kwargs:
            kwargs['integrated_rom_size']=0
        if 'integrated_sram_size' not in kwargs:
            kwargs['integrated_sram_size']=0

        print(kwargs)

        clk_freq = int(12e6)

        kwargs['uart_stub'] = True

        kwargs['cpu_reset_address']=self.mem_map["spiflash"]+platform.gateware_size
        SoCSDRAM.__init__(self, platform, clk_freq, **kwargs)

        self.submodules.crg = _CRG(platform)
        self.platform.add_period_constraint(self.crg.cd_sys.clk, 1e9/clk_freq)

        # Control and Status
        # self.submodules.cas = cas.ControlAndStatus(platform, clk_freq)

        # SPI flash peripheral
        self.submodules.spiflash = spi_flash.SpiFlashSingle(
            platform.request("spiflash"),
            dummy=platform.spiflash_read_dummy_bits,
            div=platform.spiflash_clock_div)
        self.add_constant("SPIFLASH_PAGE_SIZE", platform.spiflash_page_size)
        self.add_constant("SPIFLASH_SECTOR_SIZE", platform.spiflash_sector_size)
        self.register_mem("spiflash", self.mem_map["spiflash"],
            self.spiflash.bus, size=platform.spiflash_total_size)

        # SDRAM
        sdram_module = AS4C16M16(clk_freq, "1:1")
        self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"))
        self.register_sdram(self.sdrphy,
                sdram_module.geom_settings,
                sdram_module.timing_settings)

        bios_size = 0x8000
        self.add_constant("ROM_DISABLE", 1)
        self.add_memory_region(
            "rom", kwargs['cpu_reset_address'], bios_size,
            type="cached+linker")
        self.flash_boot_address = self.mem_map["spiflash"]+platform.gateware_size+bios_size
        self.add_constant("FLASH_BOOT_ADDRESS", self.flash_boot_address)

        self.submodules.uart_bridge = UARTWishboneBridge(platform.request("serial"), clk_freq, baudrate=115200)
        self.add_wb_master(self.uart_bridge.wishbone)
        #self.register_mem("vexriscv_debug", 0xf00f0000, self.cpu.debug_bus, 0x100)

        # We don't have a DRAM, so use the remaining SPI flash for user
        # program.
        self.add_memory_region("user_flash",
            self.flash_boot_address,
            # Leave a grace area- possible one-by-off bug in add_memory_region?
            # Possible fix: addr < origin + length - 1
            platform.spiflash_total_size - (self.flash_boot_address - self.mem_map["spiflash"]) - 0x100,
            type="cached+linker")

        # Disable final deep-sleep power down so firmware words are loaded
        # onto softcore's address bus.
        # platform.toolchain.build_template[3] = "icepack -s {build_name}.txt {build_name}.bin"
        # platform.toolchain.nextpnr_build_template[2] = "icepack -s {build_name}.txt {build_name}.bin"


def main():
    cpu_type = None
    cpu_variant = None

    platform = Platform()
    print(platform)
    soc = BaseSoC(platform, cpu_type=cpu_type, cpu_variant=cpu_variant)
    builder = Builder(soc, output_dir="build", csr_csv="test/csr.csv")
    vns = builder.build()
    soc.do_exit(vns)

if __name__ == "__main__":
    main()
