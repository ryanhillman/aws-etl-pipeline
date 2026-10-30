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

  # The longest derived name, "<project>-cleaned-<12-digit account ID>", must fit
  # S3's 63-character limit
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,40}[a-z0-9]$", var.project))
    error_message = "Use 2-42 lowercase letters, numbers and hyphens, starting and ending with a letter or number."
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  function_name = "${var.project}-transform"
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

resource "aws_iam_role" "lambda" {
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

resource "aws_iam_role_policy" "lambda" {
  name = "${var.project}-lambda"
  role = aws_iam_role.lambda.id
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
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

data "archive_file" "transform" {
  type             = "zip"
  source_file      = "${path.module}/lambda/lambda_function.py"
  output_path      = "${path.module}/build/lambda_function.zip"
  output_file_mode = "0666" # consistent file permissions across operating systems
}

resource "aws_lambda_function" "transform" {
  function_name = local.function_name
  runtime       = "python3.13"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda.arn

  filename         = data.archive_file.transform.output_path
  source_code_hash = data.archive_file.transform.output_base64sha256

  layers = ["arn:aws:lambda:${data.aws_region.current.region}:336392948345:layer:AWSSDKPandas-Python313:17"]

  environment {
    variables = {
      CLEANED_BUCKET = aws_s3_bucket.cleaned.bucket
    }
  }

  timeout = 60
}

resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transform.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "raw_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.transform.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}

output "cleaned_bucket" {
  value = aws_s3_bucket.cleaned.bucket
}
