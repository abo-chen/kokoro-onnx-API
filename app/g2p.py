"""Mixed Chinese-English G2P for Kokoro TTS.

Three-level strategy:
1. High-frequency dictionary (exact match for known words)
2. Pure uppercase abbreviations → letter-by-letter spelling
3. g2p_en fallback → ARPABET phonemes mapped to Chinese characters
"""

import logging
import re

logger = logging.getLogger(__name__)

# ARPABET phoneme → Chinese character mapping
ARPABET_MAP = {
    # Vowels
    "AA": "阿", "AA0": "阿", "AA1": "阿", "AA2": "阿",
    "AE": "艾", "AE0": "艾", "AE1": "艾", "AE2": "艾",
    "AH": "阿", "AH0": "阿", "AH1": "阿", "AH2": "阿",
    "AO": "奥", "AO0": "奥", "AO1": "奥", "AO2": "奥",
    "AW": "奥", "AW0": "奥", "AW1": "奥", "AW2": "奥",
    "AY": "艾", "AY0": "艾", "AY1": "艾", "AY2": "艾",
    "EH": "哎", "EH0": "哎", "EH1": "哎", "EH2": "哎",
    "ER": "儿", "ER0": "儿", "ER1": "儿", "ER2": "儿",
    "EY": "诶", "EY0": "诶", "EY1": "诶", "EY2": "诶",
    "IH": "伊", "IH0": "伊", "IH1": "伊", "IH2": "伊",
    "IY": "伊", "IY0": "伊", "IY1": "伊", "IY2": "伊",
    "OW": "欧", "OW0": "欧", "OW1": "欧", "OW2": "欧",
    "OY": "欧艾", "OY0": "欧艾", "OY1": "欧艾", "OY2": "欧艾",
    "UH": "乌", "UH0": "乌", "UH1": "乌", "UH2": "乌",
    "UW": "乌", "UW0": "乌", "UW1": "乌", "UW2": "乌",
    # Consonants
    "B": "布", "CH": "吃", "D": "的", "DH": "德",
    "F": "弗", "G": "格", "HH": "哈", "JH": "杰",
    "K": "克", "L": "勒", "M": "姆", "N": "恩",
    "NG": "恩", "P": "普", "R": "尔", "S": "斯",
    "SH": "什", "T": "特", "TH": "斯", "V": "弗",
    "W": "沃", "Y": "伊", "Z": "兹", "ZH": "日",
}

# High-frequency custom dictionary
CUSTOM_DICT = {
    # Tech brands/products
    "wifi": "外发艾", "app": "埃普", "bug": "巴格",
    "react": "瑞阿克特", "python": "派森", "dify": "迪发艾",
    "ollama": "欧拉马", "github": "给特哈布", "kokoro": "考考罗",
    "docker": "多克", "linux": "里纳克斯", "google": "谷歌",
    "apple": "苹果", "openai": "欧喷艾艾", "chatgpt": "恰特吉匹替",
    "claude": "克劳德", "cursor": "克瑟", "vscode": "微斯扣德",
    "npm": "恩匹艾姆", "git": "吉特", "ssh": "艾斯艾斯诶吃",
    "redis": "瑞迪斯", "kubernetes": "库伯奈提斯", "nginx": "恩金克斯",
    "mysql": "麦艾斯丘艾勒", "postgres": "波斯特格雷斯",
    "mongodb": "蒙哥德比", "redis": "瑞迪斯",
    # Tech terms
    "api": "诶匹艾", "gpu": "吉匹优", "cpu": "西匹优",
    "url": "优阿艾勒", "json": "杰森", "http": "诶吃提提匹",
    "html": "诶吃提艾姆艾勒", "pdf": "匹迪艾夫", "usb": "优艾斯必",
    "sql": "斯丘艾勒", "tcp": "替西匹", "udp": "优迪匹",
    "ssl": "艾斯艾斯艾勒", "tls": "提艾斯艾勒",
    "xml": "艾克斯艾姆艾勒", "yaml": "雅姆欧",
    # OS/software
    "mac": "麦克", "ios": "艾艾欧斯", "android": "安卓",
    "windows": "温都斯", "ubuntu": "乌班图", "debian": "德比安",
    "centos": "森托斯", "arch": "阿奇", "fedora": "菲多拉",
    # Common words
    "hello": "哈喽", "world": "沃德", "crash": "克若艾什",
    "default": "迪佛特", "server": "瑟维尔", "client": "克莱恩特",
    "database": "戴塔贝斯", "network": "奈特沃克", "browser": "布劳泽",
    "download": "当劳德", "upload": "阿普劳德", "update": "阿普戴特",
    "delete": "迪丽特", "config": "康菲格", "deploy": "迪普洛伊",
    "build": "比尔德", "debug": "迪巴格", "login": "劳印",
    "logout": "劳嘎特", "token": "托肯", "cache": "凯什",
    "proxy": "普若克西", "script": "斯克里普特",
    "codec": "扣迪克", "model": "莫德尔", "prompt": "普若姆普特",
    "audio": "欧迪欧", "video": "维迪欧", "image": "伊梅吉",
    "file": "法艾勒", "cloud": "克劳德", "stack": "斯塔克",
    "frame": "弗若艾姆", "pixel": "匹克瑟", "vector": "维克特",
    "tensor": "坦瑟", "plugin": "普拉金", "theme": "提姆",
    "route": "若特", "middleware": "米德尔瓦尔",
}

