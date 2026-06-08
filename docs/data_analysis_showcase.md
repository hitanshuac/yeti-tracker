# Yeti-Tracker: Data Analysis Showcase

*This data presentation is structured in strict accordance with the Google Data Analytics Professional Certificate frameworks: APPASA, SMART, and PACE. It leverages a localized DuckDB pipeline to analyze the massive "Personal Carbon Footprint Behavior" dataset.*

---

## Phase 1: Ask
**Objective**: Define the problem and establish clear, data-driven goals to influence climate-positive habits.

We defined the primary objective of Yeti-Tracker using the **SMART** framework:
- **Specific**: Identify the single lifestyle behavior (Diet, Transport, or Energy) that contributes the most to a user's daily carbon footprint.
- **Measurable**: Ensure the analytical query latency remains under 1 second using DuckDB, while accurately aggregating over 2,200 kg of tracked CO2e.
- **Action-oriented**: Provide personalized insights that drive immediate behavioral changes, shifting away from generic advice.
- **Relevant**: Addresses the growing demand for personal climate accountability through data, not guesswork.
- **Time-bound**: Deliver actionable insights based on a 200-day rolling dataset.

## Phase 2: Prepare
**Objective**: Determine how the data will be collected, stored, and managed.

To respect the $0 budget constraint and ensure extreme data privacy, we engineered a local ingestion layer directly into DuckDB.
- **Data Source**: A synthetic dataset mirroring Kaggle's "Personal Carbon Footprint Behavior", containing 200 daily records with dimensions like `transport_mode`, `food_type`, and `electricity_kwh`.
- **Storage**: Raw data is dynamically queried directly via DuckDB's `read_csv_auto` engine, bypassing the need for heavy external databases.
- **Ethics & Privacy**: By running processing entirely locally, user behavioral data never touches a public cloud API.

## Phase 3: Process
**Objective**: Clean, transform, and validate the data to ensure integrity.

Our data engineering pipeline acts as the sanitation gateway:
- **Validation**: Strict schema checks ensure that fields like `carbon_footprint_kg` are never negative.
- **Transformation**: The dataset is loaded into a strongly-typed Parquet/DuckDB format, enabling highly performant column-store aggregations without memory bloat.

## Phase 4: Analyze
**Objective**: Discover insights using the **PACE** (Plan, Analyze, Construct, Execute) methodology.

We constructed our analytical models directly inside DuckDB. The initial hypothesis was that *Transportation* would be the primary driver of emissions. The data proved this completely false.

### Deep Dive Insight 1: Diet is the Strongest Predictor
When aggregating the data by `food_type`, a massive disparity emerged:

| Diet Type | Total Days | Total CO2 (kg) | Average CO2/Day (kg) |
| :--- | :--- | :--- | :--- |
| **Non-Veg** | 59 | 902.95 | **15.30** |
| **Mixed** | 69 | 703.25 | **10.19** |
| **Veg** | 72 | 600.43 | **8.34** |

**Finding**: A strictly Non-Veg diet nearly *doubles* the daily carbon footprint compared to a Veg diet (15.3 kg vs 8.3 kg). 

### Deep Dive Insight 2: The "Walking Paradox"
We analyzed transportation modes to find the most eco-friendly option.

| Transport Mode | Total Days | Total CO2 (kg) | Average CO2/Day (kg) |
| :--- | :--- | :--- | :--- |
| **Walk** | 55 | 586.01 | **10.65** |
| **Car** | 31 | 437.93 | **14.13** |
| **Bus** | 31 | 367.12 | **11.84** |

**Finding**: While "Car" days have the highest average daily footprint (14.13 kg), days where the user recorded "Walk" still generated a massive 10.65 kg of CO2 on average. 
**Why?** This is a classic example of multi-variate masking. Walking generates 0 emissions, but because *Diet* and *Electricity* are such dominant factors, they completely eclipse the savings from walking. 

### Deep Dive Insight 3: Electricity vs Screen Time (Mythbusting)
To further validate assumptions, we ran a Pearson correlation matrix across our continuous variables (`electricity_kwh`, `distance_km`, `screen_time_hours`) against the total `carbon_footprint_kg`.

| Behavioral Metric | Pearson Correlation (to CO2e) | Impact Level |
| :--- | :--- | :--- |
| **Electricity Usage** | 0.42 | Strong Predictor |
| **Distance Traveled** | 0.31 | Moderate Predictor |
| **Screen Time** | -0.03 | Zero Impact |

**Finding**: Home electricity usage is a massive predictor of footprint. Furthermore, this debunks the myth that high screen time (watching TV, using a PC) significantly increases your footprint. In this dataset, screen time has practically zero correlation (-0.03) to the final carbon output.

## Phase 5: Share
**Objective**: Present the findings clearly to stakeholders.

These insights are dynamically surfaced on the Yeti-Tracker Dashboard. Instead of showing the user generic charts, the backend identifies their specific "Biggest Carbon Source" (e.g., Diet) and highlights it prominently.

**Example SQL Aggregation powering the Dashboard:**
```sql
SELECT 
    food_type, 
    COUNT(*) as days_logged, 
    SUM(carbon_footprint_kg) as total_co2, 
    AVG(carbon_footprint_kg) as avg_co2 
FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') 
GROUP BY food_type 
ORDER BY total_co2 DESC
```

## Phase 6: Act
**Objective**: Use the insights to drive data-driven decision-making.

By presenting this structured data, we shift the user's focus from ineffective actions to high-yield behavioral changes.
- **Data-Driven Action**: Instead of telling the user to "Walk more" (which the data shows is easily eclipsed by bad habits elsewhere), the dashboard explicitly advises them: **"Substitute 3 Non-Veg days with Veg days this week to cut your total footprint by ~30%."**
