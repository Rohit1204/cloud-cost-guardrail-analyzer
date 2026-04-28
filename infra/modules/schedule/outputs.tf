output "rule_name" {
  description = "EventBridge schedule rule name."
  value       = aws_cloudwatch_event_rule.schedule.name
}
