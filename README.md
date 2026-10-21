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

## Demo

https://youtu.be/CyTrPDVRbM4

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

**Prerequisites:** AWS CLI configured, Terraform installed, Python 3.11.

**1. Package the Lambda function**
```powershell
Compress-Archive -Path lambda/lambda_function.py -DestinationPath lambda/lambda_function.zip -Force
```

**2. Provision infrastructure**
```powershell
terraform init
terraform apply
```
Terraform creates both S3 buckets, the IAM role, the Lambda function (using the AWS-managed AWS SDK for pandas layer), and the S3 event trigger. The Glue crawlers, Data Catalog and Athena queries were configured in the AWS console.

**3. Test the pipeline**
```powershell
aws s3 cp sample_data/raw_data.csv s3://raw-data-ryan/raw_data.csv
```
After a few seconds, verify the output:
```powershell
aws s3 cp s3://cleaned-data-ryan/cleaned/raw_data.csv -
```

**Expected:**
```csv
Name,Age,City 
Ryan,30,Charlotte 
Palmer,9,Davidson 
```
