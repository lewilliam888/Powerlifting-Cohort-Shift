import re
import pandas as pd
import numpy as np

# IPF weight classes
IPF_CLASSES_M = {53, 59, 66, 74, 83, 93, 105, 120}
IPF_CLASSES_F = {43, 47, 52, 57, 63, 69, 76, 84}


def parse_weight_class(s):
    if pd.isna(s):
        return (np.nan, False)
    s = str(s).strip()
    if not s:
        return (np.nan, False)
    is_super = s.endswith("+")
    if is_super:
        s = s[:-1].strip()
    try:
        return (float(s), is_super)
    except ValueError:
        return (np.nan, is_super)


def is_ipf_class(weight_class, sex):
    num, _ = parse_weight_class(weight_class)
    if pd.isna(num):
        return True
    classes = IPF_CLASSES_M if sex == "M" else IPF_CLASSES_F
    return num in classes


# bodyweight cutoffs for reconstructing class when the label is missing
# (Sheffield and some invitationals record bodyweight but not WeightClassKg)
BW_CUTS_M = [(53,"53"),(59,"59"),(66,"66"),(74,"74"),(83,"83"),(93,"93"),(105,"105"),(120,"120")]
BW_CUTS_F = [(43,"43"),(47,"47"),(52,"52"),(57,"57"),(63,"63"),(69,"69"),(76,"76"),(84,"84")]

def class_from_bodyweight(bw, sex):
    if pd.isna(bw):
        return np.nan
    cuts = BW_CUTS_M if sex == "M" else BW_CUTS_F
    for lim, label in cuts:
        if bw <= lim:
            return label
    return ("120+" if sex == "M" else "84+")

def age_category(age):
    if pd.isna(age):
        return "Unknown"
    a = float(age)
    if a < 14: return "Youth"
    if a < 19: return "SubJunior"
    if a < 24: return "Junior"
    if a < 40: return "Open"
    return "Masters"


# Order matters - first match wins
DIVISION_PATTERNS = [
    (re.compile(r"\b(open|m-?o\b|f-?o\b|mr-?o\b|fr-?o\b|snr|sr|senior|seniorzy)\b", re.I), "Open"),
    (re.compile(r"\b(jr|junior|jun|u23|under\s*23|19-23|20-23)\b", re.I), "Junior"),
    (re.compile(r"\b(sj|sub-?jr|sub-?junior|t1|t2|teen)\b", re.I), "SubJunior"),
    (re.compile(r"\b(collegiate|college|m-?c\b|f-?c\b|mr-?c\b|fr-?c\b)\b", re.I), "Collegiate"),
    (re.compile(r"\b(master|m1|m2|m3|m4|t3|t4)\b", re.I), "Masters"),
]


def canonicalize_division(division):
    if pd.isna(division):
        return "Unknown"
    s = str(division).strip()
    if not s:
        return "Unknown"
    for pattern, label in DIVISION_PATTERNS:
        if pattern.search(s):
            return label
    return "Other"


# Open beats Junior beats SubJunior etc - used to dedupe lifter-meets where one performance gets recorded under multiple brackets
DIVISION_PRIORITY = {
    "Open": 1, "Junior": 2, "SubJunior": 3,
    "Collegiate": 4, "Masters": 5, "Other": 6, "Unknown": 7,
}


def dedupe_lifter_meets(df):
    df = df.copy()
    df["_p"] = df["division_canon"].map(DIVISION_PRIORITY).fillna(99).astype(int)
    df = df.sort_values(["Name", "Date", "_p"])
    df = df.drop_duplicates(subset=["Name", "Date"], keep="first")
    return df.drop(columns="_p")


def add_features(df):
    df = df.copy()

    parsed = df["WeightClassKg"].apply(parse_weight_class)
    df["wc_num"] = parsed.map(lambda t: t[0])
    df["wc_is_super"] = parsed.map(lambda t: t[1])
    df["is_ipf_class"] = df.apply(lambda r: is_ipf_class(r["WeightClassKg"], r["Sex"]), axis=1)

    # reconstruct missing class labels from bodyweight (Sheffield, some invitationals)
    miss = df["WeightClassKg"].isna() & df["BodyweightKg"].notna()
    df.loc[miss, "WeightClassKg"] = df.loc[miss].apply(
        lambda r: class_from_bodyweight(r["BodyweightKg"], r["Sex"]), axis=1)

    df["age_category"] = df["Age"].apply(age_category)
    df["division_canon"] = df["Division"].apply(canonicalize_division)
    df["junior_in_open"] = (df["age_category"] == "Junior") & (df["division_canon"] == "Open")

    return df
