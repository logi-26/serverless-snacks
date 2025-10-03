import pytest
from os import environ
from json import dumps
from unittest.mock import patch, MagicMock
from lambdas import order_creator, order_processor
from botocore.exceptions import ClientError

# -----------------------------
# order_creator lambda tests
# -----------------------------

@patch("lambdas.order_creator.dynamodb")
def test_order_creator_missing_orderId(mock_dynamodb_resource):
    """Test order_creator Lambda with missing orderId"""
    environ["TABLE_NAME"] = "OrdersTable"
    event = {"body": dumps({"item": "chips"})}
    context = {}

    response = order_creator.handler(event, context)
    assert response["statusCode"] == 400
    assert "Missing 'orderId'" in response["body"]


@patch("lambdas.order_creator.dynamodb")
def test_order_creator_invalid_json(mock_dynamodb_resource):
    """Test order_creator Lambda with invalid JSON"""
    environ["TABLE_NAME"] = "OrdersTable"
    event = {"body": "{invalid_json"}
    context = {}

    response = order_creator.handler(event, context)
    assert response["statusCode"] == 400
    assert "Invalid JSON" in response["body"]


@patch("lambdas.order_creator.dynamodb")
@patch("lambdas.order_creator.events_client")
def test_order_creator_duplicate_order(mock_events_client, mock_dynamodb_resource):
    """Test order_creator Lambda when the order already exists"""
    environ["TABLE_NAME"] = "OrdersTable"

    mock_table = MagicMock()
    # Simulate DynamoDB conditional check failure
    error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
    mock_table.put_item.side_effect = ClientError(error_response, "PutItem")
    mock_dynamodb_resource.Table.return_value = mock_table

    event = {"body": dumps({"orderId": "123", "item": "chips"})}
    context = {}

    response = order_creator.handler(event, context)
    assert response["statusCode"] == 409
    assert "Order already exists" in response["body"]

# -----------------------------
# order_processor lambda tests
# -----------------------------

@patch("lambdas.order_processor.dynamodb")
def test_order_processor_success(mock_dynamodb_resource):
    """Test order_processor Lambda successful update"""
    environ["TABLE_NAME"] = "OrdersTable"

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table

    event = {"detail": {"orderId": "123"}}
    context = {}

    response = order_processor.handler(event, context)
    assert response["statusCode"] == 200
    assert "PROCESSED" in response["body"]
    mock_table.update_item.assert_called_once()


@patch("lambdas.order_processor.dynamodb")
def test_order_processor_order_not_exist(mock_dynamodb_resource):
    """Test order_processor Lambda when order does not exist"""
    environ["TABLE_NAME"] = "OrdersTable"

    mock_table = MagicMock()
    error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
    mock_table.update_item.side_effect = ClientError(error_response, "UpdateItem")
    mock_dynamodb_resource.Table.return_value = mock_table

    event = {"detail": {"orderId": "123"}}
    context = {}

    with pytest.raises(ClientError) as exc:
        order_processor.handler(event, context)
    assert "ConditionalCheckFailedException" in str(exc.value)
