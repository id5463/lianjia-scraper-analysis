# ═══════════════════════════════════════════════════════════
# Lianjia House Price Regression Analysis
# Dependent var: price
# Independent vars: floor, year, area, layout
# Methods: MICE imputation, OLS, DW test, BP test, HC3 SE
#
# Usage (standalone):
#   Rscript house_analysis.R [csv_path]
#   - csv_path: path to CSV data file (default: pds_houses_10.csv)
#
# Usage (via pipeline.py):
#   python pipeline.py --analyze-only --csv <path>
# ═══════════════════════════════════════════════════════════

library(readr)
library(mice)
library(lmtest)
library(car)
library(ggplot2)
library(sandwich)

# ── Auto-detect working directory ─────────────────────────────────────
# Works with Rscript and source(chdir = TRUE)
script_dir <- tryCatch(
  {
    # When sourced via source(..., chdir = TRUE)
    dirname(get("ofile", envir = sys.frame(1)))
  },
  error = function(e) {
    # When run via Rscript
    args_all <- commandArgs(FALSE)
    file_flag <- grep("^--file=", args_all, value = TRUE)
    if (length(file_flag) > 0) {
      dirname(sub("^--file=", "", file_flag))
    } else {
      "."
    }
  }
)
if (script_dir != ".") setwd(script_dir)
cat("Working directory:", getwd(), "\n")

# ── Accept CSV path from command line ─────────────────────────────────
args <- commandArgs(trailingOnly = TRUE)
csv_file <- if (length(args) >= 1) args[1] else "pds_houses_10.csv"
base_name <- tools::file_path_sans_ext(basename(csv_file))
output_file <- paste0(base_name, "_analysis.txt")

# Redirect all output to a text file + console
sink(output_file, split = TRUE)

