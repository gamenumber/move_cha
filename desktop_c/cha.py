import sys
import random
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QTransform

class DesktopCharacter(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.load_character()
        self.setup_movement()
        self.setup_interactions()
        
    def setup_window(self):
        # 창 설정 - 완전 투명하고 항상 위에
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # 항상 위에
            Qt.FramelessWindowHint |   # 테두리 없음
            Qt.Tool                    # 독에 표시 안됨
        )
        
        # 투명 배경
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 화면 크기 가져오기
        screen = QApplication.desktop().screenGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        # 캐릭터 크기
        self.char_width = 150
        self.char_height = 150
        self.setFixedSize(self.char_width, self.char_height)
        
        # 랜덤 시작 위치
        start_x = random.randint(0, self.screen_width - self.char_width)
        start_y = random.randint(0, self.screen_height - self.char_height)
        self.move(start_x, start_y)
        
        # 현재 속도
        self.speed_x = random.choice([-3, -2, -1, 1, 2, 3])
        self.speed_y = random.choice([-3, -2, -1, 1, 2, 3])
        
    def load_character(self):
        # 캐릭터 이미지 로드
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        
        try:
            # 실제 이미지 파일로 교체하세요
            self.original_pixmap = QPixmap("character.png")
            if not self.original_pixmap.isNull():
                self.original_pixmap = self.original_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.label.setPixmap(self.original_pixmap)
                self.has_image = True
                self.facing_right = True  # 처음엔 오른쪽 보기
            else:
                raise FileNotFoundError
                
        except FileNotFoundError:
            # 이미지가 없을 경우 텍스트로 대체
            self.label.setText("🐱")
            self.label.setFont(QFont("Arial", 36))
            self.label.setStyleSheet("color: black; background: transparent;")
            self.has_image = False
            self.facing_right = True
        
        self.label.setGeometry(15, 15, 120, 120)
        
    def setup_movement(self):
        # 자동 움직임 타이머
        self.auto_move_enabled = True
        self.is_dragging = False
        
        self.move_timer = QTimer()
        self.move_timer.timeout.connect(self.wander_around)
        self.move_timer.start(50)  # 50ms마다 이동
        
    def wander_around(self):
        if not self.is_dragging and self.auto_move_enabled:
            # 현재 위치
            current_pos = self.pos()
            new_x = current_pos.x() + self.speed_x
            new_y = current_pos.y() + self.speed_y

            # 화면 경계에서 튕기기
            if new_x <= 0 or new_x >= self.screen_width - self.char_width:
                self.speed_x = -self.speed_x
                new_x = max(0, min(self.screen_width - self.char_width, new_x))

            if new_y <= 0 or new_y >= self.screen_height - self.char_height:
                self.speed_y = -self.speed_y
                new_y = max(0, min(self.screen_height - self.char_height, new_y))

            # 이미지 방향 변경 (왼쪽/오른쪽 이동에 따라)
            self.update_character_direction()

            # 가끔 방향 바꾸기 (3% 확률)
            if random.random() < 0.03:
                self.speed_x = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                self.speed_y = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])

            # 새 위치로 이동
            self.move(int(new_x), int(new_y))

            # 항상 최상위로 올리기
            self.raise_()  # 여기서 최상위로 올림
    
    def update_character_direction(self):
        # 이동 방향에 따라 캐릭터 이미지 반전
        if self.has_image:
            should_face_right = self.speed_x > 0
            
            if should_face_right != self.facing_right:
                self.facing_right = should_face_right
                
                if self.facing_right:
                    # 오른쪽 보기 (원본)
                    self.label.setPixmap(self.original_pixmap)
                else:
                    # 왼쪽 보기 (좌우 반전)
                    transform = QTransform()
                    transform.scale(-1, 1)  # 좌우 반전
                    flipped_pixmap = self.original_pixmap.transformed(transform)
                    self.label.setPixmap(flipped_pixmap)
        else:
            # 텍스트인 경우 이모지 변경
            if self.speed_x > 0:
                if not self.facing_right:
                    self.label.setText("🐱")  # 오른쪽
                    self.facing_right = True
            else:
                if self.facing_right:
                    self.label.setText("🐾")  # 왼쪽 (다른 이모지로 방향감 표현)
                    self.facing_right = False
    
    def setup_interactions(self):
        # 마우스 이벤트 활성화
        self.setMouseTracking(True)
        
        # 드래그 관련 변수
        self.drag_start_position = QPoint()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 드래그 시작
            self.is_dragging = True
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            
            # 드래그 후 3초 뒤 다시 자동 이동
            QTimer.singleShot(3000, self.end_drag)
            
        elif event.button() == Qt.RightButton:
            # 우클릭 메뉴
            self.show_context_menu(event.globalPos())
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            # 드래그 중
            new_pos = event.globalPos() - self.drag_start_position
            
            # 화면 경계 확인
            new_x = max(0, min(self.screen_width - self.char_width, new_pos.x()))
            new_y = max(0, min(self.screen_height - self.char_height, new_pos.y()))
            
            self.move(new_x, new_y)
    
    def mouseDoubleClickEvent(self, event):
        # 더블클릭으로 인사
        self.say_hello()
    
    def end_drag(self):
        self.is_dragging = False
        # 새로운 랜덤 속도
        self.speed_x = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        self.speed_y = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        # 방향 업데이트
        self.update_character_direction()
    
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
            pause_action = menu.addAction("멈춰! ⏸️")
            pause_action.triggered.connect(self.pause_movement)
        else:
            resume_action = menu.addAction("다시 돌아다니기 ▶️")
            resume_action.triggered.connect(self.resume_movement)
        
        menu.addSeparator()
        
        quit_action = menu.addAction("종료 ❌")
        quit_action.triggered.connect(self.close)
        
        menu.exec_(position)
    
    def say_hello(self):
        # 간단한 말풍선 효과
        messages = ["안녕하세요! 😊", "좋은 하루에요! 🌟", "뭘 도와드릴까요? 🤔", "화이팅! 💪"]
        message = random.choice(messages)
        
        # 현재 캐릭터 옆에 말풍선 생성
        bubble = SpeechBubble(message, self.pos())
        bubble.show()
    
    def pause_movement(self):
        self.auto_move_enabled = False
    
    def resume_movement(self):
        self.auto_move_enabled = True

