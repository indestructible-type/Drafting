#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"

##########################################

echo ".
GENERATING OTF
."
TT_DIR=../fonts/otf
rm -rf $TT_DIR
mkdir -p $TT_DIR

fontmake -m designspace/$fontName.designspace -i -o otf --output-dir $TT_DIR
fontmake -m designspace/$fontName_it.designspace -i -o otf --output-dir $TT_DIR

##########################################

echo ".
POST-PROCESSING OTF
."
otfs=$(ls $TT_DIR/*.otf)
for font in $otfs
do
	gftools fix-dsig --autofix $font
	gftools fix-hinting $font
	[ -f $font.fix ] && mv $font.fix $font
done


##########################################

rm -rf instance_ufo/ master_ufo/

echo ".
COMPLETE!
."
