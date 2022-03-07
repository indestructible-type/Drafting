import codecs
import math
import os
import re

from datetime import datetime
from fontTools.misc.fixedTools import otRound

from utils import SFDReadUTF7


QUOTED_RE = re.compile('(".*?")')
NUMBER_RE = re.compile("(-?\d*\.*\d+)")
LAYER_RE = re.compile("(.)\s+(.)\s+" + QUOTED_RE.pattern + "(?:\s+.)?")
GLYPH_SEGMENT_RE = re.compile("(\s[lmc]\s)")
KERNS_RE = re.compile(
    NUMBER_RE.pattern + "\s+" + NUMBER_RE.pattern + "\s+" + QUOTED_RE.pattern
)
KERNCLASS_RE = re.compile(
    NUMBER_RE.pattern + "(\+?)" + "\s+" + NUMBER_RE.pattern + "\s+" + QUOTED_RE.pattern
)
ANCHOR_RE = re.compile(
    QUOTED_RE.pattern
    + "\s+"
    + NUMBER_RE.pattern
    + "\s+"
    + NUMBER_RE.pattern
    + "\s+(\S+)\s+(\d)"
)
DEVICETABLE_RE = re.compile("\s?{.*?}\s?")
LOOKUP_RE = re.compile(
    "(\d+)\s+(\d+)\s+(\d+)\s+"
    + QUOTED_RE.pattern
    + "\s+"
    + "{(.*?)}"
    + "\s+"
    + "\[(.*?)\]"
)
TAG_RE = re.compile("'(.{,4})'")
FEATURE_RE = re.compile(TAG_RE.pattern + "\s+" + "\((.*.)\)")
LANGSYS_RE = re.compile(TAG_RE.pattern + "\s+" + "<(.*?)>" + "\s+")
SUBPOS_RE = re.compile(QUOTED_RE.pattern + "\s+(.*.)")
MARKCLASS_RE = re.compile(
    QUOTED_RE.pattern + "\s+" + NUMBER_RE.pattern + "\s+" + "(.*?)$"
)

SFDLIB_PREFIX = "org.sfdlib"
DECOMPOSEREMOVEOVERLAP_KEY = SFDLIB_PREFIX + ".decomposeAndRemoveOverlap"
MATH_KEY = SFDLIB_PREFIX + ".MATH"

CATEGORIES_KEY = "public.openTypeCategories"
UVS_KEY = "public.unicodeVariationSequences"


def _splitList(data, n):
    """Split data list to n sized sub lists."""
    return [data[i : i + n] for i in range(0, len(data), n)]


def _dumpAnchor(anchor):
    if not anchor:
        return "<anchor NULL>"
    return f"<anchor {otRound(anchor[0])} {otRound(anchor[1])}>"


def _sortGlyphs(font):
    """Emulate how FontForge orders output glyphs."""
    order = list(font.glyphOrder)

    def sort(name):
        # .notdef, .null, and nonmarkingreturn come first
        if name == ".notdef":
            return 0
        if name in (".null", "uni0000", "glyph1"):
            return 1
        if name in ("nonmarkingreturn", "uni000D", "glyph2"):
            return 2
        # Then encoded glyph in the encoding order (we are assuming Unicode
        # here, because meh).
        g = font[name]
        if g.unicode is not None:
            return g.unicode + 3
        # Then in the font order, we are adding 0x10FFFF here to make sure they
        # sort after Unicode.
        return order.index(name) + 0x10FFFF + 3

    return sorted(font.glyphOrder, key=sort)


def _parseVersion(version):
    versionMajor = ""
    versionMinor = ""
    if ";" in version:
        # Some fonts embed stuff after ";" in the version, strip it away.
        version = version.split(";")[0]
    if "." in version:
        versionMajor, versionMinor = version.split(".", 1)
    else:
        versionMajor = version

    versionMajor = int(versionMajor) if versionMajor.isdigit() else None
    versionMinor = int(versionMinor) if versionMinor.isdigit() else None

    return versionMajor, versionMinor


def _parseColor(color):
    r = (color & 255) / 255.0
    g = ((color >> 8) & 255) / 255.0
    b = ((color >> 16) & 255) / 255.0
    a = 1.0
    return f"{r:g},{g:g},{b:g},{a:g}"


def _kernClassesToUFO(subtables):
    groups = {}
    kerning = {}

    for i, (groups1, groups2, kerns) in enumerate(subtables):
        for j, group1 in enumerate(groups1):
            for k, group2 in enumerate(groups2):
                kern = kerns[(j * len(groups2)) + k]
                if group1 is not None and group2 is not None and kern != 0:
                    name1 = f"public.kern1.kc{i}_{j}"
                    name2 = f"public.kern2.kc{i}_{k}"
                    if name1 not in groups:
                        groups[name1] = group1
                    if name2 not in groups:
                        groups[name2] = group2
                    assert groups[name1] == group1
                    assert groups[name2] == group2
                    kerning[name1, name2] = kern

    return groups, kerning


