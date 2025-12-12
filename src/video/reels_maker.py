import os
from pathlib import Path
from typing import List
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Configure ImageMagick path for Windows
imagemagick_path = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
if os.path.exists(imagemagick_path):
    os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path

from moviepy.editor import *
from moviepy.video.fx.all import resize
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReelsMaker:
    def __init__(self):
        self.width = 1080
        self.height = 1920
        self.duration_per_image = 3.0
        self.transition_duration = 0.5
        self.fps = 24
        
        # 폰트 경로 확인 (프로젝트 루트의 font.ttf)
        self.font_path = "font.ttf"
        if not os.path.exists(self.font_path):
            logger.warning(f"Font file not found at {self.font_path}. Text might not render correctly or will use default.")
            self.font_path = None # None이면 MoviePy 기본값(ImageMagick 검색) 사용

    def make_reels(self, image_paths: List[str], text: str, output_filename: str):
        """
        이미지 리스트와 자막을 입력받아 릴스 영상을 생성합니다.
        - Ken Burns 효과 (Zoom-in)
        - Crossfade Transition
        - 자막 오버레이
        - 오디오 없음
        """
        if not image_paths:
            logger.error("No images provided for Reels.")
            return None

        # 1. 이미지 클립 생성 및 효과 적용
        clips = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                continue
                
            # 이미지 로드
            clip = ImageClip(img_path)
            
            # A. 9:16 비율에 맞춰 center crop 및 resize
            # 먼저 화면을 꽉 채우도록 비율 유지 리사이즈
            img_w, img_h = clip.size
            target_ratio = self.width / self.height
            img_ratio = img_w / img_h
            
            if img_ratio > target_ratio:
                # 이미지가 더 넓음 -> 높이를 1920에 맞춤
                clip = clip.resize(height=self.height)
            else:
                # 이미지가 더 길거나 같음 -> 너비를 1080에 맞춤
                clip = clip.resize(width=self.width)
                
            # 중앙 크롭 (정확히 1080x1920으로)
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=self.width, height=self.height)
            
            # B. Duration 설정
            clip = clip.set_duration(self.duration_per_image)
            
            # C. Ken Burns Effect (Zoom In 1.0 -> 1.05)
            # lambda t: 1 + 0.05 * (t / duration)
            # resize는 계산 비용이 높으므로, 미리 큰 이미지를 잘라내거나 해야 하지만,
            # 여기서는 편의상 moviepy의 resize 변환을 사용 (다소 느릴 수 있음)
            clip = clip.resize(lambda t: 1 + 0.05 * (t / self.duration_per_image))
            
            # D. Center Zoom을 위해 다시 Composition (화면 중앙 고정)
            # 크기가 커지면 중심이 어긋날 수 있으므로 'center' 위치 고정
            clip = clip.set_position(('center', 'center'))
            
            # E. Transition을 위한 Crossfade In
            # 첫 클립 제외하고 fade in 적용? 
            # concatenate_videoclips의 method='compose'와 padding을 사용할 것이므로
            # 개별 클립에 fadein을 걸어주면 겹치는 부분에서 효과가 남.
            clip = clip.crossfadein(self.transition_duration)
            
            clips.append(clip)

        if not clips:
            logger.error("No valid clips created.")
            return None

        # 2. 클립 연결 (Transition)
        # padding = -transition_duration (겹치게 함)
        video = concatenate_videoclips(clips, method="compose", padding=-self.transition_duration)
        
        # 마지막 클립의 길이가 겹침으로 인해 줄어드는 것 보정은 moviepy가 자동 처리하지만,
        # 전체 길이를 확인해볼 필요는 있음.
        
        # Ken Burns Resize로 인해 캔버스보다 커진 화면을 1080x1920으로 잘라내기 위해
        # CompositeVideoClip으로 감싸고 size를 지정
        video = CompositeVideoClip([video], size=(self.width, self.height))


        # 3. 자막 (Text Overlay)
        if text:
            # 폰트 설정
            font_to_use = self.font_path if self.font_path else 'Arial-Bold'
            
            # TextClip 생성
            # stroke_color='black', stroke_width=2 (테두리)
            # 그림자는 별도 클립으로 뒤에 깔아야 함 (MoviePy는 shadow 직접 지원 X)
            
            # 메인 자막
            txt_clip = TextClip(
                text,
                font=font_to_use,
                fontsize=70,
                color='white',
                stroke_color='black',
                stroke_width=2,
                method='caption', # 자동 줄바꿈
                size=(self.width - 100, None), # 좌우 여백 50씩
                align='South', # 하단 정렬
            )
            
            # 그림자 (검은색, 투명도 조절은 어려우니 그냥 검은색)
            shadow_clip = TextClip(
                text,
                font=font_to_use,
                fontsize=70,
                color='black',
                method='caption',
                size=(self.width - 100, None),
                align='South',
            ).set_opacity(0.6)
            
            # 위치 설정 (하단에서 200px 띄움)
            # 'bottom'은 화면 끝, margin을 주려면 ('center', height-200) 식으로 좌표 계산 필요
            # relative position: ('center', 0.8) -> 상단 80% 지점 (하단 근처)
            
            txt_y_pos = self.height - 300
            
            txt_clip = txt_clip.set_position(('center', txt_y_pos)).set_duration(video.duration)
            shadow_clip = shadow_clip.set_position(('center', txt_y_pos + 5)).set_duration(video.duration) # 5px offset
            
            # 영상 위에 자막 합성
            video = CompositeVideoClip([video, shadow_clip, txt_clip], size=(self.width, self.height))

        # 4. 렌더링 (무음)
        logger.info(f"Rendering Reels to {output_filename}...")
        
        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        video.write_videofile(
            output_filename,
            fps=self.fps,
            codec='libx264',
            audio=False,
            threads=4,
            preset='medium' # 인코딩 속도/화질 타협
        )
        logger.info("Rendering complete.")
        
        return output_filename

if __name__ == "__main__":
    # Test Logic
    maker = ReelsMaker()
    
    # Test Images (Make sure these exist or skip)
    test_images = [
        "data/temp_images/test_01.jpg", 
        "data/temp_images/test_02.jpg"
    ]
    
    # Dummy file generation for testing if not exists
    if not os.path.exists("data/temp_images"):
        os.makedirs("data/temp_images")
        
    # We can't easily generate dummy images here without PIL, 
    # but assuming user will run main.py integration mostly.
    # Just print setup.
    print("ReelsMaker intialized.")