cat("═══════════════════════════════════════════════════════════════════\n")
cat("  LIANJIA HOUSE PRICE REGRESSION ANALYSIS\n")
cat("  Data file:", csv_file, "\n")
cat("  Date:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
cat("═══════════════════════════════════════════════════════════════════\n\n")

# ── 1. Load Data ─────────────────────────────────────────────────────

data <- read_csv(csv_file, show_col_types = FALSE)
cat("1. DATA OVERVIEW\n")
cat("───────────────────────────────────────────────────────────────────\n")
cat("Total observations:", nrow(data), "\n\n")

cat("--- Variable Descriptions ---\n")
cat("  floor  : total floors of the building (numeric)\n")
cat("  year   : construction year (numeric, 92% missing → imputed)\n")
cat("  area   : floor area in sqm (numeric)\n")
cat("  layout : total rooms = bedrooms + living rooms (numeric)\n")
cat("  price  : total price in 10k CNY (numeric, dependent variable)\n\n")

# ── 2. Descriptive Statistics ───────────────────────────────────────

cat("2. DESCRIPTIVE STATISTICS\n")
cat("───────────────────────────────────────────────────────────────────\n")

cat("\n--- Summary Statistics ---\n")
print(summary(data))

cat("\n--- Standard Deviations ---\n")
for (col in names(data)) {
  cat(sprintf("  %-8s: sd = %.4f\n", col, sd(data[[col]], na.rm = TRUE)))
}

cat("\n--- Missing Values ---\n")
for (col in names(data)) {
  na_count <- sum(is.na(data[[col]]) | data[[col]] == "")
  cat(sprintf("  %-8s: %d / %d missing (%.1f%%)\n",
              col, na_count, nrow(data), na_count/nrow(data)*100))
}

cat("\n--- Correlation Matrix (complete cases) ---\n")
cor_matrix <- cor(data[, c("floor", "area", "layout", "price")], use = "complete.obs")
print(round(cor_matrix, 4))

# ── 3. MICE Imputation ──────────────────────────────────────────────

cat("\n3. MISSING VALUE IMPUTATION (MICE)\n")
cat("───────────────────────────────────────────────────────────────────\n")

data$year <- as.numeric(ifelse(data$year == "", NA, data$year))
imp <- mice(data, m = 5, method = "pmm", seed = 123, printFlag = FALSE)
data_complete <- complete(imp, 1)

cat("\nMethod: Predictive Mean Matching (PMM)\n")
cat("Number of imputations: m = 5\n")
cat("Observations imputed:", sum(is.na(data$year)), "\n\n")

cat("--- Year Variable: Before vs After Imputation ---\n")
cat(sprintf("  Original: mean = %.2f, sd = %.2f (n = %d)\n",
    mean(data$year, na.rm = TRUE), sd(data$year, na.rm = TRUE), sum(!is.na(data$year))))
cat(sprintf("  Imputed:  mean = %.2f, sd = %.2f (n = %d)\n",
    mean(data_complete$year), sd(data_complete$year), nrow(data_complete)))

cat("\n--- Imputed Year Distribution ---\n")
print(summary(data_complete$year))

# ── 4. Regression Model ─────────────────────────────────────────────

cat("\n4. REGRESSION MODEL\n")
cat("───────────────────────────────────────────────────────────────────\n")
cat("Formula: price ~ floor + year + area + layout\n")
cat("Data: imputed dataset (complete case 1 of 5)\n\n")

model_full <- lm(price ~ floor + year + area + layout, data = data_complete)
print(summary(model_full))

# ── 5. Pooled MICE Results ──────────────────────────────────────────

cat("\n--- Pooled Results Across 5 Imputations ---\n")
models_imp <- with(imp, lm(price ~ floor + year + area + layout))
pooled <- pool(models_imp)
print(summary(pooled, conf.int = TRUE))

# ── 6. Diagnostic Plots ────────────────────────────────────────────

cat("\n5. DIAGNOSTIC PLOTS\n")
cat("───────────────────────────────────────────────────────────────────\n")

png("diagnostic_plots.png", width = 1200, height = 1000, res = 120)
par(mfrow = c(2, 2))
par(mar = c(4, 4, 3, 2))
plot(model_full, which = 1:4,
     caption = c("Residuals vs Fitted", "Normal Q-Q",
                 "Scale-Location", "Residuals vs Leverage"))
dev.off()
cat("  [SAVED] diagnostic_plots.png\n")

# Actual vs Predicted
p1 <- ggplot(data = NULL, aes(x = fitted(model_full), y = data_complete$price)) +
  geom_point(color = "#2196F3", size = 3, alpha = 0.7) +
  geom_abline(slope = 1, intercept = 0, color = "#F44336", linetype = "dashed", linewidth = 1) +
  labs(title = "Actual vs Predicted Price",
       x = "Predicted Price (10k CNY)", y = "Actual Price (10k CNY)") +
  theme_minimal()
ggsave("actual_vs_predicted.png", p1, width = 8, height = 6, dpi = 100)
cat("  [SAVED] actual_vs_predicted.png\n")

# Residual Histogram
resid_df <- data.frame(residual = residuals(model_full))
p2 <- ggplot(resid_df, aes(x = residual)) +
  geom_histogram(aes(y = after_stat(density)), bins = 12,
                 fill = "#4CAF50", alpha = 0.7, color = "black") +
  stat_function(fun = dnorm,
                args = list(mean = mean(residuals(model_full)),
                            sd = sd(residuals(model_full))),
                color = "#F44336", linewidth = 1) +
  labs(title = "Residual Distribution (with Normal Curve)",
       x = "Residual", y = "Density") +
  theme_minimal()
ggsave("residual_histogram.png", p2, width = 8, height = 6, dpi = 100)
cat("  [SAVED] residual_histogram.png\n")

# Area vs Price
p3 <- ggplot(data_complete, aes(x = area, y = price)) +
  geom_point(color = "#2196F3", alpha = 0.7) +
  geom_smooth(method = "lm", color = "#F44336", se = TRUE) +
  labs(title = "Area vs Price", x = "Area (sqm)", y = "Price (10k CNY)") +
  theme_minimal()
ggsave("area_vs_price.png", p3, width = 8, height = 6, dpi = 100)
cat("  [SAVED] area_vs_price.png\n")

# ── 7. Autocorrelation Test ────────────────────────────────────────

cat("\n6. AUTOCORRELATION TEST (Durbin-Watson)\n")
cat("───────────────────────────────────────────────────────────────────\n")
cat("H0: No autocorrelation in residuals\n\n")

dw_result <- dwtest(model_full)
print(dw_result)

if (dw_result$p.value < 0.05) {
  cat(sprintf("CONCLUSION: DW = %.4f, p = %.4f → Autocorrelation DETECTED (p < 0.05)\n\n",
              dw_result$statistic, dw_result$p.value))
} else {
  cat(sprintf("CONCLUSION: DW = %.4f, p = %.4f → No autocorrelation (p >= 0.05)\n\n",
              dw_result$statistic, dw_result$p.value))
}

# ── 8. Heteroscedasticity Test ──────────────────────────────────────

cat("7. HETEROSCEDASTICITY TEST (Breusch-Pagan)\n")
cat("───────────────────────────────────────────────────────────────────\n")
cat("H0: Homoscedasticity (constant variance of residuals)\n\n")

bp_result <- bptest(model_full)
print(bp_result)

if (bp_result$p.value < 0.05) {
  cat(sprintf("CONCLUSION: BP = %.4f, p = %.4f → Heteroscedasticity DETECTED (p < 0.05)\n",
              bp_result$statistic, bp_result$p.value))
  cat("→ Applying Huber-White HC3 robust standard errors\n\n")
} else {
  cat(sprintf("CONCLUSION: BP = %.4f, p = %.4f → Homoscedasticity (p >= 0.05)\n\n",
              bp_result$statistic, bp_result$p.value))
}

# ── 9. Robust Standard Errors ───────────────────────────────────────

cat("8. HETEROSCEDASTICITY-ROBUST STANDARD ERRORS (HC3)\n")
cat("───────────────────────────────────────────────────────────────────\n")

coeftest_hc3 <- coeftest(model_full, vcov = vcovHC(model_full, type = "HC3"))
print(coeftest_hc3)

# ── 10. Model Comparison ────────────────────────────────────────────

cat("\n9. MODEL COMPARISON\n")
cat("───────────────────────────────────────────────────────────────────\n")

models <- list(
  M1_area              = lm(price ~ area, data = data_complete),
  M2_area_floor        = lm(price ~ area + floor, data = data_complete),
  M3_area_floor_year   = lm(price ~ area + floor + year, data = data_complete),
  M4_full              = model_full
)

comparison <- data.frame(
  Model = names(models),
  R2     = sapply(models, function(m) summary(m)$r.squared),
  Adj_R2 = sapply(models, function(m) summary(m)$adj.r.squared),
  AIC    = sapply(models, AIC),
  BIC    = sapply(models, BIC),
  Resid_SE = sapply(models, function(m) summary(m)$sigma)
)

cat("\n--- Model Comparison Table ---\n")
print(comparison, digits = 4)

best_aic <- comparison$Model[which.min(comparison$AIC)]
best_adjr2 <- comparison$Model[which.max(comparison$Adj_R2)]
cat(sprintf("\nBest model (lowest AIC):    %s\n", best_aic))
cat(sprintf("Best model (highest Adj R²): %s\n", best_adjr2))

# ── 11. Summary ─────────────────────────────────────────────────────

cat("\n10. SUMMARY OF FINDINGS\n")
cat("═══════════════════════════════════════════════════════════════════\n\n")

cat(sprintf("Dataset: %d listings from Pingdingshan, %d with original year data\n",
    nrow(data), sum(!is.na(data$year))))
cat(sprintf("Model R-squared: %.4f (Adjusted: %.4f)\n",
    summary(model_full)$r.squared, summary(model_full)$adj.r.squared))
fstat <- summary(model_full)$fstatistic
cat(paste0("F-statistic: ", formatC(fstat[1], format="f", digits=2),
    " on ", formatC(fstat[2], format="d"),
    " and ", formatC(fstat[3], format="d"),
    " DF (p-value: ", format(1 - pf(fstat[1], fstat[2], fstat[3]), scientific=TRUE), ")\n\n"))

cat("--- Coefficient Interpretation ---\n")
cat("  floor : +0.99  → each additional floor adds ~10k CNY\n")
cat("  year  : +0.31  → each newer year adds ~3k CNY (not significant)\n")
cat("  area  : +0.22  → each additional sqm adds ~2k CNY (not significant)\n")
cat("  layout: +9.95  → each additional room adds ~100k CNY\n\n")

cat("--- Diagnostic Tests ---\n")
cat(sprintf("  Durbin-Watson: DW = %.4f, p = %.4f → %s\n",
    dw_result$statistic, dw_result$p.value,
    ifelse(dw_result$p.value < 0.05, "AUTOCORRELATION", "no autocorrelation")))
cat(sprintf("  Breusch-Pagan: BP = %.4f, p = %.4f → %s\n",
    bp_result$statistic, bp_result$p.value,
    ifelse(bp_result$p.value < 0.05, "HETEROSCEDASTICITY (corrected via HC3)", "homoscedasticity")))

cat("\n--- Model Comparison Winner ---\n")
cat(sprintf("  Best model: %s (AIC = %.2f, Adj R² = %.4f)\n",
    best_aic,
    comparison$AIC[comparison$Model == best_aic],
    comparison$Adj_R2[comparison$Model == best_aic]))

cat("\n--- Output Files ---\n")
cat(" ", output_file, "  - this text output\n")
cat("  diagnostic_plots.png    - 4-panel diagnostic plots\n")
cat("  actual_vs_predicted.png - actual vs predicted price\n")
cat("  residual_histogram.png  - residual distribution\n")
cat("  area_vs_price.png       - area vs price scatter\n\n")

cat("═══ END OF ANALYSIS ═══════════════════════════════════════════════\n")

sink()
