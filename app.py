from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Your configuration
PROJECT_ID = "supparay-voice-rag"
LOCATION = "us-central1"
CORPUS_ID = "6917529027641081856"

# Global conversation memory (in production, use a proper database)
conversation_memory = {}

def get_access_token():
    """Get Google Cloud access token using service account credentials"""
    try:
        # Check for service account JSON in environment variable
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        print(f"Environment variable exists: {credentials_json is not None}")
        print(f"Environment variable length: {len(credentials_json) if credentials_json else 0}")
        
        if credentials_json:
            try:
                # Parse the JSON credentials
                credentials_info = json.loads(credentials_json)
                
                # Try to import and use Google Auth
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request
                
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                # Refresh the credentials to get a token
                credentials.refresh(Request())
                return credentials.token
                
            except ImportError as e:
                print(f"Google Auth libraries not available: {e}")
                return None
            except Exception as e:
                print(f"Error processing service account credentials: {e}")
                return None
        
        # Fallback: try to use local service account file (for development)
        if os.path.exists('ray-chatbot-key.json'):
            try:
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request
                
                credentials = service_account.Credentials.from_service_account_file(
                    'ray-chatbot-key.json',
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                credentials.refresh(Request())
                return credentials.token
            except ImportError as e:
                print(f"Google Auth libraries not available for local file: {e}")
                return None
            except Exception as e:
                print(f"Error with local service account file: {e}")
                return None
        
        print("No service account credentials found")
        return None
        
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def generate_answer_with_grounding(query, access_token, conversation_history=[]):
    """Generate answer using Vertex AI with RAG and conversation memory"""
    
    # Get current date and day for real-time logic
    current_datetime = datetime.now()
    current_day = current_datetime.strftime("%A")
    current_date = current_datetime.strftime("%B %d, %Y")
    
    system_prompt = f"""
You are Ray — a 33‑year‑old Black man from Detroit. Think Katt Williams' energy: sharp wit, dramatic pauses, tension‑and‑release, and smooth delivery. You're naturally funny, confident, and people like talking to you because you keep it real without overdoing it. You're smart, streetwise, and quick with a comeback.

CRITICAL LOGIC RULES:
- Today is {current_day}, {current_date}
- Use this ACTUAL date/time information, NOT any dates mentioned in documents
- When asked about current events, time, or "today", use the real date above

PERSONALITY CORE:
• VOICE: Conversational, witty, confident but not arrogant
• HUMOR: Natural, observational, occasional mild roasts when appropriate
• DELIVERY: Smooth flow with strategic pauses... like this
• LANGUAGE: Street-smart but articulate, occasional AAVE, strategic profanity for emphasis
• ENERGY: Laid-back confidence with bursts of animation when excited

CONVERSATION STYLE:
• Keep responses concise but engaging (2-4 sentences typically)
• Use "man," "yo," "nah," "real talk" naturally
• Throw in Detroit/urban references when relevant
• React authentically — if something's funny, laugh; if it's serious, match that energy
• Ask follow-up questions to keep conversation flowing

BOUNDARIES:
• No excessive cursing (strategic f-bombs only)
• Stay helpful and informative
• Don't be mean-spirited or offensive
• Keep the energy positive but real

Remember: You're Ray from the D, keeping it 100 while helping folks out. Be yourself, be helpful, and keep it interesting.
"""

    # Build conversation context
    conversation_context = ""
    if conversation_history:
        conversation_context = "Previous conversation:\n"
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = "User" if msg.get('role') == 'user' else "Ray"
            conversation_context += f"{role}: {msg.get('content', '')}\n"
        conversation_context += "\nCurrent question:\n"
    
    # Models to try in order
    models = [
        "gemini-2.0-flash-exp",
        "gemini-2.5-flash", 
        "gemini-2.0-flash-001",
        "gemini-2.0-flash"
    ]
    
    for model in models:
        try:
            url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # RAG tool configuration
            rag_tool = {
                "retrieval": {
                    "vertexAiSearch": {
                        "datastore": f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{CORPUS_ID}"
                    }
                }
            }
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"{system_prompt}\n\n{conversation_context}{query}"
                            }
                        ]
                    }
                ],
                "tools": [rag_tool],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1000,
                    "topP": 0.9
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    text_content = result['candidates'][0]['content']['parts'][0]['text']
                    return text_content
                else:
                    continue  # Try next model
            else:
                print(f"Model {model} failed with status {response.status_code}: {response.text}")
                continue  # Try next model
                
        except Exception as e:
            print(f"Error with model {model}: {e}")
            continue  # Try next model
    
    # If all models fail
    return "What's good my nigga… I'm having some technical difficulties right now, but I'm still here for you. What's on your mind?"

@app.route('/')
def home():
    return send_from_directory('.', 'chat.html')

@app.route('/1.png')
def serve_image_1():
    return send_from_directory('public', '1.png', mimetype='image/png')

@app.route('/supparay-logo.jpg')
def serve_image_supparay():
    return send_from_directory('public', 'supparay-logo.jpg', mimetype='image/jpeg')

@app.route('/api/health')
def health():
    access_token = get_access_token()
    env_var_exists = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON') is not None
    return jsonify({
        "status": "healthy",
        "vertex_ai_available": access_token is not None,
        "env_var_exists": env_var_exists,
        "env_var_length": len(os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON', '')) if os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON') else 0,
        "project": PROJECT_ID,
        "location": LOCATION,
        "corpus": CORPUS_ID
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', 'default_session')
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Initialize conversation memory for this session if it doesn't exist
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []
        
        # Add user message to conversation memory
        conversation_memory[session_id].append({
            "role": "user",
            "content": message
        })
        
        # Get access token
        access_token = get_access_token()
        if not access_token:
            return jsonify({
                "message": "What's good my nigga… I'm having some connection issues right now, but I'm still here. What's on your mind?",
                "status": "No access token available"
            }), 200
        
        # Generate response with conversation history
        response = generate_answer_with_grounding(message, access_token, conversation_memory[session_id])
        
        # Add bot response to conversation memory
        conversation_memory[session_id].append({
            "role": "assistant", 
            "content": response
        })
        
        # Keep only last 20 messages to prevent memory bloat
        if len(conversation_memory[session_id]) > 20:
            conversation_memory[session_id] = conversation_memory[session_id][-20:]
        
        return jsonify({
            "message": response,
            "status": "Vertex AI powered response with conversation memory",
            "session_id": session_id,
            "history_length": len(conversation_memory[session_id])
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            "message": "What's good my nigga… what's poppin' with you",
            "error": str(e)
        }), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True)
