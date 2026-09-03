# CustomSamplers — static_obvious (8 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| plotSizeVsRT.py:3:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:5:5 | `numpy.genfromtxt('test.csv', skiprows=1, delimiter=',')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:12:0 | `plt.plot(size, latency, '*')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:13:0 | `plt.title('RT vs Size')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:14:0 | `plt.xlabel('size [MB]')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:15:0 | `plt.ylabel('response time [ms]')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:16:0 | `plt.ticklabel_format(style='plain')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plotSizeVsRT.py:18:0 | `plt.savefig('testPlot.png', dpi=100)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
