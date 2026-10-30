# AWS Serverless ETL Pipeline

<p align="center">
  <img src="https://img.shields.io/badge/Cloud-AWS-FF9900?logo=amazon-aws&logoColor=white" />
  <img src="https://img.shields.io/badge/Architecture-Serverless%20ETL-black" />
  <img src="https://img.shields.io/badge/IaC-Terraform-844FBA?logo=terraform&logoColor=white" />
</p>

This project demonstrates a **serverless ETL pipeline** capable of ingesting, transforming, cataloging, and querying structured data.

---

## Overview
When a new CSV file is uploaded to an S3 bucket, an AWS Lambda function is automatically triggered.

The function uses pandas to transform the dataset before saving the processed data to a separate S3 bucket.

AWS Glue then catalogs the raw and cleaned datasets, allowing SQL querying with AWS Athena.

Terraform was used to provision resources and AWS CloudWatch verified the transformation logic.

---

## [Demo](https://youtu.be/CyTrPDVRbM4)

---

## Architecture Diagram

```text
         ┌─────────────────────┐
         │     Raw Data S3     │
         │  (raw-data-ryan)    │
         └─────────┬───────────┘
                   │  (CSV upload event)
                   ▼
         ┌─────────────────────┐
         │  AWS Lambda (ETL)   │
         │ etl-transform-lambda│
         └─────────┬───────────┘
                   │  (pandas transform)
                   ▼
         ┌─────────────────────┐
         │  Cleaned Data S3    │
         │ (cleaned-data-ryan) │
         └─────────┬───────────┘
                   │  (Glue Crawlers)
                   ▼
         ┌─────────────────────┐
         │  AWS Glue Catalog   │
         │ (etl_data_catalog)  │
         └─────────┬───────────┘
                   │  (SQL queries)
                   ▼
         ┌─────────────────────┐
         │   AWS Athena        │
         │   Query Results     │
         └─────────────────────┘
```

---

## Deployment

**Prerequisites:** AWS CLI configured, Terraform installed.

**1. Provision infrastructure**
```sh
terraform init
terraform apply
```
Terraform packages the Lambda code and creates both S3 buckets, the IAM role, the Lambda function (using the AWS-managed AWS SDK for pandas layer), the S3 event trigger, a log group with 14-day retention, and an SQS queue that captures failed events. The Glue crawlers, Data Catalog and Athena queries were configured in the AWS console.

**2. Test the pipeline**
```sh
aws s3 cp sample_data/raw_data.csv s3://$(terraform output -raw raw_bucket)/raw_data.csv
```
After a few seconds, verify the output:
```sh
aws s3 cp s3://$(terraform output -raw cleaned_bucket)/cleaned/raw_data.csv -
```

**Expected:**
```csv
Name,Age,City
Ryan,30,Charlotte
Palmer,9,Davidson
```

**3. Tear down**
```sh
terraform destroy
```

---

## Testing

```sh
pip install -r requirements-dev.txt
pytest
```
