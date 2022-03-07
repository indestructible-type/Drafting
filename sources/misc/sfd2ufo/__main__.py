import argparse

from ufoLib2 import Font
from parser import SFDParser


def main():
    parser = argparse.ArgumentParser(
        prog="sfd2ufo", description="Convert FontForge fonts to UFO."
    )
    parser.add_argument("sfdfile", metavar="FILE", help="input font to process")
    parser.add_argument("ufofile", metavar="FILE", help="output font to write")
    parser.add_argument(
        "--ufo-anchors",
        action="store_true",
        help="output UFO anchors instead of writing them to feature file",
    )
    parser.add_argument(
        "--ufo-kerning",
        action="store_true",
        help="output UFO kerning instead of writing it to feature file",
    )
    parser.add_argument(
        "--minimal", action="store_true", help="output enough UFO to build the font"
    )

    args = parser.parse_args()

    font = Font()
    parser = SFDParser(
        args.sfdfile,
        font,
        args.ufo_anchors,
        args.ufo_kerning,
        args.minimal,
    )
    parser.parse()

    font.save(args.ufofile, overwrite=True, validate=False)


if __name__ == "__main__":
    main()
