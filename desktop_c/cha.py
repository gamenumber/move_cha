import sys
import random
import os
import platform
import threading
import subprocess
import speech_recognition as sr
import math
import time
import requests
import io
import hashlib
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QTransform, QIcon, QPen, QBrush, QRadialGradient
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl

# OpenAI API 추가
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI 라이브러리가 설치되지 않았습니다. 'pip install openai'로 설치해주세요.")

# Eleven Labs API 설정
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')  # 환경변수에서 API 키 가져오기
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# 귀여운 여자아이 목소리 ID들 (Eleven Labs에서 제공하는 음성들)
CUTE_GIRL_VOICES = {
    "Bella": "EXAVITQu4vr4xnSDxMaL",  # 젊고 귀여운 여성 목소리
    "Elli": "MF3mGyEYCl7XYWbV9V6O",   # 부드럽고 따뜻한 여성 목소리
    "Rachel": "uHS0IiTHYRrc1pTZaPsm", # 자연스러운 여성 목소리
    "Domi": "AZnzlk1XvdvUeBnXmlld",   # 활기찬 여성 목소리
}

# 기본 음성 선택 (Bella - 가장 귀여운 목소리)
DEFAULT_VOICE_ID = CUTE_GIRL_VOICES["Rachel"]

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

class MusicNote(QWidget):
    """노래할 때 나타나는 음표 이펙트"""
    
    def __init__(self, x, y, note_type="♪"):
        super().__init__()
        self.note_type = note_type
        self.opacity = 1.0
        self.x_pos = x
        self.y_pos = y
        self.dx = random.uniform(-1, 1)
        self.dy = random.uniform(-2, -0.5)
        self.rotation = 0
        self.rotation_speed = random.uniform(-5, 5)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(40, 40)
        
        self.move(x - 20, y - 20)
        
        # 애니메이션 타이머
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_note)
        self.animation_timer.start(50)
        
        # 자동 삭제 타이머
        QTimer.singleShot(3000, self.deleteLater)
        
    def update_note(self):
        self.x_pos += self.dx
        self.y_pos += self.dy
        self.dy += 0.05  # 약간의 중력
        self.rotation += self.rotation_speed
        self.opacity -= 0.01
        
        if self.opacity <= 0:
            self.animation_timer.stop()
            self.deleteLater()
            return
            
        self.move(int(self.x_pos - 20), int(self.y_pos - 20))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(20, 20)
        painter.rotate(self.rotation)
        
        # 음표 색상 (여러 색상 중 랜덤)
        colors = [
            QColor(255, 100, 150, int(255 * self.opacity)),  # 핑크
            QColor(100, 150, 255, int(255 * self.opacity)),  # 파랑
            QColor(150, 255, 100, int(255 * self.opacity)),  # 연두
            QColor(255, 200, 100, int(255 * self.opacity)),  # 주황
            QColor(200, 100, 255, int(255 * self.opacity)),  # 보라
        ]
        color = random.choice(colors)
        
        font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(color, 2))
        painter.drawText(-10, 5, self.note_type)


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


