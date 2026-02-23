![AWS](https://img.shields.io/badge/AWS-Cloud%20Project-FF9900?logo=amazon-aws&logoColor=white)
![ETL](https://img.shields.io/badge/Data-ETL%20Pipeline-blue)

# 🧩 AWS Serverless ETL Pipeline (Lambda + Glue + Athena)

This project demonstrates a fully automated **serverless data pipeline** built on AWS — capable of ingesting, transforming, cataloging, and querying structured data without managing any servers.

---

## 📘 Overview
Whenever a new CSV file is uploaded to an S3 bucket, an AWS Lambda function is automatically triggered.  
The function uses **pandas** to clean and transform the dataset (for example, incrementing values or fixing formatting) before saving the processed data to a separate S3 bucket.  
AWS Glue then catalogs both the raw and cleaned datasets, allowing **AWS Athena** to query them directly with SQL.

---

## 🧱 Architecture Diagram

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

## ⚙️ Architecture Components

| Layer | AWS Service | Description |
|-------|--------------|-------------|
| **Ingestion** | Amazon S3 (`raw-data-ryan`) | Stores incoming CSV data uploads. |
| **Transformation** | AWS Lambda (`etl-transform-lambda`) | Automatically triggered on upload; uses pandas to transform data. |
| **Storage** | Amazon S3 (`cleaned-data-ryan`) | Stores transformed/cleaned data. |
| **Metadata** | AWS Glue | Crawlers update the Glue Data Catalog schemas for raw and cleaned datasets. |
| **Querying** | AWS Athena | Queries data from the Glue catalog using standard SQL. |
| **Infrastructure** | Terraform + AWS CLI | Used to provision all resources reproducibly. |

---

## 📊 Example Data Flow

### Raw Input (in S3)
```csv
Name,Age,City
Ryan,29,Charlotte
Palmer,8,Davidson
```

### Transformed Output (Lambda → Cleaned S3)
```csv
Name,Age,City
Ryan,30,Charlotte
Palmer,9,Davidson
```

### Example Athena Query
```sql
SELECT * 
FROM "etl_data_catalog"."cleaned_cleaned_data_ryan" 
LIMIT 10;
```

**Athena Output**
| name | age | city | partition_0 |
|------|-----|------|--------------|
| Ryan | 30  | Charlotte | cleaned |
| Palmer | 9 | Davidson | cleaned |

---

## 🧠 Key Learnings

- Implemented a **fully serverless ETL workflow** integrating AWS Lambda, S3, Glue, and Athena.
- Used **pandas** within AWS Lambda via the official `AWSSDKPandas` layer for efficient data transformations.
- Automated schema detection and metadata cataloging with AWS Glue Crawlers.
- Queried transformed data using **SQL via Athena**, with query results written back to S3.
- Deployed and managed all infrastructure via **Terraform**, ensuring repeatability and portability.
- Verified transformation logic and event-driven architecture using **CloudWatch Logs** and **AWS CLI** queries.

---

## 🛠️ Tech Stack

| Category | Technology |
|-----------|-------------|
| Programming | Python (pandas, boto3) |
| Cloud | AWS Lambda, S3, Glue, Athena |
| Infrastructure as Code | Terraform |
| Logging & Monitoring | AWS CloudWatch |
| Data Query | SQL via Athena |

---

## 🚀 How It Works (Step-by-Step)

1. **Upload**  
   Place any CSV file into the raw bucket:  
   `s3://raw-data-ryan/raw_data.csv`

2. **Transform**  
   Lambda automatically triggers, reads the file, increments numeric fields, and saves a cleaned version:  
   `s3://cleaned-data-ryan/cleaned/raw_data.csv`

3. **Catalog**  
   Glue crawlers update the schemas inside the `etl_data_catalog`.

4. **Query**  
   Athena queries the latest version directly:  
   `SELECT * FROM etl_data_catalog.cleaned_cleaned_data_ryan;`

5. **Visualize / Analyze**  
   Results can be exported or visualized using Athena workgroups and result sets in S3.

---

## 📦 Example CLI Validation

**Trigger the pipeline:**
```powershell
aws s3 cp sample_data/raw_data.csv s3://raw-data-ryan/raw_data_test.csv
```

**Check logs:**
```powershell
aws logs get-log-events `
  --log-group-name '/aws/lambda/etl-transform-lambda' `
  --log-stream-name '<latest-log-stream>' --no-cli-pager
```

**Verify cleaned data:**
```powershell
aws s3 cp s3://cleaned-data-ryan/cleaned/raw_data_test.csv -
```

**Expected:**
```csv
Name,Age,City
Ryan,30,Charlotte
Palmer,9,Davidson
```
