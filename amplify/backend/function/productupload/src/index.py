import json
import boto3
import csv
import hashlib
import re
import os
from decimal import Decimal
import math

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['STORAGE_TEZBUILDDATA_NAME'])

# Nominal to actual size chart
LUMBER_NOMINAL_ACTUAL = {
    '1x4': (0.75, 3.50),
    '1x5': (0.75, 4.72),
    '1x6': (0.75, 5.50),
    '5/4x4': (1.00, 3.50),
    '5/4x5': (1.00, 4.72),
    '5/4x6': (1.00, 5.50),
    '5/4x8': (1.00, 7.25),
    '5/4x10': (1.00, 9.25),
    '5/4x12': (1.00, 11.25),
    '2x2': (1.50, 1.50),
    '2x4': (1.50, 3.50),
    '2x6': (1.50, 5.50),
    '2x8': (1.50, 7.25),
    '2x10': (1.50, 9.25),
    '2x12': (1.50, 11.25),
    '3x4': (2.50, 3.50),
    '3x6': (2.50, 5.50),
    '3x8': (2.50, 7.25),
    '3x10': (2.50, 9.25),
    '3x12': (2.50, 11.25),
    '4x4': (3.50, 3.50),
    '4x6': (3.50, 5.50),
    '6x6': (5.50, 5.50)
}

BUNDLE_SIZES = {
    "lumber": {
        "Southern Yellow Pine": { # https://interfor.com/products/dimension-lumber/southern-yellow-pine/
            "2x4": 208,
            "2x6": 128, 
            "2x8": 96,
            "2x10": 80,
            "2x12": 64,
            "4x4": 52 # this one specifically seems to differ - GS has 104 for example
        },
        "European Spruce": { # https://interfor.com/products/dimension-lumber/spruce-pine-fir/
            "2x4": 294,
            "2x6": 189, 
            "2x8": 147,
            "2x10": 105,
            "2x12": 84
        }
    },
    "sheet_good": {
        0.5: 66,
        0.75: 44
    }
}

# TODO: find some widely accepted standard to use for these
# values are in lb/cubic ft
LUMBER_DENSITY = {
    'Southern Yellow Pine': 34,
    'European Spruce': 23,
    'Birch': 45,
    'Fir': 35,
}

def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a

def format_distance(distance: float, metric: bool = False) -> str:
    if metric:
        return f"{distance}mm"
    else:
        feet = math.floor(distance / 12)
        remaining_inches = distance % 12
        whole_inches = math.floor(remaining_inches)
        fractional_inches = remaining_inches - whole_inches
        fraction = ''
        
        if fractional_inches > 0:
            denominator = 32
            numerator = round(fractional_inches * denominator)
            common_divisor = gcd(numerator, denominator)
            simplified_numerator = numerator // common_divisor
            simplified_denominator = denominator // common_divisor
            
            if simplified_numerator > 0:
                fraction = f"{simplified_numerator}/{simplified_denominator}"
        
        result = ''
        if feet > 0:
            result += f"{feet}ft."
        
        in_flag = False
        if whole_inches > 0:
            in_flag = True
            if result:
                result += ' '
            result += f"{whole_inches}"
        
        if fraction:
            if in_flag:
                result += '-'
            elif result:
                result += ' '
            in_flag = True
            result += fraction
        
        if in_flag:
            result += 'in.'
        
        return result.strip()

def board_feet_softwood(length, profile):
    if length % 12 != 0:
        length = math.ceil(length / 12) * 12
    thickness, width = map(int, profile.split('x'))
    return width * thickness * length / 144

def clear_supplier(category, facility_id):
    print(f"Clearing {category} items for facility {facility_id}")

    # Define the partition key and sort key values to filter the items
    item_type = 'P'

    if category == "all":
        # Query for all items in the facility
        response = table.query(
            IndexName='FacilityId',
            KeyConditionExpression='ItemType = :item_type AND FacilityId = :facility_id',
            ExpressionAttributeValues={
                ':item_type': item_type,
                ':facility_id': facility_id
            }
        )
    else:
        # Query for all items of a specific category in the facility
        response = table.query(
            IndexName='FacilityId',
            KeyConditionExpression='ItemType = :item_type AND FacilityId = :facility_id',
            FilterExpression='Category = :category',
            ExpressionAttributeValues={
                ':item_type': item_type,
                ':facility_id': facility_id,
                ':category': category
            }
        )
    
    items = response.get('Items', [])

    print(f"Deleting {len(items)} items")
    
    # Loop through the items and delete each one
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'ItemType': item['ItemType'],
                    'UniqueId': item['UniqueId']
                }
            )


