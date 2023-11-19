import struct

import util

unpack = struct.unpack
import fontTools.ttLib as ttLib

OFFSET_TABLE_SIZE = 12
TABLE_DIR_SIZE = 16
NAME_TABLE_SIZE = 6
NAME_RECORD_SIZE = 12

class ParseError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

def check(val):
    if not val:
        raise ParseError("")

# a parser for TrueType/OpenType fonts.
# http://www.microsoft.com/typography/otspec/default.htm contained the
# spec at the time of the writing.
class Font:

    # load font from string s, which is the whole contents of a font file
    def __init__(self, f):
        # is this a valid font
        self.ok = False

        s = ttLib.TTFont(f)
        # parse functions for tables, and a flag for whether each has been
        # parsed successfully
        self.parseFuncs = {
            util.toLatin1("head") : [self.parseHead, False],
            util.toLatin1("name") : [self.parseName, False],
            util.toLatin1("OS/2") : [self.parseOS2, False]
            }

        try:
            self.parse(s)
        except (struct.error, ParseError) as e:
            self.error = e

            return

        self.ok = True

    # check if font was parsed correctly. none of the other
    # (user-oriented) functions can be called if this returns False.
    def isOK(self):
        return self.ok

    # get font's Postscript name.
    def getPostscriptName(self):
        return self.psName

    # returns True if font allows embedding.
    def allowsEmbedding(self):
        return self.embeddingOK

    # parse whole file
    def parse(self, s):
        for name, func in self.parseFuncs.items():
            if s.has_key(name):
                func[0](s.get(name))
                func[1] = True
            else:
                raise ParseError("Table %s missing/invalid" % name)

    # parse a single tag
    def parseTag(self, offset, s):
        tag, checkSum, tagOffset, length = unpack(">4s3L",
            s[offset : offset + TABLE_DIR_SIZE])

        check(tagOffset >= (OFFSET_TABLE_SIZE +
                            self.tableCnt * TABLE_DIR_SIZE))

        func = self.parseFuncs.get(tag)
        if func:
            func[0](s[tagOffset : tagOffset + length])
            func[1] = True

    # parse head table
    def parseHead(self, s):
        magic = s.magicNumber

        check(magic == 0x5F0F3CF5)

    # parse name table
    def parseName(self, s):
        #fmt = s.format
        fmt = 0
        check(fmt == 0)

        for nameRec in s.names:
            if self.parseNameRecord(nameRec):
                return

        raise ParseError("No Postscript name found")

    # parse a single name record. s2 is string storage. returns True if
    # this record is a valid Postscript name.
    def parseNameRecord(self, s):
        platformID = s.platformID
        encodingID = s.platEncID
        langID = s.langID
        nameID = s.nameID

        if nameID != 6:
            return False

        if (platformID == 1) and (encodingID == 0) and (langID == 0):
            # Macintosh, 1-byte strings

            #self.psName = s.getName(nameID, platformID, encodingID)
            self.psName = s.toStr()

            return True

        elif (platformID == 3) and (encodingID == 1) and (langID == 1033):
            # Windows, UTF-16BE

            #self.psName = s.get(nameID, platformID, encodingID)
            self.psName = s.toStr()

            return True

        return False

    def parseOS2(self, s):
        fsType = s.fsType

        # the font embedding bits are a mess, the meanings have changed
        # over time in the TrueType/OpenType specs. this is the least
        # restrictive interpretation common to them all.
        self.embeddingOK = (fsType & 0xF) != 2
