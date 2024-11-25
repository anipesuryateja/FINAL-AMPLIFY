import json
import boto3
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
 
# Initialize the S3 client
s3 = boto3.client('s3')
 
def handler(event, context):
    # Extract S3 bucket name and file key from the event
    bucket_name = event['bucket_name']
    file_key = event['file_key']
   
    # Fetch the .eml file from the S3 bucket
    try:
        file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)
        eml_content = file_obj['Body'].read()
    except Exception as e:
        print(f"Error retrieving file from S3: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error retrieving file from S3: {e}")
        }
 
    # Parse the email content
    msg = BytesParser(policy=policy.default).parsebytes(eml_content)
 
    # Extract basic fields from the email
    subject = msg.get('Subject')
    sender = msg.get('From')
    recipient = msg.get('To')
    date = msg.get('Date')
   
    # Print email metadata
    print(f"Subject: {subject}")
    print(f"From: {sender}")
    print(f"To: {recipient}")
    print(f"Date: {date}")
 
    # Extract the body content (HTML)
    html_body = None
    if msg.is_multipart():
        # If the message is multipart, iterate through the parts
        for part in msg.iter_parts():
            if part.get_content_type() == 'text/html':
                html_body = part.get_payload(decode=True).decode()
                break  # Stop after finding the HTML part
    else:
        # If not multipart, just grab the body directly
        html_body = msg.get_payload(decode=True).decode()
 
    if html_body:
        # Print the raw HTML body for debugging
        print("\nBody (HTML):")
        print(html_body)
 
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_body, 'html.parser')
 
    # Extract the order details (assuming a table format)
    order_details = []
    tables = soup.find_all('table')  # Find all tables in the email
    print("\nTotal tables found:", len(tables))
   
    # Extract order details from the first table
    if tables:
        # Process the first table for order details
        order_table = tables[0]
        headers = []
        rows = order_table.find_all('tr')
        print("\nRows in first table:", len(rows))
       
        # Extract headers (table column names)
        header_cells = rows[0].find_all('th')
        for header in header_cells:
            headers.append(header.get_text(strip=True))
 
        # Print headers for debugging
        print("\nHeaders found:", headers)
 
        # Extract order rows, but skip "Edit Here" rows
        sku_row = None  # To store the SKU row
        for i, row in enumerate(rows[1:]):  # Skip the header row
            # Extract columns (table data)
            columns = row.find_all('td')
            order_row = {}
           
            if len(columns) == len(headers):  # Ensure the row has all the columns
                for j, header in enumerate(headers):
                    order_row[header] = columns[j].get_text(strip=True)
 
                # Print the current row for debugging
                print(f"\nRow {i+1}: {order_row}")
 
                # Check if it's an "Edit Here" row (process these rows after a SKU row)
                if "Edit here" in str(row):
                    if sku_row:  # If there is an SKU row before it, compare
                        print(f"Comparing SKU row and Edit Here row for SKU: {sku_row.get('SKU')}")
                        for header in headers:
                            if header in order_row and header in sku_row:
                                old_value = sku_row[header]
                                new_value = order_row[header]
                                if old_value != new_value:
                                    print(f"Change detected in '{header}' for SKU: {sku_row.get('SKU')}")
                                    change = {
                                        "SKU": sku_row.get('SKU', 'Unknown'),
                                        f"old_{header}": old_value,
                                        f"new_{header}": new_value
                                    }
                                    print(f"Change: {change}")
                    # Reset sku_row after processing the "Edit here" row
                    sku_row = None
                    continue  # Skip "Edit here" rows from further processing
 
                # Store the current SKU row for comparison with the next "Edit here" row
                sku_row = order_row
 
                # Add order row to details list
                order_details.append(order_row)
 
    # Display extracted order details
    if order_details:
        print("\nOrder Details:")
        for order in order_details:
            print(order)
 
    # Extract Total and Tax from the second table inside the div
    total_cost = None
    tax_cost = None
 
    # Find the div containing the second table (summary table)
    summary_div = soup.find('div', style=lambda value: value and 'width: 200px' in value)
   
    if summary_div:
        # Now find the table inside the div
        summary_table = summary_div.find('table')
       
        if summary_table:
            # Extract rows from the summary table
            summary_rows = summary_table.find_all('tr')
            print("\nRows in second table (Summary):", len(summary_rows))
           
            # Loop through the rows to find Tax and Total
            for row in summary_rows:
                # Get all the cells in the row (th and td)
                header_cell = row.find('th')
                value_cell = row.find('td')
 
                if header_cell and value_cell:
                    label = header_cell.get_text(strip=True)  # The label in the 'th'
                    value = value_cell.get_text(strip=True)  # The value in the 'td'
 
                    # Debugging output to inspect the label and value
                    print(f"Debug: Checking label: '{label}', value: '{value}'")  # Debugging line
                   
                    # Check for the label (Tax or Total) in the header
                    if 'Tax' in label:
                        tax_cost = value
                        print(f"Found Tax: {tax_cost}")
                    elif 'Total' in label:
                        total_cost = value
                        print(f"Found Total: {total_cost}")
 
    # Print Total and Tax if found
    if total_cost:
        print(f"\nTotal Order Cost: {total_cost}")
    else:
        print("\nTotal Cost not found.")
 
    if tax_cost:
        print(f"\nTax: {tax_cost}")
    else:
        print("\nTax not found.")
 
    # Extract Delivery Address (check the text containing "Delivery Address")
    delivery_address = soup.find('p', string=lambda text: text and 'Delivery Address' in text)
    if delivery_address:
        print(f"\n{delivery_address.get_text()}")  # Delivery address found
    else:
        print("\nDelivery Address not found.")
 
    # Return success status
    return {
        "statusCode": 200,
        "body": json.dumps("EML parsed successfully")
    }