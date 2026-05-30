terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "fabric-terraform-state-staging"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "fabric-terraform-locks-staging"
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
      Environment = "staging"
      Project     = "fabric"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  cluster_name = "fabric-staging"
  azs          = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
}

module "vpc" {
  source = "../../modules/vpc"

  cluster_name       = local.cluster_name
  environment        = "staging"
  vpc_cidr           = "10.1.0.0/16"
  availability_zones = local.azs
  private_subnets    = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  public_subnets     = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]
  database_subnets   = ["10.1.201.0/24", "10.1.202.0/24", "10.1.203.0/24"]
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  environment        = "staging"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  node_instance_types = ["m6i.xlarge"]
  node_min_size      = 3
  node_max_size      = 8
  node_desired_size  = 3
}

module "rds" {
  source = "../../modules/rds"

  identifier          = "fabric-staging"
  environment         = "staging"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.database_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  instance_class      = "db.r6g.large"
  allocated_storage   = 100
  db_name             = "fabric"
  username            = "postgres"
  backup_retention_period = 3
}

module "elasticache" {
  source = "../../modules/elasticache"

  cluster_name        = "fabric-staging"
  environment         = "staging"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  node_type           = "cache.r6g.large"
  num_cache_clusters  = 2
  backup_retention_limit = 3
}

module "s3" {
  source = "../../modules/s3"

  bucket_name = "fabric-staging-assets"
  environment = "staging"
}

module "iam" {
  source = "../../modules/iam"

  cluster_name      = local.cluster_name
  environment       = "staging"
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
}
