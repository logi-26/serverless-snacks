# Serverless Snacks (AWS CDK Python Project)

This project is a serverless application built using AWS CDK in Python. It provisions AWS resources including:

- DynamoDB tables
- Lambda functions
- EventBridge rules
- Dead-letter queue (DLQ)
- CloudWatch alarms and monitoring

## Prerequisites

- Python 3.10 or newer
- Node.js 18+ (for AWS CDK)
- AWS CLI configured with access to your account
- `pip` package manager
- Docker

## Setup

1. Clone the repository:
```bash
git clone https://github.com/logi-26/serverless-snacks.git
cd serverless-snacks
```

2. Create and activate a Python virtual environment:
- Linux/macOS:
```bash
python -m venv .venv
source .venv/bin/activate
```
- Windows:
```bash
python -m venv .venv
.venv\Scripts\activate.bat
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Bootstrap AWS for CDK:
```bash
cdk bootstrap aws://<ACCOUNT_ID>/<REGION>
```

## Run unit tests:
```bash
pytest tests/
```

## Deployment

1. Synthesize the CloudFormation template:
```bash
cdk synth
```

2. Compare deployed stack with current state:
```bash
cdk diff
```

3. Deploy the stack to your AWS account:
```bash
cdk deploy
```

## Cleaning Up
To destroy all resources created by the stack:
```bash
cdk destroy
```

## Notes
- Environment variables (e.g. TABLE_NAME) must be configured before Lambda execution.
- Ensure AWS credentials are properly configured for deployment.


## Usage
The Order Creation lambda is expecting an event containing an order:

```json
{
  "body": {
    "orderId": "1",
    "item": "burger"
  }
}
```

## Screenshots

#### Unit Tests
![alt text](https://github.com/logi-26/serverless-snacks/blob/main/screenshots/tests.png?raw=true)

#### Items in DynamoDB
![alt text](https://github.com/logi-26/serverless-snacks/blob/main/screenshots/dynamo.png?raw=true)

#### Items in DLQ (sent 5 invalid orders for testing)
![alt text](https://github.com/logi-26/serverless-snacks/blob/main/screenshots/dead%20letter%20queue.png?raw=true)

#### DLQ Email Alert
![alt text](https://github.com/logi-26/serverless-snacks/blob/main/screenshots/email%20alert.png?raw=true)