# A-Z letter Chinese pronunciation
LETTER_MAP = {
    "A": "诶", "B": "必", "C": "西", "D": "弟", "E": "伊", "F": "艾夫",
    "G": "记", "H": "诶吃", "I": "艾", "J": "杰", "K": "克", "L": "艾勒",
    "M": "艾姆", "N": "恩", "O": "欧", "P": "匹", "Q": "扣", "R": "阿",
    "S": "艾斯", "T": "替", "U": "优", "V": "微", "W": "达不溜", "X": "艾克斯",
    "Y": "外", "Z": "贼",
}

_g2p_en = None


def _get_g2p_en():
    global _g2p_en
    if _g2p_en is None:
        try:
            from g2p_en import G2p
            _g2p_en = G2p()
            logger.info("g2p_en loaded for English fallback")
        except Exception as e:
            logger.warning(f"g2p_en not available, English fallback disabled: {e}")
    return _g2p_en


def _arpabet_to_chinese(phonemes: list[str]) -> str:
    """Convert ARPABET phonemes to Chinese characters."""
    chars = []
    for p in phonemes:
        chars.append(ARPABET_MAP.get(p, ""))
    result = "".join(chars)
    return result if result else "未知"


def _spell_letters(word: str) -> str:
    """Spell out an all-uppercase abbreviation letter by letter."""
    return "".join(LETTER_MAP.get(ch, ch) for ch in word.upper())


def replace_english(text: str) -> str:
    """Replace English words in text with Chinese phonetic equivalents.

    Levels:
    1. Custom dictionary lookup
    2. Pure uppercase → letter spelling
    3. g2p_en → ARPABET mapped to Chinese
    """

    def replacer(m):
        word = m.group(0)
        key = word.lower()

        # Level 1: custom dictionary
        if key in CUSTOM_DICT:
            logger.debug(f"G2P dict hit: {word} -> {CUSTOM_DICT[key]}")
            return CUSTOM_DICT[key]

        # Level 2: pure uppercase abbreviation → letter spelling
        if word.isupper() and len(word) <= 6:
            result = _spell_letters(word)
            logger.debug(f"G2P letter spell: {word} -> {result}")
            return result

        # Level 3: g2p_en fallback
        g2p = _get_g2p_en()
        if g2p is not None:
            try:
                phonemes = g2p(word)
                result = _arpabet_to_chinese(phonemes)
                logger.debug(f"G2P g2p_en: {word} -> {phonemes} -> {result}")
                return result
            except Exception as e:
                logger.warning(f"g2p_en failed for '{word}': {e}")

        # Final fallback: letter spelling
        result = _spell_letters(word)
        logger.debug(f"G2P fallback spell: {word} -> {result}")
        return result

    return re.sub(r"[a-zA-Z]+", replacer, text)


def contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))
