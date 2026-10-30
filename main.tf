terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "project" {
  description = "Prefix for all resource names"
  type        = string
  default     = "etl-pipeline"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project))
    error_message = "Use lowercase letters, numbers and hyphens (S3 bucket naming rules)."
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  glue_arn   = "arn:aws:glue:${data.aws_region.current.region}:${local.account_id}"
}

# S3 bucket names are global, so the account ID keeps them unique
resource "aws_s3_bucket" "raw" {
  bucket        = "${var.project}-raw-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "cleaned" {
  bucket        = "${var.project}-cleaned-${local.account_id}"
  force_destroy = true
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.project}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project}-lambda"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.raw.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cleaned.arn}/cleaned/*"
      },
      {
        # awswrangler creates the "cleaned" table, and updates it when new columns appear
        Effect = "Allow"
        Action = ["glue:GetTable", "glue:CreateTable", "glue:UpdateTable"]
        Resource = [
          "${local.glue_arn}:catalog",
          aws_glue_catalog_database.etl.arn,
          "${local.glue_arn}:table/${aws_glue_catalog_database.etl.name}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.lambda_failures.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      }
    ]
  })
}

data "archive_file" "lambda_zip" {
  type             = "zip"
  source_file      = "${path.module}/lambda/lambda_function.py"
  output_path      = "${path.module}/build/lambda_function.zip"
  output_file_mode = "0666" # consistent file permissions across operating systems
}

resource "aws_lambda_function" "etl_lambda" {
  function_name = "${var.project}-transform"
  runtime       = "python3.13"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python313:17"]

  environment {
    variables = {
      CLEANED_PATH  = "s3://${aws_s3_bucket.cleaned.bucket}/cleaned/"
      GLUE_DATABASE = aws_glue_catalog_database.etl.name
    }
  }

  # pandas plus awswrangler's pyarrow don't fit comfortably in the 128 MB default
  memory_size = 512
  timeout     = 60
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.etl_lambda.function_name}"
  retention_in_days = 14
}

# Events that still fail after S3's two async retries land here instead of being dropped
resource "aws_sqs_queue" "lambda_failures" {
  name                      = "${var.project}-failures"
  message_retention_seconds = 1209600 # 14 days, the maximum
}

resource "aws_lambda_function_event_invoke_config" "etl_lambda" {
  function_name = aws_lambda_function.etl_lambda.function_name

  destination_config {
    on_failure {
      destination = aws_sqs_queue.lambda_failures.arn
    }
  }

  # AWS rejects the destination unless the role can already send to the queue
  depends_on = [aws_iam_role_policy.lambda_policy]
}

resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id   = "AllowExecutionFromS3"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.etl_lambda.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.raw.arn
  source_account = local.account_id
}

resource "aws_s3_bucket_notification" "raw_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.etl_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

# Athena database and table names can't contain hyphens
resource "aws_glue_catalog_database" "etl" {
  name = replace(var.project, "-", "_")
}

resource "aws_iam_role" "glue_crawler" {
  name = "${var.project}-glue-crawler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_crawler_service" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_crawler_s3" {
  name = "${var.project}-glue-crawler-s3"
  role = aws_iam_role.glue_crawler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.raw.arn
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.raw.arn}/raw/*"
      }
    ]
  })
}

# Catalogs the raw CSVs as the "raw" table (named after the raw/ prefix)
resource "aws_glue_crawler" "raw" {
  name          = "${var.project}-raw"
  database_name = aws_glue_catalog_database.etl.name
  role          = aws_iam_role.glue_crawler.arn

  s3_target {
    path = "s3://${aws_s3_bucket.raw.bucket}/raw/"
  }
}

# Query results go to a fixed location instead of a per-user console setting
resource "aws_athena_workgroup" "etl" {
  name          = var.project
  force_destroy = true

  configuration {
    enforce_workgroup_configuration = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.cleaned.bucket}/athena-results/"
    }
  }
}

output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}


output "raw_crawler" {
  value = aws_glue_crawler.raw.name
}
