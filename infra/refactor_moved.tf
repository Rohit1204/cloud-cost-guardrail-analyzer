# State migration: root resources -> modules (Terraform 1.5+ moved blocks).
# Safe to remove after everyone has applied once with these blocks present.

moved {
  from = null_resource.lambda_build
  to   = module.lambda.null_resource.lambda_build
}

moved {
  from = data.archive_file.lambda_zip
  to   = module.lambda.data.archive_file.lambda_zip
}

moved {
  from = data.aws_iam_policy_document.lambda_assume_role
  to   = module.lambda.data.aws_iam_policy_document.lambda_assume_role
}

moved {
  from = data.aws_iam_policy_document.lambda_permissions
  to   = module.lambda.data.aws_iam_policy_document.lambda_permissions
}

moved {
  from = aws_iam_role.lambda
  to   = module.lambda.aws_iam_role.lambda
}

moved {
  from = aws_iam_role_policy.lambda
  to   = module.lambda.aws_iam_role_policy.lambda
}

moved {
  from = aws_cloudwatch_log_group.lambda
  to   = module.lambda.aws_cloudwatch_log_group.lambda
}

moved {
  from = aws_dynamodb_table.recommendation_status
  to   = module.lambda.aws_dynamodb_table.recommendation_status
}

moved {
  from = aws_lambda_function.guardrail
  to   = module.lambda.aws_lambda_function.guardrail
}

moved {
  from = aws_cloudwatch_event_rule.schedule
  to   = module.schedule.aws_cloudwatch_event_rule.schedule
}

moved {
  from = aws_cloudwatch_event_target.lambda
  to   = module.schedule.aws_cloudwatch_event_target.lambda
}

moved {
  from = aws_lambda_permission.allow_eventbridge
  to   = module.schedule.aws_lambda_permission.allow_eventbridge
}

moved {
  from = aws_apigatewayv2_api.http
  to   = module.api_gateway.aws_apigatewayv2_api.http
}

moved {
  from = aws_apigatewayv2_integration.lambda
  to   = module.api_gateway.aws_apigatewayv2_integration.lambda
}

moved {
  from = aws_apigatewayv2_route.health
  to   = module.api_gateway.aws_apigatewayv2_route.health
}

moved {
  from = aws_apigatewayv2_route.docs
  to   = module.api_gateway.aws_apigatewayv2_route.docs
}

moved {
  from = aws_apigatewayv2_route.openapi
  to   = module.api_gateway.aws_apigatewayv2_route.openapi
}

moved {
  from = aws_apigatewayv2_route.costs_summary
  to   = module.api_gateway.aws_apigatewayv2_route.costs_summary
}

moved {
  from = aws_apigatewayv2_route.recommendations
  to   = module.api_gateway.aws_apigatewayv2_route.recommendations
}

moved {
  from = aws_apigatewayv2_route.recommendations_status
  to   = module.api_gateway.aws_apigatewayv2_route.recommendations_status
}

moved {
  from = aws_apigatewayv2_route.alerts_run
  to   = module.api_gateway.aws_apigatewayv2_route.alerts_run
}

moved {
  from = aws_apigatewayv2_route.run
  to   = module.api_gateway.aws_apigatewayv2_route.run
}

moved {
  from = aws_apigatewayv2_stage.default
  to   = module.api_gateway.aws_apigatewayv2_stage.default
}

moved {
  from = aws_lambda_permission.allow_apigateway
  to   = module.api_gateway.aws_lambda_permission.allow_apigateway
}

moved {
  from = aws_s3_bucket.frontend
  to   = module.frontend_static.aws_s3_bucket.frontend
}

moved {
  from = aws_s3_bucket_ownership_controls.frontend
  to   = module.frontend_static.aws_s3_bucket_ownership_controls.frontend
}

moved {
  from = aws_s3_bucket_public_access_block.frontend
  to   = module.frontend_static.aws_s3_bucket_public_access_block.frontend
}

moved {
  from = aws_s3_bucket_versioning.frontend
  to   = module.frontend_static.aws_s3_bucket_versioning.frontend
}

moved {
  from = aws_cloudfront_origin_access_control.frontend
  to   = module.frontend_static.aws_cloudfront_origin_access_control.frontend
}

moved {
  from = aws_cloudfront_distribution.frontend
  to   = module.frontend_static.aws_cloudfront_distribution.frontend
}

moved {
  from = data.aws_iam_policy_document.frontend_bucket
  to   = module.frontend_static.data.aws_iam_policy_document.frontend_bucket
}

moved {
  from = aws_s3_bucket_policy.frontend
  to   = module.frontend_static.aws_s3_bucket_policy.frontend
}
