variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "owner" {
  description = "Owner label"
  type        = string
}

variable "billing_account" {
  description = "Billing account"
  type        = string
}

variable "env" {
  description = "Environment label"
  type        = string
  default     = "dev"
}
