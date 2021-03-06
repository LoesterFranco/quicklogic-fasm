import argparse
from pathlib import Path

header = [
    'w4 0x40004c4c 0x00000180',
    'w4 0x40004610 0x00000007',
    'w4 0x40004088 0x0000003f',
    'w4 0x40004044 0x00000007',
    'w4 0x4000404c 0x00000006',
    'w4 0x40004064 0x00000001',
    'w4 0x40004070 0x00000001',
    'w4 0x4000411c 0x00000006',
    'w4 0x40005310 0x1acce551',
    'w4 0x40004054 0x00000001',
    'sleep 100',
    'w4 0x40014000 0x0000bdff',
    'sleep 100',
]

footer = [
    'sleep 100',
    'w4 0x40014000 0x00000000',
    'w4 0x400047f0 0x00000000',
    'sleep 100',
    'w4 0x400047f4 0x00000000',
    'w4 0x40004088 0x00000000',
    'w4 0x40004094 0x00000000',
    'w4 0x400047f8 0x00000090',
    'w4 0x40004040 0x00000295',
    'w4 0x40004048 0x00000001',
    'w4 0x4000404c 0x0000003f',
    'sleep 100',
    'w4 0x40004c4c 0x000009a0',
    'sleep 100',
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts QuickLogic bitstream to JLINK script"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (bitstream)",
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (JLink script)",
    )

    args = parser.parse_args()

    jlinkscript = header

    with open(args.infile, 'rb') as bitstream:
        while True:
            data = bitstream.read(4)
            if not data:
                break
            bitword = int.from_bytes(data, 'little')
            line = 'w4 0x40014ffc, 0x{:08x}'.format(bitword)
            jlinkscript.append(line)

    jlinkscript.extend(footer)

    with open(args.outfile, 'w') as jlink:
        jlink.write('\n'.join(jlinkscript))
