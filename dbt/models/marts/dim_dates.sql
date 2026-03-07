{{ config(materialized='view') }}

SELECT
  CAST(date_ AS string) AS date_id,
  date_ AS date,
  UNIX_SECONDS(TIMESTAMP(date_)) AS epoch,
  FORMAT_DATE('%e', date_) AS day_suffix,
  FORMAT_DATE('%A', date_) AS day_name,
  FORMAT_DATE('%a', date_) AS day_name_abbr,
  EXTRACT(DAYOFWEEK FROM date_) AS day_of_week,
  EXTRACT(DAY FROM date_) AS day_of_month,
  EXTRACT(DAYOFYEAR FROM date_) AS day_of_year,
  EXTRACT(WEEK FROM date_) AS week_of_year,
  EXTRACT(ISOYEAR FROM date_) AS iso_year,
  FORMAT_DATE('%W', date_) AS week_of_year_iso,
  EXTRACT(MONTH FROM date_) AS month_,
  FORMAT_DATE('%B', date_) AS month_name,
  FORMAT_DATE('%b', date_) AS month_name_abbr,
  EXTRACT(QUARTER FROM date_) AS quarter_,
  EXTRACT(YEAR FROM date_) AS year_,
  CASE
    WHEN EXTRACT(DAYOFWEEK FROM date_) IN (1, 7) THEN TRUE
    ELSE FALSE
  END AS is_weekend
FROM
  UNNEST(GENERATE_DATE_ARRAY('2018-01-01', '2050-12-31', INTERVAL 1 DAY)) AS date_