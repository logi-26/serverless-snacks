'''
Code for the Order Creation lambda function
'''

from os import environ
from json import loads, dumps, JSONDecodeError
from typing import Any, Dict
from boto3 import resource, client
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="OrderCreator")
dynamodb = resource("dynamodb")
events_client = client("events")

def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    '''Handles order creation requests'''

    # Ensure that the table name exists in the environment
    table_name = environ.get("TABLE_NAME")
    if not table_name:
        logger.error("TABLE_NAME environment variable is missing")

        # Return the failed response
        return {"statusCode": 500, "body": dumps({"error": "Server misconfiguration"})}

    table = dynamodb.Table(table_name)

    # Parse the body of the event
    body = event.get("body", "{}")
    try:
        order = loads(body) if isinstance(body, str) else body
    except JSONDecodeError:
        logger.error("Invalid JSON in request body")

        # Return the failed response
        return {"statusCode": 400, "body": dumps({"error": "Invalid JSON in request body"})}

    # Get the required orderId from the event
    order_id = order.get("orderId")
    if not order_id:
        logger.error("Missing 'orderId' in request")

        # Return the failed response
        return {"statusCode": 400, "body": dumps({"error": "Missing 'orderId' in request"})}

    # Get the item from the event
    item = order.get("item", "unknown")

    # Write the new order to the orders table in DynamoDB
    # Only insert if there isn’t already an item with this orderId
    try:
        table.put_item(
            Item={"orderId": order_id, "status": "NEW", "item": item},
            ConditionExpression=Attr("orderId").not_exists()
        )

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.error(f"Order {order_id} already exists")
            return {"statusCode": 409, "body": dumps({"error": "Order already exists"})}

        logger.exception(f"Unexpected error writing order {order_id}")
        return {"statusCode": 500, "body": dumps({"error": "Internal server error"})}

    logger.info(f"Order {order_id} created")

    # Publish an event to event-bridge to indicate that the new order has been created
    try:
        events_client.put_events(
            Entries=[
                {
                    "Source": "serverless.snacks",
                    "DetailType": "OrderCreated",
                    "Detail": dumps({"orderId": order_id, "item": item}),
                    "EventBusName": "OrderEventBus"
                }
            ]
        )

        logger.info(f"Event published for order {order_id}")

    except (ClientError) as e:
        logger.error(f"Failed to publish event: {e}")

        # Return the failed response
        return {"statusCode": 502, "body": dumps({"error": "Failed to publish event"})}

    # Return the success response
    return {"statusCode": 200, "body": dumps({"orderId": order_id, "status": "NEW"})}
