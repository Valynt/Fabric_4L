# Fabric_4L Terraform Infrastructure

Terraform modules and environments for deploying the Fabric_4L platform on AWS.

## Structure

```
modules/
  vpc/          — VPC, subnets, NAT gateways
  eks/          — EKS cluster with managed node groups
  rds/          — PostgreSQL Multi-AZ with backup retention
  elasticache/  — Redis cluster with failover
  s3/           — S3 buckets with lifecycle rules
  iam/          — EKS roles, node roles, IRSA for services

environments/
  dev/          — Development environment
  staging/      — Staging environment
  prod/         — Production environment
```

## Prerequisites

- Terraform >= 1.5.0
- AWS CLI configured with appropriate credentials
- S3 bucket and DynamoDB table for remote state (see `scripts/init-backend.sh`)

## Usage

### Initialize backend

```bash
cd infra/terraform/scripts
./init-backend.sh
```

### Deploy an environment

```bash
cd infra/terraform/environments/dev
terraform init
terraform plan
terraform apply
```

## Modules

### VPC

Creates a VPC with public, private, and database subnets across multiple AZs.

### EKS

Creates an EKS cluster with managed node groups, auto-scaling, and essential addons (CNI, EBS CSI, etc.).

### RDS

Creates a PostgreSQL instance with:
- Multi-AZ in production
- Encrypted storage
- Backup retention
- Performance Insights
- CloudWatch monitoring

### ElastiCache

Creates a Redis cluster with:
- Automatic failover (production)
- At-rest and transit encryption
- Multi-AZ (production)

### S3

Creates an S3 bucket with:
- Versioning
- Server-side encryption
- Lifecycle transitions (Standard-IA, Glacier)
- Public access blocked

### IAM

Creates IAM roles for:
- EKS cluster
- EKS worker nodes
- Application services (IRSA)

## State Management

Remote state is stored in S3 with DynamoDB locking:
- `fabric-terraform-state-{env}` — S3 bucket
- `fabric-terraform-locks-{env}` — DynamoDB table
