output "primary_endpoint" {
  description = "Primary endpoint of the Redis cluster"
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint" {
  description = "Reader endpoint of the Redis cluster"
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  description = "Port of the Redis cluster"
  value       = aws_elasticache_replication_group.this.port
}

output "security_group_id" {
  description = "Security group ID of the Redis cluster"
  value       = aws_security_group.redis.id
}
