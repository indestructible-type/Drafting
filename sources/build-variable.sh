#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"
axes="wght"

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
GENERATING VARIABLE
."
VF_DIR=../fonts/variable
rm -rf $VF_DIR
mkdir -p $VF_DIR

fontmake -m designspace/$fontName.designspace -o variable --output-path $VF_DIR/$fontName[$axes].ttf
fontmake -m designspace/$fontName_it.designspace -o variable --output-path $VF_DIR/$fontName_it[$axes].ttf

##########################################

echo ".
POST-PROCESSING VF
."
vfs=$(ls $VF_DIR/*.ttf)
for font in $vfs
do
	gftools fix-dsig --autofix $font
	gftools fix-nonhinting $font $font.fix
	mv $font.fix $font
	gftools fix-unwanted-tables --tables MVAR $font
done
rm $VF_DIR/*gasp*

##########################################

rm -rf $UFO_DIR

echo ".
COMPLETE!
."
