_INBASE64 = [
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    62,
    -1,
    -1,
    -1,
    63,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
]


def SFDReadUTF7(data):
    """Python re-implementation of FontForge’s UTF-7 decoder which does not
    seem to be standards-complaint, so we can’t use Python’s builtin UTF-7
    codec.
    """

    out = b""

    data = data.strip('"').encode("ascii")

    if data and not isinstance(data[0], int):  # Python 2
        data = [ord(c) for c in data]

    prev_cnt = 0
    prev = 0

    ch1 = 0
    ch2 = 0
    ch3 = 0
    ch4 = 0

    i = 0
    inside = False
    while i < len(data):
        ch1 = data[i]
        i += 1

        done = False

        if not done and not inside:
            if ch1 == ord("+"):
                ch1 = data[i]
                i += 1
                if ch1 == ord("-"):
                    ch1 = ord("+")
                    done = True
                else:
                    inside = True
                    prev_cnt = 0
            else:
                done = True

        if not done:
            if ch1 == ord("-"):
                inside = False
            elif _INBASE64[ch1] == -1:
                inside = False
                done = True
            else:
                ch1 = _INBASE64[ch1]
                ch2 = _INBASE64[data[i]]
                i += 1
                if ch2 == -1:
                    i -= 1
                    ch2 = 0
                    ch3 = 0
                    ch4 = 0
                else:
                    ch3 = _INBASE64[data[i]]
                    i += 1
                    if ch3 == -1:
                        i -= 1
                        ch3 = 0
                        ch4 = 0
                    else:
                        ch4 = _INBASE64[data[i]]
                        i += 1
                        if ch4 == -1:
                            i -= 1
                            ch4 = 0

                ch1 = (ch1 << 18) | (ch2 << 12) | (ch3 << 6) | ch4

                if prev_cnt == 0:
                    prev = ch1 & 0xFF
                    ch1 >>= 8
                    prev_cnt = 1
                else:
                    ch1 |= prev << 24
                    prev = ch1 & 0xFFFF
                    ch1 = (ch1 >> 16) & 0xFFFF
                    prev_cnt = 2
                done = True

        if done:
            out += chr(ch1).encode("utf-8")
        if prev_cnt == 2:
            prev_cnt = 0
            if prev != 0:
                out += chr(prev).encode("utf-8")

    return out.decode("utf-8")
