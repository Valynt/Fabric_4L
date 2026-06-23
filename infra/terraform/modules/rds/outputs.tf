output "db_instance_id" {
  description = "ID of the RDS instance"
  value       = module.db.db_instance_id
}

output "db_instance_address" {
  description = "Address of the RDS instance"
  value       = module.db.db_instance_address
}

output "db_instance_endpoint" {
  description = "Endpoint of the RDS instance"
  value       = module.db.db_instance_endpoint
}

output "db_instance_port" {
  description = "Port of the RDS instance"
  value       = module.db.db_instance_port
}

output "db_instance_name" {
  description = "Name of the default database"
  value       = module.db.db_instance_name
}

output "db_instance_username" {
  description = "Master username"
  value       = module.db.db_instance_username
}

output "db_instance_resource_id" {
  description = "Resource ID of the RDS instance"
  value       = module.db.db_instance_resource_id
}
