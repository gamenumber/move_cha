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
import datetime
import re
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

# 레이첼 음성으로 고정 (다른 음성 제거)
RACHEL_VOICE_ID = "uHS0IiTHYRrc1pTZaPsm"  # Rachel - 자연스러운 여성 목소리

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)


class ThemeManager(QObject):
    """테마 관리 시스템 - 의상별 이미지 지원"""
    theme_changed = pyqtSignal(str)  # 테마 변경 시그널
    
    def __init__(self):
        super().__init__()
        self.current_theme = "default"
        self.auto_theme_enabled = True
        
        # 테마별 설정 - 의상 이미지 경로 체계화 (확장판)
        self.themes = {
            "default": {
                "name": "기본",
                "costume_folder": "costumes/default",
                "images": {
                    "character": "character_default.png",
                    "grab": "grab_default.png", 
                    "speaking1": "speaking1_default.png",
                    "speaking2": "speaking2_default.png",
                    "singing": "singing_default.png"
                },
                "colors": {
                    "bubble_bg": QColor(240, 255, 245, 240),
                    "bubble_border": QColor(152, 251, 152),
                    "bubble_shadow": QColor(34, 139, 34, 30)
                },
                "effects": ["footprint", "dust", "sparkle"],
                "greetings": [
                    "안녕! 오늘도 좋은 하루야!",
                    "뭔가 재미있는 이야기 없나?",
                    "나랑 대화해볼래?"
                ],
                "particles": {
                    "type": "normal",
                    "colors": [
                        QColor(255, 100, 150),
                        QColor(100, 150, 255), 
                        QColor(150, 255, 100)
                    ]
                }
            },
            
            "christmas": {
                "name": "크리스마스",
                "costume_folder": "costumes/christmas",
                "images": {
                    "character": "character_christmas.png",
                    "grab": "grab_christmas.png",
                    "speaking1": "speaking1_christmas.png",
                    "speaking2": "speaking2_christmas.png",
                    "singing": "singing_christmas.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 240, 240, 240),
                    "bubble_border": QColor(220, 20, 60),
                    "bubble_shadow": QColor(139, 0, 0, 30)
                },
                "effects": ["footprint", "snow", "sparkle"],
                "greetings": [
                    "메리 크리스마스! 🎄",
                    "크리스마스 노래 불러드릴까요? 🎅",
                    "산타할아버지 오셨나? 🎁",
                    "따뜻한 코코아 한 잔 어때요? ☕"
                ],
                "particles": {
                    "type": "snow",
                    "colors": [
                        QColor(255, 255, 255),
                        QColor(240, 248, 255),
                        QColor(220, 20, 60)
                    ]
                }
            },
            
            "halloween": {
                "name": "할로윈",
                "costume_folder": "costumes/halloween",
                "images": {
                    "character": "character_halloween.png", 
                    "grab": "grab_halloween.png",
                    "speaking1": "speaking1_halloween.png",
                    "speaking2": "speaking2_halloween.png",
                    "singing": "singing_halloween.png"
                },
                "colors": {
                    "bubble_bg": QColor(25, 25, 25, 240),
                    "bubble_border": QColor(255, 140, 0),
                    "bubble_shadow": QColor(128, 0, 128, 40)
                },
                "effects": ["footprint", "bat", "pumpkin"],
                "greetings": [
                    "부우우우~! 👻",
                    "트릭 오어 트릿! 🎃",
                    "무서운 이야기 들려드릴까요? 👻",
                    "할로윈 파티 준비됐나요? 🦇"
                ],
                "particles": {
                    "type": "spooky",
                    "colors": [
                        QColor(255, 140, 0),
                        QColor(128, 0, 128),
                        QColor(0, 0, 0)
                    ]
                }
            },
            
            "spring": {
                "name": "봄",
                "costume_folder": "costumes/spring",
                "images": {
                    "character": "character_spring.png",
                    "grab": "grab_spring.png", 
                    "speaking1": "speaking1_spring.png",
                    "speaking2": "speaking2_spring.png",
                    "singing": "singing_spring.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 240, 245, 240),
                    "bubble_border": QColor(255, 182, 193),
                    "bubble_shadow": QColor(219, 112, 147, 30)
                },
                "effects": ["footprint", "petals", "butterfly"],
                "greetings": [
                    "봄이 왔어요! 🌸",
                    "꽃이 예쁘게 피었네요! 🌺", 
                    "따뜻한 봄날이에요! ☀️",
                    "벚꽃 구경 가실래요? 🌸"
                ],
                "particles": {
                    "type": "petals",
                    "colors": [
                        QColor(255, 182, 193),
                        QColor(255, 105, 180),
                        QColor(255, 20, 147)
                    ]
                }
            },
            
            "summer": {
                "name": "여름",
                "costume_folder": "costumes/summer",
                "images": {
                    "character": "character_summer.png",
                    "grab": "grab_summer.png",
                    "speaking1": "speaking1_summer.png",
                    "speaking2": "speaking2_summer.png",
                    "singing": "singing_summer.png"
                },
                "colors": {
                    "bubble_bg": QColor(240, 248, 255, 240),
                    "bubble_border": QColor(0, 191, 255),
                    "bubble_shadow": QColor(30, 144, 255, 30)
                },
                "effects": ["footprint", "wave", "sun"],
                "greetings": [
                    "여름이에요! 시원하게 지내세요! 🏖️",
                    "아이스크림 먹고 싶어요! 🍦",
                    "바다에 가고 싶어요! 🌊",
                    "선글라스 어때요? 😎"
                ],
                "particles": {
                    "type": "bubble", 
                    "colors": [
                        QColor(0, 191, 255),
                        QColor(135, 206, 250),
                        QColor(255, 215, 0)
                    ]
                }
            },
            
            "autumn": {
                "name": "가을",
                "costume_folder": "costumes/autumn",
                "images": {
                    "character": "character_autumn.png",
                    "grab": "grab_autumn.png",
                    "speaking1": "speaking1_autumn.png",
                    "speaking2": "speaking2_autumn.png",
                    "singing": "singing_autumn.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 228, 196, 240),
                    "bubble_border": QColor(205, 133, 63),
                    "bubble_shadow": QColor(139, 69, 19, 30)
                },
                "effects": ["footprint", "leaves", "wind"],
                "greetings": [
                    "가을이에요! 단풍이 아름다워요! 🍂",
                    "낙엽이 떨어지네요~ 🍁",
                    "따뜻한 차 한 잔 어때요? ☕",
                    "가을 산책 나가실래요? 🌰"
                ],
                "particles": {
                    "type": "leaves",
                    "colors": [
                        QColor(255, 140, 0),
                        QColor(205, 133, 63),
                        QColor(139, 69, 19),
                        QColor(255, 69, 0)
                    ]
                }
            },
            
            "winter": {
                "name": "겨울",
                "costume_folder": "costumes/winter",
                "images": {
                    "character": "character_winter.png",
                    "grab": "grab_winter.png",
                    "speaking1": "speaking1_winter.png",
                    "speaking2": "speaking2_winter.png",
                    "singing": "singing_winter.png"
                },
                "colors": {
                    "bubble_bg": QColor(240, 248, 255, 240),
                    "bubble_border": QColor(176, 196, 222),
                    "bubble_shadow": QColor(70, 130, 180, 30)
                },
                "effects": ["footprint", "snow", "crystal"],
                "greetings": [
                    "겨울이에요! 따뜻하게 입으세요! ❄️",
                    "눈이 내려요~ ⛄",
                    "따뜻한 실내가 좋아요! 🔥",
                    "겨울 코트 예뻐요! 🧥"
                ],
                "particles": {
                    "type": "snow",
                    "colors": [
                        QColor(255, 255, 255),
                        QColor(240, 248, 255),
                        QColor(176, 196, 222)
                    ]
                }
            },
            
            "birthday": {
                "name": "생일",
                "costume_folder": "costumes/birthday",
                "images": {
                    "character": "character_birthday.png",
                    "grab": "grab_birthday.png",
                    "speaking1": "speaking1_birthday.png",
                    "speaking2": "speaking2_birthday.png",
                    "singing": "singing_birthday.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 240, 245, 240),
                    "bubble_border": QColor(255, 20, 147),
                    "bubble_shadow": QColor(199, 21, 133, 30)
                },
                "effects": ["footprint", "confetti", "balloon"],
                "greetings": [
                    "생일 축하해요! 🎂",
                    "파티 시작해볼까요? 🎉",
                    "소원을 빌어보세요! ⭐",
                    "케이크 맛있겠어요! 🍰"
                ],
                "particles": {
                    "type": "confetti",
                    "colors": [
                        QColor(255, 20, 147),
                        QColor(255, 215, 0),
                        QColor(50, 205, 50),
                        QColor(30, 144, 255),
                        QColor(255, 69, 0)
                    ]
                }
            },
            
            "school": {
                "name": "학교",
                "costume_folder": "costumes/school",
                "images": {
                    "character": "character_school.png",
                    "grab": "grab_school.png",
                    "speaking1": "speaking1_school.png",
                    "speaking2": "speaking2_school.png",
                    "singing": "singing_school.png"
                },
                "colors": {
                    "bubble_bg": QColor(240, 248, 255, 240),
                    "bubble_border": QColor(0, 100, 200),
                    "bubble_shadow": QColor(25, 25, 112, 30)
                },
                "effects": ["footprint", "stars", "books"],
                "greetings": [
                    "오늘도 열심히 공부해요! 📚",
                    "학교 가는 시간이에요! 🎒",
                    "숙제는 다 했나요? ✏️",
                    "공부하면서 노래 들을까요? 🎵"
                ],
                "particles": {
                    "type": "stars",
                    "colors": [
                        QColor(0, 100, 200),
                        QColor(70, 130, 180),
                        QColor(135, 206, 235)
                    ]
                }
            },
            
            "cafe": {
                "name": "카페",
                "costume_folder": "costumes/cafe",
                "images": {
                    "character": "character_cafe.png",
                    "grab": "grab_cafe.png",
                    "speaking1": "speaking1_cafe.png",
                    "speaking2": "speaking2_cafe.png",
                    "singing": "singing_cafe.png"
                },
                "colors": {
                    "bubble_bg": QColor(245, 222, 179, 240),
                    "bubble_border": QColor(160, 82, 45),
                    "bubble_shadow": QColor(101, 67, 33, 30)
                },
                "effects": ["footprint", "steam", "coffee"],
                "greetings": [
                    "커피 한 잔 하실래요? ☕",
                    "카페 분위기가 좋아요~ 🥐",
                    "따뜻한 라떼 어떠세요? 🥛",
                    "여유로운 시간이에요! 📖"
                ],
                "particles": {
                    "type": "steam",
                    "colors": [
                        QColor(160, 82, 45),
                        QColor(210, 180, 140),
                        QColor(245, 222, 179)
                    ]
                }
            },
            
            "night": {
                "name": "밤",
                "costume_folder": "costumes/night",
                "images": {
                    "character": "character_night.png",
                    "grab": "grab_night.png",
                    "speaking1": "speaking1_night.png",
                    "speaking2": "speaking2_night.png",
                    "singing": "singing_night.png"
                },
                "colors": {
                    "bubble_bg": QColor(25, 25, 112, 240),
                    "bubble_border": QColor(138, 43, 226),
                    "bubble_shadow": QColor(72, 61, 139, 40)
                },
                "effects": ["footprint", "stars", "moon"],
                "greetings": [
                    "좋은 밤이에요! 🌙",
                    "별이 참 예뻐요~ ⭐",
                    "조용한 밤이네요! 🌃",
                    "달빛이 아름다워요! 🌌"
                ],
                "particles": {
                    "type": "stars",
                    "colors": [
                        QColor(255, 255, 255),
                        QColor(255, 215, 0),
                        QColor(138, 43, 226)
                    ]
                }
            },
            
            "sports": {
                "name": "스포츠",
                "costume_folder": "costumes/sports",
                "images": {
                    "character": "character_sports.png",
                    "grab": "grab_sports.png",
                    "speaking1": "speaking1_sports.png",
                    "speaking2": "speaking2_sports.png",
                    "singing": "singing_sports.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 255, 255, 240),
                    "bubble_border": QColor(255, 69, 0),
                    "bubble_shadow": QColor(178, 34, 34, 30)
                },
                "effects": ["footprint", "energy", "speed"],
                "greetings": [
                    "운동할 시간이에요! 💪",
                    "건강한 하루 보내세요! 🏃‍♀️",
                    "스트레칭부터 해볼까요? 🤸‍♀️",
                    "파이팅! 힘내세요! ⚽"
                ],
                "particles": {
                    "type": "energy",
                    "colors": [
                        QColor(255, 69, 0),
                        QColor(255, 140, 0),
                        QColor(255, 215, 0)
                    ]
                }
            },
            
            "gothic": {
                "name": "고딕",
                "costume_folder": "costumes/gothic",
                "images": {
                    "character": "character_gothic.png",
                    "grab": "grab_gothic.png",
                    "speaking1": "speaking1_gothic.png",
                    "speaking2": "speaking2_gothic.png",
                    "singing": "singing_gothic.png"
                },
                "colors": {
                    "bubble_bg": QColor(0, 0, 0, 240),
                    "bubble_border": QColor(128, 0, 128),
                    "bubble_shadow": QColor(75, 0, 130, 40)
                },
                "effects": ["footprint", "shadow", "mystery"],
                "greetings": [
                    "어둠 속에서 안녕하세요... 🖤",
                    "신비로운 밤이에요~ 🔮",
                    "고요한 분위기가 좋아요... 🌹",
                    "우아한 어둠 속에서... ⚱️"
                ],
                "particles": {
                    "type": "shadow",
                    "colors": [
                        QColor(75, 0, 130),
                        QColor(128, 0, 128),
                        QColor(0, 0, 0)
                    ]
                }
            },
            
            "fantasy": {
                "name": "판타지",
                "costume_folder": "costumes/fantasy",
                "images": {
                    "character": "character_fantasy.png",
                    "grab": "grab_fantasy.png",
                    "speaking1": "speaking1_fantasy.png",
                    "speaking2": "speaking2_fantasy.png",
                    "singing": "singing_fantasy.png"
                },
                "colors": {
                    "bubble_bg": QColor(255, 240, 255, 240),
                    "bubble_border": QColor(186, 85, 211),
                    "bubble_shadow": QColor(147, 0, 211, 30)
                },
                "effects": ["footprint", "magic", "fairy"],
                "greetings": [
                    "마법의 세계에 오신 걸 환영해요! ✨",
                    "요정들이 춤추고 있어요~ 🧚‍♀️",
                    "마법 주문을 외워볼까요? 🪄",
                    "환상적인 모험을 떠나요! 🦄"
                ],
                "particles": {
                    "type": "magic",
                    "colors": [
                        QColor(186, 85, 211),
                        QColor(255, 20, 147),
                        QColor(0, 255, 255),
                        QColor(255, 215, 0)
                    ]
                }
            },
            
            "vintage": {
                "name": "빈티지",
                "costume_folder": "costumes/vintage",
                "images": {
                    "character": "character_vintage.png",
                    "grab": "grab_vintage.png",
                    "speaking1": "speaking1_vintage.png",
                    "speaking2": "speaking2_vintage.png",
                    "singing": "singing_vintage.png"
                },
                "colors": {
                    "bubble_bg": QColor(245, 245, 220, 240),
                    "bubble_border": QColor(139, 69, 19),
                    "bubble_shadow": QColor(101, 67, 33, 30)
                },
                "effects": ["footprint", "classic", "sepia"],
                "greetings": [
                    "옛날 스타일이 참 우아해요~ 🎩",
                    "클래식한 분위기예요! 🕰️",
                    "추억이 새록새록해요! 📸",
                    "고풍스러운 매력이 있어요! 🎭"
                ],
                "particles": {
                    "type": "sepia",
                    "colors": [
                        QColor(139, 69, 19),
                        QColor(160, 82, 45),
                        QColor(245, 245, 220)
                    ]
                }
            }
        }
        
        # 자동 테마 전환 타이머
        self.auto_theme_timer = QTimer()
        self.auto_theme_timer.timeout.connect(self.check_auto_theme)
        self.auto_theme_timer.start(3600000)  # 1시간마다 체크
        
        # 시작시 자동 테마 적용
        self.check_auto_theme()
    
    def get_current_theme_config(self):
        """현재 테마 설정 반환"""
        return self.themes.get(self.current_theme, self.themes["default"])
    
    def get_costume_image_path(self, image_type):
        """테마별 의상 이미지 경로 반환"""
        theme_config = self.get_current_theme_config()
        
        # 1. 테마별 이미지 파일명으로 검색
        theme_image = theme_config["images"].get(image_type, "")
        if theme_image and os.path.exists(theme_image):
            return theme_image
        
        # 2. 테마별 폴더에서 검색
        costume_folder = theme_config.get("costume_folder", "")
        if costume_folder:
            folder_path = os.path.join(costume_folder, f"{image_type}.png")
            if os.path.exists(folder_path):
                return folder_path
        
        # 3. 기본 이미지 폴백
        fallback_files = {
            "character": ["character.png", "default_character.png"],
            "grab": ["grab.png", "default_grab.png"],
            "speaking1": ["speaking1.png", "h1.png", "default_speaking1.png"],
            "speaking2": ["speaking2.png", "h2.png", "default_speaking2.png"],
            "singing": ["singing.png", "sing.png", "default_singing.png"]
        }
        
        for fallback in fallback_files.get(image_type, []):
            if os.path.exists(fallback):
                return fallback
        
        return None
    
    def set_theme(self, theme_name):
        """테마 변경"""
        if theme_name in self.themes:
            old_theme = self.current_theme
            self.current_theme = theme_name
            print(f"🎨 테마 변경: {old_theme} → {theme_name}")
            self.theme_changed.emit(theme_name)
            return True
        return False
    
    def get_available_themes(self):
        """사용 가능한 테마 목록"""
        return list(self.themes.keys())
    
    def get_theme_greeting(self):
        """현재 테마의 인사말 랜덤 선택"""
        theme_config = self.get_current_theme_config()
        return random.choice(theme_config["greetings"])
    
    def check_auto_theme(self):
        """자동 테마 전환 체크 - 확장된 계절 시스템"""
        if not self.auto_theme_enabled:
            return
            
        now = datetime.datetime.now()
        month = now.month
        day = now.day
        hour = now.hour
        
        # 크리스마스 시즌 (12월 20일~31일)
        if month == 12 and day >= 20:
            if self.current_theme != "christmas":
                self.set_theme("christmas")
                return
        
        # 할로윈 (10월 25일~31일)
        elif month == 10 and day >= 25:
            if self.current_theme != "halloween":
                self.set_theme("halloween")
                return
        
        # 계절별 자동 테마 (일반 기간)
        # 봄 (3-5월)
        elif month in [3, 4, 5]:
            if self.current_theme != "spring":
                self.set_theme("spring")
                return
        
        # 여름 (6-8월) 
        elif month in [6, 7, 8]:
            if self.current_theme != "summer":
                self.set_theme("summer")
                return
        
        # 가을 (9-11월, 할로윈 기간 제외)
        elif month in [9, 11] or (month == 10 and day < 25):
            if self.current_theme != "autumn":
                self.set_theme("autumn")
                return
        
        # 겨울 (12-2월, 크리스마스 기간 제외)
        elif month in [1, 2] or (month == 12 and day < 20):
            if self.current_theme != "winter":
                self.set_theme("winter")
                return
        
        # 시간대별 테마 (계절 우선)
        elif hour >= 22 or hour <= 5:  # 밤 시간
            if self.current_theme not in ["christmas", "halloween", "spring", "summer", "autumn", "winter"]:
                if self.current_theme != "night":
                    self.set_theme("night")
                    return
        
        # 기본 테마로 (위 조건에 해당하지 않을 때)
        else:
            if self.current_theme != "default":
                self.set_theme("default")
    
    def toggle_auto_theme(self):
        """자동 테마 전환 켜기/끄기"""
        self.auto_theme_enabled = not self.auto_theme_enabled
        return self.auto_theme_enabled


