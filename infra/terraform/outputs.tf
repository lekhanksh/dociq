output "alb_dns_name" {
  description = "Internal ALB DNS — use this as your backend API endpoint within the VPC"
  value       = aws_lb.internal.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.app.name
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