class SpeechBubble(QWidget):
    def __init__(self, message, char_pos):
        super().__init__()
        self.message = message
        
        # 말풍선 설정
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setFixedSize(200, 80)
        
        # 캐릭터 옆에 위치
        bubble_x = char_pos.x() + 160
        bubble_y = char_pos.y() + 20
        
        # 화면 경계 확인
        screen = QApplication.desktop().screenGeometry()
        if bubble_x + 200 > screen.width():
            bubble_x = char_pos.x() - 200
        if bubble_y + 80 > screen.height():
            bubble_y = char_pos.y() - 80
            
        self.move(bubble_x, bubble_y)
        
        # 3초 후 자동 닫기
        QTimer.singleShot(3000, self.close)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 말풍선 배경
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.setPen(QColor(100, 100, 100))
        painter.drawRoundedRect(10, 10, 180, 60, 10, 10)
        
        # 텍스트
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(20, 20, 160, 40, Qt.AlignCenter | Qt.TextWordWrap, self.message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 독에서 숨기기 (macOS)
    app.setQuitOnLastWindowClosed(False)
    
    # 시스템 트레이 아이콘 추가 (백그라운드 실행용)
    from PyQt5.QtWidgets import QSystemTrayIcon
    from PyQt5.QtGui import QIcon
    
    character = DesktopCharacter()
    character.show()
    
    # 시스템 트레이 설정 (선택사항 - 완전 종료 방지)
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        
        # 기본 아이콘 생성 (실제로는 아이콘 파일 사용 권장)
        try:
            tray_icon.setIcon(QIcon("character.png"))
        except:
            # 기본 시스템 아이콘 사용
            tray_icon.setIcon(app.style().standardIcon(app.style().SP_ComputerIcon))
        
        tray_icon.setToolTip("데스크탑 캐릭터")
        
        # 트레이 메뉴
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
        
        # 트레이 아이콘 클릭으로 캐릭터 토글
        def toggle_character():
            if character.isVisible():
                character.hide()
            else:
                character.show()
        
        tray_icon.activated.connect(lambda reason: toggle_character() if reason == QSystemTrayIcon.Trigger else None)
    
    sys.exit(app.exec_())