def parse_lumber(row, supplier_id):
    try:
        profile = row['profile'].lower()
        length = float(row['length'])
        grade = row['grade']
        base_price = float(row['basePrice'])
        species = row['species']
    except KeyError as e:
        row['error'] = f'Missing required field: {e}'
        return row
    except AttributeError as e:
        row['error'] = f'Missing or improperly formatted required field: {e}'
        return row
    except ValueError as e:
        row['error'] = f'Missing or improperly formatted required field: {e}'
        return row

    if base_price <= 0:
        row['error'] = 'Base price must be greater than 0'
        return row

    
    # attributes with defaults
    finger_joint = row.get('fingerJoint')
    if not finger_joint:
        finger_joint = 'N'
    precision = row.get('precision')
    if not precision:
        precision = 'N'

    # attributes that it is ok to leave blank
    # these are the things that we may not identify, but don't want to call attention to a lack of
    # they are being assigned a null string to avoid having "None" inserted into string formatters
    treatment = row.get('treatment')
    if not treatment or treatment == 'none':
        treatment = ''
    brand = row.get('brand')
    if not brand:
        brand = ""

    if not re.match(r'^\d[Xx]\d{1,2}$', profile):
        row['error'] = 'Invalid profile (format: 2X4, 4x6, etc.)'
        return row

    concatenated_id = f"lumber{length}#{profile}#{grade}#{species}#{finger_joint}#{precision}#{treatment}#{brand}"

    # Hash and take the first 10 characters for manageability. 10 characters is sufficiently large 
    # to avoid collisions. (16^10>1 trillion and sha256 can be thought of as a seeded pseudo-RNG.)
    hashed_id = hashlib.sha256(concatenated_id.encode()).hexdigest()[:10]
    unique_id = f"{supplier_id}#{hashed_id}"

    # TODO: if the hashed_id is found, just update costs using bdf and base_price

    # Calculate BDFT (Board Footage)
    bdf = board_feet_softwood(length, profile)

    # Retrieve width and thickness from the chart
    if profile in LUMBER_NOMINAL_ACTUAL:
        thickness, width = LUMBER_NOMINAL_ACTUAL[profile]
    else:
        row['error'] = 'Invalid profile (not found in nominal/actual chart)'
        return row

    if species in LUMBER_DENSITY:
        weight = width * thickness * length * LUMBER_DENSITY[species] / 1728
    else:
        row['error'] = 'Invalid species (not found in density chart)'
        return row
    
    if "packSize" in row and row['packSize'] != '':
        pack_size = int(row['packSize'])
    else:
        pack_size = BUNDLE_SIZES['lumber'][species].get(profile)

    if supplier_id == 'RRT':
        # RRT costs are in $/BDFT
        # adders are implemented as part of cost, but we may need to move them to prices later for accounting purposes
        price_type = 'a'
        
        if not pack_size:
            costs = [
                # If the profile is unrecognized, default to the biggest adder possible (100 forever - no break)
                ((base_price*bdf*1.25*1.1*1.15), 1)
            ]
        else:
            costs = [
                ((base_price*bdf*1.25*1.1*1.15), 1),
                ((base_price*bdf*1.25*1.1), math.ceil(pack_size/2)),
                (base_price*bdf*1.25, pack_size)
            ]
    elif supplier_id == 'BX_YL':
        # BlueLinx costs are in $/1000 BDFT
        price_type = 'a'

        if not pack_size:
            costs = [
                # If the profile is unrecognized, default to the biggest adder possible (150 forever - no break)
                ((base_price*bdf+150)/1000, 1)
            ]
        elif finger_joint == 'Y' and length > 240:
            # Adder for FJ long
            costs = [
                ((base_price*bdf+100)/1000, 1),
                ((base_price*bdf+75)/1000, math.ceil(pack_size/2)),
                (base_price*bdf/1000, pack_size)
            ]
        else:
            # Adder for standard sizes
            costs = [
                ((base_price*bdf+150)/1000, 1),
                ((base_price*bdf+75)/1000, math.ceil(pack_size/2)),
                (base_price*bdf/1000, pack_size)
            ]
    # great southern, panasofkee
    elif supplier_id == 'GS_PSK':
        price_type = 'a'

        # TODO: get the actual numbers for these adders
        if not pack_size:
            costs = [
                # If the profile is unrecognized, default to the biggest adder possible (100 forever - no break)
                ((base_price*bdf+150)/1000, 1)
            ]
        else:
            costs = [
                ((base_price*bdf+150)/1000, 1),
                ((base_price*bdf+75)/1000, math.ceil(pack_size/2)),
                (base_price*bdf/1000, pack_size)
            ]

    costs = [(round(cost, 5), q) for (cost, q) in costs]
    if supplier_id != 'RRT':
        # Simple 10% markup until we develop a pricing model, and round both costs and prices to 4 decimal places
        prices = [(round(cost*1.1, 5), q) for (cost, q) in costs]
    else:
        # TODO: determine if we need to separate these out for accounting purposes
        prices = costs

    heading = f"{profile}x{format_distance(length)} {grade} {species}"
    subheading_parts = []
    if brand:
        subheading_parts.append(brand)
    if precision == 'Y':
        subheading_parts.append("Precision End Trim")
    if treatment:
        subheading_parts.append(treatment)
    if finger_joint == 'Y':
        subheading_parts.append("Finger Joint")
    subheading = " | ".join(subheading_parts)

    item = {
        'ItemType': "P",
        'UniqueId': unique_id,
        'Category': "lumber",
        'SKU': hashed_id,
        'FacilityId': supplier_id,
        'Length': length,
        'Profile': profile,
        'Grade': grade,
        'Species': species,
        'FingerJoint': finger_joint,
        'Precision': precision,
        'Width': width,
        'Thickness': thickness,
        'BDFT': bdf,
        'Weight': weight,
        'Costs': costs,
        'Prices': prices,
        'PriceType': price_type, # 'a' for adder pricing, 'b' for price breaks
        'Heading': heading,
        'Subheading': subheading,
        'Image': profile,
        'MinPackSize': prices[0][1], # for searching/filtering the table
        'Unit': "pc", # individual pieces
    }

    # inventory only implemented for RRT
    if supplier_id == 'RRT':
        try:
            item['Inventory'] = math.floor(float(row.get('inventory', 0)))
        except Exception as e:
            row['error'] = f'Could not parse inventory: {e}'
            return row

    if brand:
        item['Brand'] = brand
    if treatment:
        item['Treatment'] = treatment
    
    return json.loads(json.dumps(item), parse_float=Decimal)


