import asyncio
import logging
import concurrent.futures
import os
import time
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
        
        # Get interview room name from URL path parameters
        self.interview_room = self.scope['url_route']['kwargs'].get('interview_room')
        logger.info(f"WebSocket connection from {self.scope['client']} for room: {self.interview_room}")
        
        # Generate session ID untuk debugging
        self.session_id = f"session_{int(time.time())}_{id(self)}"
        
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
                    'interview_room': getattr(self, 'interview_room', 'Unknown'),
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

    def _setup_deepgram(self):
        """Setup Deepgram connection (blocking operation)"""
        try:
            # Inisialisasi Deepgram
            config = DeepgramClientOptions(options={"keepalive": "true"})
            self.deepgram = DeepgramClient("91ced55ae66c593f832bcb25d3948a71b9d961f6", config)
            self.dg_connection = self.deepgram.agent.websocket.v("1")

            # Setup options
            options = SettingsOptions()
            options.audio.input = Input(encoding="linear16", sample_rate=16000)
            options.audio.output = Output(encoding="linear16", sample_rate=16000, container="none")
            options.agent.listen.provider.type = "deepgram"
            options.agent.listen.provider.model = "nova-3"
            options.agent.speak.provider.type = "deepgram"
            options.agent.think.provider.type = "open_ai"
            options.agent.think.provider.model = "gpt-4o-mini"
            # Customize prompt for interview context if in interview path
            if hasattr(self, 'interview_room') and self.interview_room:
                # Get interview session data from the database
                from interview.models import InterviewSession
                try:
                    interview_session = InterviewSession.objects.get(room_name=self.interview_room)
                    
                    # Get student and job details
                    student = interview_session.student
                    job = interview_session.job
                    
                    # Create a customized prompt based on the student and job details
                    student_context = (
                        f"Student name: {student.fullname} {student.last_name}. "
                        f"Program: {student.program}, Faculty: {student.faculty}, GPA: {student.gpa}. "
                    )
                    
                    if student.skills:
                        student_context += f"Skills: {', '.join(student.skills)}. "
                    
                    # Get student's experiences (internships and organizations)
                    experiences = []
                    try:
                        for exp in student.experiences.all():
                            exp_info = f"{exp.position} at {exp.institution_name} ({exp.get_experience_type_display()})"
                            experiences.append(exp_info)
                        
                        if experiences:
                            student_context += f"Experience: {'; '.join(experiences)}. "
                    except Exception as e:
                        logger.error(f"Error loading student experiences: {e}")
                    
                    job_context = ""
                    if job:
                        job_context = (
                            f"Job position: {job.title}. "
                            f"Job description: {job.description}. "
                        )
                        if job.required_skills:
                            job_context += f"Required skills: {', '.join(job.required_skills)}. "
                        if job.required_majors:
                            job_context += f"Required majors: {', '.join(job.required_majors)}. "
                    
                    # Include resume and cover letter if available
                    resume_context = ""
                    if interview_session.resume_content:
                        try:
                            resume_context = f"Resume content: {interview_session.resume_content[:500]}... "
                        except Exception as e:
                            logger.error(f"Error processing resume content: {e}")
                        
                    cover_letter_context = ""
                    if interview_session.cover_letter:
                        try:
                            cover_letter_context = f"Cover letter: {interview_session.cover_letter[:300]}... "
                        except Exception as e:
                            logger.error(f"Error processing cover letter: {e}")
                    
                    options.agent.think.prompt = (
                        "You are an experienced job interviewer conducting a professional interview. "
                        f"Here is information about the candidate: {student_context} "
                        f"{resume_context}"
                        f"{cover_letter_context}"
                        f"{job_context} "
                        "Based on this information, ask relevant questions about the candidate's experience, "
                        "skills, and fit for the position. Pay special attention to how their background "
                        "aligns with the job requirements. Your responses should be clear, professional, "
                        "and conversational. Evaluate the candidate's responses and provide constructive feedback. "
                        "IMPORTANT: If the candidate is not taking the interview seriously or repeatedly gives non-serious "
                        "responses, stop asking interview questions and say 'I notice that you may not be ready for this "
                        "interview today. I recommend we end this session and you can return when you're prepared to "
                        "discuss your professional qualifications. Please close this window to end the interview.' "
                        "If the candidate asks questions that are completely unrelated to the job or their qualifications, "
                        "give them one warning by saying 'Let's focus on your qualifications for this position,' and if they "
                        "continue with unrelated topics, suggest ending the session as described above. Only answer questions "
                        "directly related to the job interview process or their professional qualifications."
                    )
                    
                    # Personalized greeting
                    options.agent.greeting = f"Hello {student.fullname}, I'm your interviewer today. We'll be discussing your qualifications and experience for the {job.title if job else 'position'} role. Could you start by introducing yourself and telling me about your background?"
                    
                    # Log the interview context was successfully set
                    logger.info(f"Interview context set for session {self.interview_room} - Student: {student.fullname}, Job: {job.title if job else 'General'}")
                    
                except InterviewSession.DoesNotExist:
                    logger.warning(f"No interview session found for room {self.interview_room}, using generic prompts")
                    # Fallback to generic prompt if interview session not found
                    options.agent.think.prompt = (
                        "You are an experienced job interviewer conducting a professional interview. "
                        "Ask relevant questions about the candidate's experience, skills, and fit for the position. "
                        "Your responses should be clear, professional, and conversational. "
                        "Evaluate the candidate's responses and provide constructive feedback. "
                        "IMPORTANT: If the candidate is not taking the interview seriously or repeatedly gives non-serious "
                        "responses, stop asking interview questions and say 'I notice that you may not be ready for this "
                        "interview today. I recommend we end this session and you can return when you're prepared to "
                        "discuss your professional qualifications. Please close this window to end the interview.' "
                        "If the candidate asks questions that are completely unrelated to the job or their qualifications, "
                        "give them one warning by saying 'Let's focus on your qualifications for this position,' and if they "
                        "continue with unrelated topics, suggest ending the session as described above. Only answer questions "
                        "directly related to the job interview process or their professional qualifications."
                    )
                    options.agent.greeting = "Hello, I'm your interviewer today. We'll be discussing your qualifications and experience. Could you start by introducing yourself and telling me about your background?"
            else:
                options.agent.think.prompt = (
                    "You are a helpful voice assistant created by Deepgram. "
                    "Your responses should be friendly, human-like, and conversational. "
                    "Always keep your answers concise—1-2 sentences, no more than 120 characters."
                )
                options.agent.greeting = "Hello! I'm your Deepgram voice assistant. How can I help you today?"

            # Setup event handlers
            self.dg_connection.on(AgentWebSocketEvents.Open, lambda ws, event: self._handle_open(event))
            self.dg_connection.on(AgentWebSocketEvents.AudioData, lambda ws, data: self._handle_audio(data))
            self.dg_connection.on(AgentWebSocketEvents.Close, lambda ws, event: self._handle_close(event))
            self.dg_connection.on(AgentWebSocketEvents.Error, lambda ws, error: self._handle_error(error))

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