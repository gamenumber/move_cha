import sys
import random
import os
import platform
import threading
import subprocess
import speech_recognition as sr
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QTransform, QIcon, QPen, QBrush, QRadialGradient

# OpenAI API 추가
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI 라이브러리가 설치되지 않았습니다. 'pip install openai'로 설치해주세요.")

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

class WalkingEffect(QWidget):
    """걸어다닐 때 나타나는 이펙트"""
    
    def __init__(self, x, y, effect_type="footprint"):
        super().__init__()
        self.effect_type = effect_type
        self.opacity = 1.0
        self.scale = 1.0
        self.particles = []
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        if effect_type == "footprint":
            self.setFixedSize(30, 30)
        elif effect_type == "dust":
            self.setFixedSize(50, 50)
            # 먼지 파티클 생성
            for _ in range(8):
                particle = {
                    'x': random.randint(15, 35),
                    'y': random.randint(15, 35),
                    'size': random.randint(2, 5),
                    'dx': random.uniform(-2, 2),
                    'dy': random.uniform(-3, -1),
                    'opacity': 1.0
                }
                self.particles.append(particle)
        elif effect_type == "sparkle":
            self.setFixedSize(40, 40)
            # 반짝이 파티클 생성
            for _ in range(6):
                particle = {
                    'x': random.randint(10, 30),
                    'y': random.randint(10, 30),
                    'size': random.randint(3, 8),
                    'rotation': random.randint(0, 360),
                    'opacity': 1.0
                }
                self.particles.append(particle)
        
        self.move(x - self.width()//2, y - self.height()//2)
        
        # 애니메이션 타이머
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_effect)
        self.animation_timer.start(50)
        
        # 자동 삭제 타이머
        QTimer.singleShot(2000, self.deleteLater)
        
    def update_effect(self):
        if self.effect_type == "footprint":
            self.opacity -= 0.03
            if self.opacity <= 0:
                self.animation_timer.stop()
                self.deleteLater()
                return
        elif self.effect_type == "dust":
            # 먼지 파티클 업데이트
            for particle in self.particles:
                particle['x'] += particle['dx']
                particle['y'] += particle['dy']
                particle['dy'] += 0.1  # 중력 효과
                particle['opacity'] -= 0.02
            
            # 사라진 파티클 제거
            self.particles = [p for p in self.particles if p['opacity'] > 0]
            if not self.particles:
                self.animation_timer.stop()
                self.deleteLater()
                return
        elif self.effect_type == "sparkle":
            # 반짝이 효과 업데이트
            for particle in self.particles:
                particle['rotation'] += 10
                particle['opacity'] -= 0.025
            
            self.particles = [p for p in self.particles if p['opacity'] > 0]
            if not self.particles:
                self.animation_timer.stop()
                self.deleteLater()
                return
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.effect_type == "footprint":
            # 발자국 그리기
            color = QColor(100, 100, 100, int(100 * self.opacity))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # 발가락 부분
            for i in range(3):
                x = 8 + i * 5
                y = 5
                painter.drawEllipse(x, y, 4, 6)
            
            # 발바닥 부분
            painter.drawEllipse(5, 12, 20, 15)
            
        elif self.effect_type == "dust":
            # 먼지 파티클 그리기
            for particle in self.particles:
                color = QColor(139, 119, 101, int(150 * particle['opacity']))
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(
                    int(particle['x'] - particle['size']/2),
                    int(particle['y'] - particle['size']/2),
                    particle['size'],
                    particle['size']
                )
        
        elif self.effect_type == "sparkle":
            # 반짝이 효과 그리기
            for particle in self.particles:
                painter.save()
                painter.translate(particle['x'], particle['y'])
                painter.rotate(particle['rotation'])
                
                color = QColor(255, 215, 0, int(200 * particle['opacity']))
                painter.setPen(QPen(color, 2))
                
                size = particle['size']
                painter.drawLine(-size, 0, size, 0)
                painter.drawLine(0, -size, 0, size)
                painter.drawLine(-size*0.7, -size*0.7, size*0.7, size*0.7)
                painter.drawLine(-size*0.7, size*0.7, size*0.7, -size*0.7)
                
                painter.restore()

