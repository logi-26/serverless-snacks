'''Define the AWS infrastructure for the Serverless Snacks application using AWS CDK'''

from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    Duration,
    RemovalPolicy,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct

class ServerlessSnacksStack(Stack):
    '''Define the Serverless Snacks application stack'''

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the dynamo table to store the snack orders
        # Partition key is 'orderId' (unique identifier for each order)
        orders_table = dynamodb.Table(
            self, "OrdersTable",
            partition_key=dynamodb.Attribute(
                name="orderId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create the SQS dead letter queue for storing failed messages
        dlq = sqs.Queue(self, "OrderProcessingDLQ")

        # Create an SNS topic for dead letter queue alerts
        dlq_alert_topic = sns.Topic(
            self, "DLQAlertTopic",
            display_name="DLQ Alerts for Serverless Snacks"
        )

        # Subscribe an email address to the SNS topic for receiving the alerts
        dlq_alert_topic.add_subscription(
            subscriptions.EmailSubscription("louis_gilmartin@hotmail.co.uk")
        )

        # Create a cloud-watch metric for the number of items in the dead letter queue
        dlq_metric = dlq.metric_approximate_number_of_messages_visible(period=Duration.minutes(1))

        # Create a cloud-watch alarm when the dead letter queue contains 5 or more messages
        dlq_alarm = cloudwatch.Alarm(
            self, "DLQAlarm",
            metric=dlq_metric,
            evaluation_periods=1,
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm if there are 5 or more messages in the DLQ"
        )

        # Send SNS notification when the alarm triggers
        dlq_alarm.add_alarm_action(cw_actions.SnsAction(dlq_alert_topic))

        # Create the first lambda (Order Creation)
        # This lambda handles order creation (receives requests and writes to DynamoDB)
        order_creator_lambda = PythonFunction(
            self, "OrderCreatorLambda",
            entry="lambdas",
            index="order_creator.py",
            handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={"TABLE_NAME": orders_table.table_name},
            timeout=Duration.seconds(30)
        )

        # Create the second lambda (Order Processing)
        # This lambda processes created orders
        # It is connected to a dead letter queue in case processing fails
        order_processor_lambda = PythonFunction(
            self, "OrderProcessorLambda",
            entry="lambdas",
            index="order_processor.py",
            handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={"TABLE_NAME": orders_table.table_name},
            timeout=Duration.seconds(30),
            dead_letter_queue=dlq
        )

        # Grant the lambda permissions for the orders table in DynamoDB
        # First lambda can write data
        orders_table.grant_write_data(order_creator_lambda)

        # Second lambda can read/write data
        orders_table.grant_read_write_data(order_processor_lambda)

        # Create the event-bridge rule
        # Defines a rule to trigger the Order Processor lambda when an order has been created
        event_bus = events.EventBus(
            self, "OrderEventBus",
            event_bus_name="OrderEventBus"
        )

        rule = events.Rule(
            self, "OrderRule",
            event_pattern=events.EventPattern(
                source=["serverless.snacks"],
                detail_type=["OrderCreated"]
            ),
            event_bus=event_bus
        )
        # Attach the Order Processor lambda as the target of this rule
        rule.add_target(targets.LambdaFunction(order_processor_lambda))

        # Grant Order Creator lambda permission to publish events to event-bridge
        # This allows it to notify the event bus when a new order has been created
        event_bus.grant_put_events_to(order_creator_lambda)
