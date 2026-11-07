"""Reproduce Step 3: python outputs/step_3/step_3_eda.py (no ML)."""

import hashlib
import importlib.metadata
import json
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
    T = OUT / "tables"
    G.mkdir(exist_ok=True)
    T.mkdir(exist_ok=True)
    source = ROOT / "data/Dataset.xlsx"

    def digest():
        """Fingerprint the source to verify that analysis leaves it unchanged."""
        return hashlib.sha256(source.read_bytes()).hexdigest()

    before = digest()
    raw = pd.read_excel(source, sheet_name="2023 data")
    ts = pd.to_datetime(raw.Date, errors="coerce")
    d = raw.loc[ts.notna(), raw.columns[:6]].copy()
    d["Excel row"] = d.index + 2
    d["Date"] = ts[ts.notna()]
    d = d.set_index("Date").rename(
        columns={
            "PV generation (kW)": "PV",
            "Consumption (kW)": "Load",
            "Energy price (EUR/MWh)": "Price",
        }
    )
    V = ["PV", "Load", "Price"]
    units = {
        "PV": "PV generation (kW)",
        "Load": "Consumption (kW)",
        "Price": "Price (EUR/MWh)",
    }
    assert (
        len(d) == 8760
        and d.index.is_unique
        and d.index.to_series().diff().dropna().eq(pd.Timedelta(hours=1)).all()
    )
    d["Hour"] = d.index.hour
    d["Month"] = d.index.month
    d["Day type"] = np.where(d.index.dayofweek >= 5, "Weekend", "Weekday")
    season_order = ["Winter", "Spring", "Summer", "Autumn"]
    d["Season"] = d.Month.map(
        {
            12: "Winter",
            1: "Winter",
            2: "Winter",
            3: "Spring",
            4: "Spring",
            5: "Spring",
            6: "Summer",
            7: "Summer",
            8: "Summer",
            9: "Autumn",
            10: "Autumn",
            11: "Autumn",
        }
    )
    d["Surplus"] = (d.PV - d.Load).clip(lower=0)
    d["Deficit"] = (d.Load - d.PV).clip(lower=0)
    d["Daytime proxy"] = d.PV.gt(0)

    def save(frame, name, index=True):
        frame = frame.copy()
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = ["_".join(map(str, c)) for c in frame.columns]
        frame.to_csv(T / f"{name}.csv", index=index)

    def profile(keys, name):
        a = d.groupby(keys)[V + ["Surplus", "Deficit"]].agg(
            ["count", "mean", "median", "std", "min", "max"]
        )
        save(a, name)
        return a

    profile("Hour", "hourly_profile")
    profile("Month", "monthly_profile")
    profile("Season", "seasonal_profile")
    profile("Day type", "weekday_weekend_profile")
    save(d.groupby(["Season", "Hour"])[V].mean(), "seasonal_hourly_profile")
    save(d.groupby(["Day type", "Hour"])[V].mean(), "weekday_weekend_hourly_profile")
    save(
        d.groupby(d.index.dayofweek)[V].agg(["count", "mean", "median"]),
        "day_of_week_profile",
    )
    daily = (
        d[V + ["Surplus", "Deficit"]]
        .resample("D")
        .mean()
        .rename(columns={x: x + "_mean" for x in V + ["Surplus", "Deficit"]})
    )
    for c in ["PV", "Load", "Surplus", "Deficit"]:
        daily[c + "_kWh"] = d[c].resample("D").sum()
    daily["Peak_load_kW"] = d.Load.resample("D").max()
    daily["Price_max"] = d.Price.resample("D").max()
    daily["Season"] = daily.index.month.map(
        {
            12: "Winter",
            1: "Winter",
            2: "Winter",
            3: "Spring",
            4: "Spring",
            5: "Spring",
            6: "Summer",
            7: "Summer",
            8: "Summer",
            9: "Autumn",
            10: "Autumn",
            11: "Autumn",
        }
    )
    daily["Day type"] = np.where(daily.index.dayofweek >= 5, "Weekend", "Weekday")
    save(daily, "daily_summary")
    energy = (
        d.groupby("Month")[["PV", "Load", "Surplus", "Deficit"]]
        .sum()
        .add_suffix("_kWh")
    )
    save(energy, "monthly_energy")
    save(
        d.groupby("Season")[["PV", "Load", "Surplus", "Deficit"]]
        .sum()
        .reindex(season_order)
        .add_suffix("_kWh"),
        "seasonal_energy",
    )
    cor = []

    def correlations(frame, scope, variables):
        for method in ["pearson", "spearman"]:
            mat = frame[variables].corr(method=method)
            save(mat, "correlation_" + scope + "_" + method)
            for i, a in enumerate(variables):
                for b in variables[i + 1 :]:
                    cor.append(
                        {
                            "scope": scope,
                            "method": method,
                            "variable_1": a,
                            "variable_2": b,
                            "n": int(frame[[a, b]].dropna().shape[0]),
                            "correlation": mat.loc[a, b],
                        }
                    )

    for scope, frame in [
        ("hourly_all", d),
        ("hourly_daytime_PV_positive", d[d["Daytime proxy"]]),
    ]:
        correlations(frame, scope, V + ["Surplus", "Deficit"])
    for season in season_order:
        sub = d[d.Season.eq(season)]
        correlations(sub, "hourly_" + season, V)
        correlations(sub[sub["Daytime proxy"]], "daytime_" + season, V)
        correlations(
            daily[daily.Season.eq(season)],
            "daily_" + season,
            ["PV_mean", "Load_mean", "Price_mean"],
        )
    correlations(
        daily,
        "daily_all",
        [
            "PV_mean",
            "Load_mean",
            "Price_mean",
            "Surplus_kWh",
            "Deficit_kWh",
            "Peak_load_kW",
        ],
    )
    save(pd.DataFrame(cor), "correlation_pairs", False)

    threshold = d.Load.quantile(0.95)
    d["Peak hour"] = d.Load.ge(threshold)
    peak_comparison = d.groupby("Peak hour")[V + ["Surplus", "Deficit"]].agg(
        ["count", "mean", "median", "min", "max"]
    )
    save(peak_comparison, "peak_demand_comparison")
    save(
        d.nlargest(20, "Load")[
            V + ["Season", "Hour", "Day type", "Surplus", "Deficit", "Excel row"]
        ],
        "top_20_demand_hours",
    )
    save(
        d.nlargest(20, "Price")[
            V + ["Season", "Hour", "Day type", "Surplus", "Deficit", "Excel row"]
        ],
        "top_20_price_hours",
    )
    save(
        d.groupby(d.Surplus.gt(0))[V + ["Surplus", "Deficit"]].agg(
            ["count", "mean", "median"]
        ),
        "surplus_hour_comparison",
    )
    d["Price band"] = pd.qcut(d.Price, 4, duplicates="drop")
    save(
        d.groupby("Price band", observed=True)[V + ["Surplus", "Deficit"]].agg(
            ["count", "mean", "median"]
        ),
        "price_quartile_comparison",
    )

    # Investigation flags retain original readings; neighbouring rows are evidence, not replacements.
    flags = pd.DataFrame(index=d.index)
    for c in V:
        q1, q3 = d[c].quantile([0.25, 0.75])
        iqr = q3 - q1
        flags[c + "_IQR"] = d[c].lt(q1 - 1.5 * iqr) | d[c].gt(q3 + 1.5 * iqr)
    flags["zero_load"] = d.Load.eq(0)
    flags["zero_price"] = d.Price.eq(0)
    flags["negative_measurement"] = d[V].lt(0).any(axis=1)
    flags["PV_zero_10_to_14"] = d.PV.eq(0) & d.Hour.between(10, 14)
    save(d.join(flags).loc[flags.any(axis=1)], "suspicious_values_with_context")
    targets = flags.zero_load | flags.zero_price | flags.PV_zero_10_to_14
    context = targets.copy()
    for shift in [-2, -1, 1, 2]:
        context = context | targets.shift(shift, fill_value=False)
    neighbours = d[V + ["Excel row", "Season", "Hour"]].join(flags)
    for c in V:
        neighbours[c + "_previous_hour"] = d[c].shift(1)
        neighbours[c + "_next_hour"] = d[c].shift(-1)
    save(neighbours.loc[context], "suspicious_neighbour_windows")
    save(
        d.assign(PV_zero=d.PV.eq(0), Load_zero=d.Load.eq(0), Price_zero=d.Price.eq(0))
        .groupby("Hour")[["PV_zero", "Load_zero", "Price_zero"]]
        .sum(),
        "zero_counts_by_hour",
    )
    runs = []
    for c in ["PV", "Load", "Price"]:
        z = d[c].eq(0)
        groups = z.ne(z.shift()).cumsum()
        for _, part in d[z].groupby(groups[z]):
            runs.append(
                {
                    "variable": c,
                    "start": part.index.min(),
                    "end": part.index.max(),
                    "hours": len(part),
                }
            )
    runs = pd.DataFrame(runs)
    save(runs, "zero_runs", False)

    # Counterfactual diagnostics only: exclude flagged zero load/price in a separate correlation table.
    correlations(d[d.Load.gt(0) & d.Price.gt(0)], "sensitivity_positive_load_price", V)
    save(pd.DataFrame(cor), "correlation_pairs", False)
    weighted_price = (d.Price * d.Load).sum() / d.Load.sum()
    # Assuming each kW entry represents the mean power of its one-hour interval.
    summary = {
        "hourly_records": len(d),
        "source_sha256": before,
        "PV_kWh": d.PV.sum(),
        "load_kWh": d.Load.sum(),
        "surplus_kWh": d.Surplus.sum(),
        "deficit_kWh": d.Deficit.sum(),
        "surplus_hours": int(d.Surplus.gt(0).sum()),
        "self_consumed_kWh": np.minimum(d.PV, d.Load).sum(),
        "PV_positive_hours": int(d["Daytime proxy"].sum()),
        "peak_threshold_kW": threshold,
        "peak_hours": int(d["Peak hour"].sum()),
        "peak_timestamp": str(d.Load.idxmax()),
        "peak_load_kW": d.Load.max(),
        "mean_price_EUR_MWh": d.Price.mean(),
        "load_weighted_price_EUR_MWh": weighted_price,
        "zero_load_hours": int(flags.zero_load.sum()),
        "zero_price_hours": int(flags.zero_price.sum()),
        "midday_PV_zero_hours": int(flags.PV_zero_10_to_14.sum()),
        "gross_load_cost_EUR": (d.Load * d.Price / 1000).sum(),
        "deficit_cost_EUR": (d.Deficit * d.Price / 1000).sum(),
    }

    sns.set_theme(style="whitegrid", palette="colorblind")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
        }
    )
    colors = ["#187F9C", "#DF8C35", "#8064A2"]

    def finish(fig, name):
        fig.savefig(G / (name + ".png"), bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(3, 1, figsize=(15, 10), sharex=True, layout="constrained")
    for a, c, color in zip(ax, V, colors):
        a.plot(d.index, d[c], alpha=0.22, lw=0.35, color=color, label="Hourly")
        a.plot(daily.index, daily[c + "_mean"], color=color, lw=1.1, label="Daily mean")
        a.set_ylabel(units[c])
        a.legend(loc="upper right")
    fig.suptitle("2023 | Hourly observations and daily means", fontsize=17)
    finish(fig, "01_time_series")
    fig, ax = plt.subplots(3, 2, figsize=(14, 12), layout="constrained")
    for i, c in enumerate(V):
        sns.lineplot(
            data=d,
            x="Hour",
            y=c,
            hue="Season",
            hue_order=season_order,
            estimator="mean",
            errorbar=None,
            ax=ax[i, 0],
            palette="colorblind",
        )
        sns.lineplot(
            data=d,
            x="Hour",
            y=c,
            hue="Day type",
            estimator="mean",
            errorbar=None,
            ax=ax[i, 1],
            palette=["#187F9C", "#DF8C35"],
        )
        for a in ax[i]:
            a.set_ylabel(units[c])
            a.set_xticks(range(0, 24, 3))
    ax[0, 0].set_title("Seasonal mean hourly profiles")
    ax[0, 1].set_title("Weekday / weekend mean hourly profiles")
    finish(fig, "02_hourly_profiles")
    fig, ax = plt.subplots(3, 2, figsize=(14, 12), layout="constrained")
    for i, c in enumerate(V):
        d.groupby("Month")[c].mean().plot.bar(ax=ax[i, 0], color=colors[i], rot=0)
        sns.boxplot(
            data=d,
            x="Season",
            y=c,
            order=season_order,
            ax=ax[i, 1],
            color=colors[i],
            fliersize=1,
        )
        ax[i, 0].set_ylabel(units[c])
        ax[i, 1].set_ylabel(units[c])
    ax[0, 0].set_title("Monthly hourly means")
    ax[0, 1].set_title("Seasonal hourly distributions")
    finish(fig, "03_monthly_seasonal")
    fig, ax = plt.subplots(2, 3, figsize=(16, 9), layout="constrained")
    pairs = [("PV", "Load"), ("PV", "Price"), ("Load", "Price")]
    for j, (x, y) in enumerate(pairs):
        sns.scatterplot(
            data=d,
            x=x,
            y=y,
            hue="Season",
            hue_order=season_order,
            s=8,
            alpha=0.3,
            linewidth=0,
            ax=ax[0, j],
        )
        sns.scatterplot(
            data=daily,
            x=x + "_mean",
            y=y + "_mean",
            hue="Season",
            hue_order=season_order,
            s=22,
            alpha=0.7,
            linewidth=0,
            ax=ax[1, j],
        )
        ax[0, j].set(
            xlabel=units[x], ylabel=units[y], title="Hourly: " + x + " vs " + y
        )
        ax[1, j].set(
            xlabel=units[x] + " (daily mean)",
            ylabel=units[y] + " (daily mean)",
            title="Daily: " + x + " vs " + y,
        )
    finish(fig, "04_hourly_daily_scatter")
    fig, ax = plt.subplots(2, 3, figsize=(14, 9), layout="constrained")
    for i, method in enumerate(["pearson", "spearman"]):
        for j, (label, frame, vars_) in enumerate(
            [
                ("All hours", d, V),
                ("PV > 0 hours", d[d.PV.gt(0)], V),
                ("Daily means", daily, [c + "_mean" for c in V]),
            ]
        ):
            m = frame[vars_].corr(method=method)
            m.index = V
            m.columns = V
            sns.heatmap(
                m,
                annot=True,
                fmt=".2f",
                vmin=-1,
                vmax=1,
                center=0,
                cmap="vlag",
                square=True,
                ax=ax[i, j],
            )
            ax[i, j].set_title(method.title() + " | " + label)
    finish(fig, "05_correlation_heatmaps")
    fig, ax = plt.subplots(2, 4, figsize=(16, 8), layout="constrained")
    for i, method in enumerate(["pearson", "spearman"]):
        for j, season in enumerate(season_order):
            sub = d[d.Season.eq(season)]
            sns.heatmap(
                sub[V].corr(method=method),
                annot=True,
                fmt=".2f",
                vmin=-1,
                vmax=1,
                center=0,
                cmap="vlag",
                square=True,
                ax=ax[i, j],
                cbar=j == 3,
            )
            ax[i, j].set_title(season + " | " + method.title())
    finish(fig, "06_seasonal_correlations")
    fig, ax = plt.subplots(2, 2, figsize=(15, 10), layout="constrained")
    energy[["Surplus_kWh", "Deficit_kWh"]].div(1000).rename(
        columns={"Surplus_kWh": "Surplus", "Deficit_kWh": "Deficit"}
    ).plot.bar(ax=ax[0, 0], color=["#299D8F", "#DF8C35"], rot=0)
    ax[0, 0].set(ylabel="Energy (MWh)", title="Monthly surplus and grid deficit")
    sns.scatterplot(
        data=d,
        x="Deficit",
        y="Price",
        hue="Peak hour",
        s=9,
        alpha=0.35,
        linewidth=0,
        ax=ax[0, 1],
    )
    ax[0, 1].set(
        xlabel="Grid deficit (kW)", ylabel=units["Price"], title="Deficit and price"
    )
    sns.boxplot(
        data=d, x="Peak hour", y="Price", ax=ax[1, 0], color="#80B8C2", fliersize=2
    )
    ax[1, 0].set(ylabel=units["Price"], title="Prices during top 5% load hours")
    sns.scatterplot(
        data=d, x="Surplus", y="Price", s=8, alpha=0.3, linewidth=0, ax=ax[1, 1]
    )
    ax[1, 1].set(
        xlabel="Solar surplus (kW)", ylabel=units["Price"], title="Surplus and price"
    )
    finish(fig, "07_energy_balance_price")

    def r(scope, method, a, b):
        return next(
            x["correlation"]
            for x in cor
            if x["scope"] == scope
            and x["method"] == method
            and x["variable_1"] == a
            and x["variable_2"] == b
        )

    def md(frame):
        f = frame.reset_index()
        return (
            "| "
            + " | ".join(map(str, f.columns))
            + " |\n| "
            + " | ".join(["---"] * len(f.columns))
            + " |\n"
            + "\n".join(
                "| "
                + " | ".join(
                    f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v)
                    for v in row
                )
                + " |"
                for row in f.itertuples(index=False, name=None)
            )
        )

    monthly_means = d.groupby("Month")[V].mean()
    season_means = d.groupby("Season")[V].mean().reindex(season_order)
    week_means = d.groupby("Day type")[V].mean()
    corr_compare = pd.DataFrame(
        [
            {
                "Pair": a + " / " + b,
                "Hourly Pearson": r("hourly_all", "pearson", a, b),
                "Daily Pearson": r("daily_all", "pearson", a + "_mean", b + "_mean"),
                "Daytime Pearson": r("hourly_daytime_PV_positive", "pearson", a, b),
                "Hourly Spearman": r("hourly_all", "spearman", a, b),
                "Daily Spearman": r("daily_all", "spearman", a + "_mean", b + "_mean"),
            }
            for a, b in pairs
        ]
    ).set_index("Pair")
    save(corr_compare, "hourly_daily_correlation_comparison")
    peak = d.loc[d["Peak hour"]]
    nonpeak = d.loc[~d["Peak hour"]]
    zero_load = d.loc[d.Load.eq(0), V]
    zero_price_runs = runs[runs.variable.eq("Price")].sort_values(
        "hours", ascending=False
    )
    load_runs = runs[runs.variable.eq("Load")]
    hourmeans = d.groupby("Hour")[V].mean()
    hour_findings = "\n".join(
        f"- {units[c]}: highest mean at hour {hourmeans[c].idxmax():02d}:00 ({hourmeans[c].max():.2f}); lowest at {hourmeans[c].idxmin():02d}:00 ({hourmeans[c].min():.2f}). Roman Urdu: Is variable ka average sab se zyada {hourmeans[c].idxmax():02d}:00 aur sab se kam {hourmeans[c].idxmin():02d}:00 par hai."
        for c in V
    )
    month_findings = "\n".join(
        f"- {c}: highest monthly mean in month {monthly_means[c].idxmax()} ({monthly_means[c].max():.2f}); lowest in month {monthly_means[c].idxmin()} ({monthly_means[c].min():.2f}). Roman Urdu: {c} ka sab se bara monthly average mahina {monthly_means[c].idxmax()} mein aur sab se chhota mahina {monthly_means[c].idxmin()} mein mila."
        for c in V
    )
    sensitivity = "\n".join(
        f"- {a} / {b}: all-hour Pearson {r('hourly_all', 'pearson', a, b):.3f}; positive-load-and-price subset {r('sensitivity_positive_load_price', 'pearson', a, b):.3f}. Roman Urdu: Zero load aur zero price ko sirf diagnostic comparison mein alag rakhne par correlation yeh raha; asal analysis mein tamam values rakhi hain."
        for a, b in pairs
    )
    report = f"""# Step 3: Exploratory Data Analysis

    ## Data, definitions and research purpose / Data aur maqsad
    Pandas read actual values from `data/Dataset.xlsx`, sheet `2023 data`: 8,760 consecutive hourly observations, 1 January–31 December 2023. Four blank rows, one URL footer and the unnamed auxiliary area are outside the six labelled measurement columns; no source values were changed. Step 2 documented these separately. No observations were removed, imputed or winsorized. No ML models were trained.

    Purpose: understand when solar, demand and prices change and whether they move together, before selecting any later research method. Roman Urdu: Maqsad yeh samajhna hai ke solar, load aur price kab barhte ya ghatte hain aur aapas mein kya talluq hai. Abhi training ya data cleaning nahin ki.

    `PV` and `Load` are kW; `Price` is EUR/MWh. The verified EUR/kWh and per-unit load columns are redundant scales, so correlations use one version of each variable. Timestamps have no stored timezone. Hour labels are workbook time, not assumed Pakistan time. Winter = December + January + February (the two ends of this calendar year), spring = March–May, summer = June–August, autumn = September–November. Weekends = Saturday/Sunday; holidays are not classified.

    Daytime means **PV > 0**, a generation-based proxy, not astronomical daylight. It excludes zero-generation daylight and may include small twilight readings. Energy sums assume each reading is average kW for its one-hour interval: kW × 1 hour = kWh. If these are instantaneous readings, totals are approximations. Prices use simple time means unless explicitly load-weighted.

    Roman Urdu: Units ka khayal rakha: power kW aur energy kWh hai. Daytime ke liye PV > 0 liya, jo asal sunrise/sunset ki tasdeeq nahin. Weekend Saturday/Sunday hai. Winter calendar year ke dono siron ka data hai. Yeh definitions research ko dobara chalane aur samajhne mein madad deti hain.

    ## 1. Hourly and daily behaviour / Ghantay aur din ke patterns
    Purpose: find typical operating times and separate within-day variation from day-to-day change. Hourly profiles are means over all records at that hour, not one selected day. Daily tables include mean power, summed energy, daily peak demand and mean/max prices.

    {hour_findings}

    Across days, solar energy ranges from {daily.PV_kWh.min():,.0f} to {daily.PV_kWh.max():,.0f} kWh/day; demand ranges from {daily.Load_kWh.min():,.0f} to {daily.Load_kWh.max():,.0f} kWh/day. Mean daily solar is {daily.PV_kWh.mean():,.1f} kWh and demand {daily.Load_kWh.mean():,.1f} kWh. These ranges show that an average day does not capture all conditions. Roman Urdu: Har din aik jaisa nahin; daily energy ka range variability dikhata hai. Research mein typical profile ke saath extremes dekhna bhi zaroori hai.

    ## 2. Monthly and seasonal behaviour / Mahinay aur mausam
    Purpose: identify calendar variation and compare typical power independently of the different lengths of months. Monthly energy totals are also saved, but longer months can have higher totals simply because they contain more hours.

    {month_findings}

    Seasonal hourly means (PV/load in kW; price in EUR/MWh):

    {md(season_means)}

    Summer has the highest mean PV ({season_means.loc["Summer", "PV"]:.2f} kW), while winter has the highest mean load ({season_means.loc["Winter", "Load"]:.2f} kW). Summer also has the highest seasonal mean price ({season_means.loc["Summer", "Price"]:.2f} EUR/MWh), despite high PV. This helps explain why a within-day negative PV–price association need not hold between seasons.

    Roman Urdu: Garmiyon mein solar ka average sab se zyada, sardiyon mein load ka average sab se zyada mila. Garmiyon ka seasonal price bhi sab se zyada hai; is liye zyada solar ko har time scale par kam price ki guarantee nahin keh sakte.

    Roman Urdu: Upar har mausam ka asal average diya hai. Is se pata chalta hai ke production, demand aur price saal bhar mustaqil nahin. Seasonal means ko causal weather effect nahin keh sakte: weather, activity aur market conditions saath badal sakti hain. Research mein season-specific behaviour samajhne ka faida hai; aik saal se long-term climate trend sabit nahin hota.

    ## 3. Weekday and weekend / Kaam ke din aur weekend
    Purpose: check whether demand and prices differ with the weekly activity calendar. These are descriptive averages without holiday, weather or seasonal adjustment; no significance test is claimed.

    {md(week_means)}

    Weekend minus weekday: PV {week_means.loc["Weekend", "PV"] - week_means.loc["Weekday", "PV"]:.2f} kW; load {week_means.loc["Weekend", "Load"] - week_means.loc["Weekday", "Load"]:.2f} kW; price {week_means.loc["Weekend", "Price"] - week_means.loc["Weekday", "Price"]:.2f} EUR/MWh.

    The hourly graph shows a clear daytime load rise on weekdays, while weekend load stays near its overnight level. PV profiles are similar between the two groups; weekend daytime prices are lower. This is consistent with different weekly activity, but does not identify the type of consumer.

    Roman Urdu: Weekday mein din ke waqt load barhta hai; weekend ka load kaafi flat rehta hai. Solar profiles milte jultay hain aur weekend ke daytime rates kam hain. Yeh weekly activity ka pattern samajhne mein madad deta hai, consumer ki identity prove nahin karta.

    Roman Urdu: Yeh weekend aur weekday ka seedha farq hai. Solar ka farq lazmi weekend ki wajah se nahin: weather aur calendar mix ka asar ho sakta hai. Load aur price ka farq activity pattern ko investigate karne mein madad deta hai; sabab prove nahin karta.

    ## 4. Correlations and aggregation / Talluq aur averaging
    Purpose: quantify how two variables move together. Pearson measures straight-line association; Spearman measures ranked, monotonic association and is less sensitive to extreme magnitudes. Values near +1 mean moving together, near −1 mean moving oppositely, near 0 mean weak association of that kind. Correlation is not causation. Time dependence means 8,760 rows are not 8,760 independent experiments; no p-value claim is made.

    {md(corr_compare)}

    Daytime subset has {summary["PV_positive_hours"]:,} hours. Seasonal Pearson and Spearman results, including daytime-only and daily seasonal subsets, are in `correlation_pairs.csv` with sample sizes. The seasonal heatmap uses all hourly observations in each season.

    PV–load Pearson reverses from {r("hourly_all", "pearson", "PV", "Load"):+.3f} hourly to {r("daily_all", "pearson", "PV_mean", "Load_mean"):+.3f} daily. PV–price reverses from {r("hourly_all", "pearson", "PV", "Price"):+.3f} to {r("daily_all", "pearson", "PV_mean", "Price_mean"):+.3f}. Load–price Pearson is close to zero at both scales. Daytime PV–load Pearson is only {r("hourly_daytime_PV_positive", "pearson", "PV", "Load"):.3f}, showing that the all-hour association partly depends on the selected hours. Seasonal hourly PV–price Pearson is {r("hourly_Winter", "pearson", "PV", "Price"):.3f} in winter, {r("hourly_Spring", "pearson", "PV", "Price"):.3f} in spring, {r("hourly_Summer", "pearson", "PV", "Price"):.3f} in summer and {r("hourly_Autumn", "pearson", "PV", "Price"):.3f} in autumn: its strength is not stable across seasons.

    Roman Urdu: PV aur load ka hourly talluq positive aur daily talluq negative mila. PV aur price mein bhi sign badla. Sirf daytime mein PV–load ka seedhi line wala talluq bohat kam hai. Solar–price ka negative talluq spring/summer mein winter se zyada hai. Research mein aik overall number ki bajaye time scale aur season dono dekhna zaroori hai.

    Roman Urdu: Pearson seedhi line wala talluq aur Spearman ranks ka talluq batata hai. Plus ka matlab saath barhna, minus ka matlab ulta chalna hai. Zero ke qareeb number ka matlab har qisam ka relation na hona nahin. Daytime filter se sawal aur sample dono badal jatay hain; is ka result tamam ghanton par apply nahin karna chahiye.

    ### Why hourly and daily correlations differ
    Hourly correlations mix daytime/nighttime cycles, working hours, price schedules and differences between days. Daily averages smooth those within-day changes and compare whole days, so weather, season and activity mix receive different weight. Solar zeros at night affect hourly PV correlation; daily means combine those zeros with daylight generation. Aggregation can strengthen, weaken or reverse a correlation, and reduces the number of records from 8,760 to 365. These data show the actual differences in the table above; they do not establish one single cause. Using daily energy rather than daily mean power produces the same correlation here because every day has exactly 24 stored hours.

    Roman Urdu: Hourly data mein din/raat aur office hours ka asar milta hai. Daily average in utar charhao ko smooth kar deta hai aur poore din compare karta hai. Is liye correlation badal sakta hai; yeh calculation ki ghalti zaroori nahin. Research mein hourly operating question aur daily planning question ka jawab alag scale par dekhna chahiye.

    ## 5. Solar surplus and grid deficit / Solar ki bachat aur grid ki zaroorat
    Purpose: estimate coincidence of PV and demand, assuming they refer to the same system and time intervals. Surplus = max(PV − Load, 0); deficit = max(Load − PV, 0). These are hypothetical balance measures without storage, losses, curtailment or export constraints; they are not observed meter imports/exports.

    - Annual PV: {summary["PV_kWh"]:,.0f} kWh; demand: {summary["load_kWh"]:,.0f} kWh.
    - Solar surplus: {summary["surplus_kWh"]:,.0f} kWh in {summary["surplus_hours"]:,} hours ({summary["surplus_hours"] / len(d) * 100:.1f}% of hours).
    - Grid deficit: {summary["deficit_kWh"]:,.0f} kWh; coincident self-consumed solar: {summary["self_consumed_kWh"]:,.0f} kWh.
    - PV energy / demand = {summary["PV_kWh"] / summary["load_kWh"] * 100:.1f}%; coincident solar meets {summary["self_consumed_kWh"] / summary["load_kWh"] * 100:.1f}% of demand. These differ because surplus at one hour cannot automatically cover demand at another.

    Roman Urdu: Solar load se zyada ho to surplus aur kam ho to deficit hai. Kul solar ka load se ratio aur usi ghantay use honay wala solar alag cheezen hain. Battery assume nahin ki; aik waqt ki bachat doosray waqt ka deficit khud cover nahin karti. Yeh research mein energy timing aur mumkin storage/export sawalat samajhne mein madad deta hai.

    ## 6. Peak demand and price / Sab se zyada load aur rate
    Purpose: check whether high demand coincides with expensive energy. Peak hours are load ≥ the annual 95th percentile ({threshold:,.2f} kW), giving {len(peak)} hours; ties can make this slightly more than 5%. Maximum demand is {d.Load.max():,.0f} kW at {d.Load.idxmax()}, when PV is {d.loc[d.Load.idxmax(), "PV"]:,.0f} kW and price is {d.loc[d.Load.idxmax(), "Price"]:.2f} EUR/MWh.

    Mean price is {peak.Price.mean():.2f} EUR/MWh in peak-load hours versus {nonpeak.Price.mean():.2f} in other hours. Deficit/price Pearson is {r("hourly_all", "pearson", "Price", "Deficit"):.3f}; surplus/price Pearson is {r("hourly_all", "pearson", "Price", "Surplus"):.3f}. These balance measures mechanically contain load/PV, so their correlations are not independent causal effects. The price-quartile table and top-20 event tables provide event-level evidence.

    Time-average price is {d.Price.mean():.2f}, while load-weighted price is {weighted_price:.2f} EUR/MWh. Under the one-hour assumption, valuing all demand at the hourly recorded price gives EUR {summary["gross_load_cost_EUR"]:,.2f}; valuing only deficit gives EUR {summary["deficit_cost_EUR"]:,.2f}. These are illustrative energy-only amounts, not bills or net savings: no tariffs, taxes, network fees, export revenue or storage costs are included.

    Roman Urdu: Peak load ke waqt price ka comparison batata hai ke bari demand mehngay ghanton ke saath aati hai ya nahin. Load-weighted price zyada consumption walay ghanton ko zyada weight deta hai. Cost sirf recorded energy price par misaali hisaab hai, asal bill ya net saving nahin. Research mein timing ki economic ahmiyat samajh aati hai, lekin sabab ka dawa nahin hota.

    ## 7. Suspicious values: investigation without removal / Mashkook readings ki jaanch
    Purpose: distinguish review flags from confirmed errors. All observations remain in every primary result.

    Zero load occurs at these actual hours:

    {md(zero_load)}

    All four zero-load hours form one block on 7 August, 11:00–14:00, and PV is zero at all four hours too. At 10:00, PV/load were 907/1,630 kW; at 15:00 they were 3,164/3,381 kW. Price is 90 EUR/MWh throughout the four-hour zero block. The simultaneous loss of both power series makes a shared outage or recording problem worth checking; it is not enough evidence to select either explanation. The four clock-midday PV zeros are exactly this same block, rather than four additional events.

    Roman Urdu: 7 August ke chaar ghanton mein solar aur load dono zero hain, jab ke pehle aur baad mein dono positive hain. Aik shared outage ya recording issue mumkin hai, magar data akela final wajah nahin batata. Dono flags ko alag waqiat samajh kar double count nahin karna chahiye.

    There are {len(load_runs)} zero-load runs; the longest lasts {load_runs.hours.max()} hour(s). There are {summary["zero_price_hours"]} zero-price hours in {len(zero_price_runs)} runs; the longest is {zero_price_runs.iloc[0]["start"]} through {zero_price_runs.iloc[0]["end"]} ({zero_price_runs.iloc[0]["hours"]} hours). The zero-price value passes the EUR/MWh-to-EUR/kWh conversion check, which only establishes consistent scaling, not a valid market observation. Hourly neighbour windows show the recorded values before and after zero events and midday PV zeros. There are {summary["midday_PV_zero_hours"]} PV-zero readings between hours 10 and 14; this clock-window is only a review heuristic because site location/timezone is unknown.

    Roman Urdu: Zero load ke asal timestamps upar diye hain. Zero ka matlab shutdown, outage, missing-reading code ya asal reading ho sakta hai. Price conversion sahi honay se zero market price ki authenticity prove nahin hoti. Aagay peechay ke ghantay evidence ke liye save kiye; unse value replace nahin ki. Site aur timezone ke baghair dopahar ke zero ko bhi final ghalti nahin keh sakte.

    The 1.5×IQR method flags {int(flags.PV_IQR.sum())} PV, {int(flags.Load_IQR.sum())} load and {int(flags.Price_IQR.sum())} price readings. PV/load are skewed, so genuine operational peaks can be flagged. Top demand/price tables and seasonal scatterplots allow reviewing when extremes happen. No sensor capacity, outage log or verified market extract is available to confirm physical/source errors.

    Diagnostic sensitivity (not cleaning):

    {sensitivity}

    Roman Urdu: IQR unusual value ka signal hai, final error nahin. Sirf sensitivity mein zero load/price walay hours ko alag karke correlation dobara dekha. Yeh conditional sample hai aur asli analysis ka badal nahin. Research mein pata chalta hai ke kuch flagged readings overall relation ko kitna affect karti hain.

    ## Graph guide and reproducibility / Graphs aur dobara chalana
    1. `01_time_series.png`: hourly lines and daily means reveal variability across the year. Roman Urdu: Saal bhar ka utar charhao aur daily trend nazar aata hai.
    2. `02_hourly_profiles.png`: seasonal and weekday/weekend hourly means identify timing. Roman Urdu: Kis ghantay kis group ka average zyada hai, compare hota hai.
    3. `03_monthly_seasonal.png`: monthly means and seasonal boxplots show levels and spread. Roman Urdu: Mahinay ka average aur mausam ka phailao samajh aata hai.
    4. `04_hourly_daily_scatter.png`: all actual observations (no random sampling) compare time scales, coloured by season. Roman Urdu: Dots se hourly aur daily talluq ka farq dikhta hai.
    5. `05_correlation_heatmaps.png`: Pearson/Spearman for all hours, PV-positive hours and daily means. Roman Urdu: Mukhtalif filters aur methods ka numeric talluq aik jagah milta hai.
    6. `06_seasonal_correlations.png`: all-hour seasonal matrices check calendar dependence. Roman Urdu: Talluq har mausam mein aik jaisa hai ya nahin, pata chalta hai.
    7. `07_energy_balance_price.png`: surplus/deficit energy, price scatter and peak-hour price comparison. Roman Urdu: Solar ki timing aur grid/price ki zaroorat ka talluq samajh aata hai.

    Run from repository root: `python outputs/step_3/step_3_eda.py`. Dependencies are pinned in `requirements.txt`. Tables include counts, units in the names/definitions, pairwise sample sizes, event timestamps and source Excel rows. `assessment_summary.json` records totals and the unchanged source hash. Tables retain full calculation precision; report numbers are rounded. No statistical significance or generalization beyond this single year/site is claimed.

    Roman Urdu: Code dobara chala kar yahi outputs ban sakte hain. Original Excel ki hash pehle aur baad mein match ki. Aik saal ke patterns ko har saal ka guaranteed rule nahin samajhna chahiye. Yeh EDA baad ki research ke sawalat clear karta hai; ML abhi shuru nahin hua.
    """
    (OUT / "STEP_3_EDA_REPORT.md").write_text(report.rstrip() + "\n", encoding="utf-8")
    assert digest() == before, "Original workbook changed"
    summary["source_sha256_after"] = digest()
    (OUT / "assessment_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    (OUT / "requirements.txt").write_text(
        "".join(
            f"{package}=={importlib.metadata.version(package)}\n"
            for package in [
                "pandas",
                "numpy",
                "openpyxl",
                "matplotlib",
                "seaborn",
                "scipy",
                "contourpy",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, default=str))
    print(corr_compare.to_string())
    print(season_means.to_string())


if __name__ == "__main__":
    main()