class TTSHandler(QObject):
    """macOS TTS를 처리하는 클래스"""
    tts_finished = pyqtSignal()  # TTS 완료 시그널 추가
    
    def __init__(self):
        super().__init__()
        self.is_macos = platform.system() == "Darwin"
        self.tts_enabled = True
        self.voice = "Yuna"  # 한국어 음성 (없으면 기본 음성 사용)
        self.speech_rate = "200"  # 말하기 속도 (단어/분)
        self.is_speaking = False  # TTS 상태 추가
        
    def speak(self, text):
        """텍스트를 음성으로 출력"""
        if not self.tts_enabled:
            return
            
        self.is_speaking = True
        if self.is_macos:
            self.speak_macos(text)
        else:
            print(f"[TTS 지원되지 않음] {text}")
            self.is_speaking = False
            self.tts_finished.emit()
    
    def play_system_sound(self, sound_name="Glass"):
        """macOS 시스템 효과음 재생"""
        if not self.is_macos:
            return
            
        def sound_worker():
            try:
                subprocess.run(["afplay", f"/System/Library/Sounds/{sound_name}.aiff"], check=True)
            except subprocess.CalledProcessError:
                # 기본 효과음이 없으면 다른 시스템 효과음 시도
                try:
                    subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], check=True)
                except:
                    pass
            except Exception as e:
                print(f"효과음 재생 오류: {e}")
        
        thread = threading.Thread(target=sound_worker)
        thread.daemon = True
        thread.start()
    
    def speak_macos(self, text):
        """macOS에서 say 명령어로 TTS 실행"""
        def speak_worker():
            try:
                cmd = ["say"]
                
                # 한국어 음성 확인 및 사용
                try:
                    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
                    if "Yuna" in result.stdout:
                        cmd.extend(["-v", "Yuna"])
                    elif "korean" in result.stdout.lower():
                        for line in result.stdout.split('\n'):
                            if 'korean' in line.lower():
                                voice_name = line.split()[0]
                                cmd.extend(["-v", voice_name])
                                break
                except:
                    pass
                
                cmd.extend(["-r", self.speech_rate])
                cmd.append(text)
                subprocess.run(cmd, check=True)
                
            except subprocess.CalledProcessError as e:
                print(f"TTS 실행 오류: {e}")
            except Exception as e:
                print(f"TTS 오류: {e}")
            finally:
                self.is_speaking = False
                self.tts_finished.emit()
        
        thread = threading.Thread(target=speak_worker)
        thread.daemon = True
        thread.start()
    
    def stop_speaking(self):
        """현재 진행 중인 TTS 중지"""
        if self.is_macos:
            try:
                subprocess.run(["killall", "say"], check=False)
            except:
                pass
        self.is_speaking = False
    
    def set_voice_speed(self, speed):
        """말하기 속도 설정 (100-300 권장)"""
        self.speech_rate = str(max(100, min(400, speed)))
    
    def toggle_tts(self):
        """TTS 켜기/끄기"""
        self.tts_enabled = not self.tts_enabled
        return self.tts_enabled

