# Specify the provider and access details
provider "aws" {
  region = var.aws_region
  access_key = var.access_key
  secret_key = var.secret_key
  version = "~> 2.0"
}

resource "aws_default_vpc" "default" {
	lifecycle { prevent_destroy = true }
}


# Get default security groups
data "aws_security_groups" "sgroups" {
  filter {
    name   = "vpc-id"
    values = ["${var.default_vpc_id}"]
  }
   filter {
    name   = "group-name"
    values = ["default"]
  }
}

data "aws_security_group" "group_instances" {
  count = length(data.aws_security_groups.sgroups.ids)
  id = data.aws_security_groups.sgroups.ids[count.index]
}

output "prod_group_id" {
  value = data.aws_security_group.group_instances[0].id
}


# Get default subnet ids
data "aws_subnet_ids" "prod_subnet_ids" {
  vpc_id = var.default_vpc_id
}


# Capture subnets from the default VPC
data "aws_subnet" "prod_subnet" {
  count = "${length(data.aws_subnet_ids.prod_subnet_ids.ids)}"
  id    = "${tolist(data.aws_subnet_ids.prod_subnet_ids.ids)[count.index]}"
}

output "prod_subnets" {
  value = "${data.aws_subnet.prod_subnet.*.id}"
}

#  create a layer for Lambda functions
resource "aws_lambda_layer_version" "lambda_layer" {
  filename   = "pymysql.zip"
  layer_name = "pymysql_prod" 
  compatible_runtimes = [var.python_version]
}

data "aws_caller_identity" "current" { }


output "account_id" {
  value = "${data.aws_caller_identity.current.account_id}"
}

output "caller_arn" {
  value = "${data.aws_caller_identity.current.arn}"
}

output "caller_user" {
  value = "${data.aws_caller_identity.current.user_id}"
}

# Create Lambda role
resource "aws_iam_role" "iam_role_for_lambda_prod" {
  name = "iam_role_for_lambda_prod"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}


# This section defines lambda code source
data "archive_file" "iit_lambda_prod" {
  type        = "zip"
  source_dir = "../lambda"
  output_path = "./${var.lambda_name}.zip"
}

# Lambda 
resource "aws_lambda_function" "lambda" {
  depends_on = [aws_iam_role.iam_role_for_lambda_prod]
  filename      = "${var.lambda_name}.zip"
  source_code_hash = data.archive_file.iit_lambda_prod.output_base64sha256
  function_name = var.lambda_name
  role          = aws_iam_role.iam_role_for_lambda_prod.arn
  handler       = "lambda.${var.lambda_handler}"
  runtime       = var.python_version
  timeout		= var.timeout
  layers        = [aws_lambda_layer_version.lambda_layer.arn]
  tags          = var.tags
}


# API Gateway

resource "aws_api_gateway_rest_api" "iit-prod-api" {
  name = "iit-prod"
  description = "IIT Prod API"
}

resource "aws_api_gateway_resource" "iit-prod-get" {
  rest_api_id = aws_api_gateway_rest_api.iit-prod-api.id
  parent_id   = aws_api_gateway_rest_api.iit-prod-api.root_resource_id
  path_part   = "get"
}


############################################
# Request for GET 
resource "aws_api_gateway_method" "request_method" {
  rest_api_id   = aws_api_gateway_rest_api.iit-prod-api.id
  resource_id   = aws_api_gateway_resource.iit-prod-get.id
  http_method   = var.method
  authorization = "NONE"
}

# GET 
resource "aws_api_gateway_integration" "request_method_integration" {
  rest_api_id   = aws_api_gateway_rest_api.iit-prod-api.id
  resource_id   = aws_api_gateway_resource.iit-prod-get.id
  http_method = aws_api_gateway_method.request_method.http_method
  type        = "AWS_PROXY"
  uri         = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.lambda_name}/invocations"

  # AWS lambdas can only be invoked with the POST method
  integration_http_method = "POST"
}

# lambda => GET response
resource "aws_api_gateway_method_response" "response_method" {
  rest_api_id   = aws_api_gateway_rest_api.iit-prod-api.id
  resource_id   = aws_api_gateway_resource.iit-prod-get.id
  http_method   = aws_api_gateway_integration.request_method_integration.http_method
  status_code   = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Response for: GET 
resource "aws_api_gateway_integration_response" "response_method_integration" {
  rest_api_id   = aws_api_gateway_rest_api.iit-prod-api.id
  resource_id   = aws_api_gateway_resource.iit-prod-get.id
  http_method   = aws_api_gateway_method_response.response_method.http_method
  status_code   = aws_api_gateway_method_response.response_method.status_code

  response_templates = {
    "application/json" = ""
  }
}

resource "aws_lambda_permission" "allow_api_gateway" {
  function_name = var.lambda_name
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.iit-prod-api.id}/*/${var.method}${var.path}"
}



############################################
# Deploy the API
resource "aws_api_gateway_deployment" "iit-prod" {
	depends_on = [aws_api_gateway_method.request_method]
  rest_api_id = aws_api_gateway_rest_api.iit-prod-api.id
  stage_name  = "prod"
  description = "IIT Production"
}


resource "aws_db_instance" "default" {
  allocated_storage      = var.storage
  max_allocated_storage  = var.max_storage
  storage_type           = var.storage_type
  engine                 = var.engine
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  identifier             = var.identifier
  name                   = var.db_name
  username               = var.username
  password               = var.password
  tags                   = var.tags
  lifecycle { prevent_destroy = true }
  publicly_accessible    = true
  
}

resource "null_resource" "default" {
  provisioner "local-exec" {
    command = "mysql -h ${aws_db_instance.default.address} -P 3306 -u ${aws_db_instance.default.username} -p${var.password} ${aws_db_instance.default.name} < schema.sql"
  }

}  