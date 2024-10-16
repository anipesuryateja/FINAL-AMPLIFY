import json
import boto3
from boto3.dynamodb.conditions import Attr, Key
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['STORAGE_TEZBUILDDATA_NAME']
table = dynamodb.Table(table_name)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def send_response(statusCode, body):
    return {
        'statusCode': statusCode,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(body, default=decimal_default)
    }

def get_page_cards(body):
    id = body.get('id')
    if not id:
        return send_response(400, 'Missing id in request')
    
    response = table.query(
        KeyConditionExpression=Key('ItemType').eq('N') & Key('UniqueId').eq(id)
    )

    if not response['Items']:
        return send_response(404, 'Item not found')

    navigation_item = response['Items'][0]
    title = navigation_item.get('Title', 'No Title')
    pgids = navigation_item.get('PGIDs', [])
    pids = navigation_item.get('PIDs', [])

    # Prepare keys for batch_get_item
    keys_pg = [{'ItemType': 'PG', 'UniqueId': pgid} for pgid in pgids]

    # Retrieve group items
    response_pg = dynamodb.batch_get_item(
        RequestItems={
            table_name: {
                'Keys': keys_pg,
                'ProjectionExpression': 'Heading, Subheading, UniqueId, Image'
            }
        }
    )
    pg_items = response_pg['Responses'].get(table_name, [])

    # Retrieve product items from GSI "SKU"
    pid_items = []
    for pid in pids:
        pid_response = table.query(
            IndexName='SKU',
            KeyConditionExpression=Key('ItemType').eq("P") & Key('SKU').eq(pid),
            ProjectionExpression='Heading, Subheading, SKU, Image'
        )
        if pid_response['Items']:
            pid_items.append(pid_response['Items'][0])  # Assuming we take the first match

    # Construct the cards list
    cards = []
    for item in pg_items:
        cards.append({
            'heading': item.get('Heading', ''),
            'subheading': item.get('Subheading', ''),
            'id': item['UniqueId'],
            'image': item.get('Image', ''),
            'type': 'group'
        })
    for item in pid_items:
        cards.append({
            'heading': item.get('Heading', ''),
            'subheading': item.get('Subheading', ''),
            'id': item['SKU'],
            'image': item.get('Image', ''),
            'type': 'product'
        })

    return send_response(200, {
        'title': title,
        'cards': cards
    })

def handler(event, context):
    print('received event:')
    print(event)

    body = json.loads(event['body'])

    if 'action' not in body:
        print('Missing action in request')
        return send_response(400, 'Missing action in request')
  
    if body['action'] == 'getPageCardsByNavID':
        return get_page_cards(body)

    return send_response(400, 'Invalid action in request')