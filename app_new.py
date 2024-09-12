from decimal import Decimal
import boto3
from flask import Flask, Blueprint, request, jsonify, render_template, redirect, url_for, Response
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone
import pytz
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pytz
from matplotlib.figure import Figure


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('I-sole-users')
device_data_table = dynamodb.Table('I-sole-device-data')


@app.route('/signup', methods=['POST'])
def signup():
    try:
        # Parse the incoming data from the signup form
        signup_data = request.json
        username = signup_data['username']
        email = signup_data['email']
        full_name = signup_data['fullName']
        role = signup_data['role']
        password = signup_data['password']

        # Create a new item in the DynamoDB table
        users_table.put_item(
            Item={
                'username': username,
                'email': email,
                'name': full_name,
                'role': role,
                'password': password,
                'personal_metrics': {}  # Add an empty personal_metrics object
            }
        )

        # Fetch the user data to return in the response
        response = users_table.get_item(
            Key={
                'username': username
            }
        )
        user_data = response.get('Item', {})

        return jsonify({"success": True, "message": "User created successfully", 'user_data': user_data}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    



@app.route('/signin', methods=['POST'])
def signin():
    try:
        # Parse the incoming data from the sign-in form
        signin_data = request.json
        username = signin_data['username']
        password = signin_data['password']

        # Fetch the user's data from the DynamoDB table
        response = users_table.get_item(
            Key={
                'username': username
            }
        )
        user_data = response.get('Item', {})
        print(user_data);

        # Check if the user exists and if the password matches
        if user_data and password == user_data.get('password'):
            # Authentication successful
            return jsonify({"success": True, "message": "User signed in successfully", "user_data": user_data}), 200
        else:
            # Authentication failed
            return jsonify({"success": False, "message": "Incorrect username or password"}), 401

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/add_pressure_value/<username>', methods=['POST'])
def add_pressure_value(username):
    try:
        # Get pressure value from request
        pressure_value = request.json.get('pressure')

        # Ensure pressure value is provided
        if pressure_value is None:
            return jsonify({"success": False, "message": "Pressure value not provided"}), 400

        # Get current timestamp
        current_time = datetime.now().isoformat()

        # Add pressure value to the device_data_table in DynamoDB
        device_data_table.put_item(
            Item={
                'username': username,
                'timestamp': current_time,
                'pressure': pressure_value
            }
        )

        return jsonify({"success": True, "message": "Pressure value added successfully"}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get_pressure_data/<username>', methods=['GET'])
def get_pressure_data(username):
    try:
        # Get start and end timestamps from query parameters
        start_timestamp_str = request.args.get('start')
        end_timestamp_str = request.args.get('end')

        # Query pressure data from the device_data_table in DynamoDB
        response = device_data_table.query(
            KeyConditionExpression=Key('username').eq(username) & Key('timestamp').between(start_timestamp_str, end_timestamp_str)
        )

        # Process the response
        pressure_data = []
        for item in response['Items']:
            pressure_data.append({
                'pressure': item['pressure'],
                'timestamp': item['timestamp']
            })

        return jsonify({"success": True, "pressureData": pressure_data}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/add_glucose_value/<username>', methods=['POST'])
def add_glucose_value(username):
    try:
        # Get glucose value from request
        glucose_value = request.json.get('glucose')

        # Ensure glucose value is provided
        if glucose_value is None:
            return jsonify({"success": False, "message": "Glucose value not provided"}), 400

        # Get current timestamp
        current_time = datetime.now().isoformat()

        # Add glucose value to the device_data_table in DynamoDB
        device_data_table.put_item(
            Item={
                'username': username,
                'timestamp': current_time,
                'glucose': glucose_value
            }
        )

        return jsonify({"success": True, "message": "Glucose value added successfully"}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/get_glucose_data/<username>', methods=['GET'])
def get_glucose_data(username):
    try:
        # Get start and end timestamps from query parameters
        start_timestamp_str = request.args.get('start')
        end_timestamp_str = request.args.get('end')

        # Query glucose data from the glucose_data_table in DynamoDB
        response = device_data_table.query(
            KeyConditionExpression=Key('username').eq(username) & Key('timestamp').between(start_timestamp_str, end_timestamp_str)
        )

        # Process the response
        glucose_data = []
        for item in response['Items']:
            glucose_data.append({
                'glucose': item['glucose'],
                'timestamp': item['timestamp']
            })

        return jsonify({"success": True, "glucoseData": glucose_data}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/add_blood_glucose_level', methods=['POST'])
def add_blood_glucose_level():
    try:
        # Parse the request data
        username = request.json.get('username')
        blood_glucose_level = request.json.get('bloodGlucoseLevel')

        # Fetch the user's data from the DynamoDB table
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item', {})

        update_expression = ""
        expression_attribute_values = {}

        # Check if the 'personal_metrics' attribute exists, if not create it
        if 'personal_metrics' not in user_data:
            # Create 'personal_metrics' with the 'blood_glucose_level' field
            update_expression = 'SET personal_metrics = :metrics'
            expression_attribute_values = {':metrics': {'blood_glucose_level': blood_glucose_level}}
        else:
            # Update the existing 'personal_metrics' with the new 'blood_glucose_level' field
            update_expression = 'SET personal_metrics.blood_glucose_level = :glucose_level'
            expression_attribute_values = {':glucose_level': blood_glucose_level}

        # Update the 'blood_glucose_level' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Blood glucose level added successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/get_blood_glucose_level/<username>', methods=['GET'])
def get_blood_glucose_level(username):
    try:
        # Fetch the user's data from the DynamoDB table
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item', {})

        # Check if the user exists
        if user_data:
            # Get the blood_glucose_level from the user's personal_metrics
            blood_glucose_level = user_data.get('personal_metrics', {}).get('blood_glucose_level')
            return jsonify({"success": True, "data": {"blood_glucose_level": blood_glucose_level}}), 200
        else:
            return jsonify({"success": False, "message": "User not found"}), 404

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    
@app.route('/update_predicted_hypoglycemia', methods=['POST'])
def update_predicted_hypoglycemia():
    try:
        # Parse the request data
        username = request.json.get('username')
        predicted_hypoglycemia = request.json.get('predicted_hypoglycemia')

        # Check if the user exists in DynamoDB
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if user_data:
            # Update the 'predicted_hypoglycemia' attribute in the 'users' table in DynamoDB
            response = users_table.update_item(
                Key={'username': username},
                UpdateExpression='SET personal_metrics.predicted_hypoglycemia = :predicted_hypoglycemia',
                ExpressionAttributeValues={':predicted_hypoglycemia': predicted_hypoglycemia},
                ReturnValues='ALL_NEW'  # Return the updated item
            )
            
            # Get the updated item from the response
            updated_item = response.get('Attributes', {})

            # Return success response with the updated item
            return jsonify({"success": True, "message": "Predicted hypoglycemia updated successfully", "updated_item": updated_item}), 200
        else:
            # User doesn't exist, return error response
            return jsonify({"success": False, "message": "User not found: " + username}), 404

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/get_predicted_hypoglycemia/<username>', methods=['GET'])
def get_predicted_hypoglycemia(username):
    try:
        # Query the DynamoDB table for the user data
        response = users_table.get_item(
            Key={'username': username}
        )
        
        # Check if the user exists
        if 'Item' in response:
            user_data = response['Item']
            predicted_hypoglycemia = user_data.get('personal_metrics', {}).get('predicted_hypoglycemia')
            
            if predicted_hypoglycemia is not None:
                return jsonify({"success": True, "data": {"predicted_hypoglycemia": predicted_hypoglycemia}}), 200
            else:
                return jsonify({"success": False, "message": "Predicted hypoglycemia data not found"}), 404
        else:
            return jsonify({"success": False, "message": "User not found"}), 404

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_predicted_hyperglycemia', methods=['POST'])
def update_predicted_hyperglycemia():
    try:
        # Parse the request data
        username = request.json.get('username')
        predicted_hyperglycemia = request.json.get('predicted_hyperglycemia')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        # Update the 'predicted_hyperglycemia' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.predicted_hyperglycemia = :predicted_hypoglycemia',
            ExpressionAttributeValues={':predicted_hypoglycemia': predicted_hyperglycemia},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Predicted hyperglycemia updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/get_predicted_hyperglycemia/<username>', methods=['GET'])
def get_predicted_hyperglycemia(username):
    try:
        # Fetch the user data from DynamoDB
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        # Check if the user exists
        if not user_data:
            return jsonify({"success": False, "message": f"User {username} not found"}), 404

        # Get the predicted_hyperglycemia value from personal_metrics
        predicted_hyperglycemia = user_data.get('personal_metrics', {}).get('predicted_hyperglycemia')

        return jsonify({"success": True, "data": {"predicted_hyperglycemia": predicted_hyperglycemia}}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    


@app.route('/update_height', methods=['POST'])
def update_height():
    try:
        # Parse the request data
        username = request.json.get('username')
        height = request.json.get('height')
        
        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        
        # Update the 'height' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.height = :height',
            ExpressionAttributeValues={':height': height},
            ReturnValues='ALL_NEW'  # Return the updated item
        )
        
        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Height updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

from boto3.dynamodb.conditions import Key

@app.route('/update_insulin_dosage', methods=['POST'])
def update_insulin_dosage():
    try:
        # Parse the request data
        username = request.json.get('username')
        insulinDosage = request.json.get('insulinDosage')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404


        # Update the 'insulin_dosage' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.insulin_dosage = :dosage',
            ExpressionAttributeValues={':dosage': insulinDosage},
            ReturnValues='ALL_NEW'  # Return the updated item
        )
        
        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Insulin dosage updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_allergies', methods=['POST'])
def update_allergies():
    try:
        # Parse the request data
        username = request.json.get('username')
        allergies = request.json.get('allergies')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404


        # Update the 'allergies' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.allergies = :allergies',
            ExpressionAttributeValues={':allergies': allergies},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Allergies updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    


@app.route('/update_insulin_type', methods=['POST'])
def update_insulin_type():
    try:
        # Parse the request data
        username = request.json.get('username')
        insulin_type = request.json.get('insulin_type')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404


        # Update the 'insulin_type' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.insulin_type = :insulin_type',
            ExpressionAttributeValues={':insulin_type': insulin_type},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Insulin type updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/update_physical_activity', methods=['POST'])
def update_physical_activity():
    try:
        # Parse the request data
        username = request.json.get('username')
        physical_activity = request.json.get('physical_activity')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        # Update the 'physical_activity' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.physical_activity = :physical_activity',
            ExpressionAttributeValues={':physical_activity': physical_activity},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Physical activity updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_activity_intensity', methods=['POST'])
def update_activity_intensity():
    try:
        # Parse the request data
        username = request.json.get('username')
        activity_intensity = request.json.get('activity_intensity')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        # Update the 'activity_intensity' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.activity_intensity = :activity_intensity',
            ExpressionAttributeValues={':activity_intensity': activity_intensity},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Activity intensity updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/update_activity_duration', methods=['POST'])
def update_activity_duration():
    try:
        # Parse the request data
        username = request.json.get('username')
        activity_duration = request.json.get('activity_duration')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        # Update the 'activity_duration' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.activity_duration = :activity_duration',
            ExpressionAttributeValues={':activity_duration': activity_duration},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Activity duration updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_stress_level', methods=['POST'])
def update_stress_level():
    try:
        # Parse the request data
        username = request.json.get('username')
        stress_level = request.json.get('stress_level')

        # Check if the user exists and get the current item
        response = users_table.get_item(
            Key={'username': username}
        )
        user_data = response.get('Item')

        if not user_data:
            return jsonify({"success": False, "message": f"User {username} does not exist"}), 404

        # Update the 'stress_level' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.stress_level = :stress_level',
            ExpressionAttributeValues={':stress_level': stress_level},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Stress level updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/update_illness', methods=['POST'])
def update_illness():
    try:
        # Parse the request data
        username = request.json.get('username')
        illness = request.json.get('illness')

        # Update the 'illness' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.illness = :illness',
            ExpressionAttributeValues={':illness': illness},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Illness updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_hormonal_changes', methods=['POST'])
def update_hormonal_changes():
    try:
        # Parse the request data
        username = request.json.get('username')
        hormonal_changes = request.json.get('hormonal_changes')

        # Update the 'hormonal_changes' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.hormonal_changes = :hormonal_changes',
            ExpressionAttributeValues={':hormonal_changes': hormonal_changes},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Hormonal changes updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_alcohol_consumption', methods=['POST'])
def update_alcohol_consumption():
    try:
        # Parse the request data
        username = request.json.get('username')
        alcohol_consumption = request.json.get('alcohol_consumption')

        # Update the 'alcohol_consumption' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.alcohol_consumption = :alcohol_consumption',
            ExpressionAttributeValues={':alcohol_consumption': alcohol_consumption},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Alcohol consumption updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/update_medication', methods=['POST'])
def update_medication():
    try:
        # Parse the request data
        username = request.json.get('username')
        medication = request.json.get('medication')

        # Update the 'medication' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.medication = :medication',
            ExpressionAttributeValues={':medication': medication},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Medication updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_medication_dosage', methods=['POST'])
def update_medication_dosage():
    try:
        # Parse the request data
        username = request.json.get('username')
        medication_dosage = request.json.get('medication_dosage')

        # Update the 'medication_dosage' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.medication_dosage = :medication_dosage',
            ExpressionAttributeValues={':medication_dosage': medication_dosage},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Medication dosage updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_weather_conditions', methods=['POST'])
def update_weather_conditions():
    try:
        # Parse the request data
        username = request.json.get('username')
        weather_conditions = request.json.get('weather_conditions')

        # Update the 'weather_conditions' attribute in the 'users' table in DynamoDB
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET personal_metrics.weather_conditions = :weather_conditions',
            ExpressionAttributeValues={':weather_conditions': weather_conditions},
            ReturnValues='ALL_NEW'  # Return the updated item
        )

        # Get the updated item from the response
        updated_item = response.get('Attributes', {})

        # Return success response with the updated item
        return jsonify({"success": True, "message": "Weather conditions updated successfully", "updated_item": updated_item}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/get_personal_metrics/<username>', methods=['GET'])
def get_personal_metrics(username):
    try:
        # Query DynamoDB for the user's personal metrics
        response = users_table.get_item(
            Key={
                'username': username
            }
        )
        # Check if the item exists in the response
        if 'Item' in response:
            personal_data = response['Item']['personal_metrics']
            return jsonify({"success": True, "data": personal_data}), 200  # Set success to True and include data
        else:
            return jsonify({"success": False, "message": "Personal metrics not found"}), 404
    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/update_name', methods=['POST'])
def update_name():
    try:
        # Parse the request data
        username = request.json.get('username')
        name = request.json.get('name')
        
        # Check if the document exists
        response = users_table.get_item(
            Key={
                'username': username
            }
        )
        
        if 'Item' in response:
            # Update the name in the DynamoDB item
            users_table.update_item(
                Key={
                    'username': username
                },
                UpdateExpression='SET #nameAttr = :nameValue',
                ExpressionAttributeNames={
                    '#nameAttr': 'name'
                },
                ExpressionAttributeValues={
                    ':nameValue': name
                }
            )
            
            # Return success response
            return jsonify({"success": True}), 200
        else:
            # Document doesn't exist, return error response
            return jsonify({"success": False, "message": "Username does not exist: " + username}), 404
        
    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_email', methods=['POST'])
def update_email():
    try:
        # Parse the request data
        username = request.json.get('username')
        email = request.json.get('email')

        # Update the item in the DynamoDB table
        response = users_table.update_item(
            Key={
                'username': username
            },
            UpdateExpression='SET email = :email',
            ExpressionAttributeValues={
                ':email': email
            },
            ReturnValues='UPDATED_NEW'
        )

        # Return success response
        return jsonify({"success": True}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update_phone_number', methods=['POST'])
def update_phone_number():
    try:
        # Parse the request data
        username = request.json.get('username')
        phoneNumber = request.json.get('phoneNumber')

        # Update the item in the DynamoDB table
        response = users_table.update_item(
            Key={
                'username': username
            },
            UpdateExpression='SET phoneNumber = :val1',
            ExpressionAttributeValues={
                ':val1': phoneNumber
            },
            ReturnValues='UPDATED_NEW'
        )

        # Return success response
        return jsonify({"success": True}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_date_of_birth', methods=['POST'])
def update_date_of_birth():
    try:
        # Parse the request data
        username = request.json.get('username')
        dateOfBirth = request.json.get('dateOfBirth')

        # Update the item in the DynamoDB table
        response = users_table.update_item(
            Key={
                'username': username
            },
            UpdateExpression='SET dateOfBirth = :val1',
            ExpressionAttributeValues={
                ':val1': dateOfBirth
            },
            ReturnValues='UPDATED_NEW'
        )

        # Return success response
        return jsonify({"success": True}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/update_emergency_contact', methods=['POST'])
def update_emergency_contact():
    try:
        # Parse the request data
        username = request.json.get('username')
        emergencyContact = request.json.get('emergencyContact')
        
        # Check if the document exists
        response = users_table.get_item(Key={'username': username})
        if 'Item' in response:
            users_table.update_item(
                Key={'username': username},
                UpdateExpression='SET emergencyContact = :val',
                ExpressionAttributeValues={':val': emergencyContact}
            )
            # Return success response
            return jsonify({"success": True}), 200

        else:
            # Document doesn't exist, return error response
            return jsonify({"success": False, "message": "Document does not exist for user: " + username}), 404
        
    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/get_profile_data/<username>', methods=['GET'])
def get_profile_data(username):
    try:
        # Check if the document exists
        response = users_table.get_item(Key={'username': username})
        if 'Item' in response:
            user_data = response['Item']
            return jsonify({"success": True, "data": user_data}), 200  # Set success to True and include data
        else:
            return jsonify({"success": False, "message": "User not found"}), 404

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/update_view_activity', methods=['POST'])
def update_view_activity():
    try:
        # Parse the request data
        username = request.json.get('username')
        value = request.json.get('value')

        # Update the 'view_activity' attribute in the 'users' table
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET view_activity = :val',
            ExpressionAttributeValues={':val': value}
        )

        # Return success response
        return jsonify({"success": True}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/get_view_activity/<username>', methods=['GET'])
def get_view_activity(username):
    try:
        # Get the 'view_activity' attribute from the 'users' table
        response = users_table.get_item(Key={'username': username})
        item = response.get('Item')
        if item:
            return jsonify({"success": True, "view_activity": item.get('view_activity')}), 200  # Set success to True and include data
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500
    
@app.route('/update_view_meals', methods=['POST'])
def update_view_meals():
    try:
        # Parse the request data
        username = request.json.get('username')
        value = request.json.get('value')
        
        # Update the 'view_meals' attribute in the 'users' table
        response = users_table.update_item(
            Key={'username': username},
            UpdateExpression='SET view_meals = :val',
            ExpressionAttributeValues={':val': value}
        )

        # Return success response
        return jsonify({"success": True}), 200

    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/get_view_meals/<username>', methods=['GET'])
def get_view_meals(username):
    try:
        # Get the 'view_meals' attribute from the 'users' table
        response = users_table.get_item(Key={'username': username})
        item = response.get('Item')
        if item:
            return jsonify({"success": True, "view_meals": item.get('view_meals')}), 200  # Set success to True and include data
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        # Handle exceptions
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/plot-prediction', methods=['POST'])
def plot_prediction_endpoint():
    # Parse request data
    request_data = request.json
    input_data_df = pd.DataFrame([request_data['input_data']])
    hyperglycemia_threshold = request_data['hyperglycemia_threshold']
    hypoglycemia_threshold = request_data['hypoglycemia_threshold']

    # Load training data
    training_data = pd.read_csv('544-ws-training.csv')  # Adjust path as necessary
    
    # Here, you would call your adapted plotting function with the loaded data
    image_url = plot_prediction_with_training_and_predicted_data(
        training_data,
        input_data_df,
        hyperglycemia_threshold,
        hypoglycemia_threshold
    )

    # Return the URL to the saved image
    return jsonify({'image_url': image_url})

def plot_prediction_with_training_and_predicted_data(training_data, input_data, hyperglecemia_threshold, hypoglycemia_threshold):
    plt.figure(figsize=(12, 7), facecolor='#1b2130')
    ax = plt.axes()
    ax.set_facecolor('#1b2130')

    # Use 'America/Edmonton' for Alberta, Canada
    utc_minus_6 = pytz.timezone('America/Edmonton')
    current_time = datetime.now().astimezone(utc_minus_6)

    # Create timestamps from 5 hours in the past to 1 hour in the future
    timestamps = [current_time - timedelta(hours=10-x) for x in range(6)]  # Adjusting to include 6 timestamps

    # Adjusted to take the 2nd last to the 5th last values from training_data
    glucose_levels = np.concatenate([training_data['glucose_level_value'].iloc[-5:-1].values, input_data['glucose_level_value'].head(1).values])

    # Get predicted value
    last_row = training_data.iloc[-1:][['glucose_level_value', 'finger_stick_value', 'basal_value', 'basis_gsr_value', 'basis_skin_temperature_value', 'bolus_dose']]
    predicted_value = predict_single_entry(input_data)

    # Plot training data
    plt.plot(timestamps[:-1], glucose_levels, label='Insole Recorded Data', color='#007bff', marker='o', markersize=12, linewidth=3, markeredgewidth=2, markeredgecolor='white')
    plt.fill_between(timestamps[:-1], glucose_levels, y2=glucose_levels.min(), color='#007bff', alpha=0.075) # underglow effect for training data

    if predicted_value<=hypoglycemia_threshold or predicted_value>=hyperglecemia_threshold:
      fill_color = '#ff0000'
    else:
      fill_color = '#7CFC00'

    # Add predicted value as the future point
    predicted_time = timestamps[-1]
    plt.scatter(predicted_time, predicted_value, color=fill_color, label='Predicted Value', zorder=5, s=250, edgecolor='white', linewidth=2)
    plt.plot([timestamps[-2], predicted_time], [glucose_levels[-1], predicted_value], color=fill_color, linestyle='--', linewidth=3)

    # Add underglow effect for predicted value
    plt.fill_between([timestamps[-2], predicted_time], [glucose_levels[-1], predicted_value], y2=glucose_levels.min(), color=fill_color, alpha=0.075) # underglow effect for predicted value

    # Adjust x-axis to properly show all timestamps
    plt.xlim([timestamps[0]- timedelta(seconds=240), predicted_time + timedelta(minutes=30)])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))  # Updated time format
    plt.xticks(rotation=45, color='white', fontsize=16)
    plt.yticks(color='white', fontsize=16)

    # Adjust y-axis limits
    plt.ylim(glucose_levels.min()-2, max(glucose_levels) + 10)

    # Labeling and styling
    plt.xlabel('Time (Hourly)', color='white', fontsize=20, labelpad=20, fontweight='600')
    plt.ylabel('Glucose Level (mg/dL)', color='white', fontsize=20, labelpad=20, fontweight='550')
    # After your plot and legend setup
    legend = plt.legend(facecolor='#1b2130', edgecolor='white', fontsize=16, loc='upper left')
    # Set the color of all the legend text to white
    plt.setp(legend.get_texts(), color='white')

    # Add vertical dotted line across the last training data point
    plt.axvline(x=timestamps[-2], color='white', linestyle='--', linewidth=1.5, alpha=0.8)

    # Add small black box along the line with white text for "Now"
    bbox_props_now = dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.8)
    current_glucose_value = glucose_levels[-1]  # The current (most recent) glucose level
    text_now = f"Now\n{current_glucose_value:.1f} mg/dL"  # Glucose level on the next line, without colon
    plt.text(timestamps[-2], current_glucose_value + 4, text_now, color='white', fontsize=15, ha='center', va='center', bbox=bbox_props_now, linespacing=1.5)


    # Add small black box along the line with white text for "Future"
    bbox_props_future = dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.8)
    predicted_glucose_value = predicted_value  # The future predicted glucose level
    text_future = f"Prediction\n{predicted_glucose_value:.1f} mg/dL"  # Glucose level on the next line, without colon
    plt.text(predicted_time, predicted_glucose_value + 4, text_future, color='white', fontsize=15, ha='center', va='center', bbox=bbox_props_future, linespacing=1.5)

    # Remove the top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('white')


    plt.grid(color='gray', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    
    # Define the image save path
    image_save_path = 'glucose_plot.png'
    plt.savefig(image_save_path)
    plt.close()

    # Construct the URL to access the saved image
    # Adjust the URL based on your actual server setup and image serving mechanism
    image_url = f'https://i-sole-backend.com/{image_save_path}'

    return image_url


def predict_single_entry(input_data):
    # Load the trained model and scaler objects
    model_path = '544_trained_model.h5'
    model = load_model(model_path)
    scaler_x_path = '544_scaler_x.pkl'
    scaler_y_path = '544_scaler_y.pkl'
    scaler_x = joblib.load(scaler_x_path)
    scaler_y = joblib.load(scaler_y_path)

    # Ensure input_data is a DataFrame with the expected columns
    if isinstance(input_data, pd.DataFrame) == False:
        raise ValueError("Input data must be a pandas DataFrame.")
    
    # Ensure the DataFrame has the expected structure
    expected_cols = ['glucose_level_value', 'finger_stick_value', 'basal_value', 'basis_gsr_value', 'basis_skin_temperature_value', 'bolus_dose']
    if not all(col in input_data.columns for col in expected_cols):
        raise ValueError("Input DataFrame does not contain the expected columns.")
    
    # Preprocess the input data
    X_input = input_data.apply(pd.to_numeric, errors='coerce').fillna(0)
    scaled_X_input = scaler_x.transform(X_input)
    scaled_X_input = np.reshape(scaled_X_input, (1, scaled_X_input.shape[0], scaled_X_input.shape[1]))
    
    # Make prediction
    prediction = model.predict(scaled_X_input, batch_size=1)
    scaled_prediction = scaler_y.inverse_transform(prediction)
    
    return scaled_prediction.flatten()[0]  # Return a single predicted value



















if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)


