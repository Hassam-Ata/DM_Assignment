# Step 3: Exploratory Data Analysis

    ## Data, definitions and research purpose / Data aur maqsad
    Pandas read actual values from `data/Dataset.xlsx`, sheet `2023 data`: 8,760 consecutive hourly observations, 1 January–31 December 2023. Four blank rows, one URL footer and the unnamed auxiliary area are outside the six labelled measurement columns; no source values were changed. Step 2 documented these separately. No observations were removed, imputed or winsorized. No ML models were trained.

    Purpose: understand when solar, demand and prices change and whether they move together, before selecting any later research method. Roman Urdu: Maqsad yeh samajhna hai ke solar, load aur price kab barhte ya ghatte hain aur aapas mein kya talluq hai. Abhi training ya data cleaning nahin ki.

    `PV` and `Load` are kW; `Price` is EUR/MWh. The verified EUR/kWh and per-unit load columns are redundant scales, so correlations use one version of each variable. Timestamps have no stored timezone. Hour labels are workbook time, not assumed Pakistan time. Winter = December + January + February (the two ends of this calendar year), spring = March–May, summer = June–August, autumn = September–November. Weekends = Saturday/Sunday; holidays are not classified.

    Daytime means **PV > 0**, a generation-based proxy, not astronomical daylight. It excludes zero-generation daylight and may include small twilight readings. Energy sums assume each reading is average kW for its one-hour interval: kW × 1 hour = kWh. If these are instantaneous readings, totals are approximations. Prices use simple time means unless explicitly load-weighted.

    Roman Urdu: Units ka khayal rakha: power kW aur energy kWh hai. Daytime ke liye PV > 0 liya, jo asal sunrise/sunset ki tasdeeq nahin. Weekend Saturday/Sunday hai. Winter calendar year ke dono siron ka data hai. Yeh definitions research ko dobara chalane aur samajhne mein madad deti hain.

    ## 1. Hourly and daily behaviour / Ghantay aur din ke patterns
    Purpose: find typical operating times and separate within-day variation from day-to-day change. Hourly profiles are means over all records at that hour, not one selected day. Daily tables include mean power, summed energy, daily peak demand and mean/max prices.

    - PV generation (kW): highest mean at hour 14:00 (2884.19); lowest at 00:00 (0.00). Roman Urdu: Is variable ka average sab se zyada 14:00 aur sab se kam 00:00 par hai.
- Consumption (kW): highest mean at hour 16:00 (3587.62); lowest at 04:00 (1953.84). Roman Urdu: Is variable ka average sab se zyada 16:00 aur sab se kam 04:00 par hai.
- Price (EUR/MWh): highest mean at hour 20:00 (122.25); lowest at 14:00 (64.61). Roman Urdu: Is variable ka average sab se zyada 20:00 aur sab se kam 14:00 par hai.

    Across days, solar energy ranges from 798 to 37,278 kWh/day; demand ranges from 33,573 to 169,821 kWh/day. Mean daily solar is 17,159.8 kWh and demand 60,342.3 kWh. These ranges show that an average day does not capture all conditions. Roman Urdu: Har din aik jaisa nahin; daily energy ka range variability dikhata hai. Research mein typical profile ke saath extremes dekhna bhi zaroori hai.

    ## 2. Monthly and seasonal behaviour / Mahinay aur mausam
    Purpose: identify calendar variation and compare typical power independently of the different lengths of months. Monthly energy totals are also saved, but longer months can have higher totals simply because they contain more hours.

    - PV: highest monthly mean in month 7 (1332.65); lowest in month 12 (195.85). Roman Urdu: PV ka sab se bara monthly average mahina 7 mein aur sab se chhota mahina 12 mein mila.
- Load: highest monthly mean in month 1 (3795.97); lowest in month 7 (1872.12). Roman Urdu: Load ka sab se bara monthly average mahina 1 mein aur sab se chhota mahina 7 mein mila.
- Price: highest monthly mean in month 2 (134.23); lowest in month 11 (63.26). Roman Urdu: Price ka sab se bara monthly average mahina 2 mein aur sab se chhota mahina 11 mein mila.

    Seasonal hourly means (PV/load in kW; price in EUR/MWh):

    | Season | PV | Load | Price |