def parse_sheet_good(row, supplier_id):
    try:
        # TODO: conduct a through review of these before MVP release, and bluelinx master file
        # some of this could be solved possibly by splitting off plywood and osb
        # required fields
        length = float(row['length'])
        width = float(row['width'])
        thickness = float(row['thickness'])
        base_price = float(row['basePrice'])
        panel_type = row['panelType']
    except KeyError as e:
        row['error'] = f'Missing required field: {e}'
        return row
    except AttributeError as e:
        row['error'] = f'Missing or improperly formatted required field: {e}'
        return row
    except ValueError as e:
        row['error'] = f'Missing or improperly formatted required field: {e}'
        return row

    if base_price <= 0:
        row['error'] = 'Base price must be greater than 0'
        return row
    
    
    # attributes that it is ok to leave blank
    # these are the things that we may not identify, but don't want to call attention to a lack of
    brand = row.get('brand')
    origin = row.get('origin') # should be a country code
    grade = row.get('grade') # grade has become a sparse catchall, might split it off in future verisons of the uploader
    species = row.get('species')
    finish = row.get('finish')
    edge = row.get('edge')
    metric = row.get('metric')
    treatment = row.get('treatment')
    
    # clearing these so that they don't appear as "None" in string formatters
    if not brand:
        brand = ""
    if not origin:
        origin = ""
    if not grade:
        grade = ""
    if not species:
        species = ""
    if not finish:
        finish = ""
    if not edge:
        edge = ""
    if not metric:
        metric = ""
    if not treatment or treatment == 'none':
        treatment = ''

    # hastags are used here because there are multiple attributes which could be blank
    concatenated_id = f"sheet_good{length}#{width}#{thickness}#{species}#{grade}#{panel_type}#{treatment}#{edge}#{finish}#{brand}#{origin}#{metric}"

    hashed_id = hashlib.sha256(concatenated_id.encode()).hexdigest()[:10]
    unique_id = f"{supplier_id}#{hashed_id}"

    square_feet = length * width / 144
    if not metric:
        weight = square_feet * thickness / 12 * LUMBER_DENSITY.get(species, 50) # TODO: 50 is a placeholder value, seemed conservative
    else:
        weight = square_feet * thickness / 12 * LUMBER_DENSITY.get(species, 50) / 25.4 # TODO: 50 is a placeholder value, seemed conservative
    
    if "packSize" in row and row['packSize'] != '':
        pack_size = int(row['packSize'])
    else:
        pack_size = BUNDLE_SIZES["sheet_good"].get(thickness)

    if supplier_id == 'BX_YL':
        # BlueLinx costs are in $/1000 sq ft
        price_type = 'a'

        pc_price = row.get('pcPrice')
        try:
            pc_price = float(pc_price)
        except Exception as e:
            pc_price = None

        if not pack_size:
            if not pc_price:
                row['error'] = 'Missing packSize and pcPrice'
                return row
            costs = [
                # If the profile is unrecognized, default to the biggest adder possible (piece price forever - no break)
                ((pc_price*square_feet)/1000, 1)
            ]
        else:
            # some products are only sold in packs
            if not pc_price:
                costs = [(base_price*square_feet/1000, pack_size)]
            else:
                costs = [
                    ((pc_price*square_feet)/1000, 1),
                    (base_price*square_feet/1000, pack_size)
                ]
    elif supplier_id == 'GS_PSK':
        # TODO: get the actual numbers for these adders
        price_type = 'a'
        if not pack_size:
            costs = [
                # If the profile is unrecognized, default to the biggest adder possible (250 forever - no break)
                ((base_price*square_feet+250)/1000, 1)
            ]
        else:
            costs = [
                ((base_price*square_feet+250)/1000, 1),
                (base_price*square_feet/1000, pack_size)
            ]

    costs = [(round(cost, 5), q) for (cost, q) in costs]
    if supplier_id != 'RRT':
        # Simple 10% markup until we develop a pricing model, and round both costs and prices to 4 decimal places
        prices = [(round(cost*1.1, 5), q) for (cost, q) in costs]
    else:
        # TODO: determine if we need to separate these out for accounting purposes
        prices = costs

    heading = f"{brand} {format_distance(width)} x {format_distance(length)} x {format_distance(thickness, metric=='Y')} {panel_type}".strip()
    subheading_parts = []
    if grade:
        subheading_parts.append(grade)
    if treatment:
        subheading_parts.append(treatment)
    if edge:
        subheading_parts.append(edge)
    if finish:
        subheading_parts.append(finish)
    if origin:
        subheading_parts.append(origin)
    subheading = " | ".join(subheading_parts)

    item = {
        'ItemType': "P",
        'UniqueId': unique_id,
        'Category': "sheet_good",
        'PanelType': panel_type,
        'SKU': hashed_id,
        'FacilityId': supplier_id,
        'Length': length,
        'Width': width,
        'Thickness': thickness,
        'SQFT': square_feet,
        'Weight': weight,
        'Costs': costs,
        'Prices': prices,
        'PriceType': price_type,
        'Heading': heading,
        'Subheading': subheading,
        'Image': panel_type,
        'MinPackSize': prices[0][1], # for searching/filtering the table
        'Unit': "pc", # individual pieces
    }

    if brand:
        item['Brand'] = brand
    if origin:
        item['Origin'] = origin
    if grade:
        item['Grade'] = grade
    if species:
        item['Species'] = species
    if edge:
        item['Edge'] = edge
    if finish:
        item['Finish'] = finish
    if metric:
        item['Metric'] = metric
    if treatment:
        item['Treatment'] = treatment
    
    return json.loads(json.dumps(item), parse_float=Decimal)


