from __future__ import annotations

_JURISDICTION_ALIASES: dict[str, str] = {
    "us": "US",
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    "america": "US",
    "uk": "GB",
    "gb": "GB",
    "great britain": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "ky": "KY",
    "cayman islands": "KY",
    "cayman": "KY",
    "lu": "LU",
    "luxembourg": "LU",
    "ie": "IE",
    "ireland": "IE",
    "sg": "SG",
    "singapore": "SG",
    "vg": "VG",
    "bvi": "VG",
    "british virgin islands": "VG",
    "virgin islands": "VG",
    "ae": "AE",
    "uae": "AE",
    "united arab emirates": "AE",
    "dubai": "AE",
    "abu dhabi": "AE",
    "je": "JE",
    "jersey": "JE",
    "de": "DE",
    "germany": "DE",
    "fr": "FR",
    "france": "FR",
    "jp": "JP",
    "japan": "JP",
    "hk": "HK",
    "hong kong": "HK",
    "au": "AU",
    "australia": "AU",
    "ca": "CA",
    "canada": "CA",
    "ch": "CH",
    "switzerland": "CH",
    "nl": "NL",
    "netherlands": "NL",
}


def normalize_jurisdiction(code_or_name: str) -> str:
    canonical = _JURISDICTION_ALIASES.get(code_or_name.strip().lower())
    if canonical:
        return canonical
    upper = code_or_name.strip().upper()
    if len(upper) == 2 and upper.isalpha():
        return upper
    return code_or_name.strip()
