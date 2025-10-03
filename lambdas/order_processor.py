'''
Code for the Order Processing lambda function
'''

from os import environ
from json import dumps
from typing import Any, Dict
from boto3 import resource
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="OrderProcessor")
dynamodb = resource("dynamodb")

def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    '''Handles order processing events'''

    # Get the table name
    table_name = environ.get("TABLE_NAME")
    if not table_name:
        logger.error("TABLE_NAME environment variable is missing")

        # Return the failed response
        return {"statusCode": 500, "body": dumps({"error": "Server misconfiguration"})}

    table = dynamodb.Table(table_name)

    # Parse the orderId from the event
    order = event.get("detail")
    order_id = order.get("orderId") if order else None
    if not order_id:
        logger.error("Invalid event: missing 'detail' or 'orderId'")

        # Return the failed response
        return {"statusCode": 400, "body": dumps({"error": "Invalid event payload"})}

    # Update the order status for this orderId in the DynamoDB table
    # Only update if orderId exists
    try:
        table.update_item(
            Key={"orderId": order_id},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "PROCESSED"},
            ConditionExpression=Attr("orderId").exists()
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.error(f"Order {order_id} does not exist. Cannot process.")
        else:
            logger.exception(f"Error processing order {order_id}")

        # Raise an exception so that the lambda can retry or send to the dead letter queue
        raise

    logger.info(f"Order {order_id} processed")

    # Return the success response
    return {"statusCode": 200, "body": dumps({"orderId": order_id, "status": "PROCESSED"})}
