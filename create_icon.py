#!/usr/bin/env python3
"""
Ltorrent용 아이콘 생성 스크립트
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_torrent_icon():
    """토렌트 앱 아이콘 생성"""
    # 다양한 크기로 아이콘 생성
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    images = []
    
    for size in sizes:
        # 새 이미지 생성 (투명 배경)
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 배경 원 그리기 (토렌트 테마 색상)
        margin = size // 8
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=(45, 85, 255, 255), outline=(30, 60, 200, 255), width=max(1, size//64))
        
        # 다운로드 화살표 그리기
        arrow_size = size // 3
        center_x, center_y = size // 2, size // 2
        
        # 화살표 모양 좌표
        arrow_points = [
            (center_x, center_y - arrow_size//2),  # 위쪽 점
            (center_x - arrow_size//3, center_y),  # 왼쪽 점
            (center_x - arrow_size//6, center_y),  # 왼쪽 안쪽
            (center_x - arrow_size//6, center_y + arrow_size//2),  # 왼쪽 아래
            (center_x + arrow_size//6, center_y + arrow_size//2),  # 오른쪽 아래
            (center_x + arrow_size//6, center_y),  # 오른쪽 안쪽
            (center_x + arrow_size//3, center_y),  # 오른쪽 점
        ]
        
        draw.polygon(arrow_points, fill=(255, 255, 255, 255))
        
        # 'T' 문자 추가 (작은 크기에서는 생략)
        if size >= 64:
            try:
                font_size = size // 8
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                draw.text((center_x + arrow_size//2, center_y - arrow_size//2), 'T', 
                         fill=(255, 255, 255, 255), font=font, anchor='mm')
            except:
                pass  # 폰트 로드 실패 시 무시
        
        images.append(img)
    
    # ICNS 파일로 저장 (macOS 아이콘 형식)
    if images:
        images[0].save('icon.icns', format='ICNS', 
                      sizes=[(img.size[0], img.size[1]) for img in images])
        print("✅ icon.icns 파일이 생성되었습니다!")
    
    # PNG 파일로도 저장 (미리보기용)
    if images:
        images[-1].save('icon.png')
        print("✅ icon.png 파일이 생성되었습니다!")

if __name__ == "__main__":
    try:
        create_torrent_icon()
    except ImportError:
        print("❌ Pillow 라이브러리가 필요합니다. 'pip install Pillow' 명령으로 설치하세요.")
    except Exception as e:
        print(f"❌ 아이콘 생성 중 오류 발생: {e}")
        print("💡 기본 아이콘 없이 앱을 빌드할 수도 있습니다.") 