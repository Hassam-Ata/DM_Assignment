# Solar generation, demand and electricity price analysis

Python/Pandas analysis of the actual hourly observations in `data/Dataset.xlsx`,
sheet `2023 data`. The workbook is read only and its SHA-256 hash is checked
before and after each analysis. No ML models have been trained.

## Reproduce the results

Use Python 3.12. From the repository root, create an environment and install the
analysis dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python outputs/step_2/step_2_analysis.py
python outputs/step_3/step_3_eda.py
```

Both scripts resolve paths from their own file locations, so they can also be
called from another working directory. Importing a script does not run it.
Rerunning a step overwrites that step's generated outputs only.

## Results

- **Step 2:** [research report](outputs/step_2/research_report.md), descriptive
  statistics, data-quality evidence, normalization/conversion checks and three
  graph files in `outputs/step_2/`.
- **Step 3:** [EDA report](outputs/step_3/STEP_3_EDA_REPORT.md), 53 CSV tables,
  seven graph files, and a summary in `outputs/step_3/`.
- Reports explain the purpose, findings and research benefit in simple English
  and Roman Urdu. Generated results are committed so they can be reviewed
  without running Python.

## Interpretation

The analysis uses 8,760 hourly records for 2023. Blank worksheet areas and the
source-link footer are documented outside the observation table. Suspicious
measurements are flagged and retained in primary results.

Daytime means positive PV generation, a proxy rather than verified daylight.
Season definitions and weekday/weekend rules are documented in the EDA report.
Energy estimates assume each kW reading represents average power over one hour.
Grid deficit and solar surplus assume coincident PV and load without storage or
losses. Correlations describe association and depend on the aggregation scale;
they do not establish causation. The workbook does not establish a timezone.

Roman Urdu: Asal Excel se analysis hota hai aur original file tabdeel nahin hoti.
Mashkook values sirf flag hoti hain, delete nahin. Reports mein har analysis ka
maqsad aur matlab asaan alfaaz mein diya hai.
