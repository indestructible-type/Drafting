#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"

##########################################

echo ".
GENERATING TTF
."
TT_DIR=../fonts/ttf
rm -rf $TT_DIR
mkdir -p $TT_DIR

fontmake -m designspace/$fontName.designspace -i -o ttf --output-dir $TT_DIR
fontmake -m designspace/$fontName_it.designspace -i -o ttf --output-dir $TT_DIR

##########################################

echo ".
POST-PROCESSING TTF
."
ttfs=$(ls $TT_DIR/*.ttf)
for font in $ttfs
do
	gftools fix-dsig --autofix $font
	python3 -m ttfautohint $font $font.fix
	[ -f $font.fix ] && mv $font.fix $font
	gftools fix-hinting $font
	[ -f $font.fix ] && mv $font.fix $font
done


##########################################

rm -rf instance_ufo/ master_ufo/

echo ".
COMPLETE!
."
