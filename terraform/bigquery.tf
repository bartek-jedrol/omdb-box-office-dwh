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
