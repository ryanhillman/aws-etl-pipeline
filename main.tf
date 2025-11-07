provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "raw" {
  bucket = "raw-data-ryan"
  force_destroy = true
}

resource "aws_s3_bucket" "cleaned" {
  bucket = "cleaned-data-ryan"
  force_destroy = true
}

resource "aws_iam_role" "lambda_role" {
  name = "etl-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
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
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.raw.arn}",
          "${aws_s3_bucket.raw.arn}/*",
          "${aws_s3_bucket.cleaned.arn}",
          "${aws_s3_bucket.cleaned.arn}/*"
        ]
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

# Lambda Layer for pandas
resource "aws_lambda_layer_version" "pandas_layer" {
  filename   = "layer/pandas-layer.zip"
  layer_name = "pandas-layer"
  compatible_runtimes = ["python3.11"]
}

resource "aws_lambda_function" "etl_lambda" {
  function_name = "etl-transform-lambda"
  runtime       = "python3.11"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = "lambda/lambda_function.zip"
  source_code_hash = filebase64sha256("lambda/lambda_function.zip")

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:6"]

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  timeout = 60
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
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
