terraform {
  required_version = ">= 1.14"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id

  default_labels = {
    project = "omdb-box-office-dwh"
    env     = var.env
    owner   = var.owner
  }
}

locals {
  required_apis = [
    "cloudresourcemanager.googleapis.com",
    "bigquery.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "billingbudgets.googleapis.com",
    "iamcredentials.googleapis.com",
    "dataform.googleapis.com",
  ]
}