class ChatGPTHandler(QObject):
    """ChatGPT API를 처리하는 클래스"""
    response_ready = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.setup_openai()
        
    def setup_openai(self):
        """OpenAI API 설정"""
        if not OPENAI_AVAILABLE:
            return False
            
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("OpenAI API 키를 설정해주세요.")
            print("방법 1: 환경변수 OPENAI_API_KEY 설정")
            print("방법 2: 아래 코드에서 직접 입력")
            return False
            
        try:
            self.client = openai.OpenAI(api_key=api_key)
            return True
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {e}")
            return False
    
    def get_response(self, user_message):
        """ChatGPT에게 질문하고 응답 받기"""
        if not self.client:
            return "죄송해요, ChatGPT 연결에 문제가 있어요."
            
        try:
            system_prompt = """당신은 귀엽고 친근한 데스크탑 캐릭터입니다. 
            사용자와 대화할 때 다음 특징을 가지세요:
            - 친근하고 귀여운 말투 사용
            - 간단하고 짧은 답변 (1-2문장)
            - 이모티콘 적절히 사용
            - 한국어로 대답
            - 데스크탑에서 함께 지내는 친구 같은 느낌
            - TTS로 읽히기 때문에 너무 복잡한 기호나 이모티콘은 피하기"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"ChatGPT API 오류: {e}")
            return "음... 지금은 잘 모르겠어요"
    
    def get_response_async(self, user_message):
        """비동기로 ChatGPT 응답 받기"""
        def worker():
            response = self.get_response(user_message)
            self.response_ready.emit(response)
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

class VoiceRecognizer(QObject):
    voice_command = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def start_listening(self):
        self.is_listening = True
        thread = threading.Thread(target=self._listen_continuously)
        thread.daemon = True
        thread.start()
    
    def stop_listening(self):
        self.is_listening = False
    
    def _listen_continuously(self):
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    text = self.recognizer.recognize_google(audio, language='ko-KR')
                    print(f"음성 인식 결과: {text}")
                    self.voice_command.emit(text)
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                    
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                print(f"음성 인식 오류: {e}")

class DesktopCharacter(QWidget):
    def __init__(self):
        super().__init__()
        self.bubbles = []
        self.current_bubble = None
        self.scale_factor = 1.0
        self.base_char_width = 150
        self.base_char_height = 150
        self.base_image_size = 120
        self.base_bubble_width = 180
        self.base_bubble_height = 60
        
        # ChatGPT 응답 상태 추가
        self.is_chatgpt_responding = False
        
        # 이펙트 관련 변수
        self.walking_effects = []
        self.last_effect_time = 0
        self.effect_interval = 300  # 밀리초
        self.current_effect_type = "footprint"  # footprint, dust, sparkle
        
        # 위치 추적을 위한 변수
        self.last_x = 0
        self.last_y = 0
        
        self.setup_window()
        self.load_character()
        self.setup_movement()
        self.setup_interactions()
        self.setup_voice_recognition()
        self.setup_chatgpt()
        self.setup_tts()

    def setup_tts(self):
        """TTS 핸들러 설정"""
        self.tts_handler = TTSHandler()
        if self.tts_handler.is_macos:
            print("✅ macOS TTS가 활성화되었습니다.")
        else:
            print("⚠️  macOS가 아니므로 TTS 기능이 제한됩니다.")

    def setup_chatgpt(self):
        """ChatGPT 핸들러 설정"""
        if OPENAI_AVAILABLE:
            self.chatgpt_handler = ChatGPTHandler()
            self.chatgpt_handler.response_ready.connect(self.handle_chatgpt_response)
        else:
            self.chatgpt_handler = None

    def setup_voice_recognition(self):
        """음성 인식 설정"""
        try:
            self.voice_recognizer = VoiceRecognizer()
            self.voice_recognizer.voice_command.connect(self.handle_voice_command)
            self.voice_recognizer.start_listening()
            print("음성 인식 시작됨")
        except Exception as e:
            print(f"음성 인식 초기화 실패: {e}")
            self.voice_recognizer = None

    def clean_text_for_tts(self, text):
        """TTS에 적합하도록 텍스트 정리"""
        # 기본 이모티콘들 제거
        basic_emojis = ['😊', '😄', '😅', '🤔', '🗣️', '🏃‍♀️', '⏸️', '▶️', '🔍', '❌', '👋', '✨', '🔊', '🔇']
        for emoji in basic_emojis:
            text = text.replace(emoji, '')
        
        # 연속된 점들 정리
        text = text.replace('...', '').replace('..', '')
        
        # 불필요한 공백 정리
        text = ' '.join(text.split())
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text if text else ""

    def show_speech_with_tts(self, message):
        """말풍선과 함께 TTS로 음성 출력"""
        self.tts_handler.stop_speaking()
        self.show_speech(message)
        
        clean_message = self.clean_text_for_tts(message)
        if clean_message:
            self.tts_handler.speak(clean_message)

    def handle_voice_command(self, text):
        """음성 명령 처리"""
        text_lower = text.lower()
        
        # ChatGPT 응답 중이면 새로운 음성 명령 무시 (긴급 명령 제외)
        if self.is_chatgpt_responding:
            urgent_commands = ["멈춰", "정지", "조용"]
            if not any(cmd in text_lower for cmd in urgent_commands):
                return
        
        if "커" in text_lower or "크게" in text_lower:
            self.scale_up()
            self.show_speech_with_tts("커졌어요!")
            return
        elif "작" in text_lower or "작게" in text_lower:
            self.scale_down()
            self.show_speech_with_tts("작아졌어요!")
            return
        elif "멈춰" in text_lower or "정지" in text_lower:
            self.pause_movement()
            self.show_speech_with_tts("멈췄어요!")
            return
        elif "움직여" in text_lower or "돌아다녀" in text_lower:
            self.resume_movement()
            self.show_speech_with_tts("다시 움직일게요!")
            return
        elif "조용" in text_lower or "음소거" in text_lower:
            tts_status = self.tts_handler.toggle_tts()
            if tts_status:
                self.show_speech("소리를 다시 켤게요! 🔊")
            else:
                self.show_speech("조용히 할게요! 🔇")
            return
        elif "빨리" in text_lower and "말해" in text_lower:
            self.tts_handler.set_voice_speed(300)
            self.show_speech_with_tts("빨리 말할게요!")
            return
        elif "천천히" in text_lower and "말해" in text_lower:
            self.tts_handler.set_voice_speed(150)
            self.show_speech_with_tts("천천히 말할게요!")
            return
        elif "발자국" in text_lower:
            self.current_effect_type = "footprint"
            self.show_speech_with_tts("발자국 이펙트로 바꿨어요!")
            return
        elif "먼지" in text_lower or "티끌" in text_lower:
            self.current_effect_type = "dust"
            self.show_speech_with_tts("먼지 이펙트로 바꿨어요!")
            return
        elif "반짝" in text_lower or "별" in text_lower:
            self.current_effect_type = "sparkle"
            self.show_speech_with_tts("반짝이 이펙트로 바꿨어요!")
            return
        
        # ChatGPT를 통한 일반 대화
        if self.chatgpt_handler and self.chatgpt_handler.client:
            # ChatGPT 응답 시작 - 상태 변경 및 타이머 일시정지
            self.is_chatgpt_responding = True
            self.speech_timer.stop()  # 자동 인사 타이머 중지
            
            # macOS 효과음 재생 (TTS 대신)
            self.tts_handler.play_system_sound("Glass")  # 또는 "Ping", "Pop", "Purr" 등
            self.show_speech("🤔")  # 간단한 이모티콘만 표시
            self.chatgpt_handler.get_response_async(text)
        else:
            default_responses = [
                "네, 알겠어요!",
                "흥미로운 이야기네요!",
                "그렇군요!",
                "더 이야기해주세요!",
                "재미있어요!"
            ]
            response = random.choice(default_responses)
            self.show_speech_with_tts(response)

    def handle_chatgpt_response(self, response):
        """ChatGPT 응답 처리"""
        self.show_speech_with_tts(response)
        
        # ChatGPT 응답 완료 - 상태 변경 및 타이머 재시작
        self.is_chatgpt_responding = False
        self.speech_timer.start(15000)  # 자동 인사 타이머 재시작

    def create_walking_effect(self, x, y):
        """걸을 때 이펙트 생성"""
        current_time = QApplication.instance().tickCount() if hasattr(QApplication.instance(), 'tickCount') else 0
        
        # 시간 간격 확인 (너무 자주 생성되지 않도록)
        import time
        current_time = int(time.time() * 1000)
        if current_time - self.last_effect_time < self.effect_interval:
            return
        
        self.last_effect_time = current_time
        
        # 이동 거리 확인 (실제로 움직이고 있을 때만 이펙트 생성)
        distance_moved = math.sqrt((x - self.last_x)**2 + (y - self.last_y)**2)
        if distance_moved < 5:  # 최소 이동 거리
            return
        
        # 이펙트 생성
        effect = WalkingEffect(
            x + self.width()//2, 
            y + self.height() - 10,  # 발 위치
            self.current_effect_type
        )
        effect.show()
        self.walking_effects.append(effect)
        
        # 오래된 이펙트 정리
        self.walking_effects = [e for e in self.walking_effects if e and not e.isHidden()]
        
        # 위치 업데이트
        self.last_x = x
        self.last_y = y

    def scale_up(self):
        """캐릭터 크기 1.3배 증가"""
        self.scale_factor *= 1.3
        self.update_size()

    def scale_down(self):
        """캐릭터 크기 1.3배 감소"""
        self.scale_factor /= 1.3
        if self.scale_factor < 0.3:
            self.scale_factor = 0.3
        self.update_size()

    def update_size(self):
        """크기 업데이트"""
        new_width = int(self.base_char_width * self.scale_factor)
        new_height = int(self.base_char_height * self.scale_factor)
        new_image_size = int(self.base_image_size * self.scale_factor)
        
        self.char_width = new_width
        self.char_height = new_height
        self.setFixedSize(new_width, new_height)
        
        current_pos = self.pos()
        new_x = min(current_pos.x(), self.screen_width - new_width)
        new_y = min(current_pos.y(), self.screen_height - new_height)
        self.move(new_x, new_y)
        
        margin = (new_width - new_image_size) // 2
        self.label.setGeometry(margin, margin, new_image_size, new_image_size)
        
        self.reload_images_with_scale()

    def reload_images_with_scale(self):
        """스케일에 맞춰 이미지 다시 로드"""
        if not self.has_image:
            font_size = int(36 * self.scale_factor)
            self.label.setFont(QFont("Arial", font_size))
            return
        
        new_image_size = int(self.base_image_size * self.scale_factor)
        
        try:
            if not self.original_pixmap.isNull():
                self.original_pixmap = QPixmap("character.png").scaled(
                    new_image_size, new_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            if not self.grabbed_pixmap.isNull():
                self.grabbed_pixmap = QPixmap("grab.png").scaled(
                    new_image_size, new_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.grabbed_pixmap = self.original_pixmap
                
            if not self.speaking_pixmap.isNull():
                self.speaking_pixmap = QPixmap("h2.png").scaled(
                    new_image_size, new_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.speaking_pixmap = self.original_pixmap
            
            self.restore_image()
            
        except Exception as e:
            print(f"이미지 리로드 오류: {e}")

    def setup_window(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.desktop().screenGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.char_width = self.base_char_width
        self.char_height = self.base_char_height
        self.setFixedSize(self.char_width, self.char_height)
        start_x = random.randint(0, self.screen_width - self.char_width)
        start_y = random.randint(0, self.screen_height - self.char_height)
        self.move(start_x, start_y)
        self.last_x = start_x
        self.last_y = start_y
        self.speed_x = random.choice([-3, -2, -1, 1, 2, 3])
        self.speed_y = random.choice([-3, -2, -1, 1, 2, 3])

    def load_character(self):
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        try:
            self.original_pixmap = QPixmap("character.png")
            self.grabbed_pixmap = QPixmap("grab.png")
            self.speaking_pixmap = QPixmap("h2.png")

            if not self.original_pixmap.isNull():
                self.original_pixmap = self.original_pixmap.scaled(self.base_image_size, self.base_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.grabbed_pixmap = self.grabbed_pixmap.scaled(self.base_image_size, self.base_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not self.grabbed_pixmap.isNull() else self.original_pixmap
                self.speaking_pixmap = self.speaking_pixmap.scaled(self.base_image_size, self.base_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not self.speaking_pixmap.isNull() else self.original_pixmap
                self.label.setPixmap(self.original_pixmap)
                self.has_image = True
                self.facing_right = True
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            self.label.setText("🐱")
            self.label.setFont(QFont("Arial", 36))
            self.label.setStyleSheet("color: black; background: transparent;")
            self.has_image = False
            self.facing_right = True

        self.label.setGeometry(15, 15, self.base_image_size, self.base_image_size)

    def setup_movement(self):
        self.auto_move_enabled = True
        self.is_dragging = False
        self.move_timer = QTimer()
        self.move_timer.timeout.connect(self.wander_around)
        self.move_timer.start(50)

    def setup_interactions(self):
        self.setMouseTracking(True)
        self.drag_start_position = QPoint()
        self.speech_timer = QTimer()
        self.speech_timer.timeout.connect(self.say_hello)
        self.speech_timer.start(15000)

    def wander_around(self):
        if not self.is_dragging and self.auto_move_enabled:
            current_pos = self.pos()
            new_x = current_pos.x() + self.speed_x
            new_y = current_pos.y() + self.speed_y

            if new_x <= 0 or new_x >= self.screen_width - self.char_width:
                self.speed_x = -self.speed_x
                new_x = max(0, min(self.screen_width - self.char_width, new_x))
            if new_y <= 0 or new_y >= self.screen_height - self.char_height:
                self.speed_y = -self.speed_y
                new_y = max(0, min(self.screen_height - self.char_height, new_y))

            self.update_character_direction()

            if random.random() < 0.03:
                self.speed_x = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                self.speed_y = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])

            # 걸을 때 이펙트 생성
            self.create_walking_effect(new_x, new_y)
            
            self.move(int(new_x), int(new_y))
            self.raise_()

    def update_character_direction(self):
        if self.has_image:
            should_face_right = self.speed_x > 0
            if should_face_right != self.facing_right:
                self.facing_right = should_face_right
                self.restore_image()
        else:
            self.label.setText("🐱" if self.speed_x > 0 else "🐾")
            self.facing_right = self.speed_x > 0

    def set_speaking_image(self):
        if self.has_image:
            frames = []
            current_size = int(self.base_image_size * self.scale_factor)
            for file in ["h1.png", "h2.png"]:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    if not self.facing_right:
                        pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                    frames.append(pixmap)

            if frames:
                self.speaking_frames = frames
                self.current_frame_index = 0
                self.animation_timer = QTimer(self)
                self.animation_timer.timeout.connect(self.animate_speaking)
                self.animation_timer.start(180)
            else:
                self.set_static_speaking_image()
        else:
            self.label.setText("😺")

    def animate_speaking(self):
        if hasattr(self, "speaking_frames") and self.speaking_frames:
            self.label.setPixmap(self.speaking_frames[self.current_frame_index])
            self.current_frame_index = (self.current_frame_index + 1) % len(self.speaking_frames)

    def restore_image(self):
        if hasattr(self, "animation_timer"):
            self.animation_timer.stop()
            self.animation_timer.deleteLater()
            del self.animation_timer
            if hasattr(self, "speaking_frames"):
                del self.speaking_frames

        if self.has_image:
            pixmap = self.original_pixmap
            if not self.facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.label.setPixmap(pixmap)

    def stop_current_speech(self):
        """현재 말하기 중지 - ChatGPT 응답 중이면 상태도 초기화"""
        if hasattr(self, "animation_timer"):
            self.animation_timer.stop()
            self.animation_timer.deleteLater()
            del self.animation_timer
            if hasattr(self, "speaking_frames"):
                del self.speaking_frames

        if self.current_bubble:
            self.current_bubble.close()
            self.current_bubble = None
            
        # ChatGPT 응답이 중단되면 상태 초기화
        if self.is_chatgpt_responding:
            self.is_chatgpt_responding = False
            self.speech_timer.start(15000)

    def show_speech(self, message):
        """말풍선만 보여주기 (TTS 없음)"""
        self.stop_current_speech()
        bubble = SpeechBubble(message, self, self.scale_factor)
        self.current_bubble = bubble
        self.bubbles.append(bubble)
        bubble.show()

        self.set_speaking_image()
        QTimer.singleShot(4000, self.restore_image)
        QTimer.singleShot(4000, lambda: self.remove_bubble(bubble))

    def remove_bubble(self, bubble):
        if bubble in self.bubbles:
            self.bubbles.remove(bubble)
        bubble.close()
        if self.current_bubble == bubble:
            self.current_bubble = None

    def say_hello(self):
        """자동 인사 - ChatGPT 응답 중이면 건너뛰기"""
        if self.is_dragging or self.is_chatgpt_responding:
            return
            
        self.stop_current_speech()
        messages = ["저랑 대화해볼래요?", "뭔가 재미있는 이야기 없나요?", "안녕하세요!"]
        message = random.choice(messages)
        self.show_speech_with_tts(message)

    def say_grabbed_message(self):
        self.stop_current_speech()
        self.tts_handler.stop_speaking()

        messages = ["으아아악!", "이거 놔요!"]
        message = random.choice(messages)

        bubble = SpeechBubble(message, self, self.scale_factor)
        self.current_bubble = bubble
        self.bubbles.append(bubble)
        bubble.show()

        if self.has_image:
            pixmap = self.grabbed_pixmap
            if not self.facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.label.setPixmap(pixmap)
            
        clean_message = self.clean_text_for_tts(message)
        self.tts_handler.speak(clean_message)

    def pause_movement(self):
        self.auto_move_enabled = False

    def resume_movement(self):
        self.auto_move_enabled = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            self.speech_timer.stop()
            self.say_grabbed_message()
            if self.has_image:
                pixmap = self.grabbed_pixmap
                if not self.facing_right:
                    pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                self.label.setPixmap(pixmap)
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.end_drag()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            new_pos = event.globalPos() - self.drag_start_position
            new_x = max(0, min(self.screen_width - self.char_width, new_pos.x()))
            new_y = max(0, min(self.screen_height - self.char_height, new_pos.y()))
            self.move(new_x, new_y)

    def mouseDoubleClickEvent(self, event):
        """더블클릭 시에도 ChatGPT 응답 중이면 무시"""
        if not self.is_dragging and not self.is_chatgpt_responding:
            self.say_hello()

    def end_drag(self):
        self.is_dragging = False
        self.speed_x = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        self.speed_y = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        self.restore_image()
        self.update_character_direction()
        if self.current_bubble:
            self.current_bubble.close()
            self.current_bubble = None
        self.speech_timer.start(10000)
        
    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(255, 255, 255, 230);
                border: 1px solid gray;
                border-radius: 5px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: rgba(100, 150, 255, 100);
            }
        """)

        hello_action = menu.addAction("안녕! 👋")
        hello_action.triggered.connect(self.say_hello)

        menu.addSeparator()
        bigger_action = menu.addAction("크게 만들기 🔍+")
        bigger_action.triggered.connect(self.scale_up)
        
        smaller_action = menu.addAction("작게 만들기 🔍-")
        smaller_action.triggered.connect(self.scale_down)

        menu.addSeparator()
        if self.auto_move_enabled:
            pause_action = menu.addAction("멈추! ⏸️")
            pause_action.triggered.connect(self.pause_movement)
        else:
            resume_action = menu.addAction("다시 돌아다니기 ▶️")
            resume_action.triggered.connect(self.resume_movement)

        menu.addSeparator()
        # 이펙트 종류 선택
        effect_menu = menu.addMenu("✨ 이펙트 선택")
        footprint_action = effect_menu.addAction("👣 발자국")
        footprint_action.triggered.connect(lambda: self.change_effect_type("footprint"))
        dust_action = effect_menu.addAction("💨 먼지")
        dust_action.triggered.connect(lambda: self.change_effect_type("dust"))
        sparkle_action = effect_menu.addAction("⭐ 반짝이")
        sparkle_action.triggered.connect(lambda: self.change_effect_type("sparkle"))

        menu.addSeparator()
        if self.tts_handler.tts_enabled:
            tts_action = menu.addAction("🔊 소리 끄기")
            tts_action.triggered.connect(lambda: self.toggle_tts_and_notify())
        else:
            tts_action = menu.addAction("🔇 소리 켜기")
            tts_action.triggered.connect(lambda: self.toggle_tts_and_notify())
        
        # 말하기 속도 조절
        speed_menu = menu.addMenu("🗣️ 말하기 속도")
        slow_action = speed_menu.addAction("천천히")
        slow_action.triggered.connect(lambda: self.set_speech_speed(150))
        normal_action = speed_menu.addAction("보통")
        normal_action.triggered.connect(lambda: self.set_speech_speed(200))
        fast_action = speed_menu.addAction("빠르게")
        fast_action.triggered.connect(lambda: self.set_speech_speed(300))

        menu.addSeparator()
        # 현재 이펙트 타입 표시
        current_effect_text = {
            "footprint": "👣 발자국",
            "dust": "💨 먼지",
            "sparkle": "⭐ 반짝이"
        }
        effect_status = menu.addAction(f"현재 이펙트: {current_effect_text[self.current_effect_type]}")
        effect_status.setEnabled(False)
        
        # ChatGPT 상태 표시
        if self.is_chatgpt_responding:
            status_action = menu.addAction("🤖 ChatGPT 응답 중...")
            status_action.setEnabled(False)
        elif self.chatgpt_handler and self.chatgpt_handler.client:
            status_action = menu.addAction("🤖 ChatGPT 연결됨")
            status_action.setEnabled(False)
        else:
            status_action = menu.addAction("❌ ChatGPT 연결 안됨")
            status_action.setEnabled(False)
            
        # TTS 상태 표시
        if self.tts_handler.is_macos:
            tts_status_action = menu.addAction("🎵 macOS TTS 사용 가능")
            tts_status_action.setEnabled(False)
        else:
            tts_status_action = menu.addAction("⚠️ TTS 제한됨 (macOS 아님)")
            tts_status_action.setEnabled(False)

        menu.addSeparator()
        quit_action = menu.addAction("종료 ❌")
        quit_action.triggered.connect(self.close)

        menu.exec_(position)

    def change_effect_type(self, effect_type):
        """이펙트 타입 변경"""
        self.current_effect_type = effect_type
        effect_names = {
            "footprint": "발자국 이펙트",
            "dust": "먼지 이펙트", 
            "sparkle": "반짝이 이펙트"
        }
        self.show_speech_with_tts(f"{effect_names[effect_type]}로 바꿨어요!")

    def toggle_tts_and_notify(self):
        """TTS 토글하고 알림"""
        tts_status = self.tts_handler.toggle_tts()
        if tts_status:
            self.show_speech_with_tts("소리를 다시 켤게요!")
        else:
            self.show_speech("조용히 할게요! 🔇")

    def set_speech_speed(self, speed):
        """말하기 속도 설정하고 테스트"""
        self.tts_handler.set_voice_speed(speed)
        if speed == 150:
            self.show_speech_with_tts("천천히 말할게요")
        elif speed == 200:
            self.show_speech_with_tts("보통 속도로 말할게요")
        elif speed == 300:
            self.show_speech_with_tts("빠르게 말할게요")

    def closeEvent(self, event):
        """프로그램 종료시 음성 인식과 TTS 중지"""
        if hasattr(self, 'voice_recognizer') and self.voice_recognizer:
            self.voice_recognizer.stop_listening()
        if hasattr(self, 'tts_handler'):
            self.tts_handler.stop_speaking()
        
        # 모든 이펙트 정리
        for effect in self.walking_effects:
            if effect:
                effect.close()
        self.walking_effects.clear()
        
        event.accept()

