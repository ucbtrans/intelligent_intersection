variable "aws_region" {
  description = "AWS region to launch servers."
  default     = "us-west-1"
}

variable "access_key" {
  default = "********"
}

variable "secret_key" {
  default = "**********************"
}


variable "default_vpc_id" {
  default = "***********"
}


variable "storage" {
  default     = "10"
  description = "Storage size in GB"
}

variable "max_storage" {
  default     = "100"
  description = "Max storage size in GB"
}

variable "storage_type" {
  default     = "gp2"
  description = "Default SSD storage"
}

variable "engine" {
  default     = "mysql"
  description = "Engine type, example values mysql, postgres"
}

variable "engine_version" {
  description = "Engine version"
  default = "5.7"
}

variable "instance_class" {
  default     = "db.t2.medium"
  description = "Instance class"
}

variable "db_name" {
  default     = "iit_db_prod"
  description = "db name"
}

variable "identifier" {
  default     = "iit-db-prod"
  description = "Identifier for the DB"
}

variable "username" {
  default     = "*******"
  description = "User name"
}

variable "password" {
  default = "******"
}

variable "tags" {
  default = { "project" = "iit" }
  type = map
}


variable "cidr_blocks" {
  default     = "0.0.0.0/0"
  description = "CIDR for sg"
}

variable "subnet_1_cidr" {
  default     = "10.1.0.0/24"
  description = "CIDR 1"
}

variable "subnet_2_cidr" {
  default     = "10.1.1.0/24"
  description = "CIDR 2"
}

variable "az_1" {
  default     = "us-west-1a"
  description = "Availibility zone"
}

variable "az_2" {
  default     = "us-west-1b"
  description = "Availibility zone"
}

variable "python_version" {
  default     = "python3.7"
  description = "Python version"
}

variable "lambda_name" {
  default     = "iit_lambda_prod"
  description = "The name of the lambda to create, which also defines"
}


variable "lambda_handler" {
  description = "The handler name of the lambda"
  default     = "lambda_handler"
}

variable "timeout" {
  description = "Lambda timeout"
  default     = 30.0
}

###############################

variable "method" {
  description = "The HTTP method"
  default     = "GET"
}

variable "path" {
  description = "The API resource path"
  default = "get"
}