class VoiceRecognizer(QObject):
    """완전한 피드백 차단 기능이 적용된 음성 인식기"""
    voice_command = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        # 강화된 피드백 방지 시스템
        self.is_tts_active = False
        self.tts_start_time = 0
        self.tts_end_time = 0
        self.tts_safety_buffer = 5.0  # TTS 후 5초 완전 차단
        
        # TTS 텍스트 추적 시스템
        self.recent_tts_texts = deque(maxlen=10)  # 최근 10개 TTS 텍스트 저장
        self.tts_fingerprints = set()  # TTS 텍스트 지문
        self.blocked_until = 0  # 이 시간까지 완전 차단
        
        # 음성 인식 안전 설정
        with self.microphone as source:
            print("🎤 마이크 초기화 중...")
            self.recognizer.adjust_for_ambient_noise(source, duration=3)
            self.recognizer.energy_threshold = 800  # 매우 높은 임계값
            self.recognizer.dynamic_energy_threshold = False  # 고정 임계값 사용
            self.recognizer.pause_threshold = 1.5  # 긴 대기 시간
            self.recognizer.phrase_time_limit = 4  # 짧은 인식 시간
            print(f"🔧 마이크 설정 완료 (임계값: {self.recognizer.energy_threshold})")
    
    def create_text_fingerprint(self, text):
        """텍스트의 고유 지문 생성"""
        # 정규화: 소문자, 공백 제거, 특수문자 제거
        normalized = ''.join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()
        normalized = ' '.join(normalized.split())  # 중복 공백 제거
        
        # 해시 생성
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def add_tts_text(self, text):
        """TTS 텍스트를 추적 시스템에 추가"""
        if not text or len(text.strip()) < 2:
            return
            
        fingerprint = self.create_text_fingerprint(text)
        self.recent_tts_texts.append(text.lower().strip())
        self.tts_fingerprints.add(fingerprint)
        
        # 너무 많은 지문이 쌓이지 않도록 제한
        if len(self.tts_fingerprints) > 50:
            # 오래된 것들 제거 (간단한 방법)
            self.tts_fingerprints = set(list(self.tts_fingerprints)[-30:])
    
    def set_tts_state(self, is_active, text=""):
        """TTS 상태 설정 - 완전한 차단"""
        current_time = time.time()
        
        if is_active:
            self.is_tts_active = True
            self.tts_start_time = current_time
            self.blocked_until = current_time + 2.0  # 최소 2초 차단
            
            if text:
                self.add_tts_text(text)
                print(f"🔇 TTS 시작 - 음성 인식 완전 차단: '{text[:30]}...'")
        else:
            self.is_tts_active = False
            self.tts_end_time = current_time
            self.blocked_until = current_time + self.tts_safety_buffer
            print(f"🔊 TTS 종료 - {self.tts_safety_buffer}초간 추가 차단")
    
    def is_blocked_period(self):
        """현재 차단 기간인지 확인"""
        current_time = time.time()
        
        # TTS 활성 상태면 무조건 차단
        if self.is_tts_active:
            return True
            
        # 설정된 차단 시간까지 차단
        if current_time < self.blocked_until:
            return True
            
        return False
    
    def is_similar_to_recent_tts(self, text):
        """최근 TTS와 유사한 텍스트인지 확인"""
        if not text or len(text.strip()) < 2:
            return False
            
        text_clean = text.lower().strip()
        text_fingerprint = self.create_text_fingerprint(text)
        
        # 1. 지문 일치 확인
        if text_fingerprint in self.tts_fingerprints:
            print(f"❌ 지문 일치로 차단: {text}")
            return True
        
        # 2. 최근 TTS 텍스트와 직접 비교
        for tts_text in self.recent_tts_texts:
            # 완전 일치
            if text_clean == tts_text:
                print(f"❌ 완전 일치로 차단: {text}")
                return True
                
            # 부분 일치 (긴 문자열의 경우)
            if len(text_clean) > 5 and len(tts_text) > 5:
                if text_clean in tts_text or tts_text in text_clean:
                    print(f"❌ 부분 일치로 차단: {text}")
                    return True
            
            # 단어 기반 유사도
            text_words = set(text_clean.split())
            tts_words = set(tts_text.split())
            
            if text_words and tts_words:
                intersection = text_words & tts_words
                union = text_words | tts_words
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity > 0.7:  # 70% 이상 유사하면 차단
                    print(f"❌ 단어 유사도({similarity:.2f})로 차단: {text}")
                    return True
        
        return False
    
    def should_ignore_text(self, text):
        """텍스트를 무시해야 하는지 종합 판단"""
        # 1. 차단 기간 확인
        if self.is_blocked_period():
            return True
        
        # 2. 텍스트 길이 확인
        if len(text.strip()) < 2:
            return True
            
        # 3. TTS 유사성 확인
        if self.is_similar_to_recent_tts(text):
            return True
            
        # 4. 소음 패턴 확인
        noise_patterns = {
            "음", "어", "아", "으", "오", "이", "에", "애", "으음", "아아", "어어",
            "네", "응", "어응", "음음", "아음", "으어", "어음"
        }
        if text.strip() in noise_patterns:
            print(f"❌ 소음 패턴으로 차단: {text}")
            return True
        
        # 5. 반복 문자 확인
        if len(set(text.strip())) <= 2 and len(text.strip()) > 1:
            print(f"❌ 반복 문자로 차단: {text}")
            return True
            
        return False
    
    def start_listening(self):
        self.is_listening = True
        thread = threading.Thread(target=self._listen_safely)
        thread.daemon = True
        thread.start()
        print("🎤 안전한 음성 인식 시작")
    
    def stop_listening(self):
        self.is_listening = False
        print("🎤 음성 인식 중지")
    
    def _listen_safely(self):
        """안전한 음성 인식 루프"""
        consecutive_errors = 0
        max_errors = 3
        last_recognition = 0
        min_interval = 2.0  # 최소 2초 간격
        
        while self.is_listening:
            try:
                current_time = time.time()
                
                # 차단 기간 확인
                if self.is_blocked_period():
                    time.sleep(0.2)
                    continue
                
                # 인식 간격 제한
                if current_time - last_recognition < min_interval:
                    time.sleep(0.1)
                    continue
                
                # 매우 짧은 타임아웃으로 빠른 반응
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(
                            source,
                            timeout=0.5,
                            phrase_time_limit=3
                        )
                except sr.WaitTimeoutError:
                    continue
                
                # 음성 인식 실행
                try:
                    text = self.recognizer.recognize_google(audio, language='ko-KR')
                    last_recognition = current_time
                    
                    # 안전성 검사
                    if self.should_ignore_text(text):
                        continue
                    
                    print(f"✅ 안전한 음성 인식: {text}")
                    self.voice_command.emit(text)
                    consecutive_errors = 0
                    
                except sr.UnknownValueError:
                    # 인식 실패는 정상
                    consecutive_errors = 0
                    
                except sr.RequestError as e:
                    consecutive_errors += 1
                    print(f"❌ 음성 인식 서비스 오류: {e}")
                    
                    if consecutive_errors >= max_errors:
                        print("⏸️  오류로 인한 10초 대기")
                        time.sleep(10)
                        consecutive_errors = 0
                        
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ 음성 인식 예외: {e}")
                
                if consecutive_errors >= max_errors:
                    print("⏸️  예외로 인한 10초 대기")
                    time.sleep(10)
                    consecutive_errors = 0


