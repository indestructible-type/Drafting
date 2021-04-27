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
		gftools fix-dsig --autofix $font
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
rm -rf $UFO_DIR

echo ".
COMPLETE!
."