| --- | --- | --- | --- |
| Winter | 306.644 | 2919.176 | 90.517 |
| Spring | 928.279 | 2344.433 | 81.077 |
| Summer | 1183.648 | 2160.724 | 95.762 |
| Autumn | 429.406 | 2642.918 | 85.748 |

    Summer has the highest mean PV (1183.65 kW), while winter has the highest mean load (2919.18 kW). Summer also has the highest seasonal mean price (95.76 EUR/MWh), despite high PV. This helps explain why a within-day negative PV–price association need not hold between seasons.

    Roman Urdu: Garmiyon mein solar ka average sab se zyada, sardiyon mein load ka average sab se zyada mila. Garmiyon ka seasonal price bhi sab se zyada hai; is liye zyada solar ko har time scale par kam price ki guarantee nahin keh sakte.

    Roman Urdu: Upar har mausam ka asal average diya hai. Is se pata chalta hai ke production, demand aur price saal bhar mustaqil nahin. Seasonal means ko causal weather effect nahin keh sakte: weather, activity aur market conditions saath badal sakti hain. Research mein season-specific behaviour samajhne ka faida hai; aik saal se long-term climate trend sabit nahin hota.

    ## 3. Weekday and weekend / Kaam ke din aur weekend
    Purpose: check whether demand and prices differ with the weekly activity calendar. These are descriptive averages without holiday, weather or seasonal adjustment; no significance test is claimed.

    | Day type | PV | Load | Price |
| --- | --- | --- | --- |
| Weekday | 715.282 | 2738.783 | 93.812 |
| Weekend | 714.265 | 1958.308 | 74.548 |

    Weekend minus weekday: PV -1.02 kW; load -780.47 kW; price -19.26 EUR/MWh.

    The hourly graph shows a clear daytime load rise on weekdays, while weekend load stays near its overnight level. PV profiles are similar between the two groups; weekend daytime prices are lower. This is consistent with different weekly activity, but does not identify the type of consumer.

    Roman Urdu: Weekday mein din ke waqt load barhta hai; weekend ka load kaafi flat rehta hai. Solar profiles milte jultay hain aur weekend ke daytime rates kam hain. Yeh weekly activity ka pattern samajhne mein madad deta hai, consumer ki identity prove nahin karta.

    Roman Urdu: Yeh weekend aur weekday ka seedha farq hai. Solar ka farq lazmi weekend ki wajah se nahin: weather aur calendar mix ka asar ho sakta hai. Load aur price ka farq activity pattern ko investigate karne mein madad deta hai; sabab prove nahin karta.

    ## 4. Correlations and aggregation / Talluq aur averaging
    Purpose: quantify how two variables move together. Pearson measures straight-line association; Spearman measures ranked, monotonic association and is less sensitive to extreme magnitudes. Values near +1 mean moving together, near −1 mean moving oppositely, near 0 mean weak association of that kind. Correlation is not causation. Time dependence means 8,760 rows are not 8,760 independent experiments; no p-value claim is made.

    | Pair | Hourly Pearson | Daily Pearson | Daytime Pearson | Hourly Spearman | Daily Spearman |
