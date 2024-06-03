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
UFO_DIR=ufo
rm -rf $UFO_DIR
mkdir -p $UFO_DIR
sfds=$(ls $SOURCE_DIR/*.sfd)
for source in $sfds
do
	base=${source##*/}
#	sfd2ufo $source $UFO_DIR/${base%.*}.ufo
	python3 misc/sfd2ufo --ufo-kerning $source $UFO_DIR/${base%.*}.ufo
	cp misc/features.fea $UFO_DIR/${base%.*}.ufo/features.fea
done

##########################################

find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

echo ".
COMPLETE!
."
