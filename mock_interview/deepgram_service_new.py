# Copyright 2025 Deepgram SDK contributors. All Rights Reserved.
# Use of this source code is governed by a MIT license that can be found in the LICENSE file.
# SPDX-License-Identifier: MIT

import os
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    AgentWebSocketEvents,
    AgentKeepAlive,
)
from deepgram.clients.agent.v1.websocket.options import SettingsOptions

logger = logging.getLogger(__name__)

class MockInterviewAgent:
    """
    Deepgram Agent for conducting mock interviews using the Agent WebSocket API
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        
        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={
                "keepalive": "true",
            },
        )
        self.deepgram = DeepgramClient(self.api_key, config)
        self.connection = None
        
        # Interview state
        self.session_id = None
        self.questions = []
        self.current_question_index = 0
        self.responses = []
        self.conversation_log = []
        
        # Audio handling
        self.audio_buffer = bytearray()
        self.audio_file_counter = 0
        self.processing_complete = False
        
        # Keep alive thread
        self.keep_alive_thread = None
        self.keep_alive_running = False
        
        # Callbacks
        self.on_response_received: Optional[Callable] = None
        self.on_question_complete: Optional[Callable] = None
        self.on_interview_complete: Optional[Callable] = None
    
    def initialize_session(self, session_config: Dict) -> str:
        """Initialize a new interview session"""
        self.session_id = f"interview_{session_config.get('user_id')}_{int(time.time())}"
        self.questions = session_config.get('questions', [])
        self.current_question_index = 0
        self.responses = []
        self.conversation_log = []
        
        logger.info(f"Initialized interview session: {self.session_id}")
        return self.session_id
    
    def _setup_agent_configuration(self) -> SettingsOptions:
        """Configure the Deepgram Agent settings"""
        options = SettingsOptions()
        
        # Audio input configuration
        options.audio.input.encoding = "linear16"
        options.audio.input.sample_rate = 24000
        
        # Audio output configuration
        options.audio.output.encoding = "linear16"
        options.audio.output.sample_rate = 24000
        options.audio.output.container = "wav"
        
        # Agent configuration
        options.agent.language = "en"
        options.agent.listen.provider.type = "deepgram"
        options.agent.listen.model = "nova-3"
        options.agent.think.provider.type = "open_ai"
        options.agent.think.model = "gpt-4o-mini"
        
        # Build interview prompt
        interview_prompt = self._build_interview_prompt()
        options.agent.think.prompt = interview_prompt
        
        options.agent.speak.provider.type = "deepgram"
        options.agent.speak.model = "aura-2-thalia-en"
        
        # Set greeting based on first question
        if self.questions:
            first_question = self.questions[0]
            question_text = first_question.get('text', first_question) if isinstance(first_question, dict) else str(first_question)
            options.agent.greeting = f"Hello! Welcome to your mock interview. Let's begin. {question_text}"
        else:
            options.agent.greeting = "Hello! Welcome to your mock interview. Let's begin!"
        
        return options
    
    def _build_interview_prompt(self) -> str:
        """Build the interview prompt for the AI agent"""
        base_prompt = """You are an AI interview assistant conducting a mock job interview. 

Your role:
- Ask interview questions one by one
- Listen to the candidate's responses 
- Provide brief encouragement between questions
- Ask follow-up questions when appropriate
- Maintain a professional but friendly tone

Interview Questions:
"""
        
        for i, question in enumerate(self.questions, 1):
            question_text = question.get('text', question) if isinstance(question, dict) else str(question)
            base_prompt += f"{i}. {question_text}\n"
        
        base_prompt += """