| --- | --- | --- | --- | --- | --- |
| PV / Load | 0.245 | -0.292 | 0.086 | 0.395 | -0.272 |
| PV / Price | -0.225 | 0.128 | -0.271 | -0.213 | 0.127 |
| Load / Price | -0.067 | 0.030 | -0.021 | -0.039 | 0.188 |

    Daytime subset has 4,714 hours. Seasonal Pearson and Spearman results, including daytime-only and daily seasonal subsets, are in `correlation_pairs.csv` with sample sizes. The seasonal heatmap uses all hourly observations in each season.

    PV–load Pearson reverses from +0.245 hourly to -0.292 daily. PV–price reverses from -0.225 to +0.128. Load–price Pearson is close to zero at both scales. Daytime PV–load Pearson is only 0.086, showing that the all-hour association partly depends on the selected hours. Seasonal hourly PV–price Pearson is 0.007 in winter, -0.413 in spring, -0.453 in summer and -0.130 in autumn: its strength is not stable across seasons.

    Roman Urdu: PV aur load ka hourly talluq positive aur daily talluq negative mila. PV aur price mein bhi sign badla. Sirf daytime mein PV–load ka seedhi line wala talluq bohat kam hai. Solar–price ka negative talluq spring/summer mein winter se zyada hai. Research mein aik overall number ki bajaye time scale aur season dono dekhna zaroori hai.

    Roman Urdu: Pearson seedhi line wala talluq aur Spearman ranks ka talluq batata hai. Plus ka matlab saath barhna, minus ka matlab ulta chalna hai. Zero ke qareeb number ka matlab har qisam ka relation na hona nahin. Daytime filter se sawal aur sample dono badal jatay hain; is ka result tamam ghanton par apply nahin karna chahiye.

    ### Why hourly and daily correlations differ
    Hourly correlations mix daytime/nighttime cycles, working hours, price schedules and differences between days. Daily averages smooth those within-day changes and compare whole days, so weather, season and activity mix receive different weight. Solar zeros at night affect hourly PV correlation; daily means combine those zeros with daylight generation. Aggregation can strengthen, weaken or reverse a correlation, and reduces the number of records from 8,760 to 365. These data show the actual differences in the table above; they do not establish one single cause. Using daily energy rather than daily mean power produces the same correlation here because every day has exactly 24 stored hours.

    Roman Urdu: Hourly data mein din/raat aur office hours ka asar milta hai. Daily average in utar charhao ko smooth kar deta hai aur poore din compare karta hai. Is liye correlation badal sakta hai; yeh calculation ki ghalti zaroori nahin. Research mein hourly operating question aur daily planning question ka jawab alag scale par dekhna chahiye.

    ## 5. Solar surplus and grid deficit / Solar ki bachat aur grid ki zaroorat
    Purpose: estimate coincidence of PV and demand, assuming they refer to the same system and time intervals. Surplus = max(PV − Load, 0); deficit = max(Load − PV, 0). These are hypothetical balance measures without storage, losses, curtailment or export constraints; they are not observed meter imports/exports.

    - Annual PV: 6,263,310 kWh; demand: 22,024,941 kWh.
    - Solar surplus: 1,012,146 kWh in 770 hours (8.8% of hours).
    - Grid deficit: 16,773,777 kWh; coincident self-consumed solar: 5,251,164 kWh.
    - PV energy / demand = 28.4%; coincident solar meets 23.8% of demand. These differ because surplus at one hour cannot automatically cover demand at another.

    Roman Urdu: Solar load se zyada ho to surplus aur kam ho to deficit hai. Kul solar ka load se ratio aur usi ghantay use honay wala solar alag cheezen hain. Battery assume nahin ki; aik waqt ki bachat doosray waqt ka deficit khud cover nahin karti. Yeh research mein energy timing aur mumkin storage/export sawalat samajhne mein madad deta hai.

    ## 6. Peak demand and price / Sab se zyada load aur rate
    Purpose: check whether high demand coincides with expensive energy. Peak hours are load ≥ the annual 95th percentile (5,427.20 kW), giving 438 hours; ties can make this slightly more than 5%. Maximum demand is 11,866 kW at 2023-02-01 12:00:00, when PV is 1,772 kW and price is 107.98 EUR/MWh.

    Mean price is 78.83 EUR/MWh in peak-load hours versus 88.77 in other hours. Deficit/price Pearson is 0.083; surplus/price Pearson is -0.165. These balance measures mechanically contain load/PV, so their correlations are not independent causal effects. The price-quartile table and top-20 event tables provide event-level evidence.

    Time-average price is 88.27, while load-weighted price is 86.90 EUR/MWh. Under the one-hour assumption, valuing all demand at the hourly recorded price gives EUR 1,914,053.31; valuing only deficit gives EUR 1,518,662.94. These are illustrative energy-only amounts, not bills or net savings: no tariffs, taxes, network fees, export revenue or storage costs are included.

    Roman Urdu: Peak load ke waqt price ka comparison batata hai ke bari demand mehngay ghanton ke saath aati hai ya nahin. Load-weighted price zyada consumption walay ghanton ko zyada weight deta hai. Cost sirf recorded energy price par misaali hisaab hai, asal bill ya net saving nahin. Research mein timing ki economic ahmiyat samajh aati hai, lekin sabab ka dawa nahin hota.

    ## 7. Suspicious values: investigation without removal / Mashkook readings ki jaanch
    Purpose: distinguish review flags from confirmed errors. All observations remain in every primary result.

    Zero load occurs at these actual hours:

    | Date | PV | Load | Price |
