[![Drafting* Mono](documentation/DraftingMono.svg)](https://indestructibletype.com/Drafting)

Drafting* Mono is an original monospaced font by indestructible type*

it is inspired by typewriters. This is version 1.2

Drafting* Mono is designed and maintained by [Owen Earl](https://ewonrael.github.io/), who is the creator of the font foundry [indestructible type*](http://indestructibletype.com).

About
-----
Monospaced fonts are often used during the production stage of projects. They are used by programmers while coding, and film crews while filming. They resemble the rhythm of typewriters, which are monospaced due to technical limitations, and permeate our predigital visual landscape.

Drafting* Mono aims to capture this "still-in-the-works" spirit, with something neutral and timeless that is also personal and anachronistic. A seemingly self-contradictory desire, it takes heavy inspiration from typewriters, aiming to capture the spirit and logic of typewritten alphabets, rather than mimic the appearance literally. [Read more about it here!](https://indestructibletype.com/Drafting/)

Changelog
---------
<b>1.0</b>
initial release<br>
<b>1.1</b>
added small caps & light weights<br>
<b>1.2</b>
fixed smallcaps bold placement in italics; updated metadata for Google Fonts; added glyphs for terminal/CLI symbols

Features
--------
- Serifs that make room for their neighbours (`calt`)
- Typewriter-style 0 and 1 (`ss02`)
- Sans serif b and h (`ss01`)
- Small caps (`smcp`, `c2sc`)
- Superscript numbers, ©, ® and ℗ (`sups`)
- Subscript numbers (`subs`)

Building
--------
Drafting* Mono is built with [fontmake](https://github.com/googlefonts/fontmake) from the UFO sources. Install the required software listed in "requirements.txt", then run the build script for the output you want:

```
cd sources
./build-ttf.sh       # static TTFs into ../fonts/ttf
./build-otf.sh       # static OTFs into ../fonts/otf
./build-variable.sh  # variable fonts into ../fonts/variable
./build-woff2.sh     # woff2 webfonts into ../fonts/woff2 (from the static TTFs)
```

Contributing
---------------
Drafting* Mono's sources are [UFO](https://unifiedfontobject.org) files, found in "sources/ufo", along with designspace files that describe how the masters interpolate. UFO is an open, editor-agnostic format, so you can contribute using any UFO-compatible font editor.

Contact
-------
If you have questions or want to help out, send me and email at owen@indestructibletype.com
