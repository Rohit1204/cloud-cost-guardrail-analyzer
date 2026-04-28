variable "project_name" {
  description = "Resource name prefix."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge schedule expression."
  type        = string
}

variable "lambda_function_arn" {
  description = "Lambda function ARN to invoke."
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for permission."
  type        = string
}
