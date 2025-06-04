import asyncio
import logging
import concurrent.futures
import os
import time
import json
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    AgentWebSocketEvents,
    SettingsOptions,
    Input,
    Output,
)
from django.conf import settings

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deepgram = None
        self.dg_connection = None
        self.executor = None
        self.deepgram_task = None
        self.main_loop = None
        self.session_id = None
        self.audio_log_dir = None
        self.audio_counter = 0
        
        # Buffer untuk menggabungkan audio chunks
        self.input_audio_buffer = bytearray()
        self.output_audio_buffer = bytearray()
        self.last_input_save = time.time()
        self.last_output_save = time.time()
        self.buffer_timeout = 2.0  # Save buffer setelah 2 detik silence
        self.min_buffer_size = 16000 * 2  # Minimal 1 detik audio (16kHz * 2 bytes)

    async def connect(self):
        await self.accept()
        
        # Generate session ID untuk debugging
        self.session_id = f"session_{int(time.time())}_{id(self)}"
        self.start_time = datetime.now()
        
        # Track interview session if available
        self.interview_session_id = None
        if self.scope.get("url_route", {}).get("kwargs", {}):
            interview_room = self.scope["url_route"]["kwargs"].get("interview_room")
            if interview_room:
                # Try to get the interview session for this room
                try:
                    from interview.models import InterviewSession
                    interview_session = InterviewSession.objects.get(room_name=interview_room)
                    self.interview_session_id = interview_session.id
                    logger.info(f"Connected to interview session {self.interview_session_id}")
                except Exception as e:
                    logger.error(f"Error getting interview session from room {interview_room}: {e}")
        
        # Setup direktori untuk menyimpan audio
        self.setup_audio_logging()
        
        # Simpan referensi ke main event loop
        self.main_loop = asyncio.get_running_loop()
        
        # Buat ThreadPoolExecutor untuk menjalankan Deepgram
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Start Deepgram connection
        await self.start_deepgram_connection()

    def setup_audio_logging(self):
        """Setup direktori untuk menyimpan audio debugging"""
        try:
            # Buat direktori berdasarkan tanggal
            today = datetime.now().strftime("%Y-%m-%d")
            base_dir = getattr(settings, 'AUDIO_DEBUG_DIR', os.path.join(settings.BASE_DIR, 'audio_debug'))
            self.audio_log_dir = os.path.join(base_dir, today, self.session_id)
            
            # Buat direktori jika belum ada
            os.makedirs(self.audio_log_dir, exist_ok=True)
            
            # Buat subdirectori untuk input dan output
            os.makedirs(os.path.join(self.audio_log_dir, 'input'), exist_ok=True)
            os.makedirs(os.path.join(self.audio_log_dir, 'output'), exist_ok=True)
            
            logger.info(f"Audio logging setup for session {self.session_id} at {self.audio_log_dir}")
            
            # Simpan metadata session
            self.save_session_metadata()
            
        except Exception as e:
            logger.error(f"Error setting up audio logging: {e}")
            self.audio_log_dir = None

    def save_session_metadata(self):
        """Simpan metadata session untuk debugging"""
        if self.audio_log_dir:
            try:
                metadata = {
                    'session_id': self.session_id,
                    'start_time': datetime.now().isoformat(),
                    'user_agent': self.scope.get('headers', {}).get('user-agent', 'Unknown'),
                    'client_ip': self.scope.get('client', ['Unknown', None])[0]
                }
                
                metadata_file = os.path.join(self.audio_log_dir, 'session_metadata.txt')
                with open(metadata_file, 'w') as f:
                    for key, value in metadata.items():
                        f.write(f"{key}: {value}\n")
                        
            except Exception as e:
                logger.error(f"Error saving session metadata: {e}")

    def add_to_audio_buffer(self, audio_data, audio_type="output"):
        """Tambahkan audio chunk ke buffer"""
        if not audio_data:
            return
            
        try:
            current_time = time.time()
            
            if audio_type == "input":
                self.input_audio_buffer.extend(audio_data)
                self.last_input_save = current_time
            else:
                self.output_audio_buffer.extend(audio_data)
                self.last_output_save = current_time
                
            # Check apakah perlu save buffer
            self.check_and_save_buffers()
            
        except Exception as e:
            logger.error(f"Error adding to {audio_type} buffer: {e}")

    def check_and_save_buffers(self):
        """Check dan save buffer jika sudah cukup besar atau timeout"""
        current_time = time.time()
        
        # Check input buffer
        if (len(self.input_audio_buffer) >= self.min_buffer_size and 
            current_time - self.last_input_save >= self.buffer_timeout):
            self.flush_audio_buffer("input")
            
        # Check output buffer
        if (len(self.output_audio_buffer) >= self.min_buffer_size and 
            current_time - self.last_output_save >= self.buffer_timeout):
            self.flush_audio_buffer("output")

    def flush_audio_buffer(self, audio_type):
        """Flush buffer ke file"""
        if not self.audio_log_dir:
            return
            
        try:
            if audio_type == "input":
                buffer_data = bytes(self.input_audio_buffer)
                self.input_audio_buffer.clear()
            else:
                buffer_data = bytes(self.output_audio_buffer)
                self.output_audio_buffer.clear()
                
            if len(buffer_data) == 0:
                return
                
            self.audio_counter += 1
            timestamp = datetime.now().strftime("%H%M%S")
            duration = len(buffer_data) / (16000 * 2)  # Durasi dalam detik
            filename = f"{timestamp}_{self.audio_counter:04d}_{audio_type}_{duration:.1f}s.raw"
            filepath = os.path.join(self.audio_log_dir, audio_type, filename)
            
            # Simpan buffer ke file
            with open(filepath, 'wb') as f:
                f.write(buffer_data)
                
            logger.info(f"Saved {audio_type} audio: {filename} ({len(buffer_data)} bytes, {duration:.1f}s)")
            
            # Simpan log
            self.save_audio_log(filename, audio_type, len(buffer_data), duration)
            
            # Buat WAV file juga untuk kemudahan debugging
            self.create_wav_file(buffer_data, filepath.replace('.raw', '.wav'))
            
        except Exception as e:
            logger.error(f"Error flushing {audio_type} buffer: {e}")

    def create_wav_file(self, raw_data, wav_filepath):
        """Convert raw audio ke WAV file"""
        try:
            import wave
            import struct
            
            with wave.open(wav_filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(raw_data)
                
        except Exception as e:
            logger.error(f"Error creating WAV file: {e}")

    def save_audio_file(self, audio_data, audio_type="output"):
        """Wrapper untuk backward compatibility"""
        self.add_to_audio_buffer(audio_data, audio_type)

    def save_audio_log(self, filename, audio_type, size, duration=None):
        """Simpan log audio untuk tracking"""
        if not self.audio_log_dir:
            return
            
        try:
            log_file = os.path.join(self.audio_log_dir, 'audio_log.txt')
            with open(log_file, 'a') as f:
                timestamp = datetime.now().isoformat()
                duration_str = f" - {duration:.1f}s" if duration else ""
                f.write(f"{timestamp} - {audio_type} - {filename} - {size} bytes{duration_str}\n")
        except Exception as e:
            logger.error(f"Error writing audio log: {e}")

    async def disconnect(self, close_code):
        # Flush semua buffer sebelum disconnect
        try:
            if len(self.input_audio_buffer) > 0:
                self.flush_audio_buffer("input")
            if len(self.output_audio_buffer) > 0:
                self.flush_audio_buffer("output")
        except Exception as e:
            logger.error(f"Error flushing buffers on disconnect: {e}")
        
        # Save interview data if we have an interview session
        try:
            if hasattr(self, 'interview_session_id') and self.interview_session_id:
                from interview.models import InterviewSession
                interview_session = InterviewSession.objects.get(id=self.interview_session_id)
                
                # Mark interview as completed
                interview_session.completed = True
                
                # Calculate duration
                if hasattr(self, 'start_time'):
                    interview_duration = int((datetime.now() - self.start_time).total_seconds())
                    interview_session.interview_duration = interview_duration
                
                # Save the interview session
                interview_session.save()
                
                logger.info(f"Saved interview session {self.interview_session_id} as completed")
        except Exception as e:
            logger.error(f"Error updating interview session on disconnect: {e}")
        
        # Simpan metadata akhir session
        if self.audio_log_dir:
            try:
                end_metadata_file = os.path.join(self.audio_log_dir, 'session_end.txt')
                with open(end_metadata_file, 'w') as f:
                    f.write(f"end_time: {datetime.now().isoformat()}\n")
                    f.write(f"close_code: {close_code}\n")
                    f.write(f"total_audio_files: {self.audio_counter}\n")
                    f.write(f"final_input_buffer_size: {len(self.input_audio_buffer)}\n")
                    f.write(f"final_output_buffer_size: {len(self.output_audio_buffer)}\n")
            except Exception as e:
                logger.error(f"Error saving end metadata: {e}")
        
        # Cleanup saat disconnect
        if self.deepgram_task:
            self.deepgram_task.cancel()
            
        if self.dg_connection:
            try:
                # Jalankan cleanup di executor
                await self.main_loop.run_in_executor(
                    self.executor, self._cleanup_deepgram
                )
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        if self.executor:
            self.executor.shutdown(wait=False)

    def _cleanup_deepgram(self):
        """Cleanup Deepgram connection (blocking operation)"""
        try:
            if self.dg_connection:
                self.dg_connection.finish()
        except Exception as e:
            logger.error(f"Error closing Deepgram connection: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        # Terima audio dari browser dan kirim ke Deepgram
        if bytes_data and self.dg_connection:
            try:
                # Simpan input audio untuk debugging
                await self.main_loop.run_in_executor(
                    self.executor, self.save_audio_file, bytes_data, "input"
                )
                
                # Kirim audio ke Deepgram di executor
                await self.main_loop.run_in_executor(
                    self.executor, self._send_to_deepgram, bytes_data
                )
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")

    def _send_to_deepgram(self, audio_data):
        """Send audio to Deepgram (blocking operation)"""
        try:
            if self.dg_connection:
                self.dg_connection.send(audio_data)
        except Exception as e:
            logger.error(f"Error in _send_to_deepgram: {e}")

    async def send_audio_to_browser(self, audio_data):
        """Helper method untuk mengirim audio ke browser"""
        try:
            await self.send(bytes_data=audio_data)
        except Exception as e:
            logger.error(f"Error sending audio to browser: {e}")

    def _handle_open(self, event):
        logger.info(f"Deepgram Connection Open: {event}")

    def _handle_audio(self, data):
        # Simpan audio dari AI untuk debugging
        try:
            self.save_audio_file(data, "output")
        except Exception as e:
            logger.error(f"Error saving AI audio: {e}")
        
        # Kirim audio dari Deepgram ke browser menggunakan asyncio
        try:
            # Schedule coroutine di main event loop menggunakan referensi yang disimpan
            asyncio.run_coroutine_threadsafe(
                self.send_audio_to_browser(data),
                self.main_loop
            )
        except Exception as e:
            logger.error(f"Error in _handle_audio: {e}")

    def _handle_close(self, event):
        logger.info(f"Deepgram Connection Close: {event}")

    def _handle_error(self, error):
        logger.error(f"Deepgram Error: {error}")
        
    def _handle_transcript(self, transcript):
        """Handle transcript events from Deepgram"""
        try:
            # Extract message and speaker information
            if transcript and hasattr(transcript, 'agent'):
                message = transcript.agent.message
                is_agent = True
            elif transcript and hasattr(transcript, 'human'):
                message = transcript.human.message
                is_agent = False
            else:
                logger.warning(f"Unrecognized transcript format: {transcript}")
                return
                
            # If we have a message, send it to the browser
            if message:
                speaker = "AI Interviewer" if is_agent else "You"
                
                # Create a JSON message with transcript info
                transcript_data = {
                    "transcript": message,
                    "speaker": speaker,
                    "is_agent": is_agent
                }
                
                # Send as text message to browser
                asyncio.run_coroutine_threadsafe(
                    self.send(text_data=json.dumps(transcript_data)),
                    self.main_loop
                )
                
                # Log the transcript
                logger.info(f"Transcript [{speaker}]: {message}")
                
                # Save transcript to database if we have an interview session
                self.save_transcript_to_db(message, is_agent)
                
        except Exception as e:
            logger.error(f"Error handling transcript: {e}")
            
    def save_transcript_to_db(self, message, is_agent):
        """Save transcript to database for the interview session"""
        if not hasattr(self, 'interview_session_id') or not self.interview_session_id:
            return
            
        try:
            from interview.models import InterviewSession
            import json
            
            interview_session = InterviewSession.objects.get(id=self.interview_session_id)
            
            # Create transcript entry
            transcript_entry = {
                'timestamp': datetime.now().isoformat(),
                'speaker': 'AI Interviewer' if is_agent else 'Candidate',
                'message': message,
                'is_agent': is_agent
            }
            
            # Add to existing transcript or create new one
            if interview_session.transcript:
                try:
                    transcript = json.loads(interview_session.transcript)
                    if isinstance(transcript, list):
                        transcript.append(transcript_entry)
                    else:
                        transcript = [transcript, transcript_entry]
                except Exception:
                    transcript = [transcript_entry]
            else:
                transcript = [transcript_entry]
                
            # Save back to the database
            interview_session.transcript = json.dumps(transcript)
            interview_session.save(update_fields=['transcript'])
            
            logger.info(f"Saved transcript to database for session {self.interview_session_id}")
            
        except Exception as e:
            logger.error(f"Error saving transcript to database: {e}")

    def _setup_deepgram(self):
        """Setup Deepgram connection (blocking operation)"""
        try:
            # Inisialisasi Deepgram
            config = DeepgramClientOptions(options={"keepalive": "true"})
            from django.conf import settings
            deepgram_api_key = getattr(settings, "DEEPGRAM_API_KEY", os.getenv("DEEPGRAM_API_KEY", ""))
            if not deepgram_api_key:
                logger.error("Deepgram API key not found in settings or environment variables")
                return False
            self.deepgram = DeepgramClient(deepgram_api_key, config)
            self.dg_connection = self.deepgram.agent.websocket.v("1")

            # Get interview context
            context_data = {}
            if self.scope.get("url_route", {}).get("kwargs", {}):
                interview_room = self.scope["url_route"]["kwargs"].get("interview_room")
                if interview_room:
                    # Try to get the interview session for this room
                    try:
                        from interview.models import InterviewSession
                        interview_session = InterviewSession.objects.get(room_name=interview_room)
                        # Extract job details and resume content if available
                        if interview_session:
                            if interview_session.job:
                                context_data["job_title"] = interview_session.job.title
                                context_data["job_company"] = interview_session.job.company
                                context_data["job_description"] = interview_session.job.description
                            if interview_session.resume_content:
                                context_data["resume"] = interview_session.resume_content
                            if interview_session.cover_letter:
                                context_data["cover_letter"] = interview_session.cover_letter
                            if interview_session.student:
                                context_data["candidate_name"] = interview_session.student.fullname
                    except Exception as e:
                        logger.error(f"Error getting interview session data: {e}")
            
            # Setup options
            options = SettingsOptions()
            options.audio.input = Input(encoding="linear16", sample_rate=16000)
            options.audio.output = Output(encoding="linear16", sample_rate=16000, container="none")
            options.agent.listen.provider.type = "deepgram"
            options.agent.listen.provider.model = "nova-3"
            options.agent.speak.provider.type = "deepgram"
            options.agent.think.provider.type = "open_ai"
            options.agent.think.provider.model = "gpt-4o"  # Using a more powerful model for interviews
            
            # Set up the interview agent prompt
            interview_prompt = """You are an AI Job Interviewer conducting a professional job interview.
            
            IMPORTANT CONTEXT:
            """
            if "candidate_name" in context_data:
                interview_prompt += f"- Candidate Name: {context_data.get('candidate_name')}\n"
            if "job_title" in context_data:
                interview_prompt += f"- Position: {context_data.get('job_title')} at {context_data.get('job_company', 'the company')}\n"
            if "job_description" in context_data:
                interview_prompt += f"- Job Description: {context_data.get('job_description')}\n"
            if "resume" in context_data:
                interview_prompt += f"- Resume Summary: {context_data.get('resume')[:500]}...\n"
            
            interview_prompt += """
            YOUR ROLE:
            - You are a professional hiring manager or recruiter.
            - Conduct a realistic job interview for the position specified.
            - Ask relevant questions based on the candidate's resume and the job requirements.
            - Ask one question at a time, listen to the response, then follow up appropriately.
            - Keep your questions and responses concise and conversational.
            - Evaluate the candidate's answers in your internal thinking, but don't express judgments out loud.
            
            INTERVIEW STRUCTURE:
            1. Start with a brief introduction and welcome the candidate
            2. Ask about relevant experience related to the position
            3. Ask behavioral questions related to the job skills
            4. Discuss scenario-based problems they might face in this role
            5. Ask about their career goals and why they're interested in this position
            6. End with asking if they have questions for you
            7. Thank them for their time and explain next steps
            
            Focus on professional questions that evaluate the candidate's skills, experience, and fit for the role.
            Your responses should be friendly but professional, clear, and concise.
            """
            
            options.agent.think.prompt = interview_prompt
            options.agent.greeting = f"Hello{' ' + context_data.get('candidate_name', '') if 'candidate_name' in context_data else ''}! I'm your interviewer today for the {context_data.get('job_title', 'position')} role. Thank you for joining us. Let's get started with a few questions about your background and experience."

            # Setup event handlers
            self.dg_connection.on(AgentWebSocketEvents.Open, lambda ws, event: self._handle_open(event))
            self.dg_connection.on(AgentWebSocketEvents.AudioData, lambda ws, data: self._handle_audio(data))
            self.dg_connection.on(AgentWebSocketEvents.Close, lambda ws, event: self._handle_close(event))
            self.dg_connection.on(AgentWebSocketEvents.Error, lambda ws, error: self._handle_error(error))
            self.dg_connection.on(AgentWebSocketEvents.Transcript, lambda ws, transcript: self._handle_transcript(transcript))

            # Start Deepgram connection (blocking call)
            if self.dg_connection.start(options):
                logger.info("Deepgram connection started successfully")
                return True
            else:
                logger.error("Failed to start Deepgram connection.")
                return False
                
        except Exception as e:
            logger.exception(f"Exception in _setup_deepgram: {e}")
            return False

    async def start_deepgram_connection(self):
        """Start Deepgram connection menggunakan executor"""
        try:
            # Jalankan setup Deepgram di executor
            success = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._setup_deepgram
            )
            
            if not success:
                logger.error("Failed to setup Deepgram connection")
                await self.close()
            else:
                logger.info("Deepgram connection setup completed")
                
        except Exception as e:
            logger.exception(f"Error starting Deepgram connection: {e}")
            await self.close()