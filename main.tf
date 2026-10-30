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

resource "aws_s3_bucket" "raw" {
  bucket        = "raw-data-ryan"
  force_destroy = true
}

resource "aws_s3_bucket" "cleaned" {
  bucket        = "cleaned-data-ryan"
  force_destroy = true
}

resource "aws_iam_role" "lambda_role" {
  name = "etl-lambda-role"
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
  name = "etl-lambda-policy"
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
  function_name = "etl-transform-lambda"
  runtime       = "python3.11"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:6"]

  timeout = 60
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.etl_lambda.function_name}"
  retention_in_days = 14
}

# Events that still fail after S3's two async retries land here instead of being dropped
resource "aws_sqs_queue" "lambda_failures" {
  name                      = "etl-lambda-failures"
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
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.etl_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "raw_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.etl_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