| --- | --- | --- | --- |
| 2023-08-07 11:00:00 | 0.000 | 0.000 | 90.000 |
| 2023-08-07 12:00:00 | 0.000 | 0.000 | 90.000 |
| 2023-08-07 13:00:00 | 0.000 | 0.000 | 90.000 |
| 2023-08-07 14:00:00 | 0.000 | 0.000 | 90.000 |

    All four zero-load hours form one block on 7 August, 11:00–14:00, and PV is zero at all four hours too. At 10:00, PV/load were 907/1,630 kW; at 15:00 they were 3,164/3,381 kW. Price is 90 EUR/MWh throughout the four-hour zero block. The simultaneous loss of both power series makes a shared outage or recording problem worth checking; it is not enough evidence to select either explanation. The four clock-midday PV zeros are exactly this same block, rather than four additional events.

    Roman Urdu: 7 August ke chaar ghanton mein solar aur load dono zero hain, jab ke pehle aur baad mein dono positive hain. Aik shared outage ya recording issue mumkin hai, magar data akela final wajah nahin batata. Dono flags ko alag waqiat samajh kar double count nahin karna chahiye.

    There are 1 zero-load runs; the longest lasts 4 hour(s). There are 70 zero-price hours in 17 runs; the longest is 2023-11-05 01:00:00 through 2023-11-05 16:00:00 (16 hours). The zero-price value passes the EUR/MWh-to-EUR/kWh conversion check, which only establishes consistent scaling, not a valid market observation. Hourly neighbour windows show the recorded values before and after zero events and midday PV zeros. There are 4 PV-zero readings between hours 10 and 14; this clock-window is only a review heuristic because site location/timezone is unknown.

    Roman Urdu: Zero load ke asal timestamps upar diye hain. Zero ka matlab shutdown, outage, missing-reading code ya asal reading ho sakta hai. Price conversion sahi honay se zero market price ki authenticity prove nahin hoti. Aagay peechay ke ghantay evidence ke liye save kiye; unse value replace nahin ki. Site aur timezone ke baghair dopahar ke zero ko bhi final ghalti nahin keh sakte.

    The 1.5×IQR method flags 1011 PV, 1238 load and 9 price readings. PV/load are skewed, so genuine operational peaks can be flagged. Top demand/price tables and seasonal scatterplots allow reviewing when extremes happen. No sensor capacity, outage log or verified market extract is available to confirm physical/source errors.

    Diagnostic sensitivity (not cleaning):

    - PV / Load: all-hour Pearson 0.245; positive-load-and-price subset 0.250. Roman Urdu: Zero load aur zero price ko sirf diagnostic comparison mein alag rakhne par correlation yeh raha; asal analysis mein tamam values rakhi hain.
- PV / Price: all-hour Pearson -0.225; positive-load-and-price subset -0.222. Roman Urdu: Zero load aur zero price ko sirf diagnostic comparison mein alag rakhne par correlation yeh raha; asal analysis mein tamam values rakhi hain.
- Load / Price: all-hour Pearson -0.067; positive-load-and-price subset -0.076. Roman Urdu: Zero load aur zero price ko sirf diagnostic comparison mein alag rakhne par correlation yeh raha; asal analysis mein tamam values rakhi hain.

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
