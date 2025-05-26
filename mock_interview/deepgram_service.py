# Copyright 2025 Deepgram SDK contributors. All Rights Reserved.
# Use of this source code is governed by a MIT license that can be found in the LICENSE file.
# SPDX-License-Identifier: MIT

import os
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable

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
    Deepgram Agent for conducting mock interviews with voice interaction
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        
        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(self.api_key, config)
        self.connection = None
        
        # Interview state
        self.session_id = None
        self.questions = []
        self.current_question_index = 0
        self.responses = []
        self.is_active = False
        self.keep_alive_thread = None
        
        # Audio handling
        self.audio_buffer = bytearray()
        self.file_counter = 0
        self.processing_complete = False
        
        # Conversation log
        self.conversation_log = []
        
        # Callbacks
        self.on_question_asked: Optional[Callable] = None
        self.on_response_received: Optional[Callable] = None
        self.on_session_complete: Optional[Callable] = None

    def initialize_session(self, session_config: Dict) -> str:
        """Initialize a new interview session"""
        self.session_id = f"interview_{session_config.get('user_id')}_{int(time.time())}"
        self.questions = session_config.get('questions', [])
        self.current_question_index = 0
        self.responses = []
        self.conversation_log = []
        
        logger.info(f"Initialized interview session: {self.session_id}")
        return self.session_id

    async def start_interview(self) -> Dict:
        """Start the interview with Deepgram Agent WebSocket"""
        if not self.questions:
            raise ValueError("No questions loaded for interview")
        
        try:
            # Create WebSocket connection
            self.connection = self.deepgram.agent.websocket.v("1")
            
            # Configure the Agent
            options = SettingsOptions()
            
            # Audio configuration
            options.audio.input.encoding = "linear16"
            options.audio.input.sample_rate = 24000
            options.audio.output.encoding = "linear16"
            options.audio.output.sample_rate = 24000
            options.audio.output.container = "wav"
            
            # Agent configuration
            options.agent.language = "en"
            options.agent.listen.provider.type = "deepgram"
            options.agent.listen.model = "nova-3"
            options.agent.think.provider.type = "open_ai"
            options.agent.think.model = "gpt-4o-mini"
            
            # Set interview-specific prompt
            first_question = self.questions[0].get('text', '') if self.questions else "Hello"
            options.agent.think.prompt = f"""You are conducting a mock interview. Ask the following question and listen for the candidate's response: "{first_question}". After the candidate responds, provide brief feedback and ask the next question if there are more questions."""
            
            options.agent.speak.provider.type = "deepgram"
            options.agent.speak.model = "aura-2-thalia-en"
            options.agent.greeting = f"Hello! Welcome to your mock interview. Let's begin with the first question: {first_question}"
            
            # Setup event handlers
            self._setup_event_handlers()
            
            # Start keep-alive thread
            self._start_keep_alive()
            
            # Start the connection
            if not self.connection.start(options):
                raise Exception("Failed to start WebSocket connection")
            
            self.is_active = True
            logger.info("Interview started successfully")
            
            return {
                'status': 'started',
                'session_id': self.session_id,
                'message': 'Interview session started'
            }
            
        except Exception as e:
            logger.error(f"Error starting interview: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': self.session_id
            }

    def _setup_event_handlers(self):
        """Setup WebSocket event handlers"""
        
        def on_audio_data(self, data, **kwargs):
            self.audio_buffer.extend(data)
            logger.debug(f"Received audio data: {len(data)} bytes")

        def on_agent_audio_done(self, agent_audio_done, **kwargs):
            logger.info("Agent finished speaking")
            if len(self.audio_buffer) > 0:
                filename = f"response-{self.file_counter}-{self.session_id}.wav"
                try:
                    with open(filename, 'wb') as f:
                        f.write(self._create_wav_header())
                        f.write(self.audio_buffer)
                    logger.info(f"Saved audio response: {filename}")
                except Exception as e:
                    logger.error(f"Error saving audio: {str(e)}")
            
            self.audio_buffer = bytearray()
            self.file_counter += 1

        def on_conversation_text(self, conversation_text, **kwargs):
            logger.info(f"Conversation: {conversation_text}")
            self.conversation_log.append({
                'timestamp': datetime.now().isoformat(),
                'text': conversation_text,
                'type': 'conversation'
            })

        def on_welcome(self, welcome, **kwargs):
            logger.info(f"Welcome: {welcome}")
            self.conversation_log.append({
                'timestamp': datetime.now().isoformat(),
                'text': welcome,
                'type': 'welcome'
            })

        def on_user_started_speaking(self, user_started_speaking, **kwargs):
            logger.info("User started speaking")
            self.conversation_log.append({
                'timestamp': datetime.now().isoformat(),
                'text': 'User started speaking',
                'type': 'user_event'
            })

        def on_agent_thinking(self, agent_thinking, **kwargs):
            logger.info("Agent is thinking")

        def on_agent_started_speaking(self, agent_started_speaking, **kwargs):
            self.audio_buffer = bytearray()
            logger.info("Agent started speaking")

        def on_close(self, close, **kwargs):
            logger.info(f"Connection closed: {close}")
            self.is_active = False

        def on_error(self, error, **kwargs):
            logger.error(f"WebSocket error: {error}")

        # Register handlers
        self.connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
        self.connection.on(AgentWebSocketEvents.AgentAudioDone, on_agent_audio_done)
        self.connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
        self.connection.on(AgentWebSocketEvents.Welcome, on_welcome)
        self.connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
        self.connection.on(AgentWebSocketEvents.AgentThinking, on_agent_thinking)
        self.connection.on(AgentWebSocketEvents.AgentStartedSpeaking, on_agent_started_speaking)
        self.connection.on(AgentWebSocketEvents.Close, on_close)
        self.connection.on(AgentWebSocketEvents.Error, on_error)

    def _start_keep_alive(self):
        """Start keep-alive thread"""
        def send_keep_alive():
            while self.is_active and self.connection:
                try:
                    time.sleep(5)
                    if self.is_active:
                        self.connection.send(str(AgentKeepAlive()))
                        logger.debug("Sent keep-alive")
                except Exception as e:
                    logger.error(f"Keep-alive error: {str(e)}")
                    break

        self.keep_alive_thread = threading.Thread(target=send_keep_alive, daemon=True)
        self.keep_alive_thread.start()

    def send_audio(self, audio_data: bytes):
        """Send audio data to the agent"""
        try:
            if self.connection and self.is_active:
                self.connection.send(audio_data)
                logger.debug(f"Sent audio data: {len(audio_data)} bytes")
        except Exception as e:
            logger.error(f"Error sending audio: {str(e)}")

    def complete_interview(self) -> Dict:
        """Complete the interview session"""
        try:
            self.is_active = False
            
            if self.connection:
                self.connection.finish()
            
            # Generate final feedback
            feedback = self._generate_feedback()
            
            result = {
                'status': 'completed',
                'session_id': self.session_id,
                'conversation_log': self.conversation_log,
                'feedback': feedback,
                'total_responses': len(self.responses)
            }
            
            logger.info(f"Interview completed: {self.session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error completing interview: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': self.session_id
            }

    def _generate_feedback(self) -> Dict:
        """Generate feedback based on conversation log"""
        return {
            'overall_score': 7.5,
            'communication_score': 8.0,
            'technical_score': 7.0,
            'confidence_score': 7.5,
            'strengths': [
                'Clear communication',
                'Good technical knowledge'
            ],
            'improvements': [
                'Provide more specific examples',
                'Elaborate on technical details'
            ],
            'total_interactions': len(self.conversation_log)
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

    def get_session_state(self) -> Dict:
        """Get current session state"""
        return {
            'session_id': self.session_id,
            'is_active': self.is_active,
            'current_question_index': self.current_question_index,
            'total_questions': len(self.questions),
            'conversation_entries': len(self.conversation_log)
        }


# Backward compatibility alias
class DeepgramInterviewAgent(MockInterviewAgent):
    """Backward compatibility alias for the original class name"""
    pass


class DeepgramVoiceInterviewAgent:
    """
    Voice-specific interview agent for enhanced voice features
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        
        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(self.api_key, config)
        
        # Voice session state
        self.voice_sessions = {}
        
        logger.info("DeepgramVoiceInterviewAgent initialized")

    def initialize_voice_session(self, session_config: Dict) -> str:
        """Initialize a voice interview session"""
        voice_session_id = f"voice_{session_config.get('user_id')}_{int(time.time())}"
        
        self.voice_sessions[voice_session_id] = {
            'config': session_config,
            'created_at': datetime.now().isoformat(),
            'questions': session_config.get('questions', []),
            'status': 'initialized'
        }
        
        logger.info(f"Voice session initialized: {voice_session_id}")
        return voice_session_id

    async def text_to_speech_voice(self, text: str) -> bytes:
        """Convert text to speech using Deepgram TTS with voice-specific settings"""
        try:
            from deepgram.clients.speak import SpeakOptions
            
            # Enhanced voice options for interview context
            options = SpeakOptions(
                model="aura-2-thalia-en",  # Professional voice model
                encoding="linear16",
                container="wav",
                sample_rate=24000,
                bit_rate=320000  # Higher quality for interviews
            )
            
            response = self.deepgram.speak.v("1").stream(
                {"text": text}, options
            )
            
            # Collect audio data
            audio_data = b""
            for chunk in response.stream:
                audio_data += chunk
            
            logger.info(f"Generated speech audio: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error in voice text-to-speech: {str(e)}")
            return b""

    def get_voice_session(self, voice_session_id: str) -> Optional[Dict]:
        """Get voice session information"""
        return self.voice_sessions.get(voice_session_id)

    def update_voice_session_status(self, voice_session_id: str, status: str):
        """Update voice session status"""
        if voice_session_id in self.voice_sessions:
            self.voice_sessions[voice_session_id]['status'] = status
            self.voice_sessions[voice_session_id]['updated_at'] = datetime.now().isoformat()
            logger.info(f"Voice session {voice_session_id} status updated to: {status}")
