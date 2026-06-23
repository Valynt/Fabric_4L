terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "fabric-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "fabric-terraform-locks-dev"
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
      Environment = "dev"
      Project     = "fabric"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  cluster_name = "fabric-dev"
  azs          = ["${var.aws_region}a", "${var.aws_region}b"]
}

module "vpc" {
  source = "../../modules/vpc"

  cluster_name       = local.cluster_name
  environment        = "dev"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = local.azs
  private_subnets    = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets     = ["10.0.101.0/24", "10.0.102.0/24"]
  database_subnets   = ["10.0.201.0/24", "10.0.202.0/24"]
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  environment        = "dev"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  node_instance_types = ["m6i.large"]
  node_min_size      = 2
  node_max_size      = 5
  node_desired_size  = 2
}

module "rds" {
  source = "../../modules/rds"

  identifier          = "fabric-dev"
  environment         = "dev"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.database_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  instance_class      = "db.t3.medium"
  allocated_storage   = 50
  db_name             = "fabric"
  username            = "postgres"
  backup_retention_period = 1
}

module "elasticache" {
  source = "../../modules/elasticache"

  cluster_name        = "fabric-dev"
  environment         = "dev"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [module.vpc.vpc_cidr]
  node_type           = "cache.t3.micro"
  num_cache_clusters  = 1
  backup_retention_limit = 1
}

module "s3" {
  source = "../../modules/s3"

  bucket_name = "fabric-dev-assets"
  environment = "dev"
}

module "iam" {
  source = "../../modules/iam"

  cluster_name      = local.cluster_name
  environment       = "dev"
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
}
