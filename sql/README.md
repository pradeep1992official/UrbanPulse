# SQL investigations

The 15 queries are defined in notebook 04 and its matching script. This folder contains generated unfiltered query definitions for review; successful execution exports the run-specific versions to `data/mysql/<task>.sql` with each result CSV and chart. Parameterized filters use `%s` connector placeholders, including the task 15 thresholds (100 requests and 24 median hours by default). Bind values through the connector rather than pasting those placeholders directly into a SQL console.

The schema is derived from the validated preparation output and exported to `data/mysql/schema.sql`. MySQL 8 window functions provide exact medians and linearly interpolated IQR quartiles.
