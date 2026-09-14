resource "random_id" "landing_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "landing" {
  name                        = "landing-${random_id.landing_suffix.hex}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle {
    prevent_destroy = true
  }
}
