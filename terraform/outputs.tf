output "landing_bucket_name" {
  description = "Bucket for raw source files"
  value       = google_storage_bucket.landing.name
}
