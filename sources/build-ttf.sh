#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"

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
	python3 -m ttfautohint $font $font.fix
	[ -f $font.fix ] && mv $font.fix $font
	gftools fix-hinting $font
	[ -f $font.fix ] && mv $font.fix $font
done


##########################################

rm -rf instance_ufo/ master_ufo/

if [ $UFO_SOURCES = false ]
then
	rm -rf $UFO_DIR
	find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
fi

echo ".
COMPLETE!
."
