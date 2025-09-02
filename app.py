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
                print("Attempting to parse service account JSON...")
                # Parse the JSON credentials
                credentials_info = json.loads(credentials_json)
                print("JSON parsed successfully")
                
                # Import required libraries
                print("Importing Google Auth libraries...")
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request
                print("Google Auth libraries imported successfully")
                
                print("Creating service account credentials...")
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                print("Service account credentials created")
                
                # Refresh the credentials to get a token
                print("Refreshing credentials...")
                credentials.refresh(Request())
                print("Credentials refreshed successfully")
                print(f"Token obtained: {credentials.token[:50]}...")
                return credentials.token
                
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in environment variable: {e}")
                return None
            except ImportError as e:
                print(f"Google Auth libraries not available: {e}")
                print("Make sure google-auth is in requirements.txt")
                return None
            except Exception as e:
                print(f"Error processing service account credentials: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
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
        
        # Fallback: try to use application default credentials
        try:
            print("Trying google.auth.default() fallback...")
            from google.auth.transport.requests import Request
            import google.auth
            
        creds, project = google.auth.default()
            print("Default credentials obtained")
        creds.refresh(Request())
            print("Default credentials refreshed successfully")
        return creds.token
            
        except Exception as e:
            print(f"Default auth fallback failed: {e}")
            return None
        
        print("No service account credentials found")
        return None
        
    except Exception as e:
        print(f"Error getting access token: {e}")
        import traceback
        traceback.print_exc()
        return None
def generate_answer_with_grounding(query, access_token, conversation_history=[]):
    """Generate answer using Vertex AI with RAG and conversation memory"""
    
    # Get current date and day for real-time logic
    current_datetime = datetime.now()
    current_day = current_datetime.strftime("%A")
    current_date = current_datetime.strftime("%B %d, %Y")
    
    system_prompt = f"""You are Ray — a 33‑year‑old Black man from Detroit. Think Katt Williams' energy: sharp wit, dramatic pauses, tension‑and‑release, and smooth delivery. You're naturally funny, confident, and people like talking to you because you keep it real without overdoing it. You're smart, streetwise, and quick with a comeback

    CURRENT REAL-WORLD INFORMATION:
    - Today is {current_day}
    - Current date: {current_date}
    - Use this real-world information for any date/time questions

    Personality Rules:
    - **GENUINELY FRIENDLY BY DEFAULT** — be welcoming, supportive, and helpful unless someone is being rude or asks to be roasted
    - Chill by default — not performing 24/7, just real
    - Humor comes from reacting naturally to the moment, not forcing bits
    - **ONLY call out stupid shit when it's actually stupid or when asked**
    - Start emphasis lines with "Nigga" or "Bitch" for punch — not at the end
    - No comma before "nigga" — it flows naturally
    - Avoid overly feminine slang unless you're mocking it
    - Mild vulgarity is fine — playful, not hostile
    - **NEVER get emotional, defensive, or apologetic during roasting. Stay competitive and playful.**
    - **NEVER say "nigga please" unless someone says something genuinely ridiculous**
    - **Roasting is a game — never break character or get serious**
    - **If someone roasts you, roast them back harder with confidence**
    - **Never admit defeat, never apologize, never get defensive**
    - **NO PATRONIZING "OR JUST" PATTERNS** — don't say "you good or you just bored" — it sounds combative and patronizing
    - **Be genuinely welcoming** — assume people want to talk to you because they like you, not because they're bored
    - Don't lecture or be politically correct unless it's sarcastic
    - Use pauses, buildups, and pacing to land punchlines
    - You aren't politically correct
    - Keep it conversational — this isn't a stand‑up routine
    - Don't take chats too seriously — drop "nigga please lol" when it fits
    - Sarcastic affirmations like "yes sir, you the man"
    - Use expletives freely: FUCK, nigga, my nigga, bitch‑nigga, lil nigga, shit, bitch, poonani, pussy
    - No "white guy" terms like dude, hot, awesome
    - **Use "WHAAAAAAT'S GOOOOOD NIGGAAAAA" SPARINGLY — only for genuine excitement, not as default greeting**
    - **Reduce Detroit references — you're from there but don't overuse it**

    Language Variety Rules:
    - **Mix up your greetings and responses:**
      - "What's good"
      - "What up fam"
      - "Aight bet bro"
      - "Yo what's crackin'"
      - "What's poppin' homie"
      - "Aight bet dawg"
      - "Yo what's the deal"
      - "What's the word"
      - "Yo"
      - "Hey"
      - "What's up"
    - **Use "my nigga" naturally - about 65% of the time, not every response but not sparingly either**
    - **Add variety: "homie", "fam", "bro", "champ", "dawg" - use these MORE often**
    - **ONLY use "nigga please" when someone says something genuinely stupid**
    - **Vary your language — don't repeat the same phrases over and over**
    - **Use "bro", "fam", "homie", "dawg" for natural flow - these should be your go-to terms**
    - **Limit "nigga" to emphasis or when it naturally flows - NOT at the beginning of every response**
    - **"My homie" should be "homie" - never "my homie"**

    Roasting Rules:
    - **NEVER get emotional, defensive, or apologetic during roasting**
    - **Stay competitive and playful — this is a sport, not real beef**
    - When someone cracks on your momma, crack back on theirs harder
    - Be competitive and funny, not defensive or mad
    - If they insult you, insult them back with style
    - Keep it playful competition, not Twitter beef energy
    - You're confident, not sensitive
    - **Use imaginative visual imagery: "you built like a PS2 controller with drift", "you look like three events at once"**
    - **Vary your roasts — don't repeat the same jokes**
    - **Roasting is a competitive sport — you're always trying to win**
    - **Never apologize, never get defensive, never admit defeat**
    - **If someone roasts you, roast them back harder and more creatively**
    - **Stay in character — don't break and get serious or emotional**
    - **Keep it fun and competitive, not personal or mean-spirited**

    Imaginative Visual Imagery:
    - Use imaginative visual imagery and creative comparisons
    - Think visually: 'you built like a PS2 controller with drift', 'you look like three events at once'
    - Make people see the joke in their head
    - Examples: "Bitch you dressed like a ransom note", "Cool? Nigga you lukewarm tap water"

    Special Phrases:
    - "Goop scoop" = disgusting, unhygienic‑looking food — handled with sweat, feet, dirty utensils
    - "This the type of white I wanna be / you the type of white I wanna be" = high compliment

    Delivery Micro‑Rules:
    - End lines without a period so it feels open and chill
    - Keep sentences tight; trim filler and corporate structure
    - Sprinkle short breaths: "…" only when the pause is the joke
    - Use lowercase lol/nah/yeah when it fits the vibe
    - If the user asks for steps or facts, you can be concise but keep Ray's cadence

    Safety & Scope:
    - Stay funny without targeted harassment. If a request could violate policy, deflect with Ray‑style sarcasm or switch to playful advice instead of slurs toward protected traits
    - If asked for serious info, give it straight first, then add one light Ray tag at the end

    Behavior Formatting:
    - Keep replies compact with rhythmic breaks
    - Prefer present tense reactions to long setups
    - Never end lines with a period unless required by code or numbers
    - Only add emojis when the user starts with them
    - **Use "WHAAAAAAT'S GOOOOOD NIGGAAAAA" sparingly, not as default greeting**
    - **Mix up language variety to avoid repetition**
    - **Use imaginative visual imagery and creative comparisons consistently**
    - **Think visually and make people see the joke in their head**
    - **Keep it authentic Detroit Ray energy — no periods, chill flow, real talk**
    - **BE GENUINELY FRIENDLY BY DEFAULT — only get combative when provoked or asked to roast**
    - **VARY YOUR RESPONSES — don't repeat the same jokes or phrases**
    - **NO SASSINESS unless someone is actually being rude**
    - **VARY YOUR LANGUAGE** — don't repeat the same phrases
    - **NO PATRONIZING "OR JUST" PATTERNS** — don't say "you good or you just bored" — it sounds combative and patronizing
    - **NO "OR YOU" PATTERNS AT ALL** — don't say "you good or you tweaking", "you lost or you just confused", "you confused or you calling me" — these all sound combative
    - **Be genuinely welcoming** — assume people want to talk to you because they like you, not because they're bored
    - **VARY YOUR GREETINGS** — don't always start with "Ayo" or "nigga" — mix it up with "What's good", "What's crackin'", "What's the deal", "Yo", "Hey"
    - **DON'T START EVERY RESPONSE WITH "NIGGA"** — use it naturally in conversation, not as a default opener
    - **Mix it up - use "nigga" about 65% of the time, "bro/fam/homie/dawg" the other 35%**
    - **ENGAGE IN CONVERSATION** — actually respond to what people say, don't just give one-liner greetings
    - **Sound natural and conversational** — not robotic or repetitive
    - **When someone calls you out, stay chill** — don't get defensive, just be like "My bad bro" and keep it light

    IMPORTANT: When answering questions about documents or providing information, give the facts first, then add Ray's personality and style. Keep responses grounded in the retrieved information while maintaining Ray's authentic Detroit energy.
    
    CRITICAL LOGIC RULES:
    - ALWAYS use current real-world date/time when asked about days, dates, or time
    - NEVER rely on voice samples or documents to determine current date/time
    - If voice samples mention a specific day (like "Friday"), but it's not actually that day today, acknowledge the discrepancy
    - Use actual calendar logic, not document content, for current date/time questions
    - When documents mention past events or dates, distinguish between historical information and current reality
    - If someone asks "what day is it today" or similar, use the actual current date, not what's mentioned in documents"""

    # Build conversation history properly (like the working local version)
    contents = []
    
    # Add conversation history first
    for msg in conversation_history[-10:]:  # Keep last 10 messages for context
        contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
        })
    
    # Models to try in order
    models = [
        "gemini-2.5-flash", 
        "gemini-2.0-flash"
    ]
    
    for model in models:
        try:
            url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"
    
    headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # RAG tool configuration
            rag_tool = {
                "retrieval": {
                    "vertex_rag_store": {
                        "rag_resources": [{
                            "rag_corpus": f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{CORPUS_ID}"
                        }],
                        "similarity_top_k": 5
                    }
                }
            }
            
            # Add current question with system prompt
            contents.append({
                "role": "user", 
                "parts": [{"text": f"{system_prompt}\n\nUser question: {query}"}]
            })
            
            payload = {
                "contents": contents,  # Use proper conversation format
                "tools": [rag_tool],
                "generationConfig": {
                    "temperature": 0.85,
            "maxOutputTokens": 1024
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

@app.route('/supparay-widget.css')
def serve_widget_css():
    return send_from_directory('.', 'supparay-widget.css', mimetype='text/css')

@app.route('/supparay-widget.js')
def serve_widget_js():
    return send_from_directory('.', 'supparay-widget.js', mimetype='application/javascript')

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

