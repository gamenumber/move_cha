import sys
import random
import os
import platform
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QTransform, QIcon

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

class DesktopCharacter(QWidget):
    def __init__(self):
        super().__init__()
        self.bubbles = []
        self.current_bubble = None
        self.setup_window()
        self.load_character()
        self.setup_movement()
        self.setup_interactions()

    def setup_window(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.desktop().screenGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.char_width = 150
        self.char_height = 150
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
                self.original_pixmap = self.original_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.grabbed_pixmap = self.grabbed_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not self.grabbed_pixmap.isNull() else self.original_pixmap
                self.speaking_pixmap = self.speaking_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not self.speaking_pixmap.isNull() else self.original_pixmap
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

        self.label.setGeometry(15, 15, 120, 120)

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
            for file in ["h1.png", "h2.png"]:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        bubble = SpeechBubble(message, self)
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
        if self.is_dragging:  # 드래그 중이면 무시
            return
        self.stop_current_speech()
        messages = ["저랑 놀아줄래요?", "안녕하세요?"]
        message = random.choice(messages)
        self.show_speech(message)

    def say_grabbed_message(self):
        self.stop_current_speech()

        messages = ["으아아악!", "이거 놔요!"]
        message = random.choice(messages)

        bubble = SpeechBubble(message, self)
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

            self.speech_timer.stop()  # 자동 인사 타이머 멈춤
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

        # 🟢 말풍선 제거도 여기서 수행
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

class SpeechBubble(QWidget):
    def __init__(self, message, char_widget):
        super().__init__()
        self.message = message
        self.char_widget = char_widget
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(180, 60)
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

        painter.setBrush(shadow_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(12, 12, 160, 50, 15, 15)

        painter.setBrush(bubble_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(10, 10, 160, 50, 15, 15)

        painter.setPen(QColor(50, 90, 50))
        font = QFont("Segoe Print", 11, QFont.Bold)
        if not QFont("Segoe Print").exactMatch():
            font = QFont("Arial Rounded MT Bold", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(15, 20, 150, 40, Qt.AlignCenter | Qt.TextWordWrap, self.message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

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
