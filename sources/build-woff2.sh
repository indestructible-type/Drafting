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

if [ -f "../fonts/ttf/DraftingMono-Regular.ttf" ]; then
	TT_DIR=../fonts/ttf
	echo ".
	GENERATING WEBFONTS
	."
	ttfs=$(ls $TT_DIR/*.ttf)
	for font in $ttfs
	do
		fonttools ttLib.woff2 compress $font
	done
else
	TT_DIR=instance_ttf
	echo ".
	GENERATING TTF SOURCES
	."
	fontmake -m designspace/$fontName.designspace -i -o ttf --output-dir $TT_DIR
	fontmake -m designspace/$fontName_it.designspace -i -o ttf --output-dir $TT_DIR
	ttfs=$(ls $TT_DIR/*.ttf)
	for font in $ttfs
	do
		python3 -m ttfautohint $font $font.fix
		[ -f $font.fix ] && mv $font.fix $font
		gftools fix-hinting $font
		[ -f $font.fix ] && mv $font.fix $font
		fonttools ttLib.woff2 compress $font
	done
fi

echo ".
MOVE WEBFONTS TO OWN DIRECTORY
."
WEB_DIR=../fonts/woff2
rm -rf $WEB_DIR
mkdir -p $WEB_DIR

webfonts=$(ls $TT_DIR/*.woff2)
for font in $webfonts
do
  mv $font $WEB_DIR
done


##########################################

rm -rf instance_ufo/ master_ufo/ instance_ttf/

if [ $UFO_SOURCES = false ]
then
	rm -rf $UFO_DIR
	find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
fi

echo ".
COMPLETE!
."
