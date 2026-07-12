# polars-book-cn — static_obvious (15 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| days_month.py:5:5 | `pl.date_range(low=datetime(2021, 1, 1), high=datetime(2021, 12, 31)...` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:5:5 | `pl.date_range(low=datetime(2021, 1, 1), high=datetime(2021, 12, 31)...` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:5:23 | `datetime(2021, 1, 1)` | library / datetime | library / datetime | - | static_obvious | v: direct import-backed API call |
| days_month.py:5:50 | `datetime(2021, 12, 31)` | library / datetime | library / datetime | - | static_obvious | v: direct import-backed API call |
| days_month.py:11:12 | `pl.col('time')` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:11:12 | `pl.col('time').cumcount()` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:11:12 | `pl.col('time').cumcount().reverse()` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:11:12 | `pl.col('time').cumcount().reverse().head(3)` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:11:12 | `pl.col('time').cumcount().reverse().head(3).alias('day/eom')` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:12 | `((pl.col('time') - pl.col('time').first()).last().dt.days() + 1).al...` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:13 | `(pl.col('time') - pl.col('time').first()).last().dt.days()` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:13 | `(pl.col('time') - pl.col('time').first()).last()` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:14 | `pl.col('time')` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:31 | `pl.col('time')` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
| days_month.py:12:31 | `pl.col('time').first()` | library / polars | library / polars | - | static_obvious | v: direct import-backed API call |