class ThemedParticle(QWidget):
    """테마별 파티클 이펙트"""
    
    def __init__(self, x, y, theme_config, particle_type="normal"):
        super().__init__()
        self.theme_config = theme_config
        self.particle_type = particle_type
        self.opacity = 1.0
        self.x_pos = x
        self.y_pos = y
        self.rotation = 0
        
        # 테마별 파티클 동작 설정 (확장)
        if particle_type == "snow":
            self.dx = random.uniform(-0.5, 0.5)
            self.dy = random.uniform(0.5, 2.0)  # 아래로 떨어짐
            self.rotation_speed = random.uniform(-2, 2)
            self.size = random.randint(3, 8)
            self.shape = "circle"
            
        elif particle_type == "petals":
            self.dx = random.uniform(-1, 1) 
            self.dy = random.uniform(0.3, 1.5)
            self.rotation_speed = random.uniform(-5, 5)
            self.size = random.randint(4, 10)
            self.shape = "petal"
            
        elif particle_type == "leaves":
            self.dx = random.uniform(-1.5, 1.5)
            self.dy = random.uniform(0.5, 2.0)
            self.rotation_speed = random.uniform(-8, 8)
            self.size = random.randint(5, 12)
            self.shape = "leaf"
            
        elif particle_type == "confetti":
            self.dx = random.uniform(-2, 2)
            self.dy = random.uniform(-3, -0.5) 
            self.rotation_speed = random.uniform(-10, 10)
            self.size = random.randint(3, 6)
            self.shape = "rect"
            
        elif particle_type == "spooky":
            self.dx = random.uniform(-1, 1)
            self.dy = random.uniform(-1, 1)
            self.rotation_speed = random.uniform(-3, 3)
            self.size = random.randint(5, 12)
            self.shape = "bat"
            
        elif particle_type == "stars":
            self.dx = random.uniform(-0.5, 0.5)
            self.dy = random.uniform(-2, -0.5)
            self.rotation_speed = random.uniform(-10, 10)
            self.size = random.randint(4, 8)
            self.shape = "star"
            
        elif particle_type == "magic":
            self.dx = random.uniform(-2, 2)
            self.dy = random.uniform(-2, 2)
            self.rotation_speed = random.uniform(-15, 15)
            self.size = random.randint(3, 10)
            self.shape = "sparkle"
            
        elif particle_type == "steam":
            self.dx = random.uniform(-0.3, 0.3)
            self.dy = random.uniform(-2, -0.8)
            self.rotation_speed = random.uniform(-2, 2)
            self.size = random.randint(4, 8)
            self.shape = "circle"
            
        elif particle_type == "energy":
            self.dx = random.uniform(-1.5, 1.5)
            self.dy = random.uniform(-2.5, -0.5)
            self.rotation_speed = random.uniform(-8, 8)
            self.size = random.randint(3, 7)
            self.shape = "lightning"
            
        elif particle_type == "shadow":
            self.dx = random.uniform(-0.8, 0.8)
            self.dy = random.uniform(-1, 1)
            self.rotation_speed = random.uniform(-5, 5)
            self.size = random.randint(5, 10)
            self.shape = "wisp"
            
        elif particle_type == "sepia":
            self.dx = random.uniform(-0.5, 0.5)
            self.dy = random.uniform(-1.5, -0.3)
            self.rotation_speed = random.uniform(-3, 3)
            self.size = random.randint(4, 8)
            self.shape = "vintage"
            
        else:  # normal, bubble 등
            self.dx = random.uniform(-1, 1)
            self.dy = random.uniform(-2, -0.5)
            self.rotation_speed = random.uniform(-5, 5)
            self.size = random.randint(4, 8)
            self.shape = "circle"
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(40, 40)
        
        self.move(x - 20, y - 20)
        
        # 애니메이션 타이머
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_particle)
        self.animation_timer.start(50)
        
        # 자동 삭제 타이머
        QTimer.singleShot(4000, self.deleteLater)
    
    def update_particle(self):
        self.x_pos += self.dx
        self.y_pos += self.dy
        
        # 중력 효과 (테마별로 다름)
        if self.particle_type in ["snow", "petals"]:
            self.dy += 0.02  # 약한 중력
        elif self.particle_type == "confetti":
            self.dy += 0.1   # 강한 중력
        
        self.rotation += self.rotation_speed
        self.opacity -= 0.008
        
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
        
        # 테마 색상 가져오기
        colors = self.theme_config["particles"]["colors"]
        color = random.choice(colors)
        color.setAlpha(int(255 * self.opacity))
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 1))
        
        # 모양별 그리기 (확장)
        if self.shape == "circle":
            painter.drawEllipse(-self.size//2, -self.size//2, self.size, self.size)
            
        elif self.shape == "rect":
            painter.drawRect(-self.size//2, -self.size//2, self.size, self.size//2)
            
        elif self.shape == "petal":
            # 꽃잎 모양 (타원 여러개)
            painter.drawEllipse(-self.size//2, -self.size//3, self.size, self.size//2)
            painter.drawEllipse(-self.size//3, -self.size//2, self.size//2, self.size)
            
        elif self.shape == "leaf":
            # 나뭇잎 모양
            painter.drawEllipse(-self.size//2, -self.size//4, self.size, self.size//2)
            painter.drawLine(0, -self.size//4, 0, self.size//4)
            
        elif self.shape == "bat":
            # 박쥐 모양 (간단한 타원들)
            painter.drawEllipse(-self.size//2, -self.size//4, self.size, self.size//2)
            painter.drawEllipse(-self.size//3, -self.size//3, self.size//4, self.size//3)
            painter.drawEllipse(self.size//4, -self.size//3, self.size//4, self.size//3)
            
        elif self.shape == "star":
            # 별 모양 (십자가 형태)
            painter.drawLine(-self.size//2, 0, self.size//2, 0)
            painter.drawLine(0, -self.size//2, 0, self.size//2)
            painter.drawLine(-self.size//3, -self.size//3, self.size//3, self.size//3)
            painter.drawLine(-self.size//3, self.size//3, self.size//3, -self.size//3)
            
        elif self.shape == "sparkle":
            # 반짝이 (다이아몬드 형태)
            points = [
                QPoint(0, -self.size//2),
                QPoint(self.size//3, 0),
                QPoint(0, self.size//2),
                QPoint(-self.size//3, 0)
            ]
            painter.drawPolygon(points)
            
        elif self.shape == "lightning":
            # 번개 모양
            painter.drawLine(-self.size//3, -self.size//2, 0, 0)
            painter.drawLine(0, 0, self.size//3, self.size//2)
            painter.drawLine(-self.size//4, -self.size//4, self.size//4, self.size//4)
            
        elif self.shape == "wisp":
            # 연기/안개 모양
            painter.drawEllipse(-self.size//2, -self.size//3, self.size, self.size//2)
            painter.drawEllipse(-self.size//3, -self.size//4, self.size//2, self.size//3)
            
        elif self.shape == "vintage":
            # 빈티지 스타일 (사각형과 원의 조합)
            painter.drawRect(-self.size//3, -self.size//3, self.size//2, self.size//2)
            painter.drawEllipse(-self.size//2, -self.size//2, self.size, self.size)


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


class StrictKoreanVoiceRecognizer(QObject):
    """강화된 한국어 전용 음성 인식기"""
    voice_command = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        # 강화된 피드백 차단 시스템
        self.is_tts_blocked = False
        self.tts_block_until = 0
        
        # 한국어 필터링을 위한 패턴
        self.korean_pattern = re.compile(r'[가-힣\s\d!?.,~]+')
        self.noise_patterns = {
            "음", "어", "아", "으", "오", "으음", "아아", "어어", "음음", "네네", "응응",
            "um", "uh", "ah", "oh", "hmm", "err", "well", "so", "like", "you", "know"
        }
        
        # 음성 인식 설정
        self.setup_microphone()
        
        print("🎤 강화된 한국어 전용 음성 인식기 초기화 완료")
    
    def setup_microphone(self):
        """마이크 설정"""
        try:
            print("🎤 마이크 초기화 중...")
            
            with self.microphone as source:
                print("🔧 환경 소음 측정 중... (3초간 조용히 해주세요)")
                self.recognizer.adjust_for_ambient_noise(source, duration=3)
                
                # 엄격한 설정값
                self.recognizer.energy_threshold = max(400, self.recognizer.energy_threshold)  # 더 높은 임계값
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 1.0  # 더 긴 대기 시간
                self.recognizer.phrase_time_limit = 4  # 더 짧은 인식 시간
                self.recognizer.non_speaking_duration = 0.8  # 긴 비말하기 시간
                
                print(f"✅ 마이크 설정 완료")
                print(f"   에너지 임계값: {self.recognizer.energy_threshold}")
                print(f"   대기 시간: {self.recognizer.pause_threshold}초")
                
        except Exception as e:
            print(f"❌ 마이크 설정 오류: {e}")
            self.recognizer.energy_threshold = 400
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.0
    
    def set_tts_block(self, is_blocked):
        """TTS 차단 상태 설정"""
        current_time = time.time()
        self.is_tts_blocked = is_blocked
        
        if is_blocked:
            self.tts_block_until = current_time + 3.0  # 3초간 차단
            print(f"🔇 TTS 차단 활성화 - 3초간 음성 인식 차단")
        else:
            self.tts_block_until = current_time + 1.5  # 1.5초 추가 안전 시간
            print(f"🔊 TTS 차단 해제 - 1.5초 안전 시간")
    
    def is_korean_text(self, text):
        """한국어 텍스트인지 확인"""
        text = text.strip()
        if len(text) == 0:
            return False
        
        # 한국어 문자가 50% 이상인지 확인
        korean_chars = len(re.findall(r'[가-힣]', text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars == 0:
            return False
            
        korean_ratio = korean_chars / total_chars
        return korean_ratio >= 0.5
    
    def filter_korean_only(self, text):
        """한국어 부분만 추출"""
        # 한국어, 숫자, 기본 문장부호만 허용
        filtered = re.sub(r'[^가-힣\s\d!?.,~]', '', text)
        # 중복 공백 제거
        filtered = ' '.join(filtered.split())
        return filtered.strip()
    
    def is_valid_command(self, text):
        """유효한 명령어인지 확인"""
        text = text.strip().lower()
        
        # 차단 상태 확인
        if self.is_tts_blocked or time.time() < self.tts_block_until:
            return False
        
        # 너무 짧은 텍스트
        if len(text) < 2:
            return False
        
        # 소음 패턴 확인
        if text in self.noise_patterns:
            return False
        
        # 한국어인지 확인
        if not self.is_korean_text(text):
            print(f"❌ 한국어가 아닌 텍스트 차단: '{text}'")
            return False
        
        # 반복 문자 확인
        if len(set(text.replace(' ', ''))) <= 1:
            return False
        
        return True
    
    def start_listening(self):
        """음성 인식 시작"""
        self.is_listening = True
        thread = threading.Thread(target=self._listen_continuously)
        thread.daemon = True
        thread.start()
        print("🎤 강화된 한국어 음성 인식 시작")
    
    def stop_listening(self):
        """음성 인식 중지"""
        self.is_listening = False
        print("🎤 음성 인식 중지")
    
    def _listen_continuously(self):
        """연속 음성 인식"""
        print("🎤 한국어 전용 음성 인식 루프 시작")
        
        consecutive_failures = 0
        max_failures = 3
        
        while self.is_listening:
            try:
                # 차단 상태 확인
                if self.is_tts_blocked or time.time() < self.tts_block_until:
                    time.sleep(0.2)
                    continue
                
                # 음성 캡처
                try:
                    with self.microphone as source:
                        print("🎤 한국어 음성 대기 중...")
                        audio = self.recognizer.listen(
                            source,
                            timeout=2,      # 2초 타임아웃
                            phrase_time_limit=4  # 4초 최대 녹음
                        )
                        
                except sr.WaitTimeoutError:
                    continue
                
                # 음성 인식 시도 (한국어로 강제)
                try:
                    print("🔍 한국어 음성 분석 중...")
                    text = self.recognizer.recognize_google(
                        audio, 
                        language='ko-KR',  # 한국어로 강제
                        show_all=False
                    )
                    
                    consecutive_failures = 0
                    print(f"🎤 원본 인식 결과: '{text}'")
                    
                    # 한국어 필터링
                    filtered_text = self.filter_korean_only(text)
                    print(f"🔍 필터링된 텍스트: '{filtered_text}'")
                    
                    # 유효성 검사
                    if self.is_valid_command(filtered_text):
                        print(f"✅ 유효한 한국어 명령: '{filtered_text}'")
                        self.voice_command.emit(filtered_text)
                    else:
                        print(f"⏭️  무시된 명령: '{filtered_text}'")
                    
                except sr.UnknownValueError:
                    print("🔇 음성을 인식할 수 없습니다")
                    consecutive_failures += 1
                    
                except sr.RequestError as e:
                    print(f"❌ 음성 인식 서비스 오류: {e}")
                    consecutive_failures += 1
                    
                # 연속 실패시 대기
                if consecutive_failures >= max_failures:
                    print("⏸️  연속 오류로 인한 5초 대기")
                    time.sleep(5)
                    consecutive_failures = 0
                    
            except Exception as e:
                print(f"❌ 음성 인식 예외: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    print("⏸️  예외로 인한 5초 대기")
                    time.sleep(5)
                    consecutive_failures = 0
                else:
                    time.sleep(1)


class PureTTSHandler(QObject):
    """순수 TTS 핸들러 (레이첼 고정)"""
    tts_started = pyqtSignal(str)
    tts_finished = pyqtSignal()
    
    def __init__(self, voice_recognizer):
        super().__init__()
        self.voice_recognizer = voice_recognizer
        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = RACHEL_VOICE_ID  # 레이첼로 고정
        self.tts_enabled = True
        self.is_speaking = False
        self.current_text = ""
        
        # 미디어 플레이어 설정
        self.media_player = QMediaPlayer()
        self.media_player.stateChanged.connect(self.on_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        print("🎤 레이첼 전용 TTS 핸들러 초기화")
    
    def on_state_changed(self, state):
        """플레이어 상태 변경"""
        if state == QMediaPlayer.PlayingState:
            self.is_speaking = True
            self.voice_recognizer.set_tts_block(True)
            self.tts_started.emit(self.current_text)
            
        elif state == QMediaPlayer.StoppedState:
            if self.is_speaking:
                self.is_speaking = False
                self.voice_recognizer.set_tts_block(False)
                self.tts_finished.emit()
                self.current_text = ""
    
    def on_media_status_changed(self, status):
        """미디어 상태 변경"""
        if status in [QMediaContent.EndOfMedia, QMediaContent.InvalidMedia]:
            if self.is_speaking:
                self.is_speaking = False
                self.voice_recognizer.set_tts_block(False)
                self.tts_finished.emit()
                self.current_text = ""
    
    def speak(self, text, is_singing=False):
        """TTS 실행 (레이첼 고정)"""
        if not self.tts_enabled or not self.api_key or not text.strip():
            return
            
        # 이전 TTS 즉시 중지
        self.stop_speaking()
        
        self.current_text = text.strip()
        print(f"🎤 레이첼 TTS 시작: {self.current_text[:50]}...")
        
        # 백그라운드에서 TTS 생성
        thread = threading.Thread(target=self._generate_rachel_tts, args=(text, is_singing))
        thread.daemon = True
        thread.start()
    
    def stop_speaking(self):
        """TTS 즉시 중지"""
        if self.is_speaking:
            print("⏹️  TTS 강제 중지")
            self.media_player.stop()
            self.is_speaking = False
            self.voice_recognizer.set_tts_block(False)
            self.current_text = ""
    
    def _generate_rachel_tts(self, text, is_singing=False):
        """레이첼 TTS 생성 및 재생"""
        try:
            # 미리 음성 인식 차단 시작
            self.voice_recognizer.set_tts_block(True)
            
            # 레이첼 전용 설정
            settings = {
                "stability": 0.85,
                "similarity_boost": 0.75,
                "style": 0.8,  # 노래든 말이든 동일한 스타일
                "use_speaker_boost": True
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
                self.voice_recognizer.set_tts_block(False)
                
        except Exception as e:
            print(f"❌ TTS 생성 오류: {e}")
            self.voice_recognizer.set_tts_block(False)
    
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


class KoreanChatGPTHandler(QObject):
    """강화된 한국어 전용 ChatGPT 핸들러"""
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
            return False
            
        try:
            self.client = openai.OpenAI(api_key=api_key)
            return True
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {e}")
            return False
    
    def get_response(self, user_message):
        """ChatGPT에게 질문하고 한국어 응답만 받기"""
        if not self.client:
            return "죄송해요, ChatGPT 연결에 문제가 있어요."
            
        try:
            system_prompt = """당신은 귀엽고 친근한 한국 데스크탑 캐릭터입니다. 
            다음 규칙을 반드시 지키세요:
            
            ■ 응답 언어: 반드시 한국어로만 대답하세요. 영어나 다른 언어는 절대 사용하지 마세요.
            ■ 말투: 친근한 반말 사용 ("~해", "~야", "~지")
            ■ 길이: 1-2문장으로 짧고 간결하게
            ■ 이모티콘: 적절히 사용하되 과도하지 않게
            ■ 성격: 밝고 귀여운 여자아이 캐릭터
            ■ 금지사항: 영어, 일본어, 중국어 등 한국어가 아닌 언어 사용 금지
            
            사용자가 영어로 말해도 반드시 한국어로만 답변하세요."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            # 한국어가 아닌 응답 필터링
            korean_pattern = re.compile(r'[가-힣]')
            if not korean_pattern.search(answer):
                return "음... 한국말로 대답하기 어려워 💭"
            
            # 영어 단어가 섞여있으면 제거
            answer = re.sub(r'[a-zA-Z]+', '', answer)
            answer = ' '.join(answer.split())  # 공백 정리
            
            return answer if answer.strip() else "잘 모르겠어 💭"
            
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
        
        # 노래 관련 변수 추가 (강화)
        self.is_singing = False
        self.music_notes = []
        self.note_timer = None
        self.song_database = SongDatabase()
        self.song_mode_active = False  # 노래 모드 활성화 플래그
        
        # 이펙트 관련 변수
        self.walking_effects = []
        self.themed_particles = []
        self.last_effect_time = 0
        self.effect_interval = 300
        self.current_effect_type = "footprint"
        
        # 위치 추적을 위한 변수
        self.last_x = 0
        self.last_y = 0
        
        self.setup_window()
        self.setup_theme_system()
        self.load_character()
        self.setup_movement()
        self.setup_interactions()
        self.setup_korean_voice_system()  # 강화된 한국어 시스템
        self.setup_korean_chatgpt()

    def setup_theme_system(self):
        """테마 시스템 초기화"""
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        
        print(f"🎨 테마 시스템 초기화: {self.theme_manager.current_theme}")
        
    def on_theme_changed(self, theme_name):
        """테마 변경 시 처리"""
        print(f"🎨 테마 적용: {theme_name}")
        self.load_themed_costumes()
        
        theme_config = self.theme_manager.get_current_theme_config()
        greeting = random.choice(theme_config["greetings"])
        
        QTimer.singleShot(500, lambda: self.show_speech_with_tts(f"테마가 '{theme_config['name']}'로 바뀌었어요! {greeting}"))
        self.create_theme_celebration()
    
    def load_themed_costumes(self):
        """테마별 의상 이미지 로드 - 완전 개선된 버전"""
        print(f"👗 테마별 의상 로드 시작: {self.theme_manager.current_theme}")
        current_size = int(self.base_image_size * self.scale_factor)
        
        try:
            # 기본 캐릭터 이미지 (평상시)
            char_path = self.theme_manager.get_costume_image_path("character")
            if char_path:
                self.original_pixmap = QPixmap(char_path).scaled(
                    current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                print(f"✅ 기본 의상 로드: {char_path}")
            else:
                # 기본 이미지 폴백
                self.original_pixmap = self.create_default_character_image(current_size)
                print("⚠️  기본 의상을 찾을 수 없어 기본 이미지 생성")
            
            # 잡기 이미지 (드래그할 때)
            grab_path = self.theme_manager.get_costume_image_path("grab")
            if grab_path:
                self.grabbed_pixmap = QPixmap(grab_path).scaled(
                    current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                print(f"✅ 잡기 의상 로드: {grab_path}")
            else:
                # 기본 이미지를 어둡게 처리
                self.grabbed_pixmap = self.create_darkened_pixmap(self.original_pixmap)
                print("⚠️  잡기 의상을 찾을 수 없어 어둡게 처리")
                
            # 말하기 이미지들 (2개 애니메이션)
            speaking1_path = self.theme_manager.get_costume_image_path("speaking1")
            speaking2_path = self.theme_manager.get_costume_image_path("speaking2")
            
            self.speaking_frames = []
            
            if speaking1_path:
                frame1 = QPixmap(speaking1_path).scaled(
                    current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.speaking_frames.append(frame1)
                print(f"✅ 말하기1 의상 로드: {speaking1_path}")
            
            if speaking2_path:
                frame2 = QPixmap(speaking2_path).scaled(
                    current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.speaking_frames.append(frame2)
                print(f"✅ 말하기2 의상 로드: {speaking2_path}")
            
            # 말하기 이미지가 없으면 기본 이미지 사용
            if not self.speaking_frames:
                self.speaking_frames = [self.original_pixmap, self.original_pixmap]
                print("⚠️  말하기 의상을 찾을 수 없어 기본 이미지 사용")
            elif len(self.speaking_frames) == 1:
                # 1개만 있으면 복사해서 2개로 만들기
                self.speaking_frames.append(self.speaking_frames[0])
                print("⚠️  말하기 의상이 1개만 있어서 복사")
            
            # 노래 이미지 (1개)
            singing_path = self.theme_manager.get_costume_image_path("singing")
            if singing_path:
                self.singing_pixmap = QPixmap(singing_path).scaled(
                    current_size, current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                print(f"✅ 노래 의상 로드: {singing_path}")
            else:
                self.singing_pixmap = self.original_pixmap
                print("⚠️  노래 의상을 찾을 수 없어 기본 이미지 사용")
            
            # 즉시 현재 상태에 맞는 이미지 적용
            self.apply_current_costume_state()
            print(f"✅ 테마 '{self.theme_manager.current_theme}' 의상 로드 완료")
            
        except Exception as e:
            print(f"❌ 테마 의상 로드 실패: {e}")
            self.create_fallback_costumes(current_size)
    
    def create_default_character_image(self, size):
        """기본 캐릭터 이미지 생성 (이미지 파일이 없을 때)"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 간단한 캐릭터 그리기
        center = size // 2
        
        # 얼굴
        painter.setBrush(QBrush(QColor(255, 220, 177)))
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawEllipse(size//4, size//4, size//2, size//2)
        
        # 눈
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(size//3, size//3, 6, 8)
        painter.drawEllipse(size*2//3-6, size//3, 6, 8)
        
        # 입
        painter.setPen(QPen(QColor(255, 100, 100), 3))
        painter.drawArc(size//2-10, size//2, 20, 15, 0, 180*16)
        
        painter.end()
        return pixmap
    
    def create_fallback_costumes(self, size):
        """폴백 의상들 생성"""
        print("🔧 폴백 의상 생성")
        
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            self.original_pixmap = self.create_default_character_image(size)
        
        if not hasattr(self, 'grabbed_pixmap') or self.grabbed_pixmap.isNull():
            self.grabbed_pixmap = self.create_darkened_pixmap(self.original_pixmap)
        
        if not hasattr(self, 'speaking_frames') or not self.speaking_frames:
            self.speaking_frames = [self.original_pixmap, self.original_pixmap]
        
        if not hasattr(self, 'singing_pixmap') or self.singing_pixmap.isNull():
            self.singing_pixmap = self.original_pixmap
    
    def create_darkened_pixmap(self, original_pixmap):
        """원본 이미지를 어둡게 처리하여 grab 이미지로 사용"""
        if original_pixmap.isNull():
            return original_pixmap
        
        darkened = QPixmap(original_pixmap.size())
        darkened.fill(Qt.transparent)
        
        painter = QPainter(darkened)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 원본 이미지 그리기
        painter.drawPixmap(0, 0, original_pixmap)
        
        # 어두운 오버레이 추가
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.fillRect(darkened.rect(), QColor(120, 120, 120, 180))
        
        painter.end()
        return darkened
    
    def apply_current_costume_state(self):
        """현재 상태에 맞는 의상 적용"""
        if not self.has_image:
            return
            
        if getattr(self, 'is_dragging', False):
            pixmap = self.grabbed_pixmap
        elif hasattr(self, 'is_speaking_animation') and getattr(self, 'is_speaking_animation', False):
            # 애니메이션 중이면 그대로 두기
            return
        else:
            pixmap = self.original_pixmap
        
        # 방향 적용
        if not getattr(self, 'facing_right', True):
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        
        self.label.setPixmap(pixmap)
    
    def create_theme_celebration(self):
        """테마 전환 축하 파티클"""
        theme_config = self.theme_manager.get_current_theme_config()
        particle_type = theme_config["particles"]["type"]
        
        char_center_x = self.x() + self.width() // 2
        char_center_y = self.y() + self.height() // 2
        
        for _ in range(8):
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-30, 30)
            
            particle = ThemedParticle(
                char_center_x + offset_x,
                char_center_y + offset_y, 
                theme_config,
                particle_type
            )
            particle.show()
            self.themed_particles.append(particle)
        
        self.themed_particles = [p for p in self.themed_particles if p and not p.isHidden()]
    
    def create_themed_walking_effect(self, x, y):
        """테마별 걷기 이펙트"""
        self.create_walking_effect(x, y)
        
        if random.random() < 0.1:
            theme_config = self.theme_manager.get_current_theme_config()
            particle_type = theme_config["particles"]["type"]
            
            particle = ThemedParticle(x, y + self.height() - 10, theme_config, particle_type)
            particle.show()
            self.themed_particles.append(particle)

    def setup_korean_voice_system(self):
        """강화된 한국어 음성 시스템 설정"""
        print("🎤 강화된 한국어 전용 음성 시스템 초기화 중...")
        
        # 1. 강화된 한국어 음성 인식기
        self.voice_recognizer = StrictKoreanVoiceRecognizer()
        self.voice_recognizer.voice_command.connect(self.handle_voice_command)
        
        # 2. 레이첼 전용 TTS 핸들러
        self.tts_handler = PureTTSHandler(self.voice_recognizer)
        self.tts_handler.tts_finished.connect(self.on_tts_finished)
        
        # 3. 음성 인식 시작
        self.voice_recognizer.start_listening()
        
        if self.tts_handler.api_key:
            print("✅ Eleven Labs 레이첼 TTS 활성화")
        else:
            print("⚠️  Eleven Labs API 키가 설정되지 않았습니다.")
        
        print("🛡️  강화된 한국어 전용 시스템 활성화 완료")
        
        # 시작 인사
        QTimer.singleShot(2000, lambda: self.themed_say_hello())

    def setup_korean_chatgpt(self):
        """한국어 전용 ChatGPT 핸들러 설정"""
        if OPENAI_AVAILABLE:
            self.chatgpt_handler = KoreanChatGPTHandler()
            self.chatgpt_handler.response_ready.connect(self.handle_chatgpt_response)
        else:
            self.chatgpt_handler = None

    def clean_text_for_tts(self, text):
        """TTS에 적합하도록 텍스트 정리 (한국어 전용)"""
        # 기본 이모티콘들 제거
        text = re.sub(r'[😊😄😅🤔🗣️🏃‍♀️⏸️▶️🔍❌👋✨🔊🔇🎵🎶♪♫💭🎄🎃🌸🏖️🎂]', '', text)
        
        # 영어 제거
        text = re.sub(r'[a-zA-Z]+', '', text)
        
        # 연속된 특수문자 정리
        text = re.sub(r'[.]{2,}', '', text)
        text = re.sub(r'[~]+', ' ', text)
        
        # 한국어와 기본 문장부호만 남기기
        text = re.sub(r'[^가-힣\s\d!?.,]', '', text)
        
        # 공백 정리
        text = ' '.join(text.split())
        text = text.strip()
        
        return text if text else ""

    def show_speech_with_tts(self, message, is_singing=False):
        """말풍선과 함께 안전한 TTS로 음성 출력"""
        # 노래 모드일 때는 노래만 허용
        if self.song_mode_active and not is_singing:
            return
            
        self.tts_handler.stop_speaking()
        self.show_speech(message)
        
        clean_message = self.clean_text_for_tts(message)
        if clean_message:
            self.tts_handler.speak(clean_message, is_singing)

    def on_tts_finished(self):
        """TTS 완료 시 호출"""
        if self.is_singing:
            self.stop_singing()

    def start_singing(self, song):
        """노래 시작 (완전 독립 모드)"""
        print(f"🎵 노래 모드 시작: {song['title']}")
        
        # 노래 모드 활성화
        self.song_mode_active = True
        self.is_singing = True
        
        # 모든 기존 활동 중지
        self.stop_current_speech()
        self.speech_timer.stop()  # 자동 인사 중지
        
        # 노래 제목 먼저 보여주기 (말풍선만)
        self.show_speech(f"🎵 {song['title']} 🎵")
        
        # 2초 후 노래 시작
        QTimer.singleShot(2000, lambda: self.sing_pure_song(song))
        
        # 음표 이펙트 시작
        self.start_music_notes()
        
        # 노래하는 의상으로 변경
        self.set_singing_costume()

    def sing_pure_song(self, song):
        """순수 노래만 부르기"""
        if not self.is_singing:
            return
        
        print(f"🎤 순수 노래 시작: {song['lyrics'][:30]}...")
        
        # 노래 가사만 TTS로 (대화 차단)
        self.show_speech(song['lyrics'])
        clean_lyrics = self.clean_text_for_tts(song['lyrics'])
        if clean_lyrics:
            self.tts_handler.speak(clean_lyrics, is_singing=True)

    def stop_singing(self):
        """노래 중지"""
        print("🎵 노래 모드 종료")
        
        self.is_singing = False
        self.song_mode_active = False
        self.stop_music_notes()
        self.restore_costume()
        
        # 자동 인사 재시작
        self.speech_timer.start(15000)
        
        # 노래 끝 인사
        QTimer.singleShot(500, lambda: self.show_speech_with_tts("노래 끝! 어떠셨나요? 🎵"))

    def start_music_notes(self):
        """음표 이펙트 시작"""
        if self.note_timer:
            self.note_timer.stop()
            
        self.note_timer = QTimer()
        self.note_timer.timeout.connect(self.create_music_note)
        self.note_timer.start(400)

    def stop_music_notes(self):
        """음표 이펙트 중지"""
        if self.note_timer:
            self.note_timer.stop()
            self.note_timer = None

    def create_music_note(self):
        """음표 생성"""
        if not self.is_singing:
            return
            
        char_center_x = self.x() + self.width() // 2
        char_center_y = self.y() + self.height() // 2
        
        notes = ["♪", "♫", "♬", "🎵", "🎶"]
        note_type = random.choice(notes)
        
        offset_x = random.randint(-30, 30)
        offset_y = random.randint(-20, 10)
        
        note_x = char_center_x + offset_x
        note_y = char_center_y + offset_y
        
        note = MusicNote(note_x, note_y, note_type)
        note.show()
        self.music_notes.append(note)
        
        self.music_notes = [n for n in self.music_notes if n and not n.isHidden()]

    def handle_voice_command(self, text):
        """강화된 음성 명령 처리 (한국어 전용)"""
        text_lower = text.lower()
        print(f"🎤 한국어 음성 명령 처리: '{text}'")
        
        # 노래 모드 중이면 노래 제어 명령만 허용
        if self.song_mode_active or self.is_singing:
            if "멈춰" in text_lower or "그만" in text_lower or "중지" in text_lower:
                self.stop_singing()
                return
            else:
                print("🎵 노래 모드 중 - 다른 명령 무시")
                return
        
        # ChatGPT 응답 중이면 긴급 명령만 허용
        if self.is_chatgpt_responding:
            urgent_commands = ["멈춰", "정지", "조용"]
            if not any(cmd in text_lower for cmd in urgent_commands):
                print("⏭️  ChatGPT 응답 중이므로 명령 무시")
                return
        
        # 테마 관련 명령어 처리
        if self.handle_theme_voice_commands(text_lower):
            return
        
        # 노래 관련 명령어 처리
        if "노래" in text_lower:
            if "불러" in text_lower or "해줘" in text_lower or "부탁" in text_lower:
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
                self.start_random_song()
                return
        
        # 기본 명령어들
        if "커" in text_lower or "크게" in text_lower:
            self.scale_up()
            self.show_speech_with_tts("커졌어!")
            return
        elif "작" in text_lower or "작게" in text_lower:
            self.scale_down()
            self.show_speech_with_tts("작아졌어!")
            return
        elif "멈춰" in text_lower or "정지" in text_lower:
            self.pause_movement()
            self.show_speech_with_tts("멈췄어!")
            return
        elif "움직여" in text_lower or "돌아다녀" in text_lower:
            self.resume_movement()
            self.show_speech_with_tts("다시 움직일게!")
            return
        elif "조용" in text_lower or "음소거" in text_lower:
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
        elif "테스트" in text_lower:
            self.show_speech_with_tts("한국어 음성 인식이 잘 작동하고 있어!")
            return
        
        # ChatGPT를 통한 일반 대화 (한국어 전용)
        if self.chatgpt_handler and self.chatgpt_handler.client:
            self.is_chatgpt_responding = True
            self.speech_timer.stop()
            
            self.show_speech("🤔")
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
        """ChatGPT 응답 처리 (한국어 전용)"""
        self.show_speech_with_tts(response)
        
        self.is_chatgpt_responding = False
        self.speech_timer.start(15000)

    def handle_theme_voice_commands(self, text_lower):
        """테마 관련 음성 명령 처리 - 확장된 테마 지원"""
        if "테마" in text_lower or "분위기" in text_lower or "의상" in text_lower:
            if "크리스마스" in text_lower:
                if self.theme_manager.set_theme("christmas"):
                    return True
            elif "할로윈" in text_lower:
                if self.theme_manager.set_theme("halloween"):
                    return True
            elif "봄" in text_lower:
                if self.theme_manager.set_theme("spring"):
                    return True
            elif "여름" in text_lower:
                if self.theme_manager.set_theme("summer"):
                    return True
            elif "가을" in text_lower:
                if self.theme_manager.set_theme("autumn"):
                    return True
            elif "겨울" in text_lower:
                if self.theme_manager.set_theme("winter"):
                    return True
            elif "생일" in text_lower:
                if self.theme_manager.set_theme("birthday"):
                    return True
            elif "학교" in text_lower or "학생" in text_lower:
                if self.theme_manager.set_theme("school"):
                    return True
            elif "카페" in text_lower or "커피" in text_lower:
                if self.theme_manager.set_theme("cafe"):
                    return True
            elif "밤" in text_lower or "달" in text_lower:
                if self.theme_manager.set_theme("night"):
                    return True
            elif "스포츠" in text_lower or "운동" in text_lower:
                if self.theme_manager.set_theme("sports"):
                    return True
            elif "고딕" in text_lower or "어둠" in text_lower:
                if self.theme_manager.set_theme("gothic"):
                    return True
            elif "판타지" in text_lower or "마법" in text_lower:
                if self.theme_manager.set_theme("fantasy"):
                    return True
            elif "빈티지" in text_lower or "클래식" in text_lower:
                if self.theme_manager.set_theme("vintage"):
                    return True
            elif "기본" in text_lower or "원래" in text_lower:
                if self.theme_manager.set_theme("default"):
                    return True
            elif "자동" in text_lower:
                auto_status = self.theme_manager.toggle_auto_theme()
                status_text = "켰어" if auto_status else "껐어"
                self.show_speech_with_tts(f"자동 테마 전환을 {status_text}!")
                return True
            else:
                current_theme = self.theme_manager.get_current_theme_config()
                self.show_speech_with_tts(f"지금은 '{current_theme['name']}' 의상을 입고 있어요!")
                return True
        
        return False

    def get_themed_speech_bubble_colors(self):
        """테마별 말풍선 색상 반환"""
        theme_config = self.theme_manager.get_current_theme_config()
        return theme_config["colors"]
    
    def themed_say_hello(self):
        """테마별 인사"""
        # 노래 모드 중이면 인사 안함
        if self.song_mode_active or self.is_singing:
            return
            
        greeting = self.theme_manager.get_theme_greeting()
        self.show_speech_with_tts(greeting)

    def create_walking_effect(self, x, y):
        """걸을 때 이펙트 생성"""
        current_time = int(time.time() * 1000)
        if current_time - self.last_effect_time < self.effect_interval:
            return
        
        self.last_effect_time = current_time
        
        distance_moved = math.sqrt((x - self.last_x)**2 + (y - self.last_y)**2)
        if distance_moved < 5:
            return
        
        effect = WalkingEffect(
            x + self.width()//2, 
            y + self.height() - 10,
            self.current_effect_type
        )
        effect.show()
        self.walking_effects.append(effect)
        
        self.walking_effects = [e for e in self.walking_effects if e and not e.isHidden()]
        
        self.last_x = x
        self.last_y = y

    def scale_up(self):
        """캐릭터 크기 1.3배 증가 - 개선된 버전"""
        old_scale = self.scale_factor
        self.scale_factor *= 1.3
        if self.scale_factor > 3.0:  # 최대 크기 제한
            self.scale_factor = 3.0
        
        print(f"🔍 크기 증가: {old_scale:.2f} → {self.scale_factor:.2f}")
        self.update_size()

    def scale_down(self):
        """캐릭터 크기 1.3배 감소 - 개선된 버전"""
        old_scale = self.scale_factor
        self.scale_factor /= 1.3
        if self.scale_factor < 0.3:  # 최소 크기 제한
            self.scale_factor = 0.3
        
        print(f"🔍 크기 감소: {old_scale:.2f} → {self.scale_factor:.2f}")
        self.update_size()

    def update_size(self):
        """크기 업데이트 - 완전히 재작성된 버전"""
        print(f"🔧 크기 업데이트 시작: scale_factor = {self.scale_factor}")
        
        # 새로운 크기 계산
        new_widget_width = int(self.base_char_width * self.scale_factor)
        new_widget_height = int(self.base_char_height * self.scale_factor)
        new_image_size = int(self.base_image_size * self.scale_factor)
        
        print(f"🔧 새로운 크기: 위젯({new_widget_width}x{new_widget_height}), 이미지({new_image_size}x{new_image_size})")
        
        # 현재 위치 저장
        current_pos = self.pos()
        
        # 위젯 크기 변경
        self.char_width = new_widget_width
        self.char_height = new_widget_height
        self.setFixedSize(new_widget_width, new_widget_height)
        
        # 화면 경계 체크 및 위치 조정
        new_x = min(current_pos.x(), self.screen_width - new_widget_width)
        new_y = min(current_pos.y(), self.screen_height - new_widget_height)
        new_x = max(0, new_x)
        new_y = max(0, new_y)
        
        # 위치 이동
        self.move(new_x, new_y)
        
        # 라벨 크기와 위치 설정 (중앙 정렬)
        margin_x = (new_widget_width - new_image_size) // 2
        margin_y = (new_widget_height - new_image_size) // 2
        self.label.setGeometry(margin_x, margin_y, new_image_size, new_image_size)
        
        print(f"🔧 라벨 위치: ({margin_x}, {margin_y}), 크기: {new_image_size}x{new_image_size}")
        
        # 의상 다시 로드 및 적용
        self.reload_costumes_with_new_scale()
        
        # 즉시 화면 업데이트
        self.update()
        self.label.update()
        
        print(f"✅ 크기 업데이트 완료")

    def reload_costumes_with_new_scale(self):
        """새로운 스케일로 의상 다시 로드 - 개선된 버전"""
        if not self.has_image:
            # 텍스트 모드일 때 폰트 크기 조정
            font_size = int(36 * self.scale_factor)
            self.label.setFont(QFont("Arial", font_size))
            return
        
        print("👗 의상 리로드 시작")
        
        # 현재 상태 저장
        current_is_dragging = getattr(self, 'is_dragging', False)
        current_facing_right = getattr(self, 'facing_right', True)
        
        # 애니메이션 중지
        if hasattr(self, "animation_timer") and self.animation_timer and self.animation_timer.isActive():
            self.animation_timer.stop()
            self.is_speaking_animation = False
        
        try:
            # 테마별 의상 다시 로드 (새로운 스케일로)
            self.load_themed_costumes()
            
            # 현재 상태에 맞는 의상 선택
            if current_is_dragging:
                pixmap = self.grabbed_pixmap
            else:
                pixmap = self.original_pixmap
            
            # 방향 적용
            if not current_facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            
            # 의상 적용
            self.label.setPixmap(pixmap)
            
            print("✅ 의상 리로드 완료")
            
        except Exception as e:
            print(f"❌ 의상 리로드 오류: {e}")

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
            # 초기 테마별 의상 로드 시도
            self.load_themed_costumes()
            self.has_image = True
            self.facing_right = True
        except:
            # 폴백: 텍스트 모드
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
        self.speech_timer.timeout.connect(self.themed_say_hello)
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

            self.create_themed_walking_effect(new_x, new_y)
            
            self.move(int(new_x), int(new_y))
            self.raise_()

    def update_character_direction(self):
        if self.has_image:
            should_face_right = self.speed_x > 0
            if should_face_right != self.facing_right:
                self.facing_right = should_face_right
                self.apply_current_costume_state()
        else:
            self.label.setText("🐱" if self.speed_x > 0 else "🐾")
            self.facing_right = self.speed_x > 0

    def set_speaking_costume(self):
        """말하기 의상 설정 - 2개 이미지로 애니메이션"""
        if self.has_image:
            # 말하기 애니메이션 프레임 준비 (2개)
            frames = []
            
            # 현재 테마의 말하기 이미지들 사용
            for pixmap in self.speaking_frames:
                if not pixmap.isNull():
                    if not self.facing_right:
                        pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                    frames.append(pixmap)

            if frames:
                self.speaking_animation_frames = frames
                self.current_frame_index = 0
                self.is_speaking_animation = True
                if hasattr(self, 'animation_timer') and self.animation_timer:
                    self.animation_timer.stop()
                self.animation_timer = QTimer(self)
                self.animation_timer.timeout.connect(self.animate_speaking)
                self.animation_timer.start(500)  # 말하기는 천천히 (0.5초)
            else:
                self.set_static_speaking_costume()
        else:
            self.label.setText("😺")

    def set_singing_costume(self):
        """노래할 때 의상 설정 - 1개 이미지로 고정"""
        if self.has_image and hasattr(self, 'singing_pixmap') and not self.singing_pixmap.isNull():
            print(f"🎵 노래 의상으로 변경")
            
            # 방향에 맞게 이미지 준비
            pixmap = self.singing_pixmap
            if not self.facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            
            # 애니메이션 중지하고 고정 이미지로 설정
            if hasattr(self, 'animation_timer') and self.animation_timer:
                self.animation_timer.stop()
            
            self.is_speaking_animation = False
            self.label.setPixmap(pixmap)
        else:
            # 폴백: 텍스트 모드
            self.label.setText("🎵")

    def set_static_speaking_costume(self):
        """정적 말하기 의상 설정"""
        if self.has_image and self.speaking_frames:
            pixmap = self.speaking_frames[0]  # 첫 번째 프레임 사용
            if not self.facing_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.label.setPixmap(pixmap)

    def animate_speaking(self):
        """말하기 애니메이션 - 2개 이미지 순환"""
        if hasattr(self, "speaking_animation_frames") and self.speaking_animation_frames:
            self.label.setPixmap(self.speaking_animation_frames[self.current_frame_index])
            self.current_frame_index = (self.current_frame_index + 1) % len(self.speaking_animation_frames)

    def restore_costume(self):
        """의상 복원 - 개선된 버전"""
        # 애니메이션 정리
        if hasattr(self, "animation_timer") and self.animation_timer:
            self.animation_timer.stop()
            self.animation_timer.deleteLater()
            del self.animation_timer
            
        if hasattr(self, "speaking_animation_frames"):
            del self.speaking_animation_frames
            
        if hasattr(self, "is_speaking_animation"):
            self.is_speaking_animation = False

        # 기본 의상으로 복원
        self.apply_current_costume_state()

    def stop_current_speech(self):
        """현재 말하기 중지"""
        if hasattr(self, "animation_timer") and self.animation_timer:
            self.animation_timer.stop()
            self.animation_timer.deleteLater()
            del self.animation_timer
            
        if hasattr(self, "speaking_animation_frames"):
            del self.speaking_animation_frames
            
        if hasattr(self, "is_speaking_animation"):
            self.is_speaking_animation = False

        if self.current_bubble:
            self.current_bubble.close()
            self.current_bubble = None
            
        if self.is_chatgpt_responding:
            self.is_chatgpt_responding = False
            self.speech_timer.start(15000)

    def show_speech(self, message):
        """말풍선만 보여주기"""
        self.stop_current_speech()
        bubble = SpeechBubble(message, self, self.scale_factor, self.theme_manager)
        self.current_bubble = bubble
        self.bubbles.append(bubble)
        bubble.show()

        self.set_speaking_costume()
        QTimer.singleShot(4000, self.restore_costume)
        QTimer.singleShot(4000, lambda: self.remove_bubble(bubble))

    def remove_bubble(self, bubble):
        if bubble in self.bubbles:
            self.bubbles.remove(bubble)
        bubble.close()
        if self.current_bubble == bubble:
            self.current_bubble = None

    def say_grabbed_message(self):
        self.stop_current_speech()
        self.tts_handler.stop_speaking()
        
        if self.is_singing:
            self.stop_singing()

        messages = ["으아아악!", "이거 놔!", "놔줘!"]
        message = random.choice(messages)

        bubble = SpeechBubble(message, self, self.scale_factor, self.theme_manager)
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
        """더블클릭 시에도 노래 중이면 무시"""
        if not self.is_dragging and not self.is_chatgpt_responding and not self.song_mode_active:
            self.themed_say_hello()

    def end_drag(self):
        self.is_dragging = False
        self.speed_x = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        self.speed_y = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        self.apply_current_costume_state()
        self.update_character_direction()
        if self.current_bubble:
            self.current_bubble.close()
            self.current_bubble = None
        if not self.song_mode_active:  # 노래 모드가 아닐 때만 타이머 재시작
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
        hello_action.triggered.connect(self.themed_say_hello)

        # 한국어 음성 테스트 메뉴
        voice_test_action = menu.addAction("🎤 한국어 음성 테스트")
        voice_test_action.triggered.connect(lambda: self.show_speech_with_tts("한국어 음성 인식이 잘 작동하고 있어!"))

        menu.addSeparator()
        
        # 테마/의상 메뉴 - 확장된 버전
        theme_menu = menu.addMenu("👗 테마/의상 변경")
        
        themes = {
            "default": "🌟 기본 의상",
            "spring": "🌸 봄 의상",
            "summer": "🏖️ 여름 의상", 
            "autumn": "🍂 가을 의상",
            "winter": "❄️ 겨울 의상",
            "christmas": "🎄 크리스마스 의상", 
            "halloween": "🎃 할로윈 의상",
            "birthday": "🎂 생일 의상",
            "school": "📚 학교 의상",
            "cafe": "☕ 카페 의상",
            "night": "🌙 밤 의상",
            "sports": "💪 스포츠 의상",
            "gothic": "🖤 고딕 의상",
            "fantasy": "✨ 판타지 의상",
            "vintage": "🎭 빈티지 의상"
        }
        
        for theme_id, theme_name in themes.items():
            action = theme_menu.addAction(theme_name)
            action.triggered.connect(self.create_theme_changer(theme_id))
            
            if theme_id == self.theme_manager.current_theme:
                action.setText(f"✓ {theme_name}")
        
        theme_menu.addSeparator()
        
        auto_text = "🔄 자동 의상 변경 끄기" if self.theme_manager.auto_theme_enabled else "🔄 자동 의상 변경 켜기"
        auto_action = theme_menu.addAction(auto_text)
        auto_action.triggered.connect(self.toggle_auto_theme)
        
        menu.addSeparator()
        
        # 노래 메뉴 (레이첼 전용)
        song_menu = menu.addMenu("🎵 노래 (레이첼)")
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
            twinkle_action = song_menu.addAction("작은별")
            twinkle_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("작은별")))
            
            bear_action = song_menu.addAction("곰 세마리")
            bear_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("곰 세마리")))
            
            arirang_action = song_menu.addAction("아리랑")
            arirang_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("아리랑")))
            
            birthday_action = song_menu.addAction("생일축하")
            birthday_action.triggered.connect(lambda: self.start_singing(self.song_database.search_song("happy birthday")))

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
            tts_action = menu.addAction("🔊 레이첼 소리 끄기")
            tts_action.triggered.connect(lambda: self.toggle_tts_and_notify())
        else:
            tts_action = menu.addAction("🔇 레이첼 소리 켜기")
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
        
        # 현재 테마/의상 표시
        current_theme = self.theme_manager.get_current_theme_config()
        theme_status = menu.addAction(f"👗 현재 의상: {current_theme['name']}")
        theme_status.setEnabled(False)
        
        # 현재 크기 표시
        scale_status = menu.addAction(f"🔍 현재 크기: {self.scale_factor:.1f}배")
        scale_status.setEnabled(False)
        
        # 레이첼 음성으로 고정 표시
        voice_status = menu.addAction("🎤 음성: Rachel (고정)")
        voice_status.setEnabled(False)
        
        # 노래 상태 표시
        if self.is_singing:
            song_status = menu.addAction("🎵 노래 모드 (테마별 의상)")
            song_status.setEnabled(False)
        
        # ChatGPT 상태 표시
        if self.is_chatgpt_responding:
            status_action = menu.addAction("🤖 ChatGPT 응답 중...")
            status_action.setEnabled(False)
        elif self.chatgpt_handler and self.chatgpt_handler.client:
            status_action = menu.addAction("🤖 한국어 ChatGPT 연결됨")
            status_action.setEnabled(False)
        else:
            status_action = menu.addAction("❌ ChatGPT 연결 안됨")
            status_action.setEnabled(False)
            
        # TTS 상태 표시
        if self.tts_handler.api_key:
            tts_status_action = menu.addAction("🎤 레이첼 TTS 연결됨")
            tts_status_action.setEnabled(False)
        else:
            tts_status_action = menu.addAction("⚠️ Eleven Labs API 키 필요")
            tts_status_action.setEnabled(False)

        # 강화된 한국어 음성 인식 상태
        voice_recognition_status = menu.addAction("🇰🇷 강화된 한국어 전용 인식")
        voice_recognition_status.setEnabled(False)

        # 자동 테마 전환 상태 표시
        auto_theme_status = "켜짐" if self.theme_manager.auto_theme_enabled else "꺼짐"
        auto_status_action = menu.addAction(f"🔄 자동 의상 변경: {auto_theme_status}")
        auto_status_action.setEnabled(False)

        menu.addSeparator()
        quit_action = menu.addAction("종료 ❌")
        quit_action.triggered.connect(self.close)

        menu.exec_(position)

    def create_theme_changer(self, theme_id):
        """테마 변경 함수 생성"""
        def change_theme():
            self.theme_manager.set_theme(theme_id)
        return change_theme
    
    def toggle_auto_theme(self):
        """자동 테마 전환 토글"""
        auto_status = self.theme_manager.toggle_auto_theme()
        status_text = "켰어" if auto_status else "껐어"
        self.show_speech_with_tts(f"자동 의상 변경을 {status_text}!")

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
            self.show_speech_with_tts("레이첼 소리를 다시 켤게!")
        else:
            self.show_speech("레이첼 소리를 껐어! 🔇")

    def closeEvent(self, event):
        """프로그램 종료시 정리"""
        if hasattr(self, 'voice_recognizer') and self.voice_recognizer:
            self.voice_recognizer.stop_listening()
        if hasattr(self, 'tts_handler'):
            self.tts_handler.stop_speaking()
        
        if self.is_singing:
            self.stop_singing()
        
        # 모든 이펙트 정리
        for effect in self.walking_effects:
            if effect:
                effect.close()
        self.walking_effects.clear()
        
        for note in self.music_notes:
            if note:
                note.close()
        self.music_notes.clear()
        
        for particle in self.themed_particles:
            if particle:
                particle.close()
        self.themed_particles.clear()
        
        event.accept()


class SpeechBubble(QWidget):
    def __init__(self, message, char_widget, scale_factor=1.0, theme_manager=None):
        super().__init__()
        self.message = message
        self.char_widget = char_widget
        self.scale_factor = scale_factor
        self.theme_manager = theme_manager
        
        # 메시지 길이에 따라 말풍선 크기 동적 조정
        base_width = 200
        base_height = 70
        
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

        # 테마별 색상 가져오기
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_config()["colors"]
            bubble_color = theme_colors["bubble_bg"]
            border_color = theme_colors["bubble_border"]
            shadow_color = theme_colors["bubble_shadow"]
        else:
            bubble_color = QColor(240, 255, 245, 240)
            border_color = QColor(152, 251, 152)
            shadow_color = QColor(34, 139, 34, 30)

        # 노래 중일 때는 특별한 색상
        if hasattr(self.char_widget, 'song_mode_active') and self.char_widget.song_mode_active:
            bubble_color = QColor(255, 240, 255, 240)  # 연한 보라색
            border_color = QColor(186, 85, 211)  # 보라색
            shadow_color = QColor(138, 43, 226, 30)  # 진한 보라색 그림자

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

        # 테마별 텍스트 색상
        if self.theme_manager and self.theme_manager.current_theme == "halloween":
            text_color = QColor(255, 255, 255)
        else:
            text_color = QColor(50, 90, 50)
            
        painter.setPen(text_color)
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

    if OPENAI_AVAILABLE:
        print("✅ OpenAI 라이브러리가 설치되어 있습니다.")
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print("✅ OpenAI API 키가 설정되어 있습니다.")
        else:
            print("⚠️  OpenAI API 키가 설정되지 않았습니다.")
    else:
        print("⚠️  OpenAI 라이브러리가 설치되지 않았습니다.")

    if ELEVENLABS_API_KEY:
        print("✅ Eleven Labs API 키가 설정되어 있습니다.")
        print("🎤 레이첼(Rachel) 목소리로 TTS가 작동합니다! (고정)")
    else:
        print("⚠️  Eleven Labs API 키가 설정되지 않았습니다.")

    print("\n👗 테마별 의상 시스템 (15가지):")
    print("• 🌟 기본 의상 - 깔끔한 기본 의상")
    print("• 🌸 봄 의상 - 분홍 테마, 꽃잎 효과")
    print("• 🏖️ 여름 의상 - 파란 테마, 시원한 느낌")
    print("• 🍂 가을 의상 - 갈색 테마, 낙엽 효과")
    print("• ❄️ 겨울 의상 - 하얀 테마, 눈 효과")
    print("• 🎄 크리스마스 의상 - 빨간 테마, 크리스마스 분위기")
    print("• 🎃 할로윈 의상 - 어두운 테마, 할로윈 분위기")
    print("• 🎂 생일 의상 - 파티 테마, 색종이 효과")
    print("• 📚 학교 의상 - 학생복, 공부 분위기")
    print("• ☕ 카페 의상 - 갈색 테마, 카페 분위기")
    print("• 🌙 밤 의상 - 어두운 파란색, 별 효과")
    print("• 💪 스포츠 의상 - 활동적인 의상")
    print("• 🖤 고딕 의상 - 검은색 테마, 신비로운 분위기")
    print("• ✨ 판타지 의상 - 마법 테마, 판타지 분위기")
    print("• 🎭 빈티지 의상 - 클래식한 복고 스타일")

    print("\n📂 의상 이미지 파일 구조:")
    print("방법 1 - 개별 파일:")
    print("  character_default.png, grab_default.png")
    print("  speaking1_default.png, speaking2_default.png, singing_default.png")
    print("  character_christmas.png, grab_christmas.png, ...")
    print("방법 2 - 폴더 구조:")
    print("  costumes/default/character.png, grab.png")
    print("  costumes/default/speaking1.png, speaking2.png, singing.png")
    print("  costumes/christmas/, costumes/halloween/, ...")

    print("\n🎭 의상 종류:")
    print("• character - 평상시 의상")
    print("• grab - 잡힐 때 의상 (없으면 어둡게 처리)")
    print("• speaking1, speaking2 - 말할 때 애니메이션 의상 (2개)")
    print("• singing - 노래할 때 의상 (1개 고정)")

    print("\n🔍 개선된 크기 조절 시스템:")
    print("• 즉시 크기 반영 (지연 없음)")
    print("• 의상 스케일링 개선")
    print("• 위치 자동 보정")
    print("• 애니메이션 상태 유지")
    print("• 테마별 의상 자동 적용")

    print("\n🇰🇷 강화된 한국어 전용 시스템:")
    print("• 한국어 전용 음성 인식 (영어 차단)")
    print("• 한국어 텍스트 필터링 시스템")
    print("• 엄격한 소음 패턴 차단")
    print("• 레이첼(Rachel) 목소리로 고정")
    print("• 한국어 우선 ChatGPT 응답")
    print("• 테마별 노래 의상 지원")

    print("\n🎵 테마별 노래 의상:")
    print("• 노래 시작시 테마별 노래 의상으로 변경")
    print("• singing1, singing2로 애니메이션")
    print("• 노래 종료시 기본 의상으로 복귀")
    print("• 테마마다 다른 노래 의상 지원")

    print("\n🎤 음성 명령어 (한국어만):")
    print("• '의상 바꿔' / '테마 바꿔' - 테마 변경")
    print("• '봄 의상' / '여름 의상' / '가을 의상' / '겨울 의상' - 계절 의상")
    print("• '크리스마스 의상' / '할로윈 의상' / '생일 의상' - 특별 의상")
    print("• '학교 의상' / '카페 의상' / '밤 의상' - 상황별 의상")
    print("• '스포츠 의상' / '고딕 의상' / '판타지 의상' - 스타일별 의상")
    print("• '노래 불러줘' - 랜덤 노래 (테마별 의상)")
    print("• '크게' / '작게' - 크기 조절")
    print("• '멈춰' / '움직여' - 움직임 제어")

    print("\n🔧 필요한 설정:")
    print("1. Eleven Labs API 키 (레이첼 TTS)")
    print("2. OpenAI API 키 (한국어 ChatGPT, 선택)")
    print("3. 마이크 권한 허용")
    print("4. 테마별 의상 이미지 파일 준비")

    print("\n✨ 말하기 2개, 노래 1개 의상 시스템:")
    print("• 👗 15가지 테마 × 4가지 의상 = 60개 이미지 파일")
    print("• 🎭 말하기: 2개 이미지로 애니메이션 (speaking1, speaking2)")
    print("• 🎵 노래: 1개 이미지로 고정 (singing)")
    print("• 🔄 지능형 자동 의상 변경 (계절/시간/특별일)")
    print("• 📐 크기 조절시 의상도 자동 스케일링")
    print("• 🎨 각 테마마다 고유한 색상과 파티클 효과")
    print("• 🌅 시간대별 자동 테마 (밤 시간대 등)")
    print("• 🗓️ 특별한 날 자동 의상 (크리스마스, 할로윈 등)")

    character = DesktopCharacter()
    character.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        try:
            tray_icon.setIcon(QIcon("character.png"))
        except:
            tray_icon.setIcon(app.style().standardIcon(app.style().SP_ComputerIcon))

        tray_icon.setToolTip("테마별 의상 시스템 - 레이첼 한국어 전용 데스크탑 캐릭터")
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