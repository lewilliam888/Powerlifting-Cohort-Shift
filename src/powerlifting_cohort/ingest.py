import pandas as pd

KEEP_COLS = [
    "Name", "Sex", "Event", "Equipment",
    "Age", "AgeClass", "BirthYearClass", "Division",
    "BodyweightKg", "WeightClassKg",
    "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg", "TotalKg",
    "Place", "Dots", "Goodlift",
    "Tested", "Country", "Federation", "ParentFederation",
    "Date", "MeetCountry", "MeetName",
]


def load_raw(csv_path):
    df = pd.read_csv(csv_path, low_memory=False, usecols=KEEP_COLS)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def apply_scope(df):
    mask = (
        (df["Equipment"] == "Raw")
        & (df["Event"] == "SBD")
        & (df["Tested"] == "Yes")
        & (df["ParentFederation"] == "IPF")
    )
    out = df.loc[mask].copy()
    out["Year"] = out["Date"].dt.year
    return out


def ingest(csv_path, output_path):
    raw = load_raw(csv_path)
    print(f"raw: {len(raw):,} rows")

    scoped = apply_scope(raw)
    print(f"scoped: {len(scoped):,} rows, {scoped['Name'].nunique():,} lifters")

    scoped.to_pickle(output_path)
    return scoped


if __name__ == "__main__":
    import sys
    csv = sys.argv[1] if len(sys.argv) > 1 else "data/openipf-2026-06-06/openipf-2026-06-06-aa0dd710.csv"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/processed/openipf_scoped.pkl"
    ingest(csv, out)
