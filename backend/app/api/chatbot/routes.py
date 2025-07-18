
import json
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_cors import cross_origin
import uuid
from app.services.ai_service import ai_service
from app.api.projects.routes import get_project

chatbot_bp = Blueprint('chatbot', __name__)

# Simple session management
conversation_sessions: dict[str, list] = {}

@chatbot_bp.route('/chat', methods=['POST'])
@cross_origin()
def chat():
    """Handles chat messages and returns a streaming response."""
    data = request.json
    message = data.get('message', '')
    project_id = data.get('projectId')
    session_id = data.get('sessionId')
    tool_context = data.get('toolContext')  # New: tool context from frontend

    print(f"[CHATBOT API] Received request:")
    print(f"  Message: {message}")
    print(f"  Project ID: {project_id}")
    print(f"  Tool Context: {tool_context}")
    
    if tool_context:
        print(f"[CHATBOT API] Tool context details:")
        print(f"  Tool name: {tool_context.get('tool_name', 'Not specified')}")
        print(f"  Description: {tool_context.get('description', 'Not specified')}")
        print(f"  Parameters: {tool_context.get('parameters', [])}")
        print(f"  Current values: {tool_context.get('current_values', {})}")
    else:
        print(f"[CHATBOT API] No tool context provided")

    if not session_id:
        session_id = str(uuid.uuid4())
        conversation_sessions[session_id] = []

    # Get conversation history
    conversation_history = conversation_sessions.get(session_id, [])

    def generate_response():
        # Get the AI service response generator
        response_generator = ai_service.get_react_response(
            message,
            project_id=project_id,
            conversation_history=conversation_history,
            tool_context=tool_context
        )
        
        # Stream the main response
        for chunk in response_generator:
            yield chunk
        
        # After streaming is complete, check for tool recommendations and parameter applications
        agent = ai_service.get_last_agent()
        if agent:
            tool_recommendation = agent.get_tool_recommendation()
            if tool_recommendation:
                # Send tool recommendation as a special message
                recommendation_data = {
                    "type": "tool_recommendation",
                    "recommendation": tool_recommendation,
                    "timestamp": time.time()
                }
                yield f"\n\n__TOOL_RECOMMENDATION__:{json.dumps(recommendation_data)}"
            
            # Check for parameter suggestion and application actions
            if hasattr(agent, 'last_tool_results'):
                for tool_result in agent.last_tool_results:
                    if (tool_result.is_success and 
                        tool_result.metadata and 
                        tool_result.metadata.get('action') == 'parameter_suggestion'):
                        # Send parameter suggestion as a special message
                        param_suggestion_data = {
                            "type": "parameter_suggestion",
                            "tool_name": tool_result.metadata.get('tool_name'),
                            "suggested_parameters": tool_result.metadata.get('suggested_parameters'),
                            "summary": tool_result.metadata.get('summary'),
                            "timestamp": time.time()
                        }
                        yield f"\n\n__PARAMETER_SUGGESTION__:{json.dumps(param_suggestion_data)}"
                    elif (tool_result.is_success and 
                          tool_result.metadata and 
                          tool_result.metadata.get('action') == 'apply_parameters'):
                        # Send parameter application as a special message
                        param_data = {
                            "type": "parameter_application",
                            "tool_name": tool_result.metadata.get('tool_name'),
                            "parameters": tool_result.metadata.get('parameters'),
                            "summary": tool_result.metadata.get('summary'),
                            "timestamp": time.time()
                        }
                        yield f"\n\n__PARAMETER_APPLICATION__:{json.dumps(param_data)}"

    return Response(stream_with_context(generate_response()), mimetype='text/plain')

@chatbot_bp.route('/project/status/<project_id>', methods=['GET'])
@cross_origin()
def get_project_status_route(project_id):
    """Get the status of a specific project."""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        
        # The get_project function from projects/routes.py returns a Flask Response object
        # We need to get the JSON data from it
        project_data = project.get_json()
        
        return jsonify({
            "status": project_data.get('status', 'unknown'),
            "details": project_data.get('status_details', {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chatbot_bp.route('/health', methods=['GET'])
@cross_origin()
def chatbot_health():
    """Health check endpoint for the chatbot service."""
    try:
        # Simple health check - verify the AI service is available
        return jsonify({
            'status': 'healthy',
            'service': 'chatbot',
            'model': ai_service.model
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'service': 'chatbot',
            'error': str(e)
        }), 500
