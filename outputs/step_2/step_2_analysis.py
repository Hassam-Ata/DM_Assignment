"""Read-only Step 2 assessment. Run: python outputs/step_2/step_2_analysis.py"""

import hashlib
import json
import platform
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def main():
    """Generate the assessment outputs from the unchanged source workbook."""
    ROOT = Path(__file__).resolve().parents[2]
    OUT = Path(__file__).resolve().parent
    G = OUT / "graphs"
    G.mkdir(exist_ok=True)
    SOURCE = ROOT / "data" / "Dataset.xlsx"

    def sha():
        """Fingerprint the source to verify that analysis leaves it unchanged."""
        return hashlib.sha256(SOURCE.read_bytes()).hexdigest()

    before = sha()
    raw = pd.read_excel(SOURCE, sheet_name="2023 data")
    core = list(raw.columns[:6])
    cols = core[1:]
    # Datetimes are selected by type, avoiding accidental parsing of the URL footer.
    dates = pd.to_datetime(raw["Date"], errors="coerce")
    mask = dates.notna()
    d = raw.loc[mask, core].copy()
    d["Date"] = dates[mask]
    excel_rows = pd.Series(d.index + 2, index=d.index)
    numeric = d[cols].apply(pd.to_numeric, errors="coerce")
    schema = pd.DataFrame(
        {
            "column": raw.columns,
            "raw_dtype": raw.dtypes.astype(str).values,
            "nonmissing_raw": raw.notna().sum().values,
            "missing_raw": raw.isna().sum().values,
            "role": ["timestamp"]
            + ["measurement"] * 5
            + ["unlabelled auxiliary / empty"] * (len(raw.columns) - 6),
        }
    )
    schema.to_csv(OUT / "column_inventory.csv", index=False)
    raw.loc[~mask].assign(excel_row=lambda x: x.index + 2).to_csv(
        OUT / "non_observation_rows.csv", index=False
    )
    aux = []
    for c in raw.columns[6:]:
        for i, v in raw[c].dropna().items():
            aux.append({"excel_row": i + 2, "column": c, "value": v})
    pd.DataFrame(aux).to_csv(OUT / "auxiliary_cells.csv", index=False)
    stats = numeric.describe().T.rename(
        columns={
            "min": "Min",
            "max": "Max",
            "mean": "Mean",
            "50%": "Median",
            "std": "Std",
            "25%": "Q1",
            "75%": "Q3",
            "count": "Count",
        }
    )
    stats = stats[["Count", "Min", "Max", "Mean", "Median", "Std", "Q1", "Q3"]]
    stats.to_csv(OUT / "descriptive_statistics.csv", index_label="column")
    quality = []
    flags = []
    for c in cols:
        s = numeric[c]
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        tests = {
            "missing": d[c].isna(),
            "non_numeric": d[c].notna() & s.isna(),
            "non_finite": s.notna() & ~np.isfinite(s),
            "zero": s.eq(0),
            "negative": s.lt(0),
            "IQR_outlier": s.lt(low) | s.gt(high),
        }
        quality.append(
            {
                "column": c,
                **{k: int(v.sum()) for k, v in tests.items()},
                "IQR_lower": low,
                "IQR_upper": high,
            }
        )
        for kind, m in tests.items():
            for i in d.index[m]:
                flags.append(
                    {
                        "excel_row": int(excel_rows[i]),
                        "Date": d.at[i, "Date"],
                        "column": c,
                        "check": kind,
                        "value": d.at[i, c],
                    }
                )
    q = pd.DataFrame(quality).set_index("column")
    q.to_csv(OUT / "quality_summary.csv")
    pd.DataFrame(flags).to_csv(OUT / "flagged_values.csv", index=False)
    dup = d.duplicated(keep=False)
    dup_t = d["Date"].duplicated(keep=False)
    d.assign(excel_row=excel_rows).loc[dup | dup_t].to_csv(
        OUT / "duplicate_records.csv", index=False
    )
    expected = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h")
    unique = pd.DatetimeIndex(d.Date.drop_duplicates().sort_values())
    missing = expected.difference(unique)
    extra = unique.difference(expected)
    pd.DataFrame({"missing_timestamp": missing}).to_csv(
        OUT / "missing_timestamps.csv", index=False
    )
    ordered = d.Date.sort_values()
    delta = ordered.diff()
    pd.DataFrame({"Date": ordered, "interval": delta}).loc[
        delta.notna() & delta.ne(pd.Timedelta(hours=1))
    ].to_csv(OUT / "timestamp_irregularities.csv", index=False)
    base = numeric["Consumption (kW)"].max()
    norm_expected = numeric["Consumption (kW)"] / base
    price_expected = numeric["Energy price (EUR/MWh)"] / 1000
    norm_error = (numeric["Consumption (pu)"] - norm_expected).abs()
    price_error = (numeric["Energy price (EUR/kWh)"] - price_expected).abs()
    tolerance = 1e-10
    checks = pd.DataFrame(
        {
            "excel_row": excel_rows,
            "Date": d.Date,
            "expected_consumption_pu": norm_expected,
            "actual_consumption_pu": numeric["Consumption (pu)"],
            "normalization_abs_error": norm_error,
            "expected_EUR_kWh": price_expected,
            "actual_EUR_kWh": numeric["Energy price (EUR/kWh)"],
            "price_abs_error": price_error,
        }
    )
    checks.to_csv(OUT / "normalization_conversion_checks.csv", index=False)
    summary = {
        "source": "data/Dataset.xlsx",
        "sheet": "2023 data",
        "raw_shape": list(raw.shape),
        "hourly_shape": list(d.shape),
        "date_min": str(d.Date.min()),
        "date_max": str(d.Date.max()),
        "fully_blank_rows": int(raw.isna().all(axis=1).sum()),
        "nondate_nonempty_rows": int((~mask & raw.notna().any(axis=1)).sum()),
        "unnamed_nonempty_cells": len(aux),
        "fully_empty_columns": int(raw.isna().all().sum()),
        "duplicate_rows_excess": int(d.duplicated().sum()),
        "duplicate_timestamps_excess": int(d.Date.duplicated().sum()),
        "missing_hours": len(missing),
        "outside_2023": len(extra),
        "non_increasing_source_intervals": int(
            d.Date.diff().dropna().le(pd.Timedelta(0)).sum()
        ),
        "non_hour_aligned": int(d.Date.ne(d.Date.dt.floor("h")).sum()),
        "normalization_base_kW": float(base),
        "normalization_max_abs_error": float(norm_error.max()),
        "normalization_mismatches": int((norm_error > tolerance).sum()),
        "price_max_abs_error": float(price_error.max()),
        "price_mismatches": int((price_error > tolerance).sum()),
        "absolute_tolerance": tolerance,
        "source_sha256_before": before,
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }

    sns.set_theme(style="whitegrid", context="notebook", palette="deep")
    plt.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 200,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    def panels(kind):
        fig, axes = plt.subplots(3, 2, figsize=(13, 12), layout="constrained")
        for ax, c in zip(axes.flat, cols):
            if kind == "distributions":
                sns.histplot(numeric[c], bins=45, ax=ax, color="#207A96")
                ax.set_ylabel("Hourly records")
            else:
                sns.boxplot(
                    x=numeric[c], ax=ax, color="#67B5B0", fliersize=2, linewidth=1
                )
                ax.set_xlabel(c)
            ax.set_title(c, fontsize=11)
        axes.flat[-1].axis("off")
        fig.suptitle(
            "2023 hourly data | "
            + (
                "Value distributions"
                if kind == "distributions"
                else "Boxplots: potential extremes (1.5 × IQR)"
            ),
            fontsize=17,
        )
        fig.savefig(G / f"{kind}.png")
        plt.close(fig)

    panels("distributions")
    panels("boxplots")
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), layout="constrained")
    raw.isna().mean().mul(100).plot.bar(ax=axes[0], color="#207A96")
    axes[0].set(title="Raw worksheet: missing cells by column", ylabel="Missing (%)")
    axes[0].tick_params(axis="x", labelsize=8, rotation=65)
    d.isna().sum().plot.barh(ax=axes[1], color="#67B5B0")
    axes[1].set(
        title="Hourly observation table: no missing cells in the six core columns",
        xlabel="Missing cells",
        xlim=(0, 1),
    )
    fig.savefig(G / "missing_values.png")
    plt.close(fig)
    summary["source_sha256_after"] = sha()
    assert before == summary["source_sha256_after"], "Source file changed"
    (OUT / "assessment_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    def table(frame):
        # Markdown without optional tabulate dependency.
        f = frame.reset_index()
        header = "| " + " | ".join(map(str, f.columns)) + " |\n"
        return (
            header
            + "| "
            + " | ".join(["---"] * len(f.columns))
            + " |\n"
            + "\n".join(
                "| "
                + " | ".join(
                    f"{v:.6g}" if isinstance(v, (float, np.floating)) else str(v)
                    for v in row
                )
                + " |"
                for row in f.itertuples(index=False, name=None)
            )
        )

    report = f"""# Step 2: Data Quality Assessment & Descriptive Statistics

    ## Scope and method / Kaam ka daira
    Actual values were read with Pandas from `data/Dataset.xlsx`, sheet `2023 data`. No values were filled, deleted from the source, or corrected. No Step 3 or ML training was performed. SHA-256 before and after: `{before}` (identical).

    Roman Urdu: Asal Excel values par analysis hua. Original file mein koi tabdeeli nahin ki. Sirf Step 2 ki jaanch aur statistics banaye gaye.

    ## 1. Structure and dates / Data ki banawat
    Purpose: establish what one record means before calculating statistics. The raw import has {raw.shape[0]:,} rows and {raw.shape[1]} columns, excluding the Excel header. There are {len(d):,} hourly observations, six labelled core columns, {summary["fully_empty_columns"]} fully empty columns and five unnamed columns with {len(aux)} auxiliary values of unknown meaning. Four blank rows and one URL footer are outside the observation table. These are documented separately; unnamed values were not silently treated as measurements. `column_inventory.csv` preserves all imported column types and missing counts. Date is initially object because it mixes datetimes and the URL; all five core measurements import as float64.

    Hourly coverage is {d.Date.min()} through {d.Date.max()}, with no timezone stored in the timestamps. We do not assume a local timezone or daylight-saving rule.

    Roman Urdu: Har asal row aik ghantay ka record hai. Sheet ke aakhir mein 4 khaali rows aur aik source link hai. Unnamed columns ki 20 values ka matlab clear nahin, is liye unhein alag record kiya. Is se statistics mein ghair mutaliqa cells shamil nahin hotay aur research ka data scope saaf rehta hai.

    ## 2. Missing values, duplicates and invalid data / Data ki jaanch
    Purpose: detect incomplete or repeated observations and impossible representations. The core hourly table has {int(d.isna().sum().sum())} missing cells, {summary["duplicate_rows_excess"]} excess duplicate full rows, and {summary["duplicate_timestamps_excess"]} excess duplicate timestamps. There are {int(q.non_numeric.sum())} non-numeric measurements and {int(q.non_finite.sum())} non-finite measurements. All {len(d)} observations are in 2023 and aligned to full hours. The URL footer is metadata, not an invalid hourly observation. Raw-sheet missing counts include intentionally blank areas; they must not be confused with missing hourly measurements.

    Roman Urdu: Asal hourly table mein missing value ya duplicate record nahin mila. Number wali columns mein text ya infinity bhi nahin mili. Khaali side columns ko missing hourly data kehna ghalat hota. Yeh jaanch research mein completeness aur double counting ko samajhne mein madad karti hai.

    ## 3. Zeros, negatives and outliers / Zero aur intehai values
    Purpose: identify values needing context. Outliers use Q1 − 1.5 × IQR and Q3 + 1.5 × IQR, where IQR = Q3 − Q1. These are review flags, not proof of errors. No automatic removal was done. Negative generation/load would be suspicious under the stated generation/consumption meanings; negative market prices could be valid. No site capacity or sensor specification is provided, so positive values cannot all be certified physically valid.

    {table(q[["zero", "negative", "IQR_outlier", "IQR_lower", "IQR_upper"]])}

    PV zeros can reflect no sunlight, but this assessment cannot prove every zero is correct. Consumption zeros may represent shutdown, outage or missing readings encoded as zero; source confirmation is needed. Zero electricity prices may be real or placeholders and also need source confirmation. High PV/load values may be legitimate peaks. Both price columns and both consumption columns describe the same underlying quantities, so their flags are not independent events.

    Roman Urdu: Zero ko missing nahin samjha. Solar ka zero dhoop na honay ki wajah se ho sakta hai. Load ka zero shutdown ya meter ka masla bhi ho sakta hai. Price ka zero asal rate ya placeholder ho sakta hai. IQR sirf unusual values dikhata hai; yeh lazmi ghalti nahin. Is liye koi value remove nahin ki. Research mein peaks aur mumkin measurement issues alag samajhne mein madad milti hai.

    ## 4. Timestamp gaps / Waqt ka tasalsul
    Purpose: compare unique timestamps to all 8,760 expected hours of the non-leap year 2023. Missing hours: {len(missing)}; outside-year timestamps: {len(extra)}; non-increasing intervals in original order: {summary["non_increasing_source_intervals"]}. All consecutive sorted observations are one hour apart. This verifies the stored naive hourly grid, not timezone correctness.

    Roman Urdu: 2023 ke tamam 8,760 ghantay maujood hain aur har agla record aik ghantay baad hai. Koi gap nahin mila. Is se time-based research mein sequence par bharosa barhta hai, lekin timezone ki tasdeeq nahin hoti.

    ## 5. Descriptive statistics / Buniyadi statistics
    Purpose: summarize typical size, spread and extremes. Mean is the average; median is the middle value; sample Std (ddof=1) measures spread; Q1 and Q3 are the 25th and 75th percentiles (Pandas linear interpolation). Only the five core numerical measurements enter this table; auxiliary numbers have no defined variable meaning. All {len(d):,} observations, including zeros and outlier flags, are retained.

    {table(stats)}

    Roman Urdu: Mean average hai, median beech ki value hai, aur Std values ka phailao batata hai. Q1 tak 25% aur Q3 tak 75% values hoti hain. PV ka mean {stats.loc[cols[0], "Mean"]:.2f} kW aur median {stats.loc[cols[0], "Median"]:.2f} kW hai; yeh unequal distribution dikhata hai. Load ka mean {stats.loc[cols[1], "Mean"]:.2f} kW hai. Research mein typical demand, variability aur peak levels samajhne ke liye yeh numbers kaam aate hain.

    ## 6. Normalization and unit conversion / Scale aur units ki tasdeeq
    The actual column name is `Consumption (pu)` (the requested p.u. variable). Every row matches `Consumption (kW) / 11866`, where 11,866 kW is the observed annual maximum. Maximum absolute difference: {norm_error.max():.3g}; mismatches at absolute tolerance {tolerance}: {summary["normalization_mismatches"]}. Values are between 0 and 1. This verifies numerical consistency with annual-maximum scaling. Because the minimum load is zero, min–max scaling gives the same values; the intended normalization method/base cannot be uniquely established without documentation. Stored cells are numeric values, not formulas.

    Every price row matches `EUR/kWh = EUR/MWh / 1000`: 1 MWh equals 1,000 kWh. Maximum absolute difference: {price_error.max():.3g}; mismatches: {summary["price_mismatches"]}. This verifies the unit arithmetic, not the correctness of the underlying market prices or source timezone. For example, the maximum 220 EUR/MWh becomes 0.220 EUR/kWh.

    Roman Urdu: Har load value ko 11,866 se divide karne par workbook ka pu milta hai. Zero minimum ki wajah se min–max ka result bhi yahi hai, is liye asal method documentation ke baghair final nahin keh sakte. Price ko 1,000 se divide karna har row mein sahi mila. Is se units ki wajah se 1,000 guna ghalti se bacha ja sakta hai. Yeh sirf verification hai; nayi scaling ya training nahin ki gayi.

    ## 7. Graphs / Tasaveer
    - `graphs/distributions.png`: histograms show frequency and skew, using original units and zeros. PV has many low/zero values and a right tail; consumption also has a high-value tail.
    - `graphs/boxplots.png`: separate axes preserve each unit; dots show the IQR flags, which need interpretation.
    - `graphs/missing_values.png`: distinguishes raw-sheet blank areas from the complete six-column hourly table.

    Roman Urdu: Histogram batata hai konsi values zyada aati hain. Boxplot unusual values ko nazar mein lata hai. Missing graph side ke khaali cells aur asal data ka farq dikhata hai. Yeh graphs research findings ko asani se explain karne mein madad karte hain.

    ![Distributions](graphs/distributions.png)
    ![Boxplots](graphs/boxplots.png)
    ![Missing values](graphs/missing_values.png)

    ## Conclusion and saved evidence / Natija aur files
    The hourly grid is complete and the two derived columns are numerically consistent. The main unresolved questions are the meaning of auxiliary cells and the authenticity of zero/large readings. No cleaning or later research step was performed.

    Roman Urdu: Ghanton ka record mukammal hai aur conversion checks sahi hain. Extra cells aur zero/bohat bari values ki source se tasdeeq baqi hai. Original data mehfooz hai; Step 3 shuru nahin hua.

    CSV evidence: column inventory, non-observation rows, auxiliary cells, descriptive statistics, quality summary, flagged values (including zeros), duplicate records, missing timestamps, timestamp irregularities, and row-by-row normalization/conversion checks. Excel row numbers include the header, so the first observation is row 2. JSON records headline checks, source hashes and runtime versions. Reproduce from repository root with `python outputs/step_2/step_2_analysis.py`; dependencies are in `requirements.txt`.
    """
    (OUT / "research_report.md").write_text(report.rstrip() + "\n", encoding="utf-8")
    (OUT / "requirements.txt").write_text(
        f"pandas=={pd.__version__}\nnumpy=={np.__version__}\nopenpyxl==3.1.5\nmatplotlib=={matplotlib.__version__}\nseaborn=={sns.__version__}\ncontourpy==1.3.3\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(q.to_string())


if __name__ == "__main__":
    main()
