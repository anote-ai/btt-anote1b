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
    
    # Validate task_type
    valid_task_types = ["text_classification", "named_entity_recognition", "document_qa", "line_qa"]
    if data.get("task_type") not in valid_task_types:
        return False, f"Invalid task_type. Must be one of: {', '.join(valid_task_types)}"
    
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
    
    if data.get("score") < 0 or data.get("score") > 1:
        return False, "Score must be between 0 and 1"
    
    return True, "Valid"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Anote Leaderboard API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/leaderboard/docs', methods=['GET'])
def api_docs():
    """API documentation endpoint"""
    return jsonify({
        "service": "Anote Model Leaderboard API",
        "version": "1.0.0",
        "description": "Public API for adding datasets and model submissions to the Anote AI Leaderboard",
        "endpoints": {
            "GET /api/health": {
                "description": "Health check endpoint",
                "method": "GET",
                "response": "Service health status"
            },
            "GET /api/leaderboard/docs": {
                "description": "API documentation",
                "method": "GET",
                "response": "API documentation and usage guide"
            },
            "GET /api/leaderboard/get_datasets": {
                "description": "Get all datasets with their models",
                "method": "GET",
                "response": "List of all datasets and leaderboard data"
            },
            "POST /api/leaderboard/add_dataset": {
                "description": "Add a new benchmark dataset to the leaderboard",
                "method": "POST",
                "content_type": "application/json",
                "required_fields": ["name", "url", "task_type"],
                "optional_fields": ["description", "models"],
                "task_types": ["text_classification", "named_entity_recognition", "document_qa", "line_qa"],
                "example_request": {
                    "name": "Financial Phrasebank - Classification Accuracy",
                    "url": "https://huggingface.co/datasets/takala/financial_phrasebank",
                    "task_type": "text_classification",
                    "description": "A dataset for financial sentiment classification.",
                    "models": [
                        {
                            "rank": 1,
                            "model": "Gemini",
                            "score": 0.95,
                            "ci": "0.93 - 0.97",
                            "updated": "Sep 2024"
                        }
                    ]
                },
                "example_response": {
                    "status": "success",
                    "message": "Dataset added to leaderboard successfully",
                    "dataset_id": "uuid-string",
                    "dataset": "full dataset object"
                }
            },
            "POST /api/leaderboard/add_model": {
                "description": "Add a new model submission to an existing dataset",
                "method": "POST",
                "content_type": "application/json",
                "required_fields": ["dataset_name", "model", "score", "updated"],
                "optional_fields": ["ci"],
                "example_request": {
                    "dataset_name": "Financial Phrasebank - Classification Accuracy",
                    "model": "Llama3",
                    "score": 0.92,
                    "ci": "0.90 - 0.94",
                    "updated": "Sep 2024"
                },
                "example_response": {
                    "status": "success",
                    "message": "Model added to dataset successfully",
                    "model": "model object with auto-calculated rank"
                }
            },
            "GET /api/leaderboard/stats": {
                "description": "Get leaderboard statistics",
                "method": "GET",
                "response": "Statistics about datasets, models, and task types"
            }
        },
        "notes": {
            "ranking": "Model ranks are automatically calculated based on score (highest to lowest)",
            "duplicates": "Duplicate dataset names and model names within datasets are not allowed",
            "scores": "Scores must be between 0 and 1",
            "persistence": "Data is persisted to leaderboard_data.json file"
        },
        "contact": {
            "project_lead": "Natan Vidra",
            "email": "nvidra@anote.ai",
            "website": "https://anote.ai/leaderboard"
        }
    }), 200

@app.route('/api/leaderboard/stats', methods=['GET'])
def get_stats():
    """Get leaderboard statistics"""
    leaderboard_data = load_leaderboard_data()
    
    total_datasets = len(leaderboard_data)
    total_models = sum(len(dataset.get('models', [])) for dataset in leaderboard_data)
    
    task_type_counts = {}
    for dataset in leaderboard_data:
        task_type = dataset.get('task_type', 'unknown')
        task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
    
    return jsonify({
        "status": "success",
        "statistics": {
            "total_datasets": total_datasets,
            "total_models": total_models,
            "datasets_by_task_type": task_type_counts,
            "average_models_per_dataset": round(total_models / total_datasets, 2) if total_datasets > 0 else 0
        },
        "timestamp": datetime.now().isoformat()
    }), 200

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
        
        # Sort models by score if any exist
        if new_dataset['models']:
            new_dataset['models'].sort(key=lambda x: x.get('score', 0), reverse=True)
            for i, model in enumerate(new_dataset['models']):
                model['rank'] = i + 1
        
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
    
@app.route('/api/leaderboard/get_datasets', methods=['GET'])
def get_datasets():
    """Return all datasets with their models"""
    leaderboard_data = load_leaderboard_data()
    return jsonify({
        "status": "success",
        "datasets": leaderboard_data,
        "count": len(leaderboard_data)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Home endpoint with basic info"""
    return jsonify({
        "service": "Anote Model Leaderboard API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/leaderboard/docs",
        "health_check": "/api/health",
        "message": "Welcome to the Anote AI Leaderboard API! Visit /api/leaderboard/docs for API documentation."
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)