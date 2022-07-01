if grep -q 'Drafting\*' "../designspace/Drafting.designspace"; then
  echo "Drafting* Mono to Drafting Mono"

  sed -i 's/Drafting\*/Drafting/g' ../ufo/Drafting-Regular.ufo/fontinfo.plist
  sed -i 's/Drafting\*/Drafting/g' ../ufo/Drafting-Italic.ufo/fontinfo.plist
  sed -i 's/Drafting\*/Drafting/g' ../designspace/Drafting.designspace
  sed -i 's/Drafting\*/Drafting/g' ../designspace/Drafting-Italic.designspace

else
  echo "Drafting Mono to Drafting* Mono"

  sed -i 's/Drafting Mono/Drafting* Mono/g' ../ufo/Drafting-Regular.ufo/fontinfo.plist
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../ufo/Drafting-Italic.ufo/fontinfo.plist
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../designspace/Drafting.designspace
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../designspace/Drafting-Italic.designspace
  
fi
