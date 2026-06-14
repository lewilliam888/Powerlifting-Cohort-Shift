import numpy as np
import pandas as pd


def bootstrap_stat(data, stat_fn, n_boot=1000, seed=42):
  rng = np.random.default_rng(seed)
  n = len(data)
  out = np.empty(n_boot)
  for b in range(n_boot):
    idx = rng.integers(0, n, size=n)
    out[b] = stat_fn(data.iloc[idx] if hasattr(data, "iloc") else data[idx])
  return out


def ci(samples, level=0.95):
  lo = (1 - level) / 2
  hi = 1 - lo
  return (np.percentile(samples, lo*100), np.percentile(samples, hi*100))


def median_age_top_n(lifter_year, sex, year, n=50, n_boot=1000, seed=42):
  sub = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"]==year)]
  if len(sub) < n: return (np.nan, np.nan, np.nan)
  point = sub.nlargest(n, "Goodlift")["Age"].median()

  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for b in range(n_boot):
    rs = sub.sample(n=len(sub), replace=True, random_state=rng.integers(0, 2**31))
    top = rs.nlargest(n, "Goodlift")
    out[b] = top["Age"].median()
  lo, hi = ci(out)
  return (point, lo, hi)


def junior_share_top_n(lifter_year, sex, year, n=50, n_boot=1000, seed=42):
  sub = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"]==year)]
  if len(sub) < n: return (np.nan, np.nan, np.nan)
  point = (sub.nlargest(n, "Goodlift")["age_category"]=="Junior").mean()

  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for b in range(n_boot):
    rs = sub.sample(n=len(sub), replace=True, random_state=rng.integers(0, 2**31))
    top = rs.nlargest(n, "Goodlift")
    out[b] = (top["age_category"]=="Junior").mean()
  lo, hi = ci(out)
  return (point, lo, hi)


def peak_age_from_window(window_df, n_boot=1000, seed=42):
  if len(window_df) < 200: return (np.nan, np.nan, np.nan)

  def fit_peak(df):
    x = df["Age"].values
    y = df["Goodlift"].values
    X = np.column_stack([np.ones_like(x), x, x**2])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    if beta[2] >= 0: return np.nan
    return -beta[1] / (2*beta[2])

  point = fit_peak(window_df)

  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for b in range(n_boot):
    rs = window_df.sample(n=len(window_df), replace=True, random_state=rng.integers(0, 2**31))
    out[b] = fit_peak(rs)
  out = out[~np.isnan(out)]
  lo, hi = ci(out)
  return (point, lo, hi)


def class_pctile_diff(ly, sex, weight_class, year_a, year_b, pct=95, n_boot=1000, seed=42):
  a = ly[(ly["Sex"]==sex) & (ly["WeightClassKg"]==weight_class) & (ly["Year"]==year_a)]
  b = ly[(ly["Sex"]==sex) & (ly["WeightClassKg"]==weight_class) & (ly["Year"]==year_b)]
  if len(a)<5 or len(b)<5: return (np.nan, np.nan, np.nan)
  point = np.percentile(b["TotalKg"], pct) - np.percentile(a["TotalKg"], pct)
  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for i in range(n_boot):
    a_rs = a.sample(n=len(a), replace=True, random_state=rng.integers(0, 2**31))
    b_rs = b.sample(n=len(b), replace=True, random_state=rng.integers(0, 2**31))
    out[i] = np.percentile(b_rs["TotalKg"], pct) - np.percentile(a_rs["TotalKg"], pct)
  lo, hi = ci(out)
  return (point, lo, hi)

def median_age_diff(lifter_year, sex, year_a, year_b, n=50, n_boot=1000, seed=42):
  a = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"]==year_a)]
  b = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"]==year_b)]
  if len(a) < n or len(b) < n: return (np.nan, np.nan, np.nan)
  point = b.nlargest(n, "Goodlift")["Age"].median() - a.nlargest(n, "Goodlift")["Age"].median()
  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for i in range(n_boot):
    a_rs = a.sample(n=len(a), replace=True, random_state=rng.integers(0, 2**31))
    b_rs = b.sample(n=len(b), replace=True, random_state=rng.integers(0, 2**31))
    out[i] = b_rs.nlargest(n, "Goodlift")["Age"].median() - a_rs.nlargest(n, "Goodlift")["Age"].median()
  lo, hi = ci(out)
  return (point, lo, hi)

def median_age_diff_pooled(lifter_year, sex, years_a, years_b, n=50, n_boot=1000, seed=42):
  a = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"].isin(years_a))]
  b = lifter_year[(lifter_year["Sex"]==sex) & (lifter_year["Year"].isin(years_b))]

  def pooled_median(df, years):
    medians = []
    for yr in years:
      sub = df[df["Year"]==yr]
      if len(sub) >= n:
        medians.append(sub.nlargest(n, "Goodlift")["Age"].median())
    return np.mean(medians) if medians else np.nan

  point = pooled_median(b, years_b) - pooled_median(a, years_a)
  rng = np.random.default_rng(seed)
  out = np.empty(n_boot)
  for i in range(n_boot):
    a_rs = a.sample(n=len(a), replace=True, random_state=rng.integers(0, 2**31))
    b_rs = b.sample(n=len(b), replace=True, random_state=rng.integers(0, 2**31))
    out[i] = pooled_median(b_rs, years_b) - pooled_median(a_rs, years_a)
  lo, hi = ci(out)
  return (point, lo, hi)
