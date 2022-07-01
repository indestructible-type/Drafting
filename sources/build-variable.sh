#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"
axes="wght"

##########################################

echo ".
CHECKING FOR SOURCE FILES
."
if [ -e ufo ]
then
    echo ".
USING UFO SOURCE FILES
."
    UFO_SOURCES=true
else
    UFO_SOURCES=false
fi

##########################################

if [ $UFO_SOURCES = false ]
    then
    echo ".
GENERATING SOURCES
."
    SOURCE_DIR=fontforge
    UFO_DIR=ufo
    rm -rf $UFO_DIR
    mkdir -p $UFO_DIR
    sfds=$(ls $SOURCE_DIR/*.sfd)
    for source in $sfds
    do
	base=${source##*/}
	# fontforge -c "fontforge.open('$source').generate('$UFO_DIR/${base%.*}.ufo')"
	python3 misc/sfd2ufo --ufo-kerning $source $UFO_DIR/${base%.*}.ufo
	cp misc/features.fea $UFO_DIR/${base%.*}.ufo/features.fea
    done
fi

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

if [ $UFO_SOURCES = false ]
then
	rm -rf $UFO_DIR
	find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
fi

echo ".
COMPLETE!
."
