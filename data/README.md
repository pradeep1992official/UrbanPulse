# Local data

Run extraction and preparation to generate the canonical dataset filenames. Data files are excluded from new tracking because they are large and contain record-level locations and free text.

Existing `nyc_311_100k.csv` and `nyc_311_cleaned.csv` files belong to the earlier workflow. They are not interchangeable with the new 16-source-field / 41-final-column contract. Do not rename them and invent extraction metadata. Either run notebook 01 or bring the matching raw snapshot and its genuine metadata from the original Colab run.
