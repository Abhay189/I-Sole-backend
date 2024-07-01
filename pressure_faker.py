import boto3
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('I-sole-device-data')

def generate_random_pressure_data():
    return {
        'p1': Decimal(str(round(random.uniform(1.0, 5.0), 3))),
        'p2': Decimal(str(round(random.uniform(1.0, 5.0), 3))),
        'p3': Decimal(str(round(random.uniform(1.0, 5.0), 3))),
        'p4': Decimal(str(round(random.uniform(1.0, 5.0), 3))),
        'p5': Decimal(str(round(random.uniform(1.0, 5.0), 3))),
        'p6': Decimal(str(round(random.uniform(1.0, 5.0), 3)))
    }

def add_pressure_data(username, num_records):
    for i in range(num_records):
        # Generate current timestamp and format it as string
        timestamp = (datetime.utcnow() - timedelta(minutes=i)).isoformat(sep='T', timespec='microseconds')
        
        # Generate random pressure data
        pressure_data = generate_random_pressure_data()
        
        # Prepare the item to be inserted
        item = {
            'username': username,
            'timestamp': timestamp,
            'pressure': pressure_data
        }
        
        # Put the item into the DynamoDB table
        table.put_item(Item=item)
        print(f"Inserted item with timestamp {timestamp}")

if __name__ == "__main__":
    username = 'testuser'
    num_records = 10  # Adjust the number of records as needed
    add_pressure_data(username, num_records)