class SafeTTSHandler(QObject):
    """안전한 TTS 핸들러"""
    tts_started = pyqtSignal(str)
    tts_finished = pyqtSignal()
    
    def __init__(self, voice_recognizer):
        super().__init__()
        self.voice_recognizer = voice_recognizer
        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = DEFAULT_VOICE_ID
        self.tts_enabled = True
        self.is_speaking = False
        self.is_singing = False
        self.current_text = ""
        
        # 미디어 플레이어 설정
        self.media_player = QMediaPlayer()
        self.media_player.stateChanged.connect(self.on_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        print("🎤 안전한 TTS 핸들러 초기화")
    
    def on_state_changed(self, state):
        """플레이어 상태 변경"""
        if state == QMediaPlayer.PlayingState:
            self.is_speaking = True
            # 음성 인식기에 TTS 시작 알림
            self.voice_recognizer.set_tts_state(True, self.current_text)
            self.tts_started.emit(self.current_text)
            
        elif state == QMediaPlayer.StoppedState:
            if self.is_speaking:  # 실제로 재생 중이었다면
                self.is_speaking = False
                self.is_singing = False
                # 음성 인식기에 TTS 종료 알림
                self.voice_recognizer.set_tts_state(False)
                self.tts_finished.emit()
                self.current_text = ""
    
    def on_media_status_changed(self, status):
        """미디어 상태 변경"""
        if status in [QMediaContent.EndOfMedia, QMediaContent.InvalidMedia]:
            if self.is_speaking:
                self.is_speaking = False
                self.is_singing = False
                self.voice_recognizer.set_tts_state(False)
                self.tts_finished.emit()
                self.current_text = ""
    
    def speak(self, text, is_singing=False):
        """안전한 TTS 실행"""
        if not self.tts_enabled or not self.api_key or not text.strip():
            return
            
        # 이전 TTS 즉시 중지
        self.stop_speaking()
        
        self.current_text = text.strip()
        self.is_singing = is_singing
        print(f"🎤 안전한 TTS 시작: {self.current_text[:50]}...")
        
        # 백그라운드에서 TTS 생성
        thread = threading.Thread(target=self._generate_tts, args=(text, is_singing))
        thread.daemon = True
        thread.start()
    
    def stop_speaking(self):
        """TTS 즉시 중지"""
        if self.is_speaking:
            print("⏹️  TTS 강제 중지")
            self.media_player.stop()
            self.is_speaking = False
            self.is_singing = False
            self.voice_recognizer.set_tts_state(False)
            self.current_text = ""
    
    def _generate_tts(self, text, is_singing=False):
        """TTS 생성 및 재생"""
        try:
            # 미리 음성 인식 차단 시작
            self.voice_recognizer.set_tts_state(True, text)
            
            settings = {
                "stability": 0.6 if is_singing else 0.5,
                "similarity_boost": 0.7 if is_singing else 0.6,
                "style": 0.4 if is_singing else 0.2,
                "use_speaker_boost": False
            }
            
            headers = {
                "Accept": "audio/mpeg", 
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": settings
            }
            
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                json=data,
                headers=headers,
                timeout=20
            )
            
            if response.status_code == 200:
                # 임시 파일 생성 및 재생
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                    tmp_file.write(response.content)
                    tmp_filename = tmp_file.name
                
                # 재생
                url = QUrl.fromLocalFile(tmp_filename)
                self.media_player.setMedia(QMediaContent(url))
                self.media_player.play()
                
                # 파일 정리
                QTimer.singleShot(20000, lambda: self._cleanup_file(tmp_filename))
                
            else:
                print(f"❌ TTS API 오류: {response.status_code}")
                self.voice_recognizer.set_tts_state(False)
                
        except Exception as e:
            print(f"❌ TTS 생성 오류: {e}")
            self.voice_recognizer.set_tts_state(False)
    
    def _cleanup_file(self, filename):
        """임시 파일 정리"""
        try:
            import os
            os.unlink(filename)
        except:
            pass
    
    def toggle_tts(self):
        """TTS 활성화/비활성화"""
        self.tts_enabled = not self.tts_enabled
        if not self.tts_enabled:
            self.stop_speaking()
        return self.tts_enabled
    
    def set_voice(self, voice_name):
        """음성 변경"""
        if voice_name in CUTE_GIRL_VOICES:
            self.voice_id = CUTE_GIRL_VOICES[voice_name]
            print(f"음성을 {voice_name}로 변경했습니다.")
            return True
        return False


