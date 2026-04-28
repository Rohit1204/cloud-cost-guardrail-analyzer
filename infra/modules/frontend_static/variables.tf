variable "project_name" {
  description = "Resource name prefix."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for static assets."
  type        = string
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
}