class SpeechBubble(QWidget):
    def __init__(self, message, char_widget, scale_factor=1.0):
        super().__init__()
        self.message = message
        self.char_widget = char_widget
        self.scale_factor = scale_factor
        
        # 메시지 길이에 따라 말풍선 크기 동적 조정
        base_width = 200
        base_height = 70
        
        # 긴 메시지의 경우 크기 증가
        if len(message) > 20:
            base_width = 250
            base_height = 90
        if len(message) > 40:
            base_width = 300
            base_height = 110
            
        bubble_width = int(base_width * scale_factor)
        bubble_height = int(base_height * scale_factor)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(bubble_width, bubble_height)
        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self.follow_character)
        self.follow_timer.start(30)
        self.follow_character()

    def follow_character(self):
        char_pos = self.char_widget.pos()
        bubble_x = char_pos.x() + (self.char_widget.width() // 2) - (self.width() // 2)
        bubble_y_above = char_pos.y() - self.height() - 10
        bubble_y_below = char_pos.y() + self.char_widget.height() + 10
        if bubble_y_above <= 0:
            self.move(bubble_x, bubble_y_below)
        else:
            self.move(bubble_x, bubble_y_above)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bubble_color = QColor(240, 255, 245, 240)
        border_color = QColor(152, 251, 152)
        shadow_color = QColor(34, 139, 34, 30)

        # 동적 크기 계산
        shadow_width = self.width() - 20
        shadow_height = self.height() - 20
        bubble_width = self.width() - 20
        bubble_height = self.height() - 20
        radius = int(15 * self.scale_factor)
        
        shadow_offset = int(12 * self.scale_factor)
        bubble_offset = int(10 * self.scale_factor)

        painter.setBrush(shadow_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_offset, shadow_offset, shadow_width, shadow_height, radius, radius)

        painter.setBrush(bubble_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(bubble_offset, bubble_offset, bubble_width, bubble_height, radius, radius)

        painter.setPen(QColor(50, 90, 50))
        font_size = max(9, int(11 * self.scale_factor))
        font = QFont("Segoe Print", font_size, QFont.Bold)
        if not QFont("Segoe Print").exactMatch():
            font = QFont("Arial", font_size, QFont.Bold)
        painter.setFont(font)
        
        text_margin = int(15 * self.scale_factor)
        text_rect = self.rect().adjusted(text_margin, text_margin, -text_margin, -text_margin)
        
        painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 운영체제 확인
    if platform.system() == "Darwin":
        print("✅ macOS 감지됨 - TTS 기능이 완전히 지원됩니다.")
    else:
        print(f"⚠️  {platform.system()} 감지됨 - TTS 기능이 제한될 수 있습니다.")

    # 필요한 라이브러리 확인
    try:
        import speech_recognition as sr
        print("✅ 음성 인식 라이브러리가 설치되어 있습니다.")
    except ImportError:
        print("❌ speech_recognition 라이브러리를 설치해주세요: pip install SpeechRecognition")
        print("❌ 또한 pyaudio도 필요합니다: pip install pyaudio")
        sys.exit(1)

    # OpenAI 라이브러리 상태 출력
    if OPENAI_AVAILABLE:
        print("✅ OpenAI 라이브러리가 설치되어 있습니다.")
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print("✅ OpenAI API 키가 설정되어 있습니다.")
        else:
            print("⚠️  OpenAI API 키가 설정되지 않았습니다.")
            print("   환경변수 OPENAI_API_KEY를 설정하거나 코드에서 직접 입력하세요.")
    else:
        print("⚠️  OpenAI 라이브러리가 설치되지 않았습니다.")
        print("   pip install openai 로 설치하면 ChatGPT 기능을 사용할 수 있습니다.")

    print("\n🎮 수정된 기능:")
    print("• ChatGPT 응답 중에는 자동 인사 중단")
    print("• ChatGPT 응답 완료 후 자동 인사 재시작")
    print("• 응답 중 긴급 명령('멈춰', '조용') 외에는 새 음성 명령 무시")
    print("• 우클릭 메뉴에서 ChatGPT 상태 확인 가능")
    
    print("\n🎮 이펙트 기능:")
    print("• 음성으로 '발자국', '먼지', '반짝' 등으로 이펙트 변경 가능")
    print("• 우클릭 메뉴에서도 이펙트 선택 가능")
    print("• 걸어다닐 때 이펙트 생성 (드래그 시에는 생성 안됨)")

    character = DesktopCharacter()
    character.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        try:
            tray_icon.setIcon(QIcon("character.png"))
        except:
            tray_icon.setIcon(app.style().standardIcon(app.style().SP_ComputerIcon))

        tray_icon.setToolTip("데스크탑 캐릭터 (ChatGPT + TTS + 걸어다니기 이펙트)")
        tray_menu = QMenu()
        show_action = tray_menu.addAction("캐릭터 보이기")
        show_action.triggered.connect(character.show)
        hide_action = tray_menu.addAction("캐릭터 숨기기")
        hide_action.triggered.connect(character.hide)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("완전 종료")
        quit_action.triggered.connect(app.quit)
        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()

        def toggle_character():
            if character.isVisible():
                character.hide()
            else:
                character.show()

        tray_icon.activated.connect(lambda reason: toggle_character() if reason == QSystemTrayIcon.Trigger else None)

    sys.exit(app.exec_())