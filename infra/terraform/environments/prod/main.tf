terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "fabric-terraform-state-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "fabric-terraform-locks-prod"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "fabric"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  cluster_name = "fabric-prod"
  azs          = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
}

module "vpc" {
  source = "../../modules/vpc"

  cluster_name       = local.cluster_name
  environment        = "production"
  vpc_cidr           = "10.2.0.0/16"
  availability_zones = local.azs
  private_subnets    = ["10.2.1.0/24", "10.2.2.0/24", "10.2.3.0/24"]
  public_subnets     = ["10.2.101.0/24", "10.2.102.0/24", "10.2.103.0/24"]
  database_subnets   = ["10.2.201.0/24", "10.2.202.0/24", "10.2.203.0/24"]
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  environment        = "production"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  node_instance_types = ["m6i.2xlarge"]
  node_min_size      = 5
  node_max_size      = 20
  node_desired_size  = 5
}

module "rds" {
  source = "../../modules/rds"

  identifier          = "fabric-prod"
  environment         = "production"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.database_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  instance_class      = "db.r6g.xlarge"
  allocated_storage   = 500
  max_allocated_storage = 2000
  db_name             = "fabric"
  username            = "postgres"
  backup_retention_period = 14
}

module "elasticache" {
  source = "../../modules/elasticache"

  cluster_name        = "fabric-prod"
  environment         = "production"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  node_type           = "cache.r6g.xlarge"
  num_cache_clusters  = 3
  backup_retention_limit = 14
}

module "s3" {
  source = "../../modules/s3"

  bucket_name = "fabric-prod-assets"
  environment = "production"
}

module "iam" {
  source = "../../modules/iam"

  cluster_name      = local.cluster_name
  environment       = "production"
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
}