class SFDParser:
    """Parses an SFD file or SFDIR directory."""

    def __init__(
        self,
        path,
        font,
        ufo_anchors=False,
        ufo_kerning=False,
        minimal=False,
    ):
        self._path = path
        self._font = font
        self._use_ufo_anchors = ufo_anchors
        self._use_ufo_kerning = ufo_kerning
        self._minimal = minimal

        self._layers = []
        self._layerType = []

        self._glyphRefs = {}
        self._glyphAnchors = {}
        self._glyphPosSub = {}
        self._glyphOrder = {}

        self._anchorClasses = {}
        self._markAttachClasses = []
        self._markAttachSets = []
        self._kernPairs = {}
        self._kernClasses = {}
        self._gsubLookups = {}
        self._gposLookups = {}
        self._lookupInfo = {}
        self._ligatureCarets = {}

        self._sanitizedLookupNames = {}

    def _parseAltuni(self, name, altuni):
        unicodes = []
        lib = self._font.lib
        for uni, uvs, _ in altuni:
            if uvs in (-1, 0xFFFFFFFF):
                unicodes.append(uni)
            else:
                uvs = f"{uvs:04X}"
                uni = f"{uni:04X}"
                lib.setdefault(UVS_KEY, {}).setdefault(uvs, {})[uni] = name

        return unicodes

    def _parsePrivateDict(self, data):
        info = self._font.info
        n = int(data.pop(0))
        assert len(data) == n

        StdHW = StdVW = None

        for line in data:
            key, n, value = [v.strip() for v in line.split(" ", 2)]
            assert len(value) == int(n)

            if value.startswith("[") and value.endswith("]"):
                value = [float(n) for n in value[1:-1].strip().split(" ")]
            else:
                value = float(value)

            if key == "BlueValues":
                info.postscriptBlueValues = value
            elif key == "OtherBlues":
                info.postscriptOtherBlues = value
            elif key == "FamilyBlues":
                info.postscriptFamilyBlues = value
            elif key == "FamilyOtherBlues":
                info.postscriptFamilyOtherBlues = value
            elif key == "BlueFuzz":
                info.postscriptBlueFuzz = value
            elif key == "BlueShift":
                info.postscriptBlueShift = value
            elif key == "BlueScale":
                info.postscriptBlueScale = value
            elif key == "ForceBold":
                info.postscriptForceBold = value
            elif key == "StemSnapH":
                info.postscriptStemSnapH = value
            elif key == "StemSnapV":
                info.postscriptStemSnapV = value
            elif key == "StdHW":
                StdHW = value[0]
            elif key == "StdVW":
                StdVW = value[0]

        if StdHW:
            if StdHW in info.postscriptStemSnapH:
                info.postscriptStemSnapH.pop(info.postscriptStemSnapH.index(StdHW))
            info.postscriptStemSnapH.insert(0, StdHW)
        if StdVW:
            if StdVW in info.postscriptStemSnapV:
                info.postscriptStemSnapV.pop(info.postscriptStemSnapV.index(StdVW))
            info.postscriptStemSnapV.insert(0, StdVW)

    def _parseGaspTable(self, data):
        info = self._font.info

        data = data.split(" ")
        num = int(data.pop(0))
        version = int(data.pop())
        assert len(data) == num * 2
        data = _splitList(data, 2)

        records = []
        for ppem, flags in data:
            ppem = int(ppem)
            flags = int(flags)
            flags = [i for i in range(4) if flags & (1 << i)]
            records.append(dict(rangeMaxPPEM=ppem, rangeGaspBehavior=flags))

        if records:
            info.openTypeGaspRangeRecords = records

    _NAMES = [
        "copyright",
        "familyName",  # XXX styleMapFamily
        "styleName",  # XXX styleMapStyle
        "openTypeNameUniqueID",
        None,  # XXX styleMapFamily and styleMapStyle
        "openTypeNameVersion",
        "postscriptFontName",
        "trademark",
        "openTypeNameManufacturer",
        "openTypeNameDesigner",
        "openTypeNameDescription",
        "openTypeNameManufacturerURL",
        "openTypeNameDesignerURL",
        "openTypeNameLicense",
        "openTypeNameLicenseURL",
        None,  # Reserved
        "openTypeNamePreferredFamilyName",
        "openTypeNamePreferredSubfamilyName",
        "openTypeNameCompatibleFullName",
        "openTypeNameSampleText",
        None,  # XXX
        "openTypeNameWWSFamilyName",
        "openTypeNameWWSSubfamilyName",
    ]

    def _parseNames(self, data):
        info = self._font.info

        data = data.split(" ", 1)
        if len(data) < 2:
            return

        langId = int(data[0])
        data = QUOTED_RE.findall(data[1])

        for nameId, name in enumerate(data):
            name = SFDReadUTF7(name)
            if name:
                if langId == 1033 and self._NAMES[nameId]:
                    # English (United States)
                    setattr(info, self._NAMES[nameId], name)
                else:
                    if not info.openTypeNameRecords:
                        info.openTypeNameRecords = []
                    info.openTypeNameRecords.append(
                        dict(
                            nameID=nameId,
                            languageID=langId,
                            string=name,
                            platformID=3,
                            encodingID=1,
                        )
                    )

    def _getSection(self, data, i, end, value=None):
        section = []
        if value is not None:
            section.append(value)

        while not data[i].startswith(end):
            section.append(data[i])
            i += 1

        return section, i + 1

    def _parseSplineSet(self, data):
        contours = []

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if line == "Spiro":
                spiro, i = self._getSection(data, i, "EndSpiro")
            elif line.startswith("Named"):
                name = SFDReadUTF7(line.split(": ")[1])
                contours[-1].append(name)
            else:
                pts, segmentType, flags = [
                    c.strip() for c in GLYPH_SEGMENT_RE.split(line)
                ]
                pts = [float(c) for c in pts.split(" ")]
                pts = _splitList(pts, 2)
                if segmentType == "m":
                    assert len(pts) == 1
                    contours.append([(pts, segmentType, flags)])
                elif segmentType == "l":
                    assert len(pts) == 1
                    contours[-1].append((pts, segmentType, flags))
                elif segmentType == "c":
                    assert len(pts) == 3
                    contours[-1].append((pts, segmentType, flags))

        return contours

    def _drawContours(self, name, layerIdx, contours):
        quadratic = self._layerType[layerIdx]
        glyph = self._layers[layerIdx][name]
        pen = glyph.getPointPen()
        for contour in contours:
            forceOpen = False
            if not isinstance(contour[-1], (tuple, list)):
                name = contour.pop()

            ufoContour = []
            for pts, segmentType, flags in contour:
                flag = flags.split(",")[0]
                flag = flag.split("x")[0]
                flag = int(flag)

                if flag & 0x400:  # SFD_PTFLAG_FORCE_OPEN_PATH
                    forceOpen = True
                smooth = (flag & 0x3) != 1

                if segmentType == "m":
                    ufoContour.append((pts[0], "move", smooth))
                elif segmentType == "l":
                    ufoContour.append((pts[0], "line", smooth))
                else:
                    curve = "curve"
                    if quadratic:
                        curve = "qcurve"

                        # XXX I don’t know what I’m doing
                        assert pts[0] == pts[1]
                        pts.pop(0)

                        if flag & 0x80:  # SFD_PTFLAG_INTERPOLATE
                            for pt in pts:
                                ufoContour.append((pt, None, None))
                            continue

                    for pt in pts[:-1]:
                        ufoContour.append((pt, None, None))
                    ufoContour.append((pts[-1], curve, smooth))

            # Closed path.
            if not forceOpen and (
                len(ufoContour) > 1 and ufoContour[0][0] == ufoContour[-1][0]
            ):
                ufoContour[0] = ufoContour[-1]
                ufoContour.pop()

            pen.beginPath()
            for pt, segmentType, smooth in ufoContour:
                pen.addPoint(pt, segmentType=segmentType, smooth=smooth)
            pen.endPath()

    def _parseGrid(self, data):
        font = self._font

        data = [l.strip() for l in data]
        contours = self._parseSplineSet(data)

        for contour in contours:
            name = None
            p0 = None
            if not isinstance(contour[-1], (tuple, list)):
                name = contour.pop()

            if len(contour) != 2:
                # UFO guidelines are simple straight lines, so I can handle any
                # complex contours here.
                continue

            for pts, segmentType, flags in contour:
                if segmentType == "m":
                    p0 = pts[0]
                elif segmentType == "l":
                    p1 = pts[0]

                    x = None
                    y = None
                    angle = None

                    if p0[0] == p1[0]:
                        x = p0[0]
                    elif p0[1] == p1[1]:
                        y = p0[1]
                    else:
                        x = p0[0]
                        y = p0[1]
                        angle = math.atan2(p1[0] - p0[0], p1[1] - p0[1])
                        angle = math.degrees(angle)
                        if angle < 0:
                            angle = 360 + angle
                    font.appendGuideline(dict(x=x, y=y, name=name, angle=angle))
                else:
                    p0 = pts[0]

    def _parseImage(self, glyph, data):
        pass  # XXX

    def _parseImage2(self, glyph, data):
        pass  # XXX

    def _parseKerns(self, glyph, data):
        kerns = KERNS_RE.findall(data)
        assert kerns
        for (gid, kern, subtable) in kerns:
            subtable = SFDReadUTF7(subtable)
            if subtable not in self._kernPairs:
                self._kernPairs[subtable] = {}
            if glyph.name not in self._kernPairs[subtable]:
                self._kernPairs[subtable][glyph.name] = []
            gid = int(gid)
            kern = int(kern)
            self._kernPairs[subtable][glyph.name].append((gid, kern))

    def _parseKernClass(self, data, i, value):
        m = KERNCLASS_RE.match(value)
        groups = m.groups()
        n1, plus, n2, name = groups
        classstart = 1
        if plus:
            classstart = 0
        n1 = int(n1)
        n2 = int(n2)
        name = SFDReadUTF7(name)

        first = data[i : i + n1 - classstart]
        first = [v.split()[1:] for v in first]
        if classstart != 0:
            first.insert(0, None)
        i += n1 - classstart

        second = data[i : i + n2 - 1]
        second = [v.split()[1:] for v in second]
        second.insert(0, None)
        i += n2 - 1

        kerns = data[i]
        kerns = DEVICETABLE_RE.split(kerns)
        kerns = [int(k) for k in kerns if k]

        self._kernClasses[name] = (first, second, kerns)

        return i + 1

    def _parseMarkClasses(self, data, i, count):
        classes = []
        for line in data[i : i + count]:
            m = MARKCLASS_RE.match(line)
            name, _, glyphs = m.groups()
            name = SFDReadUTF7(name)
            classes.append((name, glyphs))
        return i + count, classes

    def _parseAnchorClass(self, data):
        assert not self._anchorClasses
        data = [SFDReadUTF7(v) for v in QUOTED_RE.findall(data)]
        for anchor, subtable in _splitList(data, 2):
            if subtable not in self._anchorClasses:
                self._anchorClasses[subtable] = []
            self._anchorClasses[subtable].append(anchor)

    def _parseAnchorPoint(self, glyph, data):
        m = ANCHOR_RE.match(data)
        assert m
        name, x, y, kind, index = m.groups()
        name = SFDReadUTF7(name)
        x = float(x)
        y = float(y)
        index = int(index)

        if self._use_ufo_anchors:
            if kind == "mark":
                name = f"_{name}"
            elif kind == "ligature":
                name = f"{name}_{index}"
            elif kind in ["entry", "exit"]:
                name = f"{kind}.{name}"
            glyph.appendAnchor(dict(name=name, x=x, y=y))
        else:
            if glyph.name not in self._glyphAnchors:
                self._glyphAnchors[glyph.name] = {}
            if name not in self._glyphAnchors[glyph.name]:
                self._glyphAnchors[glyph.name][name] = {}
            self._glyphAnchors[glyph.name][name][kind] = (x, y, index)

    def _parsePosSub(self, glyph, key, data):
        m = SUBPOS_RE.match(data)
        assert m

        key = key[:-1]

        subtable, possub = m.groups()
        subtable = SFDReadUTF7(subtable)
        possub = possub.strip().split()

        if glyph.name not in self._glyphPosSub:
            self._glyphPosSub[glyph.name] = {}

        if key == "Position":
            possub = [int(p.split("=")[1]) for p in possub]
        elif key == "PairPos":
            possub = possub[:1] + [int(p.split("=")[1]) for p in possub[1:]]

        if key in (
            "Ligature",
            "Substitution",
            "AlternateSubs",
            "MultipleSubs",
            "Position",
            "PairPos",
        ):
            if subtable not in self._glyphPosSub[glyph.name]:
                self._glyphPosSub[glyph.name][subtable] = []
            self._glyphPosSub[glyph.name][subtable].append((key, possub))
        else:
            assert False, (key, possub)

    _LAYER_KEYWORDS = ["Back", "Fore", "Layer"]

    _CATEGORIES = [
        None,
        "unassigned",
        "base",
        "ligature",
        "mark",
        "component",
    ]

    def _parseChar(self, data):
        _, name = data.pop(0).split(": ")
        if name.startswith('"'):
            name = SFDReadUTF7(name)

        font = self._font
        glyph = font.newGlyph(name)
        layerIdx = None
        unicodes = []

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if ": " in line:
                key, value = line.split(": ", 1)
            else:
                key = line
                value = None

            if key == "Width":
                glyph.width = int(value)
            elif key == "VWidth":
                glyph.height = int(value)
            elif key == "Encoding":
                enc, uni, order = [int(v) for v in value.split()]
                if uni >= 0:
                    unicodes.append(uni)
            elif key == "AltUni2":
                altuni = [int(v, 16) for v in value.split(".")]
                altuni = _splitList(altuni, 3)
                unicodes += self._parseAltuni(name, altuni)
            elif key == "GlyphClass":
                font.lib[CATEGORIES_KEY][name] = self._CATEGORIES[int(value)]
            elif key == "UnlinkRmOvrlpSave":
                glyph.lib[DECOMPOSEREMOVEOVERLAP_KEY] = bool(int(value))
            elif key == "AnchorPoint":
                self._parseAnchorPoint(glyph, value)
            elif key in self._LAYER_KEYWORDS:
                layerIdx = value and int(value) or self._LAYER_KEYWORDS.index(key)
                if self._minimal and layerIdx != 1:
                    layerIdx = None
                    continue
                layer = self._layers[layerIdx]
                if glyph.name not in layer:
                    layer.newGlyph(name).width = glyph.width
            elif key == "SplineSet":
                splines, i = self._getSection(data, i, "EndSplineSet")
                if layerIdx is not None:
                    contours = self._parseSplineSet(splines)
                    self._drawContours(name, layerIdx, contours)
            elif key == "Image":
                image, i = self._getSection(data, i, "EndImage", value)
                if not self._minimal:
                    self._parseImage(self._layers[layerIdx][name], image)
            elif key == "Image2":
                image, i = self._getSection(data, i, "EndImage2", value)
                if not self._minimal:
                    self._parseImage2(self._layers[layerIdx][name], image)
            elif key == "Refer":
                # Just collect the refs here, we can’t insert them until all the
                # glyphs are parsed since FontForge uses glyph indices not names.
                # The calling code will process the references at the end.
                if layerIdx is None:
                    continue
                self._glyphRefs.setdefault((name, layerIdx), []).append(value)
            elif key == "Kerns2":
                self._parseKerns(glyph, value)
            elif key == "LCarets2":
                v = [int(v) for v in value.split(" ")]
                num = v.pop(0)
                assert len(v) == num
                if any(v):
                    self._ligatureCarets[glyph.name] = v
                    if self._use_ufo_anchors:
                        for idx, x in enumerate(v):
                            anchor = dict(name=f"caret_{idx+1}", x=x, y=0)
                            glyph.appendAnchor(anchor)
            elif key in (
                "Position2",
                "PairPos2",
                "Ligature2",
                "Substitution2",
                "AlternateSubs2",
                "MultipleSubs2",
            ):
                self._parsePosSub(glyph, key, value)
            elif key in ("ItalicCorrection", "TopAccentHorizontal", "IsExtendedShape"):
                if MATH_KEY not in glyph.lib:
                    glyph.lib[MATH_KEY] = {}
                glyph.lib[MATH_KEY][key] = int(value)
            elif key in ("GlyphVariantsVertical", "GlyphVariantsHorizontal"):
                if MATH_KEY not in glyph.lib:
                    glyph.lib[MATH_KEY] = {}
                glyph.lib[MATH_KEY][key] = value.split(" ")
            elif key in ("GlyphCompositionVertical", "GlyphCompositionHorizontal"):
                if MATH_KEY not in glyph.lib:
                    glyph.lib[MATH_KEY] = {}
                value = value.split(" ")[1:]
                value = [c.split("%") for c in value if c]
                glyph.lib[MATH_KEY][key] = value
            elif key in ("HStem", "VStem", "DStem2", "CounterMasks"):
                pass  # XXX
            elif key == "Flags":
                pass  # XXX
            elif key == "LayerCount":
                pass  # XXX
            elif not self._minimal:
                if key == "Comment":
                    glyph.note = SFDReadUTF7(value)
                elif key == "Colour":
                    glyph.markColor = _parseColor(int(value, 16))

        #   elif value is not None:
        #      print(key, value)

        glyph.unicodes = unicodes

        return glyph, order

    def _processReferences(self):
        for (name, layerIdx), refs in self._glyphRefs.items():
            glyph = self._layers[layerIdx][name]
            pen = glyph.getPointPen()

            refs.reverse()
            for ref in refs:
                ref = ref.split()
                base = self._glyphOrder[int(ref[0])]
                matrix = [float(v) for v in ref[3:9]]
                pen.addComponent(base, matrix)

    def _processUFOKerning(self):
        if not self._use_ufo_kerning:
            return

        for subtable in self._kernPairs:
            for name1 in self._kernPairs[subtable]:
                for gid2, kern in self._kernPairs[subtable][name1]:
                    name2 = self._font.glyphOrder[gid2]
                    self._font.kerning[name1, name2] = kern

        subtables = []
        for lookup in self._gposLookups:
            for subtable in self._gposLookups[lookup]:
                if subtable in self._kernClasses:
                    subtables.append(self._kernClasses[subtable])

        groups, kerning = _kernClassesToUFO(subtables)
        self._font.groups.update(groups)
        self._font.kerning.update(kerning)

    def _fixUFOAnchors(self):
        if not self._use_ufo_anchors:
            return

        anchors = set()
        for glyph in self._layers[1]:
            for anchor in glyph.anchors:
                if anchor.name.startswith(("exit.", "entry.")):
                    anchors.add(anchor.name.split(".", 1)[1])
        if len(anchors) == 1:
            for glyph in self._layers[1]:
                for anchor in glyph.anchors:
                    if anchor.name.startswith(("exit.", "entry.")):
                        anchor.name = anchor.name.split(".")[0]

    def _parseChars(self, data):
        font = self._font
        glyphOrderMap = {}

        font.lib[CATEGORIES_KEY] = {}

        data = [l.strip() for l in data if l.strip()]

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if line.startswith("StartChar"):
                char, i = self._getSection(data, i, "EndChar", line)
                glyph, order = self._parseChar(char)
                glyphOrderMap[glyph.name] = order

        # We need two glyph orders, the internal one to resolve references as
        # they indexes not names, and the output glyph order that FontForge
        # uses when writing out fonts.
        assert len(font) == len(glyphOrderMap)
        self._glyphOrder = font.glyphOrder = sorted(
            glyphOrderMap, key=glyphOrderMap.get
        )
        font.glyphOrder = _sortGlyphs(font)

    _LOOKUP_TYPES = {
        0x001: "gsub_single",
        0x002: "gsub_multiple",
        0x003: "gsub_alternate",
        0x004: "gsub_ligature",
        0x005: "gsub_context",
        0x006: "gsub_contextchain",
        # GSUB extension 7
        0x008: "gsub_reversecchain",
        0x0FD: "morx_indic",
        0x0FE: "morx_context",
        0x0FF: "morx_insert",
        0x101: "gpos_single",
        0x102: "gpos_pair",
        0x103: "gpos_cursive",
        0x104: "gpos_mark2base",
        0x105: "gpos_mark2ligature",
        0x106: "gpos_mark2mark",
        0x107: "gpos_context",
        0x108: "gpos_contextchain",
        # GPOS extension 9
        0x1FF: "kern_statemachine",
        # lookup&0xff == lookup type for the appropriate table
        # lookup>>8:     0=>GSUB, 1=>GPOS
    }

    def _parseLookup(self, data):
        m = LOOKUP_RE.match(data)
        assert m

        kind, flag, _, lookup, subtables, feature = m.groups()
        kind = int(kind)
        flag = int(flag)
        lookup = SFDReadUTF7(lookup)
        subtables = [SFDReadUTF7(v) for v in QUOTED_RE.findall(subtables)]

        if kind >> 8:  # GPOS
            self._gposLookups[lookup] = subtables
        else:
            self._gsubLookups[lookup] = subtables

        features = []
        for tag, langsys in FEATURE_RE.findall(feature):
            features.append([tag])
            for script, langs in LANGSYS_RE.findall(langsys):
                features[-1].append((script, TAG_RE.findall(langs)))

        self._lookupInfo[lookup] = (self._LOOKUP_TYPES[kind], flag, features)

    _OFFSET_METRICS = {
        "HheadAOffset": "openTypeHheaAscender",
        "HheadDOffset": "openTypeHheaDescender",
        "OS2TypoAOffset": "openTypeOS2TypoAscender",
        "OS2TypoDOffset": "openTypeOS2TypoDescender",
        "OS2WinAOffset": "openTypeOS2WinAscent",
        "OS2WinDOffset": "openTypeOS2WinDescent",
    }

    def _fixOffsetMetrics(self, metrics):
        if not metrics:
            return
        info = self._font.info
        bbox = [int(round(v)) for v in self._font.bounds]
        bounds = dict(xMin=bbox[0], yMin=bbox[1], xMax=bbox[2], yMax=bbox[3])
        for metric in metrics:
            value = getattr(info, metric)

            if metric == "openTypeOS2TypoAscender":
                value = info.ascender + value
            elif metric == "openTypeOS2TypoDescender":
                value = info.descender + value
            elif metric == "openTypeOS2WinAscent":
                value = bounds["yMax"] + value
            elif metric == "openTypeOS2WinDescent":
                value = max(-bounds["yMin"] + value, 0)
            elif metric == "openTypeHheaAscender":
                value = bounds["yMax"] + value
            elif metric == "openTypeHheaDescender":
                value = bounds["yMin"] + value

            setattr(info, metric, value)

    def _writeGDEF(self):
        font = self._font
        categories = font.lib[CATEGORIES_KEY]
        for name in font.glyphOrder:
            glyph = font[name]
            category = categories.get(name)
            if category == "unassigned":
                continue
            if category is None:
                if name == ".notdef":
                    continue
                category = "base"
                if name in self._glyphPosSub:
                    for subtable in self._glyphPosSub[name]:
                        for kind, _ in self._glyphPosSub[name][subtable]:
                            if kind == "Ligature":
                                category = "ligature"
                                break
                categories[name] = category

        lines = []
        for category in ["base", "mark", "ligature", "component"]:
            glyphs = {k for k, v in categories.items() if v == category}
            lines.append(f"@GDEF_{category} = [{' '.join(sorted(glyphs))}];")

        lines.append(
            """
            table GDEF {
            GlyphClassDef @GDEF_base,
                          @GDEF_ligature,
                          @GDEF_mark,
                          @GDEF_component;"""
        )

        for k, v in self._ligatureCarets.items():
            v = " ".join(str(i) for i in v)
            lines.append(f"  LigatureCaretByPos {k} {v};")
        lines.append("} GDEF;")

        if font.features.text is None:
            font.features.text = "\n"
        font.features.text += "\n".join(lines)

    _SHORT_LOOKUP_TYPES = {
        "gsub_single": "single",
        "gsub_multiple": "mult",
        "gsub_alternate": "alt",
        "gsub_ligature": "ligature",
        "gsub_context": "context",
        "gsub_contextchain": "chain",
        "gsub_reversecchain": "reversecc",
        "gpos_single": "single",
        "gpos_pair": "pair",
        "gpos_cursive": "cursive",
        "gpos_mark2base": "mark2base",
        "gpos_mark2ligature": "mark2liga",
        "gpos_mark2mark": "mark2mark",
        "gpos_context": "context",
        "gpos_contextchain": "chain",
    }

    def _santizeLookupName(self, lookup, isgpos=None):
        if lookup in self._sanitizedLookupNames:
            return self._sanitizedLookupNames[lookup]

        assert isgpos is not None

        out = ""
        for i, ch in enumerate(lookup):
            if ord(ch) >= 127:
                continue
            if ch.isalpha():
                out += ch
            elif ch in (".", "_"):
                out += ch
            elif i != 0 and ch.isdigit():
                out += ch
        out = out[:63]

        if out not in self._sanitizedLookupNames.values():
            self._sanitizedLookupNames[lookup] = out
        else:
            kind, _, fealangsys = self._lookupInfo[lookup]
            feat = ""
            script = ""
            kind = self._SHORT_LOOKUP_TYPES.get(kind, "unknown")
            if len(fealangsys):
                feat = fealangsys[0][0]
                for langsys in fealangsys[0]:
                    if langsys[0] != "DFLT":
                        script = langsys[0]
            i = 0
            while True:
                out = f"{isgpos and 'pos' or 'sub'}_{kind}_{feat}{script}_{i}"
                if out not in self._sanitizedLookupNames.values():
                    self._sanitizedLookupNames[lookup] = out
                    break
                i += 2

        return self._sanitizedLookupNames[lookup]

    def _sanitizeName(self, name):
        out = ""
        for i, ch in enumerate(name):
            if ord(ch) >= 127:
                continue
            if ch == " ":
                out += "_"
            if ch.isalnum() or ch in (".", "_"):
                out += ch

        return out

    def _pruneSubtables(self, subtables, isgpos):
        out = []
        for sub in subtables:
            if any(sub in self._glyphPosSub[g] for g in self._glyphPosSub):
                out.append(sub)
            elif sub in self._anchorClasses:
                out.append(sub)
            elif not self._use_ufo_kerning:
                if sub in self._kernClasses:
                    out.append(sub)
                elif sub in self._kernPairs:
                    out.append(sub)

        return out

    def _writeAnchorClass(self, lookup, subtable):
        lines = []

        kind, _, _ = self._lookupInfo[lookup]

        bases = []
        marks = []
        for anchorClass in self._anchorClasses[subtable]:
            for glyph in self._font.glyphOrder:
                if (
                    glyph in self._glyphAnchors
                    and anchorClass in self._glyphAnchors[glyph]
                ):
                    anchor = self._glyphAnchors[glyph][anchorClass]
                    if kind == "gpos_cursive":
                        entry = anchor.get("entry")
                        exit = anchor.get("exit")
                        if entry or exit:
                            entry = _dumpAnchor(entry)
                            exit = _dumpAnchor(exit)
                            lines.append(f"    pos cursive {glyph} {entry} {exit};")
                    else:
                        mark = anchor.get("mark")
                        base = anchor.get("basechar", anchor.get("basemark"))
                        if mark:
                            marks.append((glyph, mark[:2], anchorClass))
                        if base:
                            bases.append((glyph, base[:2], anchorClass))

        for glyph, anchor, anchorClass in marks:
            anchor = _dumpAnchor(anchor)
            className = self._sanitizeName(anchorClass)
            lines.append(f"  markClass {glyph} {anchor} @{className};")

        markClasses = [m[2] for m in marks]
        for glyph, anchor, anchorClass in bases:
            if anchorClass not in markClasses:
                # Base anchor without a corresponding mark, nothing to do here.
                continue
            anchor = _dumpAnchor(anchor)
            className = self._sanitizeName(anchorClass)
            pos = kind.split("2")[1]
            assert pos != "ligature"  # XXX
            lines.append(f"  pos {pos} {glyph} {anchor} mark @{className};")

        return lines

    def _writeKernClass(self, subtable):
        lines = []
        groups1, groups2, kerns = self._kernClasses[subtable]
        i = list(self._kernClasses.keys()).index(subtable)
        for j, group in enumerate(groups1):
            if group:
                glyphs = " ".join(group)
                lines.append(f"    @kc{i}_first_{j} = [{glyphs}];")

        for j, group in enumerate(groups2):
            name = f"kc{i}_second_{j}"
            if group:
                glyphs = " ".join(group)
                lines.append(f"    @kc{i}_second_{j} = [{glyphs}];")

        for j, group1 in enumerate(groups1):
            for k, group2 in enumerate(groups2):
                kern = kerns[(j * len(groups2)) + k]
                if group1 and group2 and kern != 0:
                    lines.append(f"    pos @kc{i}_first_{j} @kc{i}_second_{k} {kern};")
        return lines

    def _writeKernPairs(self, subtable):
        lines = []
        for name1 in self._kernPairs[subtable]:
            for gid2, kern in self._kernPairs[subtable][name1]:
                name2 = self._font.glyphOrder[gid2]
                lines.append(f"    pos {name1} {name2} {kern};")
        return lines

    _LOOKUP_FLAGS = {
        1: "RightToLeft",
        2: "IgnoreBaseGlyphs",
        4: "IgnoreLigatures",
        8: "IgnoreMarks",
    }

    def _writeGSUBGPOS(self, isgpos=False):
        # Ugly as hell, rewrite later.
        font = self._font

        if isgpos:
            tableLookups = self._gposLookups
        else:
            tableLookups = self._gsubLookups

        for lookup in tableLookups:
            self._santizeLookupName(lookup, isgpos)

        # Prune empty lookups
        lookups = {}
        for lookup, subtables in tableLookups.items():
            if any(self._pruneSubtables(subtables, isgpos)):
                lookups[lookup] = subtables

        if not lookups:
            return

        featureSet = []
        scriptSet = set()
        langSet = {}
        for lookup in lookups:
            _, _, fealangsys = self._lookupInfo[lookup]
            for feature in fealangsys:
                if feature[0] not in featureSet:
                    featureSet.append(feature[0])
                for script, languages in feature[1:]:
                    scriptSet.add(script)
                    if script not in langSet:
                        langSet[script] = set()
                    langSet[script].update(languages)

        scriptSet = sorted(scriptSet)
        langSet = {
            s: sorted(langSet[s], key=lambda l: l == "dflt" and "0" or l)
            for s in langSet
        }

        features = {}
        for feature in featureSet:
            outf = {}
            for script in scriptSet:
                outs = {}
                for language in langSet[script]:
                    outl = []
                    for lookup in lookups:
                        _, _, fealangsys = self._lookupInfo[lookup]
                        for fl in fealangsys:
                            if feature == fl[0]:
                                for sl in fl[1:]:
                                    if script == sl[0]:
                                        for ll in sl[1]:
                                            if language == ll:
                                                outl.append(
                                                    self._santizeLookupName(lookup)
                                                )
                    if outl:
                        outs[language] = outl
                if outs:
                    outf[script] = outs
            if outf:
                features[feature] = outf

        lines = []
        for name, glyphs in self._markAttachSets + self._markAttachClasses:
            lines.append(f"@{name} = [{glyphs}];")

        skip = set()

        for lookup in lookups:
            kind, flag, _ = self._lookupInfo[lookup]

            body = []
            for i, subtable in enumerate(lookups[lookup]):
                if subtable in self._anchorClasses:
                    body += self._writeAnchorClass(lookup, subtable)
                    continue
                if subtable in self._kernClasses:
                    body += self._writeKernClass(subtable)
                    continue
                if subtable in self._kernPairs:
                    body += self._writeKernPairs(subtable)
                    continue
                for glyph in self._glyphPosSub:
                    if subtable in self._glyphPosSub[glyph]:
                        for _, possub in self._glyphPosSub[glyph][subtable]:
                            if kind.startswith("gsub_"):
                                possub = " ".join(possub)

                            if kind in ("gsub_single", "gsub_multiple"):
                                body.append(f"    sub {glyph} by {possub};")
                            elif kind == "gsub_alternate":
                                body.append(f"    sub {glyph} from [{possub}];")
                            elif kind == "gsub_ligature":
                                body.append(f"    sub {possub} by {glyph};")
                            elif kind == "gpos_single":
                                possub = " ".join([str(v) for v in possub])
                                body.append(f"    pos {glyph} <{possub}>;")
                            elif kind == "gpos_pair":
                                glyph2 = possub.pop(0)
                                pos1 = " ".join([str(v) for v in possub[:4]])
                                pos2 = " ".join([str(v) for v in possub[4:]])
                                body.append(
                                    f"    pos {glyph} <{pos1}> {glyph2} <{pos2}>;"
                                )
                            else:
                                assert False, (kind, possub)
            if not body:
                skip.add(self._santizeLookupName(lookup))
                continue

            flags = []
            for i, name in sorted(self._LOOKUP_FLAGS.items()):
                if flag & i:
                    flags.append(name)

            if flag & 0xFF00:
                markclass = (flag >> 8) & 0xFF
                if markclass < len(self._markAttachClasses):
                    name = self._markAttachClasses[markclass - 1][0]
                    flags.append(f"MarkAttachmentType @{name}")

            if flag & 0x10:
                markset = (flag >> 16) & 0xFFFF
                if markset < len(self._markAttachSets):
                    name = self._markAttachSets[markset][0]
                    flags.append(f"UseMarkFilteringSet @{name}")

            lines.append(f"lookup {self._santizeLookupName(lookup)} {{")

            if flags:
                lines.append(f"  lookupflag {' '.join(flags)};")

            lines += body

            lines.append(f"}} {self._santizeLookupName(lookup)};")

        for feature in features:
            alllookups = set()
            for script in features[feature]:
                for language in features[feature][script]:
                    for lookup in features[feature][script][language]:
                        if lookup not in skip:
                            alllookups.add(lookup)
            if not alllookups:
                continue

            lines.append(f"feature {feature} {{")
            for script in features[feature]:
                lines.append(f" script {script};")
                for language in features[feature][script]:
                    excludedflt = language != "dflt" and "exclude_dflt" or ""
                    lines.append(f"     language {language} {excludedflt};")
                    for lookup in features[feature][script][language]:
                        if lookup in skip:
                            continue
                        lines.append(f"      lookup {lookup};")
            lines.append(f"}} {feature};")

        if font.features.text is None:
            font.features.text = "\n"
        font.features.text += "\n".join(lines)

    def parse(self):
        isdir = os.path.isdir(self._path)
        if isdir:
            props = os.path.join(self._path, "font.props")
            if os.path.isfile(props):
                with open(props) as fd:
                    data = fd.readlines()
            else:
                raise Exception("Not an SFD directory")
        else:
            with open(self._path) as fd:
                data = fd.readlines()

        font = self._font
        info = font.info

        charData = None
        offsetMetrics = []

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if ":" in line:
                key, value = [v.strip() for v in line.split(":", 1)]
            else:
                key = line.strip()
                value = None

            if i == 1:
                if key != "SplineFontDB":
                    raise Exception("Not an SFD file.")
                version = float(value)
                if version not in (3.0, 3.2):
                    raise Exception(f"Unsupported SFD version: {version}")

            elif key == "FontName":
                info.postscriptFontName = value
            elif key == "FullName":
                info.postscriptFullName = value
            elif key == "FamilyName":
                info.familyName = value
            elif key == "DefaultBaseFilename":
                pass  # info.XXX = value
            elif key == "Weight":
                info.postscriptWeightName = value
            elif key == "Copyright":
                # Decode escape sequences.
                info.copyright = codecs.escape_decode(value)[0].decode("utf-8")
            elif key == "Version":
                info.versionMajor, info.versionMinor = _parseVersion(value)
            elif key == "ItalicAngle":
                info.italicAngle = info.postscriptSlantAngle = float(value)
            elif key == "UnderlinePosition":
                info.postscriptUnderlinePosition = float(value)
            elif key == "UnderlineWidth":
                info.postscriptUnderlineThickness = float(value)
            elif key in "Ascent":
                info.ascender = int(value)
            elif key in "Descent":
                info.descender = -int(value)
            elif key == "sfntRevision":
                pass  # info.XXX = int(value, 16)
            elif key == "WidthSeparation":
                pass  # XXX = float(value) # auto spacing
            elif key == "LayerCount":
                self._layers = int(value) * [None]
                self._layerType = int(value) * [None]
            elif key == "Layer":
                m = LAYER_RE.match(value)
                idx, quadratic, name = m.groups()
                idx = int(idx)
                quadratic = bool(int(quadratic))
                name = SFDReadUTF7(name)
                if idx == 1:
                    self._layers[idx] = font.layers.defaultLayer
                elif not self._minimal:
                    self._layers[idx] = name
                self._layerType[idx] = quadratic
            elif key == "DisplayLayer":
                pass  # XXX default layer
            elif key == "DisplaySize":
                pass  # GUI
            elif key == "AntiAlias":
                pass  # GUI
            elif key == "FitToEm":
                pass  # GUI
            elif key == "WinInfo":
                pass  # GUI
            elif key == "Encoding":
                pass  # XXX encoding = value
            elif key == "CreationTime":
                v = datetime.utcfromtimestamp(int(value))
                info.openTypeHeadCreated = v.strftime("%Y/%m/%d %H:%M:%S")
            elif key == "ModificationTime":
                pass  # XXX
            elif key == "FSType":
                v = int(value)
                v = [bit for bit in range(16) if v & (1 << bit)]
                info.openTypeOS2Type = v
            elif key == "PfmFamily":
                pass  # info.XXX = value
            elif key in ("TTFWeight", "PfmWeight"):
                info.openTypeOS2WeightClass = int(value)
            elif key == "TTFWidth":
                info.openTypeOS2WidthClass = int(value)
            elif key == "Panose":
                v = value.split()
                info.openTypeOS2Panose = [int(n) for n in v]
            elif key == "LineGap":
                info.openTypeHheaLineGap = int(value)
            elif key == "VLineGap":
                info.openTypeVheaVertTypoLineGap = int(value)
            elif key == "HheadAscent":
                info.openTypeHheaAscender = int(value)
            elif key == "HheadDescent":
                info.openTypeHheaDescender = int(value)
            elif key == "OS2TypoLinegap":
                info.openTypeOS2TypoLineGap = int(value)
            elif key == "OS2Vendor":
                info.openTypeOS2VendorID = value.strip("'")
            elif key == "OS2FamilyClass":
                v = int(value)
                info.openTypeOS2FamilyClass = (v >> 8, v & 0xFF)
            elif key == "OS2Version":
                pass  # XXX
            elif key == "OS2_WeightWidthSlopeOnly":
                if int(value):
                    if not info.openTypeOS2Selection:
                        info.openTypeOS2Selection = []
                    info.openTypeOS2Selection += [8]
            elif key == "OS2_UseTypoMetrics":
                if not info.openTypeOS2Selection:
                    info.openTypeOS2Selection = []
                info.openTypeOS2Selection += [7]
            elif key == "OS2CodePages":
                pass  # XXX
            elif key == "OS2UnicodeRanges":
                pass  # XXX
            elif key == "OS2TypoAscent":
                info.openTypeOS2TypoAscender = int(value)
            elif key == "OS2TypoDescent":
                info.openTypeOS2TypoDescender = int(value)
            elif key == "OS2WinAscent":
                info.openTypeOS2WinAscent = int(value)
            elif key == "OS2WinDescent":
                info.openTypeOS2WinDescent = int(value)
            elif key in self._OFFSET_METRICS:
                if int(value):
                    offsetMetrics.append(self._OFFSET_METRICS[key])
            elif key == "OS2SubXSize":
                info.openTypeOS2SubscriptXSize = int(value)
            elif key == "OS2SubYSize":
                info.openTypeOS2SubscriptYSize = int(value)
            elif key == "OS2SubXOff":
                info.openTypeOS2SubscriptXOffset = int(value)
            elif key == "OS2SubYOff":
                info.openTypeOS2SubscriptYOffset = int(value)
            elif key == "OS2SupXSize":
                info.openTypeOS2SuperscriptXSize = int(value)
            elif key == "OS2SupYSize":
                info.openTypeOS2SuperscriptYSize = int(value)
            elif key == "OS2SupXOff":
                info.openTypeOS2SuperscriptXOffset = int(value)
            elif key == "OS2SupYOff":
                info.openTypeOS2SuperscriptYOffset = int(value)
            elif key == "OS2StrikeYSize":
                info.openTypeOS2StrikeoutSize = int(value)
            elif key == "OS2StrikeYPos":
                info.openTypeOS2StrikeoutPosition = int(value)
            elif key == "OS2CapHeight":
                info.capHeight = int(value)
            elif key == "OS2XHeight":
                info.xHeight = int(value)
            elif key == "UniqueID":
                info.postscriptUniqueID = int(value)
            elif key == "LangName":
                self._parseNames(value)
            elif key == "GaspTable":
                self._parseGaspTable(value)
            elif key == "BeginPrivate":
                section, i = self._getSection(data, i, "EndPrivate", value)
                self._parsePrivateDict(section)
            elif key == "BeginChars":
                charData, i = self._getSection(data, i, "EndChars")
            elif key == "KernClass2":
                i = self._parseKernClass(data, i, value)
            elif key == "Lookup":
                self._parseLookup(value)
            elif key == "AnchorClass2":
                self._parseAnchorClass(value)
            elif key == "MarkAttachClasses":
                count = int(value) - 1
                i, self._markAttachClasses = self._parseMarkClasses(data, i, count)
            elif key == "MarkAttachSets":
                count = int(value)
                i, self._markAttachSets = self._parseMarkClasses(data, i, count)
            elif key == "MATH":
                if MATH_KEY not in font.lib:
                    font.lib[MATH_KEY] = {}
                c, v = value.split(": ")
                # Match OT spec names.
                if c == "FractionDenominatorDisplayStyleGapMin":
                    c = "FractionDenomDisplayStyleGapMin"
                elif c == "FractionNumeratorDisplayStyleGapMin":
                    c = "FractionNumDisplayStyleGapMin"
                font.lib[MATH_KEY][c] = int(v)
            elif key == "XUID":
                pass  # XXX
            elif key == "UnicodeInterp":
                pass  # XXX
            elif key == "NameList":
                pass  # XXX
            elif key == "DEI":
                pass
            elif key == "EndSplineFont":
                break
            elif not self._minimal:
                if key == "Comments":
                    info.note = value
                elif key == "UComments":
                    old = info.note
                    info.note = SFDReadUTF7(value)
                    if old:
                        info.note += "\n" + old
                elif key == "FontLog":
                    if not info.note:
                        info.note = ""
                    else:
                        info.note = "\n"
                    info.note += "Font log:\n" + SFDReadUTF7(value)
                elif key == "Grid":
                    grid, i = self._getSection(data, i, "EndSplineSet")
                    self._parseGrid(grid)

        #   else:
        #      print(key, value)

        # FontForge does not match OpenType here.
        if info.postscriptUnderlinePosition and info.postscriptUnderlineThickness:
            info.postscriptUnderlinePosition += info.postscriptUnderlineThickness / 2

        for idx, name in enumerate(self._layers):
            if not isinstance(name, str):
                continue
            if self._minimal and idx != 1:
                continue
            if idx not in (0, 1) and self._layers.count(name) != 1:
                # FontForge layer names are not unique, make sure ours are.
                name += f"_{idx}"
            self._layers[idx] = font.newLayer(name)

        if isdir:
            assert charData is None
            import pathlib

            charData = []
            for filename in pathlib.Path(self._path).glob("*.glyph"):
                with open(filename) as fp:
                    charData += fp.readlines()

        self._parseChars(charData)

        # We can’t insert the references while parsing the glyphs since
        # FontForge uses glyph indices so we need to know the glyph order
        # first.
        self._processReferences()

        # Same for kerning.
        self._processUFOKerning()

        self._fixUFOAnchors()

        # Need to run after parsing glyphs so that we can calculate font
        # bounding box.
        self._fixOffsetMetrics(offsetMetrics)

        self._writeGSUBGPOS(isgpos=False)
        self._writeGSUBGPOS(isgpos=True)
        self._writeGDEF()

        # FontForge does not have an explicit UPEM setting, it is the sum of its
        # ascender and descender.
        info.unitsPerEm = info.ascender - info.descender

        # Fallback for missing styleName.
        # FontForge does more magic in its _GetModifiers functions, but this is
        # a stripped down version.
        if info.styleName is None:
            value = "Regular"
            if info.postscriptFontName and "-" in info.postscriptFontName:
                value = info.postscriptFontName.split("-", 1)[1]
            elif info.postscriptWeightName:
                value = info.postscriptWeightName
            info.styleName = value
