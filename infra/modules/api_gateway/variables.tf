variable "project_name" {
  description = "Resource name prefix."
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for invoke permissions."
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Lambda invoke ARN for API Gateway integration."
  type        = string
}

variable "frontend_allowed_origins" {
  description = "Allowed browser origins for CORS."
  type        = list(string)
}

variable "alerts_run_throttle_rate_limit" {
  type = number
}

variable "alerts_run_throttle_burst_limit" {
  type = number
}
