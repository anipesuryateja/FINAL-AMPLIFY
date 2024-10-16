import json
import boto3
from boto3.dynamodb.conditions import Attr, Key
import hashlib
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['STORAGE_TEZBUILDDATA_NAME'])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def send_response(statusCode, body):
    if isinstance(body, list):
        for item in body:
            if 'Costs' in item:
                del item['Costs']

    return {
        'statusCode': statusCode,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(body, default=decimal_default)
    }

def create_product_groups_by_variants(event):
    category = event.get('Category')
    key_attrs = event.get('keyAttr', [])  # the list of attributes whose variants the groups will be created around, e.g. ["Profile", "Precision"]
    title_expr = event.get('titleExpr')  # the expression to generate the title of the product group
    image_attr = event.get('imageAttr')  # the attribute to use as the image for the product group
    if not category:
        return send_response(400, 'Missing category in request')
    if not title_expr:
        return send_response(400, 'Missing title expression in request')
    if not image_attr:
        return send_response(400, 'Missing image attribute in request')
    
    filter_attr = event.get('filterAttr', {})  # the attributes to filter the groups by
    print("filters", filter_attr)
    
    # Initialize the set to store unique combinations of key_attrs
    variants = set()

    # Prepare expression attribute names to handle reserved keywords
    expression_attribute_names = {f"#{key}": key for key in key_attrs}
    filter_expression = Key('ItemType').eq('P') & Key('Category').eq(category)
    for key, value in filter_attr.items():
        filter_expression &= Attr(key).eq(value)
    
    # Initialize the ExclusiveStartKey to None for the first scan
    exclusive_start_key = None
    
    if key_attrs:
        while True:
            # Perform a scan operation with a filter expression to get items of the given category and item type
            if exclusive_start_key:
                response = table.scan(
                    IndexName='Category',
                    FilterExpression=filter_expression,
                    ProjectionExpression=','.join(f"#{key}" for key in key_attrs),
                    ExpressionAttributeNames=expression_attribute_names,
                    ExclusiveStartKey=exclusive_start_key
                )
            else:
                response = table.scan(
                    IndexName='Category',
                    FilterExpression=filter_expression,
                    ProjectionExpression=','.join(f"#{key}" for key in key_attrs),
                    ExpressionAttributeNames=expression_attribute_names
                )
            
            # Extract unique combinations of the key_attrs attributes
            for item in response['Items']:
                variant = {key: item[key] for key in key_attrs if key in item}
                if len(variant) == len(key_attrs):  # Ensure all key attributes are present
                    variants.add(tuple(sorted(variant.items())))
            
            # Check if there are more items to retrieve
            if 'LastEvaluatedKey' in response:
                exclusive_start_key = response['LastEvaluatedKey']
            else:
                break
    else:
        # Create a single product group with the given category and filter attributes
        variants.add(tuple(sorted(filter_attr.items())))

    if not variants:
        return send_response(404, 'No variants found for the given category and key attributes')
    
    # Convert the set of tuples back to a list of dictionaries
    variant_list = [dict(variant) for variant in variants]

    print("variants", variant_list)

    # Create product groups for each unique variant
    ids = []
    with table.batch_writer() as batch:
        for unique_variant in variant_list:
            item = unique_variant.copy()
            item.update(filter_attr)
            item["Category"] = category

            concat_id = ""
            for key, value in sorted(item.items()):
                concat_id += f"{key}:{value}#"
            hashed_id = hashlib.sha256(concat_id.encode()).hexdigest()[:10] 

            item["ItemType"] = "PG"
            item["UniqueId"] = hashed_id

            title = ""
            for i in range(len(title_expr)):
                title += title_expr[i]
                if i < len(key_attrs):
                    title += item[key_attrs[i]]

            item["Heading"] = title
            item["Subheading"] = ""

            item["Image"] = item[image_attr]

            batch.put_item(Item=item)
            ids.append(hashed_id)

    return send_response(200, {
        "message": 'Product groups created successfully',
        "ids": ids
    })

def handler(event, context):
    print('received event:')
    print(event)

    body = event

    if 'action' not in body:
        print('Missing action in request')
        return send_response(400, 'Missing action in request')

    if body['action'] == 'createGroupsByVariants':
        return create_product_groups_by_variants(body)

    return send_response(400, 'Invalid action in request')
