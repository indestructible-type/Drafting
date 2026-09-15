#!/bin/sh
set -e
#source ../env/bin/activate

fontName="Drafting"
fontName_it="Drafting-Italic"
# Canonical filenames must match the font's postscript family name (no space).
outName="DraftingMono"
outName_it="DraftingMono-Italic"
axes="wght"

##########################################

echo ".
GENERATING VARIABLE
."
VF_DIR=../fonts/variable
rm -rf $VF_DIR
mkdir -p $VF_DIR

fontmake -m designspace/$fontName.designspace -o variable --output-path $VF_DIR/$outName[$axes].ttf
fontmake -m designspace/$fontName_it.designspace -o variable --output-path $VF_DIR/$outName_it[$axes].ttf

##########################################

echo ".
POST-PROCESSING VF
."
vfs=$(ls $VF_DIR/*.ttf)
for font in $vfs
do
	gftools fix-nonhinting $font $font.fix
	mv $font.fix $font
	gftools fix-unwanted-tables --tables MVAR $font
done
rm $VF_DIR/*gasp*

echo ".
GENERATING STAT
."
gftools gen-stat $VF_DIR/$outName[$axes].ttf $VF_DIR/$outName_it[$axes].ttf --inplace

echo ".
SETTING VARIATIONS POSTSCRIPT NAME PREFIX (nameID 25)
."
python3 - "$VF_DIR/$outName[$axes].ttf" "$VF_DIR/$outName_it[$axes].ttf" <<'PYEOF'
import sys
from fontTools.ttLib import TTFont

roman, italic = sys.argv[1], sys.argv[2]

f = TTFont(roman)
f["name"].setName("DraftingMono", 25, 3, 1, 0x409)
f.save(roman)

f = TTFont(italic)
f["name"].setName("DraftingMonoItalic", 25, 3, 1, 0x409)
f.save(italic)
PYEOF

##########################################

find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

echo ".
COMPLETE!
."
