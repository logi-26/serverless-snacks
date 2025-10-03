'''Unit tests for the Serverless Snacks application stack and the lambda functions'''

from os import environ
from json import loads, dumps
from unittest.mock import patch, MagicMock
from aws_cdk import App
from aws_cdk.assertions import Template

# Import the Serverless Snack stack
from serverless_snacks.serverless_snacks_stack import ServerlessSnacksStack

# Import the order creation handler
from lambdas.order_creator import handler as order_creation_handler


def test_stack_resources():
    '''Test that the stack contains the expected resources'''

    app = App()
    stack = ServerlessSnacksStack(app, "ServerlessSnacksStack")
    template = Template.from_stack(stack)

    # Verify dynamo table exists
    template.resource_count_is("AWS::DynamoDB::Table", 1)
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": [{"AttributeName": "orderId", "KeyType": "HASH"}]
    })

    # Verify 2 lambda functions exist
    template.resource_count_is("AWS::Lambda::Function", 2)

    # Verify event-bridge rule exists
    template.resource_count_is("AWS::Events::Rule", 1)

    # Verify dead letter queue exists
    template.resource_count_is("AWS::SQS::Queue", 1)

    # Verify SNS topic for dead letter queue alerts
    template.resource_count_is("AWS::SNS::Topic", 1)

    # Verify cloud-watch alarm for the dead letter queue
    template.resource_count_is("AWS::CloudWatch::Alarm", 1)

    # Verify SNS subscription exists
    template.resource_count_is("AWS::SNS::Subscription", 1)

    # Verify the alarm SNS action
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "Threshold": 5,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "AlarmDescription": "Alarm if there are 5 or more messages in the DLQ"
    })


@patch("lambdas.order_creator.dynamodb")
@patch("lambdas.order_creator.events_client")
def test_order_creator_handler(mock_events_client, mock_dynamodb_resource):
    '''Test the order creation lambda handler'''

    # Setup environment
    environ["TABLE_NAME"] = "OrdersTable"

    # Mock dynamo table and put_item
    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table

    # Mock event-bridge put_events
    mock_events_client.put_events.return_value = {"FailedEntryCount": 0, "Entries": []}

    # Create the event and context
    event = {"body": dumps({"orderId": "123", "item": "chips"})}
    context = {}

    response = order_creation_handler(event, context)

    # Validate the response
    assert response["statusCode"] == 200
    body = loads(response["body"])
    assert body["orderId"] == "123"
    assert body["status"] == "NEW"

    # Validate dynamo call
    mock_table.put_item.assert_called_once_with(
        Item={"orderId": "123", "status": "NEW", "item": "chips"},
        ConditionExpression=mock_table.put_item.call_args.kwargs["ConditionExpression"]
    )

    # Validate that 1 event was sent to event-bridge
    mock_events_client.put_events.assert_called_once()


def test_dlq_alarm_metric():
    '''Test that the dead letter queue alarm is associated with the correct metric'''

    app = App()
    stack = ServerlessSnacksStack(app, "ServerlessSnacksStack")
    template = Template.from_stack(stack)

    alarms = template.find_resources("AWS::CloudWatch::Alarm")
    assert len(alarms) == 1
    alarm_props = list(alarms.values())[0]["Properties"]

    metric_name = (
        alarm_props["Metrics"][0]["MetricStat"]["Metric"]["MetricName"]
        if "Metrics" in alarm_props
        else alarm_props.get("MetricName")
    )

    assert metric_name in [
        "ApproximateNumberOfMessagesVisible", 
        "ApproximateNumberOfMessagesNotVisible"
    ]
