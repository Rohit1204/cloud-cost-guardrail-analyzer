cd infra
terraform fmt --recursive
AWS_PROFILE=cloud-cost-bot terraform plan
AWS_PROFILE=cloud-cost-bot terraform apply --auto-approve