[![Drafting Mono](documentation/DraftingMono.svg)](https://indestructibletype.com/Drafting)

Drafting Mono is an original monospaced font by indestructible type*

it is inspired by typewriters. This is version 1.2

Drafting Mono is designed and maintained by [Owen Earl](https://ewonrael.github.io/), who is the creator of the font foundry [indestructible type*](http://indestructibletype.com).

About
-----
Monospaced fonts are often used during the production stage of projects. They are used by programmers while coding, and film crews while filming. They resemble the rhythm of typewriters, which are monospaced due to technical limitations, and permeate our predigital visual landscape.

Drafting Mono aims to capture this "still-in-the-works" spirit, with something neutral and timeless that is also personal and anachronistic. A seemingly self-contradictory desire, it takes heavy inspiration from typewriters, aiming to capture the spirit and logic of typewritten alphabets, rather than mimic the appearance literally. [Read more about it here!](https://indestructibletype.com/Drafting/)

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
Drafting Mono is built with Google Fonts' pipeline, [gftools builder](https://github.com/googlefonts/gftools). Install the required software listed in "requirements.txt", then run:

```
cd sources
./build.sh
```

This builds everything into the "fonts" folder: variable fonts, static TTF and OTF, woff2 webfonts, and the Drafting Mono SC small-caps family.

Contributing
---------------
Drafting Mono's sources are [UFO](https://unifiedfontobject.org) files, found in "sources/ufo", along with designspace files that describe how the masters interpolate. UFO is an open, editor-agnostic format, so you can contribute using any UFO-compatible font editor.

Contact
-------
If you have questions or want to help out, send me and email at owen@indestructibletype.com
