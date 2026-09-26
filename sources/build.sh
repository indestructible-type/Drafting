#!/bin/bash
set -e

rm -rf designspace/instance_ufos
gftools builder config.yaml

for font in ../fonts/ttf/*.ttf ../fonts/otf/*.otf ../fonts/woff2/*.woff2
do
	[[ $font == *"["* ]] && continue
	gftools fix-isfixedpitch --fonts "$font"
	[ -f "$font.fix" ] && mv "$font.fix" "$font"
done
