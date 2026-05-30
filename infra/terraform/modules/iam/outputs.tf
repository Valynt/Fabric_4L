output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_role_arn" {
  description = "ARN of the EKS node IAM role"
  value       = aws_iam_role.eks_node.arn
}

output "app_service_role_arn" {
  description = "ARN of the app service IAM role"
  value       = aws_iam_role.app_service.arn
}

output "app_service_role_name" {
  description = "Name of the app service IAM role"
  value       = aws_iam_role.app_service.name
}
