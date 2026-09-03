# fuel_forecast_explorer — static_obvious (5 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| data_cleaning.py:7:5 | `pd.read_csv('./data/aggregated/prices_all.csv.gz', compression='gzip')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| data_cleaning.py:20:18 | `pd.to_datetime(df['timestamp'], format='%Y%m%d %H:%M')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| data_cleaning.py:38:14 | `np.where(df.price > 2500, np.NaN, df.price)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data_cleaning.py:40:14 | `np.where(df.price < 600, np.NaN, df.price)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data_cleaning.py:45:15 | `pd.read_csv('./data/aggregated/sites_closed.csv', sep=';')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
