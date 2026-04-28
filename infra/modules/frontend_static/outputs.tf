output "bucket_name" {
  description = "S3 bucket name for static assets."
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidations."
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_url" {
  description = "HTTPS URL for the static site."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}
