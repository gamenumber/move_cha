import sys
import random
import os
import platform
import threading
import speech_recognition as sr
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QTransform, QIcon

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

class VoiceRecognizer(QObject):
    voice_command = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        # 마이크 조정
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
                    # 짧은 시간으로 설정해서 반응성 향상
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                try:
                    # 한국어로 음성 인식
                    text = self.recognizer.recognize_google(audio, language='ko-KR')
                    print(f"음성 인식 결과: {text}")
                    self.voice_command.emit(text)
                except sr.UnknownValueError:
                    # 인식 실패시 무시
                    pass
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                    
            except sr.WaitTimeoutError:
                # 타임아웃시 계속 진행
                pass
            except Exception as e:
                print(f"음성 인식 오류: {e}")

class DesktopCharacter(QWidget):
    def __init__(self):
        super().__init__()
        self.bubbles = []
        self.current_bubble = None
        self.scale_factor = 1.0  # 현재 크기 배율
        self.base_char_width = 150  # 기본 캐릭터 크기
        self.base_char_height = 150
        self.base_image_size = 120  # 기본 이미지 크기
        self.base_bubble_width = 180  # 기본 말풍선 크기
        self.base_bubble_height = 60
        
        self.setup_window()
        self.load_character()
        self.setup_movement()
        self.setup_interactions()
        self.setup_voice_recognition()

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

    def handle_voice_command(self, text):
        """음성 명령 처리"""
        text = text.lower()
        
        if "커" in text:
            self.scale_up()
            self.show_speech("커졌어요! 😊")
        elif "작" in text:
            self.scale_down()
            self.show_speech("작아졌어요! 😄")

    def scale_up(self):
        """캐릭터 크기 1.3배 증가"""
        self.scale_factor *= 1.3
        self.update_size()

    def scale_down(self):
        """캐릭터 크기 1.3배 감소"""
        self.scale_factor /= 1.3
        # 최소 크기 제한 (너무 작아지지 않도록)
        if self.scale_factor < 0.3:
            self.scale_factor = 0.3
        self.update_size()

    def update_size(self):
        """크기 업데이트"""
        # 새로운 크기 계산
        new_width = int(self.base_char_width * self.scale_factor)
        new_height = int(self.base_char_height * self.scale_factor)
        new_image_size = int(self.base_image_size * self.scale_factor)
        
        # 위젯 크기 변경
        self.char_width = new_width
        self.char_height = new_height
        self.setFixedSize(new_width, new_height)
        
        # 현재 위치 조정 (화면 경계 체크)
        current_pos = self.pos()
        new_x = min(current_pos.x(), self.screen_width - new_width)
        new_y = min(current_pos.y(), self.screen_height - new_height)
        self.move(new_x, new_y)
        
        # 라벨 크기와 위치 조정
        margin = (new_width - new_image_size) // 2
        self.label.setGeometry(margin, margin, new_image_size, new_image_size)
        
        # 이미지 다시 로드
        self.reload_images_with_scale()

    def reload_images_with_scale(self):
        """스케일에 맞춰 이미지 다시 로드"""
        if not self.has_image:
            # 텍스트 캐릭터인 경우 폰트 크기 조정
            font_size = int(36 * self.scale_factor)
            self.label.setFont(QFont("Arial", font_size))
            return
        
        # 이미지 크기 계산
        new_image_size = int(self.base_image_size * self.scale_factor)
        
        try:
            # 원본 이미지들 다시 로드
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
            
            # 현재 상태에 맞는 이미지 적용
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
        self.speech_timer.start(10000)

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
        if hasattr(self, "animation_timer"):
            self.animation_timer.stop()
            self.animation_timer.deleteLater()
            del self.animation_timer
            if hasattr(self, "speaking_frames"):
                del self.speaking_frames

        if self.current_bubble:
            self.current_bubble.close()
            self.current_bubble = None

    def show_speech(self, message):
        self.stop_current_speech()
        bubble = SpeechBubble(message, self, self.scale_factor)
        self.current_bubble = bubble
        self.bubbles.append(bubble)
        bubble.show()

        self.set_speaking_image()
        QTimer.singleShot(3000, self.restore_image)
        QTimer.singleShot(3000, lambda: self.remove_bubble(bubble))

    def remove_bubble(self, bubble):
        if bubble in self.bubbles:
            self.bubbles.remove(bubble)
        bubble.close()
        if self.current_bubble == bubble:
            self.current_bubble = None

    def say_hello(self):
        if self.is_dragging:
            return
        self.stop_current_speech()
        messages = ["저랑 놀아줄래요?", "안녕하세요?"]
        message = random.choice(messages)
        self.show_speech(message)

    def say_grabbed_message(self):
        self.stop_current_speech()

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
        if not self.is_dragging:
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
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: rgba(100, 150, 255, 100);
            }
        """)

        hello_action = menu.addAction("안녕! 👋")
        hello_action.triggered.connect(self.say_hello)

        # 크기 조절 메뉴 추가
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
        quit_action = menu.addAction("종료 ❌")
        quit_action.triggered.connect(self.close)

        menu.exec_(position)

    def closeEvent(self, event):
        """프로그램 종료시 음성 인식 중지"""
        if hasattr(self, 'voice_recognizer') and self.voice_recognizer:
            self.voice_recognizer.stop_listening()
        event.accept()

class SpeechBubble(QWidget):
    def __init__(self, message, char_widget, scale_factor=1.0):
        super().__init__()
        self.message = message
        self.char_widget = char_widget
        self.scale_factor = scale_factor
        
        # 스케일에 맞춰 말풍선 크기 조정
        bubble_width = int(180 * scale_factor)
        bubble_height = int(60 * scale_factor)
        
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

        # 스케일에 맞춰 크기 조정
        shadow_width = int(160 * self.scale_factor)
        shadow_height = int(50 * self.scale_factor)
        bubble_width = int(160 * self.scale_factor)
        bubble_height = int(50 * self.scale_factor)
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
        font_size = int(11 * self.scale_factor)
        font = QFont("Segoe Print", font_size, QFont.Bold)
        if not QFont("Segoe Print").exactMatch():
            font = QFont("Arial Rounded MT Bold", font_size, QFont.Bold)
        painter.setFont(font)
        
        text_margin = int(15 * self.scale_factor)
        text_y = int(20 * self.scale_factor)
        text_width = int(150 * self.scale_factor)
        text_height = int(40 * self.scale_factor)
        
        painter.drawText(text_margin, text_y, text_width, text_height, 
                        Qt.AlignCenter | Qt.TextWordWrap, self.message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 음성 인식 라이브러리 확인
    try:
        import speech_recognition as sr
        print("음성 인식 라이브러리가 설치되어 있습니다.")
    except ImportError:
        print("speech_recognition 라이브러리를 설치해주세요: pip install SpeechRecognition")
        print("또한 pyaudio도 필요합니다: pip install pyaudio")
        sys.exit(1)

    character = DesktopCharacter()
    character.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        try:
            tray_icon.setIcon(QIcon("character.png"))
        except:
            tray_icon.setIcon(app.style().standardIcon(app.style().SP_ComputerIcon))

        tray_icon.setToolTip("데스크탑 캐릭터")
        tray_menu = QMenu()
        show_action = tray_menu.addAction("캐릭터 보이기")
        show_action.triggered.connect(character.show)
        hide_action = tray_menu.addAction("캐릭터 숨기")
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