if grep -q 'Drafting\*' "../UFO/Drafting-Regular.ufo/fontinfo.plist"; then
  echo "Drafting* Mono to Drafting Mono"

  sed -i 's/Drafting\*/Drafting/g' ../UFO/Drafting-Regular.ufo/fontinfo.plist
  sed -i 's/Drafting\*/Drafting/g' ../UFO/Drafting-Italic.ufo/fontinfo.plist
  sed -i 's/Drafting\*/Drafting/g' ../designspace/Drafting.designspace
  sed -i 's/Drafting\*/Drafting/g' ../designspace/Drafting-Italic.designspace

else
  echo "Drafting Mono to Drafting* Mono"

  sed -i 's/Drafting Mono/Drafting* Mono/g' ../UFO/Drafting-Regular.ufo/fontinfo.plist
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../UFO/Drafting-Italic.ufo/fontinfo.plist
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../designspace/Drafting.designspace
  sed -i 's/Drafting Mono/Drafting* Mono/g' ../designspace/Drafting-Italic.designspace
  
fi
