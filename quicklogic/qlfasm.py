#!/usr/bin/env python3
from fasm_utils import fasm_assembler
from fasm import FasmLine
import math
import argparse
import os
import errno
from pathlib import Path
from fasm_utils.database import Database


class QL732BAssembler(fasm_assembler.FasmAssembler):

    def __init__(self, db):
        '''Class for generating bitstream for QuickLogic's QL732B FPGA.

        Class inherits from fasm_assembler.FasmAssembler class, and implements
        enable_feature method, as well as produce_bitstream method. It contains
        the bitstream generation process for QL732B device.
        :param BANKSTARTBITIDX: contains the bit offset for a given bank
        :param MAXBL: the maximum value for bit line
        :param MAXWL: the maximum value for word line
        :param NUMOFBANLS: the number of config bit banks
        '''
        super().__init__(db)
        self.BANKSTARTBITIDX = [0, 43, 88, 133, 178, 223, 268, 313,
                                673, 628, 583, 538, 493, 448, 403, 358,
                                0, 43, 88, 133, 178, 223, 268, 313,
                                673, 628, 583, 538, 493, 448, 403, 358]
        self.MAXBL = 716
        self.MAXWL = 844

        self.NUMOFBANKS = 32

        self.BANKNUMBITS = math.ceil(self.MAXBL / (self.NUMOFBANKS / 2))

    def enable_feature(self, fasmline: FasmLine):
        feature = self.db.get_feature(fasmline.set_feature.feature)

        if feature is None:
            raise fasm_assembler.FasmLookupError(
                'FASM line "{}" tries to enable unavailable feature'
                .format(fasmline)
            )

        for coord in feature.coords:
            if coord.isset:
                self.set_config_bit((coord.x, coord.y), fasmline)
            else:
                self.clear_config_bit((coord.x, coord.y), fasmline)

    def produce_bitstream(self, outfilepath: str, verbose=False):

        def get_value_for_coord(bitidx, wlidx, wlshift):
            if (bitidx, wlidx + wlshift) not in self.configbits:
                return -1
            else:
                return self.configbits[(bitidx, wlidx + wlshift)]

        bitstream = []

        for wlidx in range(self.MAXWL // 2 - 1, -1, -1):
            for bitnum in range(0, self.BANKNUMBITS):
                currval = 0
                for banknum in range(self.NUMOFBANKS - 1, -1, -1):
                    val = 1
                    bitidx = 0
                    if banknum in (0, 8, 16, 24):
                        if bitnum in (0, 1):
                            val = 0
                            continue
                        else:
                            bitidx = self.BANKSTARTBITIDX[banknum] + bitnum - 2
                    else:
                        bitidx = self.BANKSTARTBITIDX[banknum] + bitnum

                    if banknum >= self.NUMOFBANKS // 2:
                        val = get_value_for_coord(bitidx, wlidx, self.MAXWL // 2)
                    else:
                        val = get_value_for_coord(bitidx, wlidx, 0)

                    if val == -1:
                        val = 0

                    if val == 1:
                        currval = currval | (1 << banknum)
                if verbose: print('{}_{}:  {:02X}'.format(wlidx, bitnum, currval))
                bitstream.append(currval)

        if verbose: print('Size of bitstream:  {}B'.format(len(bitstream) * 4))

        with open(outfilepath, 'w+b') as output:
            for batch in bitstream:
                output.write(batch.to_bytes(4, 'little'))


    def read_bitstream(self, bitfilepath):
        bitstream = []
        with open(bitfilepath, 'rb') as input:
            while True:
                bytes = input.read(4)
                if not bytes:
                    break;
                bitstream.append(int.from_bytes(bytes, 'little'))

        def set_bit(bitidx, wlidx, wlshift, value):
            coord = (bitidx, wlidx + wlshift)
            if value == 1:
                self.set_config_bit(coord, None)
            else:
                self.clear_config_bit(coord, None)

        val = iter(bitstream)
        for wlidx in reversed(range(self.MAXWL // 2)):
            for bitnum in range(self.BANKNUMBITS):
                currval = next(val)
                for banknum in reversed(range(self.NUMOFBANKS)):
                    bit = (currval >> banknum) & 1
                    bitidx = 0

                    if banknum in (0, 8, 16, 24):
                        if bitnum in (0, 1):
                            continue
                        else:
                            bitidx = self.BANKSTARTBITIDX[banknum] + bitnum - 2
                    else:
                        bitidx = self.BANKSTARTBITIDX[banknum] + bitnum

                    if banknum >= self.NUMOFBANKS // 2:
                        set_bit(bitidx, wlidx, self.MAXWL // 2, bit)
                    else:
                        set_bit(bitidx, wlidx, 0, bit)


    def disassemble(self, outfilepath: str, verbose=False):
        features = []
        for feature in self.db:
            for bit in feature.coords:
                coord = (bit.x, bit.y)
                if coord not in self.configbits \
                        or bool(self.configbits[coord]) != bit.isset:
                    break
            else:
                features.append(feature.signature)
                if verbose:
                    print(f'{feature.signature}')

        with open(outfilepath, 'w') as fasm_file:
            print(*features, sep='\n', file=fasm_file)


def main():

    DB_FILES_DIR = Path(__file__).resolve().parent/'../ql732b/db/'

    parser = argparse.ArgumentParser(
        description="Converts FASM file to the bitstream or the other way around"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (FASM, or bitstream when disassembling)"
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (bitstream, or FASM when disassembling)"
    )

    parser.add_argument(
        "-d", "--disassemble",
        action="store_true",
        help="Disasseble bitstream"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Adds some verbose messages during bitstream production"
    )

    args = parser.parse_args()

    if not args.infile.exists:
        print("The input file does not exist")
        exit(errno.ENOENT)

    if not args.outfile.parent.is_dir():
        print("The path to file is not a valid directory")
        exit(errno.ENOTDIR)

    db = Database(DB_FILES_DIR)
    db.add_table('macro', DB_FILES_DIR / 'macro.db')
    db.add_table('colclk', DB_FILES_DIR / 'colclk.db')
    db.add_table('testmacro', DB_FILES_DIR / 'testmacro.db')

    assembler = QL732BAssembler(db)

    if not args.disassemble:
        assembler.parse_fasm_filename(args.infile)
        assembler.produce_bitstream(args.outfile, verbose=args.verbose)
    else:
        assembler.read_bitstream(args.infile)
        assembler.disassemble(args.outfile, verbose=args.verbose)

if __name__ == "__main__":
    main()
