import os

# lambda_function reads these at import time; Terraform sets them in AWS
os.environ.setdefault("CLEANED_PATH", "s3://test-cleaned/cleaned/")
os.environ.setdefault("GLUE_DATABASE", "test_db")
