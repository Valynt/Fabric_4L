terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  tags = merge(
    var.tags,
    {
      Name        = var.cluster_name
      Environment = var.environment
    },
  )

  egress_cidr_blocks = length(var.egress_cidr_blocks) > 0 ? var.egress_cidr_blocks : var.allowed_cidr_blocks
}

resource "aws_security_group" "redis" {
  name        = "${var.cluster_name}-redis"
  description = "Security group for ElastiCache Redis"
  vpc_id      = var.vpc_id
  tags        = local.tags

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Redis from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = local.egress_cidr_blocks
    description = "Redis egress limited to approved VPC/service CIDRs"
  }
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.cluster_name}-redis-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = local.tags
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = var.cluster_name
  description          = "Redis cluster for ${var.cluster_name}"

  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_clusters
  port                 = 6379
  parameter_group_name = var.parameter_group_name

  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = var.backup_retention_limit
  snapshot_window          = "03:00-04:00"

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.redis.id]

  tags = local.tags
}
