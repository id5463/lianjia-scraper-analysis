# Lianjia House Scraper & Analysis 链家二手房爬虫与分析

**Scrape second-hand house listings from Lianjia (Beike) and run regression analysis in one pipeline.**

**从链家/贝壳爬取二手房数据，并通过回归分析一键出报告。**

---

## Why This Project 为什么做这个

Buying a house is a big decision, but the raw data on listing sites doesn't tell you much. This project started as a personal tool to answer a simple question: **what actually drives house prices in a city?**

It scrapes structured data (floor, area, layout, year, price) from Lianjia/Beike, then runs a full econometric analysis — MICE imputation for missing data, OLS regression, autocorrelation and heteroscedasticity tests, robust standard errors, and model comparison. Results come out as a readable text report plus diagnostic charts.

All in one `pipeline.py` command, or use the scraper and analyzer independently.

---

## Project Structure 项目结构

```
lianjia-scraper-analysis/
├── scrape_lianjia.py          # Crawler: scrape listings from ke.com
├── house_analysis.R           # Analyzer: MICE + OLS regression in R
├── pipeline.py                # Orchestrator: run both or either
├── pds_houses_10.csv          # Sample data: 50 listings from Pingdingshan
├── pds_houses_10_analysis.txt # Sample output: full analysis report
├── diagnostic_plots.png       # 4-panel diagnostic plots
├── actual_vs_predicted.png    # Actual vs predicted price scatter
├── residual_histogram.png     # Residual distribution
├── area_vs_price.png          # Area vs price scatter
├── LICENSE                    # Unlicense — do whatever you want
└── README.md                  # This file
```

---

## Dependencies 依赖

### Python

| Package | Version | Purpose |
|---------|---------|---------|
| selenium | ≥4.x | Browser automation for scraping |
| webdriver-manager | ≥4.x | Auto-download ChromeDriver |

Install:

```bash
pip install selenium webdriver-manager
```

> **Note**: Requires Google Chrome installed at the default path. The crawler launches a headed browser — you'll see the window pop up and may need to solve CAPTCHAs manually.

### R

| Package | Purpose |
|---------|---------|
| readr | CSV loading |
| mice | Multiple imputation for missing year data |
| lmtest | Durbin-Watson & Breusch-Pagan tests |
| car | Companion to applied regression |
| ggplot2 | Diagnostic charts |
| sandwich | HC3 heteroscedasticity-robust standard errors |

Install in R:

```r
install.packages(c("readr", "mice", "lmtest", "car", "ggplot2", "sandwich"))
```

---

## ⚠️ Important: CAPTCHA Handling ⚠️ 重要：验证码处理

Beike (ke.com) frequently presents CAPTCHAs during automated browsing. The crawler **does not solve them automatically**. Instead:

1. A headed Chrome browser window will pop up
2. If a CAPTCHA is detected, your PC **beeps 5 times** and the script waits
3. **Solve the CAPTCHA manually** in the browser window
4. **Press the `Alt` key** (one tap) to let the script continue
5. If still blocked, it beeps again — solve and press `Alt` once more

> The Alt key is edge-triggered: one press = one attempt. No need to hold it down.

贝壳/链家经常弹出验证码。爬虫 **不会自动处理验证码**：

1. 会弹出一个有头 Chrome 浏览器窗口
2. 检测到验证码时，电脑会 **响 5 声提示音**，脚本暂停等待
3. **在浏览器窗口中手动通过验证**
4. **按一下 `Alt` 键**（轻触即可），脚本继续
5. 如果仍然被拦截，会再次响铃 — 重复以上步骤

> Alt 键是边缘触发：按一下算一次，不需要长按。

---

## Usage 用法

### Pipeline (recommended) 完整管道（推荐）

```bash
# Full pipeline: crawl → analyze
python pipeline.py --city pds --count 50

# Crawl only, no analysis
python pipeline.py --crawl-only --city bj --count 100

# Analyze only (use latest CSV for that city)
python pipeline.py --analyze-only --city pds

# Analyze only (specify a CSV file)
python pipeline.py --analyze-only --csv my_data.csv

# Specify Rscript path if auto-detection fails
python pipeline.py --city pds --r-path "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
```

### Standalone 独立使用

```bash
# Crawler
python scrape_lianjia.py --city pds --count 99

# Analyzer (defaults to pds_houses_10.csv)
Rscript house_analysis.R
Rscript house_analysis.R my_data.csv
```

### City Abbreviations 城市缩写

Use the Pinyin abbreviation from the Beike URL. Examples:

| City 城市 | URL | `--city` value |
|-----------|-----|----------------|
| Pingdingshan 平顶山 | pds.ke.com | `pds` |
| Beijing 北京 | bj.ke.com | `bj` |
| Shanghai 上海 | sh.ke.com | `sh` |
| Shenzhen 深圳 | sz.ke.com | `sz` |
| Xi'an 西安 | xa.ke.com | `xa` |

---

## What the Analysis Does 分析内容

1. **Data overview** — summary stats, missing values, correlations
2. **MICE imputation** — Predictive Mean Matching for ~92% missing year data
3. **OLS regression** — `price ~ floor + year + area + layout`
4. **Pooled MICE results** — averaged across 5 imputations
5. **Diagnostic plots** — residuals, Q-Q, scale-location, leverage
6. **Durbin-Watson test** — autocorrelation check
7. **Breusch-Pagan test** — heteroscedasticity check → HC3 robust SE if needed
8. **Model comparison** — 4 nested models (AIC, BIC, Adj R²)

Output: one `.txt` report + 4 `.png` charts.

---

## Sample Results 示例结果

Using 50 listings from Pingdingshan (92% missing year data imputed via MICE):

| Metric | Value |
|--------|-------|
| R² | 0.7404 |
| Adj R² | 0.7173 |
| DW (autocorrelation) | 1.97, p=0.47 → none detected |
| BP (heteroscedasticity) | 14.41, p=0.006 → corrected via HC3 |

Key findings: **floor** and **layout** are significant predictors of price; **year** and **area** are not (in this small sample).

---

## License 许可

**Unlicense** — This is free and unencumbered software released into the public domain. Do whatever you want with it. No warranty, no strings attached.

**Unlicense** — 本软件已放弃版权，属于公有领域。你可以随意使用、修改、分发、商用。无任何担保。

See [LICENSE](./LICENSE) for details.