class SongDatabase:
    """노래 데이터베이스"""
    
    def __init__(self):
        self.songs = {
            "동요": [
                {
                    "title": "작은별",
                    "lyrics": "반짝반짝 작은별~ 아름답게 비치네~ 서쪽하늘 높이떠서~ 아름답게 비치네~",
                    "tempo": "slow"
                },
                {
                    "title": "곰 세마리",
                    "lyrics": "곰 세마리가 한집에 있어~ 아빠곰 엄마곰 애기곰~ 아빠곰은 뚱뚱해~ 엄마곰은 날씬해~ 애기곰은 너무 귀여워~",
                    "tempo": "medium"
                },
                {
                    "title": "학교종",
                    "lyrics": "학교종이 땡땡땡~ 어서모이자~ 선생님이 우리를~ 기다리신다~",
                    "tempo": "fast"
                },
                {
                    "title": "산토끼",
                    "lyrics": "산토끼 토끼야~ 어디를 가느냐~ 깡총깡총 뛰면서~ 어디를 가느냐~",
                    "tempo": "fast"
                }
            ],
            "가요": [
                {
                    "title": "아리랑",
                    "lyrics": "아리랑 아리랑 아라리요~ 아리랑 고개로 넘어간다~ 나를 버리고 가시는 님은~ 십리도 못가서 발병난다~",
                    "tempo": "slow"
                },
                {
                    "title": "도라지",
                    "lyrics": "도라지 도라지 백도라지~ 심심산천에 백도라지~ 한두뿌리만 캐어도~ 대바구니 넘는다~",
                    "tempo": "medium"
                },
                {
                    "title": "고향의 봄",
                    "lyrics": "나의 살던 고향은~ 꽃피는 산골~ 복숭아꽃 살구꽃~ 아기진달래~",
                    "tempo": "slow"
                }
            ],
            "팝송": [
                {
                    "title": "Happy Birthday",
                    "lyrics": "Happy birthday to you~ Happy birthday to you~ Happy birthday dear friend~ Happy birthday to you~",
                    "tempo": "medium"
                },
                {
                    "title": "Mary Had a Little Lamb",
                    "lyrics": "Mary had a little lamb~ Its fleece was white as snow~ And everywhere that Mary went~ The lamb was sure to go~",
                    "tempo": "medium"
                }
            ]
        }
    
    def get_random_song(self, genre=None):
        """랜덤 노래 가져오기"""
        if genre and genre in self.songs:
            return random.choice(self.songs[genre])
        else:
            all_songs = []
            for genre_songs in self.songs.values():
                all_songs.extend(genre_songs)
            return random.choice(all_songs)
    
    def search_song(self, keyword):
        """키워드로 노래 검색"""
        keyword = keyword.lower()
        for genre, songs in self.songs.items():
            for song in songs:
                if keyword in song["title"].lower() or keyword in song["lyrics"].lower():
                    return song
        return None
    
    def get_all_genres(self):
        """모든 장르 목록 반환"""
        return list(self.songs.keys())


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
            - 친근하고 귀여운 말투 사용 (반말, 애교 표현)
            - 간단하고 짧은 답변 (1-2문장)
            - 이모티콘 적절히 사용
            - 한국어로 대답
            - 데스크탑에서 함께 지내는 친구 같은 느낌
            - 귀여운 여자아이 목소리로 말할 예정이므로 그에 맞는 톤
            - 노래와 관련된 요청이 있으면 기꺼이 도와주기
            - '~해요', '~이에요' 보다는 '~해', '~야' 등 친근한 반말 사용"""
            
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
            return "음... 지금은 잘 모르겠어 💭"
    
    def get_response_async(self, user_message):
        """비동기로 ChatGPT 응답 받기"""
        def worker():
            response = self.get_response(user_message)
            self.response_ready.emit(response)
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()


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
        
        # 노래 관련 변수 추가
        self.is_singing = False
        self.music_notes = []
        self.note_timer = None
        self.song_database = SongDatabase()
        
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
        self.setup_safe_voice_system()
        self.setup_chatgpt()

    def setup_safe_voice_system(self):
        """완전한 피드백 차단 시스템 설정"""
        # 1. 음성 인식기 먼저 생성
        self.voice_recognizer = VoiceRecognizer()
        self.voice_recognizer.voice_command.connect(self.handle_voice_command)
        
        # 2. 안전한 TTS 핸들러 생성 (음성 인식기 참조 전달)
        self.tts_handler = SafeTTSHandler(self.voice_recognizer)
        self.tts_handler.tts_finished.connect(self.on_tts_finished)
        
        # 3. 음성 인식 시작
        self.voice_recognizer.start_listening()
        
        if self.tts_handler.api_key:
            print("✅ Eleven Labs TTS가 활성화되었습니다. (완전한 피드백 차단)")
        else:
            print("⚠️  Eleven Labs API 키가 설정되지 않았습니다.")
        
        print("🛡️  완전한 피드백 차단 시스템 활성화")

    def setup_chatgpt(self):
        """ChatGPT 핸들러 설정"""
        if OPENAI_AVAILABLE:
            self.chatgpt_handler = ChatGPTHandler()
            self.chatgpt_handler.response_ready.connect(self.handle_chatgpt_response)
        else:
            self.chatgpt_handler = None

    def clean_text_for_tts(self, text):
        """TTS에 적합하도록 텍스트 정리"""
        # 기본 이모티콘들 제거
        basic_emojis = ['😊', '😄', '😅', '🤔', '🗣️', '🏃‍♀️', '⏸️', '▶️', '🔍', '❌', '👋', '✨', '🔊', '🔇', '🎵', '🎶', '♪', '♫', '💭']
        for emoji in basic_emojis:
            text = text.replace(emoji, '')
        
        # 연속된 점들과 물결표 정리
        text = text.replace('...', '').replace('..', '').replace('~', ' ')
        
        # 불필요한 공백 정리
        text = ' '.join(text.split())
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text if text else ""

    def show_speech_with_tts(self, message, is_singing=False):
        """말풍선과 함께 안전한 TTS로 음성 출력"""
        self.tts_handler.stop_speaking()
        self.show_speech(message)
        
        clean_message = self.clean_text_for_tts(message)
        if clean_message:
            self.tts_handler.speak(clean_message, is_singing)

    def on_tts_finished(self):
        """TTS 완료 시 호출"""
        if self.is_singing:
            # 노래가 끝나면 노래 모드 종료
            self.stop_singing()

    def start_singing(self, song):
        """노래 시작"""
        self.is_singing = True
        self.stop_current_speech()
        
        # 노래 제목 먼저 보여주기
        self.show_speech(f"🎵 {song['title']} 🎵")
        
        # 1초 후 노래 시작
        QTimer.singleShot(1000, lambda: self.sing_song(song))
        
        # 음표 이펙트 시작
        self.start_music_notes()
        
        # 노래하는 모드 애니메이션
        self.set_singing_image()

    def sing_song(self, song):
        """실제 노래 부르기"""
        if not self.is_singing:
            return
            
        # 노래 가사를 말풍선으로 보여주고 TTS로 부르기
        self.show_speech_with_tts(song['lyrics'], is_singing=True)

    def stop_singing(self):
        """노래 중지"""
        self.is_singing = False
        self.stop_music_notes()
        self.restore_image()
        
        # 노래 끝 인사
        QTimer.singleShot(500, lambda: self.show_speech_with_tts("노래 끝! 어떠셨나요? 🎵"))

    def start_music_notes(self):
        """음표 이펙트 시작"""
        if self.note_timer:
            self.note_timer.stop()
            
        self.note_timer = QTimer()
        self.note_timer.timeout.connect(self.create_music_note)
        self.note_timer.start(400)  # 400ms마다 음표 생성

    def stop_music_notes(self):
        """음표 이펙트 중지"""
        if self.note_timer:
            self.note_timer.stop()
            self.note_timer = None

    def create_music_note(self):
        """음표 생성"""
        if not self.is_singing:
            return
            
        # 캐릭터 주변에서 음표 생성
        char_center_x = self.x() + self.width() // 2
        char_center_y = self.y() + self.height() // 2
        
        # 음표 종류 랜덤 선택
        notes = ["♪", "♫", "♬", "🎵", "🎶"]
        note_type = random.choice(notes)
        
        # 캐릭터 주변에서 랜덤 위치
        offset_x = random.randint(-30, 30)
        offset_y = random.randint(-20, 10)
        
        note_x = char_center_x + offset_x
        note_y = char_center_y + offset_y
        
        # 음표 생성
        note = MusicNote(note_x, note_y, note_type)
        note.show()
        self.music_notes.append(note)
        
        # 오래된 음표 정리 (메모리 절약)
        self.music_notes = [n for n in self.music_notes if n and not n.isHidden()]

    def handle_voice_command(self, text):
        """음성 명령 처리"""
        text_lower = text.lower()
        
        # ChatGPT 응답 중이면 새로운 음성 명령 무시 (긴급 명령 제외)
        if self.is_chatgpt_responding:
            urgent_commands = ["멈춰", "정지", "조용"]
            if not any(cmd in text_lower for cmd in urgent_commands):
                return
        
        # 노래 관련 명령어 처리
        if "노래" in text_lower:
            if "멈춰" in text_lower or "그만" in text_lower or "중지" in text_lower:
                if self.is_singing:
                    self.stop_singing()
                    self.show_speech_with_tts("노래를 멈췄어!")
                    return
                else:
                    self.show_speech_with_tts("지금 노래하고 있지 않아!")
                    return
            elif "불러" in text_lower or "해줘" in text_lower or "부탁" in text_lower:
                self.start_random_song()
                return
            elif "동요" in text_lower:
                self.start_song_by_genre("동요")
                return
            elif "가요" in text_lower or "민요" in text_lower:
                self.start_song_by_genre("가요")
                return
            elif "팝송" in text_lower or "영어" in text_lower:
                self.start_song_by_genre("팝송")
                return
            elif "작은별" in text_lower:
                song = self.song_database.search_song("작은별")
                if song:
                    self.start_singing(song)
                    return
            elif "곰" in text_lower and "세마리" in text_lower:
                song = self.song_database.search_song("곰 세마리")
                if song:
                    self.start_singing(song)
                    return
            elif "아리랑" in text_lower:
                song = self.song_database.search_song("아리랑")
                if song:
                    self.start_singing(song)
                    return
            elif "생일" in text_lower or "birthday" in text_lower:
                song = self.song_database.search_song("happy birthday")
                if song:
                    self.start_singing(song)
                    return
            else:
                # 일반적인 노래 요청
                self.start_random_song()
                return
        
        # 음성 변경 명령어
        if "목소리" in text_lower or "음성" in text_lower:
            if "벨라" in text_lower or "bella" in text_lower:
                self.change_voice("Bella")
                return
            elif "엘리" in text_lower or "elli" in text_lower:
                self.change_voice("Elli")
                return
            elif "레이첼" in text_lower or "rachel" in text_lower:
                self.change_voice("Rachel")
                return
            elif "도미" in text_lower or "domi" in text_lower:
                self.change_voice("Domi")
                return
        
        # 기존 명령어들
        if "커" in text_lower or "크게" in text_lower:
            self.scale_up()
            self.show_speech_with_tts("커졌어!")
            return
        elif "작" in text_lower or "작게" in text_lower:
            self.scale_down()
            self.show_speech_with_tts("작아졌어!")
            return
        elif "멈춰" in text_lower or "정지" in text_lower:
            if self.is_singing:
                self.stop_singing()
                self.show_speech_with_tts("노래를 멈췄어!")
            else:
                self.pause_movement()
                self.show_speech_with_tts("멈췄어!")
            return
        elif "움직여" in text_lower or "돌아다녀" in text_lower:
            self.resume_movement()
            self.show_speech_with_tts("다시 움직일게!")
            return
        elif "조용" in text_lower or "음소거" in text_lower:
            if self.is_singing:
                self.stop_singing()
                self.show_speech("노래를 멈췄어! 🔇")
            else:
                tts_status = self.tts_handler.toggle_tts()
                if tts_status:
                    self.show_speech("소리를 다시 켤게! 🔊")
                else:
                    self.show_speech("조용히 할게! 🔇")
            return
        elif "발자국" in text_lower:
            self.current_effect_type = "footprint"
            self.show_speech_with_tts("발자국 이펙트로 바꿨어!")
            return
        elif "먼지" in text_lower or "티끌" in text_lower:
            self.current_effect_type = "dust"
            self.show_speech_with_tts("먼지 이펙트로 바꿨어!")
            return
        elif "반짝" in text_lower or "별" in text_lower:
            self.current_effect_type = "sparkle"
            self.show_speech_with_tts("반짝이 이펙트로 바꿨어!")
            return
        
        # ChatGPT를 통한 일반 대화
        if self.chatgpt_handler and self.chatgpt_handler.client:
            # ChatGPT 응답 시작 - 상태 변경 및 타이머 일시정지
            self.is_chatgpt_responding = True
            self.speech_timer.stop()  # 자동 인사 타이머 중지
            
            self.show_speech("🤔")  # 간단한 이모티콘만 표시
            self.chatgpt_handler.get_response_async(text)
        else:
            default_responses = [
                "네, 알겠어!",
                "흥미로운 이야기네!",
                "그렇구나!",
                "더 이야기해줘!",
                "재미있어!"
            ]
            response = random.choice(default_responses)
            self.show_speech_with_tts(response)

    def change_voice(self, voice_name):
        """음성 변경"""
        if self.tts_handler.set_voice(voice_name):
            self.show_speech_with_tts(f"{voice_name} 목소리로 바꿨어!")
        else:
            self.show_speech_with_tts("그 목소리는 없어!")

    def start_random_song(self):
        """랜덤 노래 시작"""
        if self.is_singing:
            self.show_speech_with_tts("이미 노래하고 있어! 먼저 멈춰줘!")
            return
            
        song = self.song_database.get_random_song()
        self.start_singing(song)

    def start_song_by_genre(self, genre):
        """장르별 노래 시작"""
        if self.is_singing:
            self.show_speech_with_tts("이미 노래하고 있어! 먼저 멈춰줘!")
            return
            
        song = self.song_database.get_random_song(genre)
        self.start_singing(song)

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

    def set_singing_image(self):
        """노래할 때 이미지 설정"""
        if self.has_image:
            frames = []
            current_size = int(self.base_image_size * self.scale_factor)
            # 노래용 프레임들 (있다면 사용, 없으면 말하기 프레임 사용)
            for file in ["sing1.png", "sing2.png"]:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    if not self.facing_right:
                        pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                    frames.append(pixmap)
            
            # 노래 이미지가 없으면 말하기 이미지 사용
            if not frames:
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
                self.animation_timer.start(150)  # 노래할 때는 조금 더 빠르게
            else:
                self.set_static_speaking_image()
        else:
            self.label.setText("🎵")

    def set_static_speaking_image(self):
        """정적 말하기 이미지 설정"""
        if self.has_image:
            pixmap = self.speaking_pixmap
            if not self.facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.label.setPixmap(pixmap)

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
        """자동 인사 - ChatGPT 응답 중이거나 노래 중이면 건너뛰기"""
        if self.is_dragging or self.is_chatgpt_responding or self.is_singing:
            return
            
        self.stop_current_speech()
        messages = ["나랑 대화해볼래?", "뭔가 재미있는 이야기 없나?", "안녕!", "노래 불러드릴까? 🎵"]
        message = random.choice(messages)
        self.show_speech_with_tts(message)

    def say_grabbed_message(self):
        self.stop_current_speech()
        self.tts_handler.stop_speaking()
        
        # 노래 중이면 노래도 중지
        if self.is_singing:
            self.stop_singing()

        messages = ["으아아악!", "이거 놔!"]
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
        """더블클릭 시에도 ChatGPT 응답 중이거나 노래 중이면 무시"""
        if not self.is_dragging and not self.is_chatgpt_responding and not self.is_singing:
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
        
        # 노래 메뉴 추가
        song_menu = menu.addMenu("🎵 노래")
        if self.is_singing:
            stop_song_action = song_menu.addAction("노래 멈추기")
            stop_song_action.triggered.connect(self.stop_singing)
        else:
            random_song_action = song_menu.addAction("랜덤 노래")
            random_song_action.triggered.connect(self.start_random_song)
            
            song_menu.addSeparator()
            dongyo_action = song_menu.addAction("동요 부르기")
            dongyo_action.triggered.connect(lambda: self.start_song_by_genre("동요"))
            
            gayo_action = song_menu.addAction("가요 부르기")
            gayo_action.triggered.connect(lambda: self.start_song_by_genre("가요"))
            
            pop_action = song_menu.addAction("팝송 부르기")
            pop_action.triggered.connect(lambda: self.start_song_by_genre("팝송"))
            
            song_menu.addSeparator()
            # 특정 노래들
            twinkle_action = song_menu.addAction("작은별")
            twinkle_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("작은별")))
            
            bear_action = song_menu.addAction("곰 세마리")
            bear_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("곰 세마리")))
            
            arirang_action = song_menu.addAction("아리랑")
            arirang_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("아리랑")))
            
            birthday_action = song_menu.addAction("생일축하")
            birthday_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("happy birthday")))

        menu.addSeparator()
        
        # 음성 변경 메뉴 추가
        voice_menu = menu.addMenu("🎤 음성 변경")
        bella_action = voice_menu.addAction("Bella (기본 - 귀여운)")
        bella_action.triggered.connect(lambda: self.change_voice("Bella"))
        
        elli_action = voice_menu.addAction("Elli (부드러운)")
        elli_action.triggered.connect(lambda: self.change_voice("Elli"))
        
        rachel_action = voice_menu.addAction("Rachel (자연스러운)")
        rachel_action.triggered.connect(lambda: self.change_voice("Rachel"))
        
        domi_action = voice_menu.addAction("Domi (활기찬)")
        domi_action.triggered.connect(lambda: self.change_voice("Domi"))

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

        menu.addSeparator()
        # 현재 상태 표시
        current_effect_text = {
            "footprint": "👣 발자국",
            "dust": "💨 먼지",
            "sparkle": "⭐ 반짝이"
        }
        effect_status = menu.addAction(f"현재 이펙트: {current_effect_text[self.current_effect_type]}")
        effect_status.setEnabled(False)
        
        # 현재 음성 표시
        current_voice = "Rachel"  # 기본값
        for voice_name, voice_id in CUTE_GIRL_VOICES.items():
            if voice_id == self.tts_handler.voice_id:
                current_voice = voice_name
                break
        voice_status = menu.addAction(f"현재 음성: {current_voice}")
        voice_status.setEnabled(False)
        
        # 노래 상태 표시
        if self.is_singing:
            song_status = menu.addAction("🎵 노래 중...")
            song_status.setEnabled(False)
        
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
        if self.tts_handler.api_key:
            tts_status_action = menu.addAction("🎤 Eleven Labs TTS 연결됨")
            tts_status_action.setEnabled(False)
        else:
            tts_status_action = menu.addAction("⚠️ Eleven Labs API 키 필요")
            tts_status_action.setEnabled(False)

        # 피드백 차단 상태 표시
        feedback_status = menu.addAction("🛡️ 완전한 피드백 차단 활성화")
        feedback_status.setEnabled(False)

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
        self.show_speech_with_tts(f"{effect_names[effect_type]}로 바꿨어!")

    def toggle_tts_and_notify(self):
        """TTS 토글하고 알림"""
        tts_status = self.tts_handler.toggle_tts()
        if tts_status:
            self.show_speech_with_tts("소리를 다시 켤게!")
        else:
            self.show_speech("조용히 할게! 🔇")

    def closeEvent(self, event):
        """프로그램 종료시 음성 인식과 TTS 중지"""
        if hasattr(self, 'voice_recognizer') and self.voice_recognizer:
            self.voice_recognizer.stop_listening()
        if hasattr(self, 'tts_handler'):
            self.tts_handler.stop_speaking()
        
        # 노래 중지
        if self.is_singing:
            self.stop_singing()
        
        # 모든 이펙트 정리
        for effect in self.walking_effects:
            if effect:
                effect.close()
        self.walking_effects.clear()
        
        # 모든 음표 이펙트 정리
        for note in self.music_notes:
            if note:
                note.close()
        self.music_notes.clear()
        
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

        # 노래 중일 때는 다른 색상 사용
        if hasattr(self.char_widget, 'is_singing') and self.char_widget.is_singing:
            bubble_color = QColor(255, 240, 245, 240)  # 연한 분홍색
            border_color = QColor(255, 182, 193)  # 분홍색
            shadow_color = QColor(199, 21, 133, 30)  # 진한 분홍색 그림자
        else:
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
    print(f"🖥️  운영체제: {platform.system()}")

    # 필요한 라이브러리 확인
    try:
        import speech_recognition as sr
        print("✅ 음성 인식 라이브러리가 설치되어 있습니다.")
    except ImportError:
        print("❌ speech_recognition 라이브러리를 설치해주세요: pip install SpeechRecognition")
        print("❌ 또한 pyaudio도 필요합니다: pip install pyaudio")
        sys.exit(1)

    try:
        import requests
        print("✅ requests 라이브러리가 설치되어 있습니다.")
    except ImportError:
        print("❌ requests 라이브러리를 설치해주세요: pip install requests")
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

    # Eleven Labs API 키 확인
    if ELEVENLABS_API_KEY:
        print("✅ Eleven Labs API 키가 설정되어 있습니다.")
        print("🎤 귀여운 여자아이 목소리로 TTS가 작동합니다!")
    else:
        print("⚠️  Eleven Labs API 키가 설정되지 않았습니다.")
        print("   환경변수 ELEVENLABS_API_KEY를 설정해주세요.")
        print("   https://elevenlabs.io 에서 API 키를 발급받을 수 있습니다.")

    print("\n🛡️  완전한 TTS 피드백 루프 차단 시스템:")
    print("• TTS 재생 중 완전 음성 인식 차단")
    print("• TTS 종료 후 5초 추가 안전 시간")
    print("• 텍스트 지문(Fingerprint) 기반 유사도 검사")
    print("• 다층 필터링 시스템 (완전일치, 부분일치, 단어유사도)")
    print("• 소음 패턴 자동 차단")
    print("• 최소 2초 간격 음성 인식")

    print("\n🎤 Eleven Labs TTS 기능:")
    print("• Bella - 기본 귀여운 여자아이 목소리")
    print("• Elli - 부드럽고 따뜻한 여성 목소리")
    print("• Rachel - 자연스러운 여성 목소리")
    print("• Domi - 활기찬 여성 목소리")
    print("• 음성으로 '벨라 목소리로', '엘리 목소리로' 등으로 변경 가능")
    print("• 우클릭 메뉴에서도 음성 변경 가능")
    
    print("\n🎵 노래 기능:")
    print("• 음성으로 '노래 불러줘', '동요 불러줘', '아리랑 불러줘' 등 요청 가능")
    print("• 우클릭 메뉴에서 노래 선택 및 제어 가능")
    print("• 노래할 때 음표 이펙트와 특별한 애니메이션")
    print("• 노래 중에는 자동 인사 중단")
    print("• '노래 멈춰' 또는 '그만'으로 노래 중지")
    
    print("\n🎮 기존 기능:")
    print("• ChatGPT 대화 (OpenAI API 키 필요)")
    print("• 음성 명령 인식")
    print("• 걸어다니기 이펙트 (발자국, 먼지, 반짝이)")
    print("• 크기 조절, 움직임 제어")
    
    print("\n🎵 지원하는 노래:")
    print("• 동요: 작은별, 곰 세마리, 학교종, 산토끼")
    print("• 가요: 아리랑, 도라지, 고향의 봄")
    print("• 팝송: Happy Birthday, Mary Had a Little Lamb")

    print("\n🎤 음성 명령어 예시:")
    print("• '노래 불러줘' - 랜덤 노래")
    print("• '동요 불러줘' - 동요 중 랜덤")
    print("• '작은별 불러줘' - 특정 노래")
    print("• '노래 멈춰' - 노래 중지")
    print("• '벨라 목소리로' - 음성 변경")
    print("• '크게' / '작게' - 크기 조절")
    print("• '멈춰' / '움직여' - 움직임 제어")
    print("• '조용' - TTS 끄기/켜기")

    print("\n🔧 필요한 설정:")
    print("1. Eleven Labs 계정 생성 및 API 키 발급")
    print("2. 환경변수 ELEVENLABS_API_KEY 설정")
    print("3. OpenAI API 키 (ChatGPT 기능용, 선택사항)")
    print("4. 마이크 권한 허용 (음성 인식용)")
    
    print("\n💡 완전한 피드백 차단을 위한 팁:")
    print("• 헤드셋 사용 권장 (스피커 출력이 마이크로 들어가지 않음)")
    print("• 마이크를 스피커에서 멀리 배치")
    print("• 적절한 볼륨 조절")
    print("• 시스템이 자동으로 TTS와 음성 인식을 완전 분리")

    character = DesktopCharacter()
    character.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        try:
            tray_icon.setIcon(QIcon("character.png"))
        except:
            tray_icon.setIcon(app.style().standardIcon(app.style().SP_ComputerIcon))

        tray_icon.setToolTip("데스크탑 캐릭터 (완전한 피드백 차단 + ChatGPT + Eleven Labs TTS + 노래 + 이펙트)")
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