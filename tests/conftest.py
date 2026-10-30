import os

# lambda_function reads this at import time; Terraform sets it in AWS
os.environ.setdefault("CLEANED_BUCKET", "test-cleaned")
