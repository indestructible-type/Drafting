#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"

##########################################

echo ".
GENERATING SOURCES
."
SOURCE_DIR=fontforge
UFO_DIR=UFO
rm -rf $UFO_DIR
mkdir -p $UFO_DIR
sfds=$(ls $SOURCE_DIR/*.sfd)
for source in $sfds
do
	base=${source##*/}
#	sfd2ufo $source $UFO_DIR/${base%.*}.ufo
	fontforge -c "fontforge.open('$source').generate('$UFO_DIR/${base%.*}.ufo')"
done

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
rm -rf $UFO_DIR

echo ".
COMPLETE!
."