def handler(event, context):
    key = 'admin/productupload/' + event['key'] + '.csv'
    print(f"Processing file: {key}")
    
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=os.environ['STORAGE_TEZBUILDDATABUCKET_BUCKETNAME'], Key=key)
    lines = response['Body'].read().decode('utf-8').splitlines()
    
    reader = csv.DictReader(lines)

    supplier_id = event['supplierId']

    if supplier_id not in ['RRT', 'BX_YL', 'GS_PSK']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid supplierId'
            })
        }

    category = event.get('category')
    if category and category not in ['lumber', 'sheet_good']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid global category'
            })
        }
    
    # If this flag is set, clear all existing product data for that supplier and category
    # Example usage: RRT's inventory does not include certain products every month, so we want to remove them
    # In the future we can get more sophisticated and move them somewhere or set a flag preventing them from being shown
    clearCategory = event.get('clearCategory', False)
    if clearCategory:
        clear_supplier(category, supplier_id)

    clearSupplier = event.get('clearSupplier', False)
    if clearSupplier:
        clear_supplier("all", supplier_id)

    rejected_items = []
    with table.batch_writer() as batch:
        for row in reader:
            print(row)
            if 'category' in row:
                category = row.get('category')

            if category == 'lumber':
                item = parse_lumber(row, supplier_id)
            elif category == 'sheet_good':
                item = parse_sheet_good(row, supplier_id)
            else:
                row['error'] = 'Invalid row category'
                item = row

            if item is None:
                row['error'] = 'Parser returned None'
                item = row
                
            if 'error' in item:
                rejected_items.append(row)
                continue

            batch.put_item(Item=item)
    
    print(f"Rejected items: {rejected_items}")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Upload completed with ' + str(len(rejected_items)) + ' rejected items' if rejected_items else 'Upload successful!',
            'rejected_items': rejected_items
        })
    }
