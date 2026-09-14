locals {
  datasets = {
    raw          = "Source data as delivered: box office CSV and OMDb responses"
    staging      = "One model per source, same shape and grain as the source"
    intermediate = "Joins across sources, aggregations and OMDb match rules"
    mart         = "Dimensional model for reporting"
    assertions   = "Dataform data quality test results"
  }
}

resource "google_bigquery_dataset" "datasets" {
  for_each    = local.datasets
  dataset_id  = each.key
  description = each.value
  project     = var.project_id
  location    = var.region

  delete_contents_on_destroy = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_table" "box_office" {
  dataset_id          = google_bigquery_dataset.datasets["raw"].dataset_id
  table_id            = "box_office"
  project             = var.project_id
  description         = "Daily box office CSV as delivered. All columns are STRING"
  deletion_protection = false

  external_data_configuration {
    source_format = "CSV"
    autodetect    = false
    schema        = file("${path.module}/schemas/box_office.json")
    source_uris   = ["gs://${google_storage_bucket.landing.name}/box_office/revenues_per_day.csv"]

    csv_options {
      quote             = "\""
      skip_leading_rows = 1
    }
  }
}