Guidelines:
- Ask one question at a time
- Wait for complete responses before moving to the next question
- Keep responses concise and professional
- End the interview after all questions are answered
- Provide a brief closing statement when the interview is complete
"""
        
        return base_prompt
    
    def _send_keep_alive(self):
        """Send keep alive messages to maintain connection"""
        while self.keep_alive_running:
            time.sleep(5)
            if self.connection:
                try:
                    self.connection.send(str(AgentKeepAlive()))
                    logger.debug("Keep alive sent")
                except Exception as e:
                    logger.error(f"Error sending keep alive: {e}")
                    break
            else:
                break
    
    def _setup_event_handlers(self):
        """Setup event handlers for the WebSocket connection"""
        
        def on_audio_data(self, data, **kwargs):
            """Handle audio data from agent"""
            self.audio_buffer.extend(data)
            logger.debug(f"Received audio data: {len(data)} bytes")
        
        def on_agent_audio_done(self, agent_audio_done, **kwargs):
            """Handle agent audio completion"""
            logger.info("Agent finished speaking")
            if len(self.audio_buffer) > 0:
                # Save audio file for the response
                filename = f"interview_audio_{self.session_id}_{self.audio_file_counter}.wav"
                try:
                    with open(filename, 'wb') as f:
                        f.write(self._create_wav_header())
                        f.write(self.audio_buffer)
                    logger.info(f"Saved agent audio: {filename}")
                except Exception as e:
                    logger.error(f"Error saving audio: {e}")
                
                self.audio_buffer = bytearray()
                self.audio_file_counter += 1
        
        def on_conversation_text(self, conversation_text, **kwargs):
            """Handle conversation text updates"""
            logger.info(f"Conversation Text: {conversation_text}")
            
            # Log conversation
            self.conversation_log.append({
                'timestamp': datetime.now().isoformat(),
                'data': conversation_text.__dict__ if hasattr(conversation_text, '__dict__') else str(conversation_text)
            })
            
            # Check if this is a user response
            if hasattr(conversation_text, 'role') and conversation_text.role == 'user':
                self._handle_user_response(conversation_text)
        
        def on_welcome(self, welcome, **kwargs):
            """Handle welcome message"""
            logger.info(f"Welcome message received: {welcome}")
        
        def on_settings_applied(self, settings_applied, **kwargs):
            """Handle settings applied confirmation"""
            logger.info(f"Settings applied: {settings_applied}")
        
        def on_user_started_speaking(self, user_started_speaking, **kwargs):
            """Handle user started speaking event"""
            logger.info("User started speaking")
        
        def on_agent_thinking(self, agent_thinking, **kwargs):
            """Handle agent thinking event"""
            logger.info("Agent is thinking...")
        
        def on_agent_started_speaking(self, agent_started_speaking, **kwargs):
            """Handle agent started speaking event"""
            self.audio_buffer = bytearray()  # Reset buffer for new response
            logger.info("Agent started speaking")
        
        def on_close(self, close, **kwargs):
            """Handle connection close"""
            logger.info(f"Connection closed: {close}")
            self.keep_alive_running = False
        
        def on_error(self, error, **kwargs):
            """Handle connection error"""
            logger.error(f"Connection error: {error}")
        
        def on_unhandled(self, unhandled, **kwargs):
            """Handle unhandled events"""
            logger.warning(f"Unhandled event: {unhandled}")
        
        # Register event handlers
        self.connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
        self.connection.on(AgentWebSocketEvents.AgentAudioDone, on_agent_audio_done)
        self.connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
        self.connection.on(AgentWebSocketEvents.Welcome, on_welcome)
        self.connection.on(AgentWebSocketEvents.SettingsApplied, on_settings_applied)
        self.connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
        self.connection.on(AgentWebSocketEvents.AgentThinking, on_agent_thinking)
        self.connection.on(AgentWebSocketEvents.AgentStartedSpeaking, on_agent_started_speaking)
        self.connection.on(AgentWebSocketEvents.Close, on_close)
        self.connection.on(AgentWebSocketEvents.Error, on_error)
        self.connection.on(AgentWebSocketEvents.Unhandled, on_unhandled)
        
        logger.info("Event handlers registered")
    
    def _handle_user_response(self, conversation_text):
        """Handle user response and track interview progress"""
        try:
            response_data = {
                'question_index': self.current_question_index,
                'response_text': conversation_text.content if hasattr(conversation_text, 'content') else str(conversation_text),
                'timestamp': datetime.now().isoformat(),
                'confidence': getattr(conversation_text, 'confidence', None)
            }
            
            self.responses.append(response_data)
            
            # Call callback if set
            if self.on_response_received:
                self.on_response_received(response_data)
            
            # Check if interview is complete
            if len(self.responses) >= len(self.questions):
                self._complete_interview()
            
        except Exception as e:
            logger.error(f"Error handling user response: {e}")
    
    def _complete_interview(self):
        """Complete the interview session"""
        logger.info("Interview completed")
        self.processing_complete = True
        
        if self.on_interview_complete:
            interview_results = {
                'session_id': self.session_id,
                'responses': self.responses,
                'conversation_log': self.conversation_log,
                'completed_at': datetime.now().isoformat()
            }
            self.on_interview_complete(interview_results)
    
    def start_interview(self) -> bool:
        """Start the interview session"""
        try:
            if not self.questions:
                raise ValueError("No questions loaded for interview")
            
            # Create WebSocket connection
            self.connection = self.deepgram.agent.websocket.v("1")
            logger.info("Created WebSocket connection")
            
            # Setup event handlers
            self._setup_event_handlers()
            
            # Configure agent
            options = self._setup_agent_configuration()
            
            # Start the connection
            logger.info("Starting WebSocket connection...")
            if not self.connection.start(options):
                logger.error("Failed to start connection")
                return False
            
            logger.info("WebSocket connection started successfully")
            
            # Start keep-alive thread
            self.keep_alive_running = True
            self.keep_alive_thread = threading.Thread(target=self._send_keep_alive, daemon=True)
            self.keep_alive_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting interview: {e}")
            return False
    
    def send_audio_data(self, audio_data: bytes):
        """Send audio data to the agent"""
        try:
            if self.connection:
                self.connection.send(audio_data)
                logger.debug(f"Sent audio data: {len(audio_data)} bytes")
        except Exception as e:
            logger.error(f"Error sending audio data: {e}")
    
    def wait_for_completion(self, timeout: int = 300) -> bool:
        """Wait for interview completion with timeout"""
        start_time = time.time()
        
        while not self.processing_complete and (time.time() - start_time) < timeout:
            time.sleep(1)
        
        return self.processing_complete
    
    def stop_interview(self):
        """Stop the interview session"""
        try:
            self.keep_alive_running = False
            
            if self.connection:
                self.connection.finish()
                logger.info("Interview session stopped")
            
        except Exception as e:
            logger.error(f"Error stopping interview: {e}")
    
    def get_interview_results(self) -> Dict:
        """Get the complete interview results"""
        return {
            'session_id': self.session_id,
            'questions': self.questions,
            'responses': self.responses,
            'conversation_log': self.conversation_log,
            'completed': self.processing_complete,
            'completed_at': datetime.now().isoformat() if self.processing_complete else None
        }
    
    def _create_wav_header(self, sample_rate=24000, bits_per_sample=16, channels=1):
        """Create a WAV header with the specified parameters"""
        byte_rate = sample_rate * channels * (bits_per_sample // 8)
        block_align = channels * (bits_per_sample // 8)

        header = bytearray(44)
        # RIFF header
        header[0:4] = b'RIFF'
        header[4:8] = b'\x00\x00\x00\x00'  # File size (to be updated later)
        header[8:12] = b'WAVE'
        # fmt chunk
        header[12:16] = b'fmt '
        header[16:20] = b'\x10\x00\x00\x00'  # Subchunk1Size (16 for PCM)
        header[20:22] = b'\x01\x00'  # AudioFormat (1 for PCM)
        header[22:24] = channels.to_bytes(2, 'little')  # NumChannels
        header[24:28] = sample_rate.to_bytes(4, 'little')  # SampleRate
        header[28:32] = byte_rate.to_bytes(4, 'little')  # ByteRate
        header[32:34] = block_align.to_bytes(2, 'little')  # BlockAlign
        header[34:36] = bits_per_sample.to_bytes(2, 'little')  # BitsPerSample
        # data chunk
        header[36:40] = b'data'
        header[40:44] = b'\x00\x00\x00\x00'  # Subchunk2Size (to be updated later)

        return header


class DeepgramInterviewAgent:
    """
    Legacy Deepgram service for backward compatibility
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("Deepgram API key is required")
        
        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(self.api_key, config)
        
        # Interview state
        self.session_id = None
        self.current_question_index = 0
        self.questions = []
        self.responses = []
        self.is_listening = False
        
        # Callbacks
        self.on_question_asked: Optional[Callable] = None
        self.on_response_received: Optional[Callable] = None
        self.on_session_complete: Optional[Callable] = None

    def initialize_session(self, session_config: Dict) -> str:
        """Initialize a new interview session"""
        self.session_id = f"interview_{session_config.get('user_id')}_{session_config.get('timestamp', '')}"
        self.questions = session_config.get('questions', [])
        self.current_question_index = 0
        self.responses = []
        
        logger.info(f"Initialized interview session: {self.session_id}")
        return self.session_id

    async def start_interview(self) -> Dict:
        """Start the interview session"""
        if not self.questions:
            raise ValueError("No questions loaded for interview")
        
        # Ask the first question
        return await self.ask_next_question()

    async def ask_next_question(self) -> Dict:
        """Ask the next question in the interview"""
        if self.current_question_index >= len(self.questions):
            return await self.complete_interview()
        
        question = self.questions[self.current_question_index]
        question_text = question.get('text', '') if isinstance(question, dict) else str(question)
        
        try:
            # Generate speech for the question using Deepgram TTS
            audio_data = await self.text_to_speech(question_text)
            
            question_data = {
                'question_id': self.current_question_index,
                'text': question_text,
                'audio_data': audio_data,
                'timestamp': time.time()
            }
            
            # Call callback if set
            if self.on_question_asked:
                await self.on_question_asked(question_data)
            
            return {
                'status': 'question_asked',
                'question': question_data,
                'session_id': self.session_id
            }
            
        except Exception as e:
            logger.error(f"Error asking question: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': self.session_id
            }

    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using Deepgram TTS"""
        try:
            from deepgram.clients.speak import SpeakOptions
            
            options = SpeakOptions(
                model="aura-asteria-en",
                encoding="linear16",
                container="wav",
                sample_rate=16000
            )
            
            response = self.deepgram.speak.v("1").stream(
                {"text": text}, options
            )
            
            # Return the audio data as bytes
            audio_data = b""
            for chunk in response.stream:
                audio_data += chunk
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {str(e)}")
            return b""

    async def process_response(self, transcript: str, audio_data: bytes = None) -> Dict:
        """Process the candidate's response"""
        try:
            # Analyze the response
            analysis = await self.analyze_response(transcript)
            
            response_data = {
                'question_id': self.current_question_index,
                'transcript': transcript,
                'analysis': analysis,
                'timestamp': time.time()
            }
            
            self.responses.append(response_data)
            
            # Call callback if set
            if self.on_response_received:
                await self.on_response_received(response_data)
            
            # Move to next question
            self.current_question_index += 1
            
            if self.current_question_index >= len(self.questions):
                return await self.complete_interview()
            else:
                return await self.ask_next_question()
                
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': self.session_id
            }

    async def analyze_response(self, transcript: str) -> Dict:
        """Analyze the candidate's response using AI"""
        try:
            # Import here to avoid circular imports
            from utils.llm_utils import analyze_interview_response
            
            # Get current question
            current_question = self.questions[self.current_question_index]
            question_text = current_question.get('text', '') if isinstance(current_question, dict) else str(current_question)
            
            # Analyze using LLM
            analysis = analyze_interview_response(
                question=question_text,
                response=transcript,
                job_position="General"  # Default job position
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            return {
                'content_quality': 5.0,
                'communication_clarity': 5.0,
                'technical_accuracy': 5.0,
                'confidence_level': 5.0,
                'overall_score': 5.0,
                'feedback': f"Error analyzing response: {str(e)}"
            }

    async def complete_interview(self) -> Dict:
        """Complete the interview session"""
        try:
            # Generate final feedback
            feedback = await self.generate_final_feedback()
            
            result = {
                'status': 'completed',
                'session_id': self.session_id,
                'total_questions': len(self.questions),
                'responses': self.responses,
                'feedback': feedback
            }
            
            # Call callback if set
            if self.on_session_complete:
                await self.on_session_complete(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error completing interview: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': self.session_id
            }

    async def generate_final_feedback(self) -> Dict:
        """Generate comprehensive feedback for the interview"""
        if not self.responses:
            return {}
        
        # Calculate average scores
        total_responses = len(self.responses)
        
        content_scores = [r['analysis'].get('content_quality', 0) for r in self.responses]
        communication_scores = [r['analysis'].get('communication_clarity', 0) for r in self.responses]
        technical_scores = [r['analysis'].get('technical_accuracy', 0) for r in self.responses]
        confidence_scores = [r['analysis'].get('confidence_level', 0) for r in self.responses]
        
        feedback = {
            'content_quality_score': sum(content_scores) / total_responses if content_scores else 0,
            'communication_score': sum(communication_scores) / total_responses if communication_scores else 0,
            'technical_score': sum(technical_scores) / total_responses if technical_scores else 0,
            'confidence_score': sum(confidence_scores) / total_responses if confidence_scores else 0,
        }
        
        # Calculate overall score
        feedback['overall_score'] = (
            feedback['content_quality_score'] + 
            feedback['communication_score'] + 
            feedback['technical_score'] + 
            feedback['confidence_score']
        ) / 4
        
        # Generate summary feedback
        feedback['summary'] = self._generate_feedback_summary(feedback)
        feedback['strengths'] = self._identify_strengths(feedback)
        feedback['improvements'] = self._identify_improvements(feedback)
        
        return feedback

    def _generate_feedback_summary(self, feedback: Dict) -> str:
        """Generate a summary of the interview performance"""
        overall_score = feedback.get('overall_score', 0)
        
        if overall_score >= 8:
            return "Excellent performance! You demonstrated strong skills across all areas."
        elif overall_score >= 6:
            return "Good performance overall with some areas for improvement."
        elif overall_score >= 4:
            return "Fair performance. Focus on improving communication and technical accuracy."
        else:
            return "Performance needs improvement. Consider practicing more before your actual interview."

    def _identify_strengths(self, feedback: Dict) -> List[str]:
        """Identify strengths based on scores"""
        strengths = []
        
        if feedback.get('communication_score', 0) >= 7:
            strengths.append("Clear and effective communication")
        if feedback.get('technical_score', 0) >= 7:
            strengths.append("Strong technical knowledge")
        if feedback.get('confidence_score', 0) >= 7:
            strengths.append("Confident delivery")
        if feedback.get('content_quality_score', 0) >= 7:
            strengths.append("Well-structured responses")
        
        return strengths

    def _identify_improvements(self, feedback: Dict) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        if feedback.get('communication_score', 0) < 6:
            improvements.append("Work on clearer communication and articulation")
        if feedback.get('technical_score', 0) < 6:
            improvements.append("Strengthen technical knowledge and accuracy")
        if feedback.get('confidence_score', 0) < 6:
            improvements.append("Build confidence through practice")
        if feedback.get('content_quality_score', 0) < 6:
            improvements.append("Structure responses more effectively")
        
        return improvements
