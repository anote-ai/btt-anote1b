from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# In-memory storage
LEADERBOARD_FILE = "leaderboard_data.json"

def load_leaderboard_data():
    """Load leaderboard data from JSON file"""
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_leaderboard_data(data):
    """Save leaderboard data to JSON file"""
    try:
        with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def validate_dataset_data(data):
    """Validate dataset input data"""
    required_fields = ["name", "url", "task_type"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if not isinstance(data.get("models", []), list):
        return False, "Models must be a list"
    
    return True, "Valid"

def validate_model_data(data):
    """Validate model submission data"""
    required_fields = ["dataset_name", "model", "score", "updated"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if not isinstance(data.get("score"), (int, float)):
        return False, "Score must be a number"
    
    return True, "Valid"

@app.route('/api/leaderboard/add_dataset', methods=['POST'])
def add_dataset():
    """Add a new benchmark dataset to the leaderboard"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Validate input data
        is_valid, message = validate_dataset_data(data)
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": message
            }), 400
        
        # Load existing data
        leaderboard_data = load_leaderboard_data()
        
        # Check if dataset already exists
        for dataset in leaderboard_data:
            if dataset.get('name') == data['name']:
                return jsonify({
                    "status": "error",
                    "message": "Dataset with this name already exists"
                }), 409
        
        # Create new dataset
        dataset_id = str(uuid.uuid4())
        new_dataset = {
            "id": dataset_id,
            "name": data["name"],
            "url": data["url"],
            "task_type": data["task_type"],
            "description": data.get("description", ""),
            "models": data.get("models", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add to leaderboard
        leaderboard_data.append(new_dataset)
        
        # Save to file
        if save_leaderboard_data(leaderboard_data):
            return jsonify({
                "status": "success",
                "message": "Dataset added to leaderboard successfully",
                "dataset_id": dataset_id,
                "dataset": new_dataset
            }), 201
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save dataset"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/leaderboard/add_model', methods=['POST'])
def add_model():
    """Add a new model submission to an existing dataset"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Validate input data
        is_valid, message = validate_model_data(data)
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": message
            }), 400
        
        # Load existing data
        leaderboard_data = load_leaderboard_data()
        
        # Find the dataset
        dataset_found = False
        for dataset in leaderboard_data:
            if dataset.get('name') == data['dataset_name']:
                dataset_found = True
                
                # Check if model already exists
                for existing_model in dataset.get('models', []):
                    if existing_model.get('model') == data['model']:
                        return jsonify({
                            "status": "error",
                            "message": "Model already exists in this dataset"
                        }), 409
                
                # Create new model entry
                new_model = {
                    "rank": data.get("rank", len(dataset.get('models', [])) + 1),
                    "model": data["model"],
                    "score": data["score"],
                    "ci": data.get("ci", ""),
                    "updated": data["updated"]
                }
                
                # Add model to dataset
                if 'models' not in dataset:
                    dataset['models'] = []
                dataset['models'].append(new_model)
                
                # Update dataset timestamp
                dataset['updated_at'] = datetime.now().isoformat()
                
                # Sort models by score (descending) and update ranks
                if dataset['models']:
                    dataset['models'].sort(key=lambda x: x['score'], reverse=True)
                    for i, model in enumerate(dataset['models']):
                        model['rank'] = i + 1
                
                break
        
        if not dataset_found:
            return jsonify({
                "status": "error",
                "message": "Dataset not found"
            }), 404
        
        # Save updated data
        if save_leaderboard_data(leaderboard_data):
            return jsonify({
                "status": "success",
                "message": "Model added to dataset successfully",
                "model": new_model
            }), 201
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save model submission"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
