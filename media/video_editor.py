"""
動画自動編集モジュール
トレンド分析を活用してジャンル別に最適な編集を適用
"""
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import json
import shutil

from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class EditingStyle:
    """編集スタイル設定"""
    name: str
    # カット設定
    intro_duration: float = 3.0  # イントロ秒数
    outro_duration: float = 3.0  # アウトロ秒数
    max_clip_duration: float = 30.0  # 最大クリップ長
    # エフェクト
    fade_in: float = 0.5
    fade_out: float = 0.5
    speed_factor: float = 1.0  # 再生速度
    # 音声
    background_music: bool = False
    music_volume: float = 0.3
    # テキスト
    add_captions: bool = False
    # フィルター
    color_correction: str = ""  # FFmpegフィルター


# ジャンル別編集スタイル
EDITING_STYLES = {
    "tech": EditingStyle(
        name="tech",
        intro_duration=2.0,
        max_clip_duration=45.0,
        speed_factor=1.1,
        color_correction="eq=contrast=1.1:brightness=0.05"
    ),
    "vlog": EditingStyle(
        name="vlog", 
        intro_duration=3.0,
        fade_in=1.0,
        fade_out=1.0,
        background_music=True,
        color_correction="curves=vintage"
    ),
    "gaming": EditingStyle(
        name="gaming",
        intro_duration=1.0,
        max_clip_duration=20.0,
        speed_factor=1.2,
        color_correction="eq=saturation=1.3:contrast=1.2"
    ),
    "education": EditingStyle(
        name="education",
        intro_duration=5.0,
        max_clip_duration=60.0,
        speed_factor=1.0,
        add_captions=True
    ),
    "short": EditingStyle(
        name="short",
        intro_duration=0.5,
        outro_duration=0.5,
        max_clip_duration=15.0,
        speed_factor=1.3,
        fade_in=0.3,
        fade_out=0.3
    )
}


class VideoEditor:
    """
    動画自動編集クライアント
    FFmpegを使用してジャンル/プラットフォーム別に最適化
    """
    
    def __init__(self):
        config = get_config()
        self.output_dir = config.project_root / "media" / "edited"
        self.temp_dir = config.project_root / "media" / "temp"
        ensure_dir(self.output_dir)
        ensure_dir(self.temp_dir)
        
        # FFmpeg確認
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        logger.info("VideoEditor initialized")
    
    def detect_genre(self, video_path: Path) -> str:
        """
        動画のジャンルを推測（メタデータ/ファイル名から）
        将来的にはAIで内容分析も可能
        """
        name = video_path.stem.lower()
        
        if any(w in name for w in ["game", "play", "gaming", "ゲーム"]):
            return "gaming"
        elif any(w in name for w in ["vlog", "日常", "travel", "旅"]):
            return "vlog"
        elif any(w in name for w in ["tutorial", "講座", "解説", "教育"]):
            return "education"
        elif any(w in name for w in ["short", "shorts", "tiktok", "reel"]):
            return "short"
        else:
            return "tech"  # デフォルト
    
    def get_video_info(self, video_path: Path) -> dict:
        """動画のメタ情報を取得"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffprobe failed: {result.stderr}")
            return {}
        
        return json.loads(result.stdout)
    
    def edit_video(
        self,
        input_path: Path,
        output_format: str = "both",  # "horizontal", "vertical", "both"
        genre: Optional[str] = None,
        custom_style: Optional[EditingStyle] = None
    ) -> List[Path]:
        """
        動画を編集
        
        Args:
            input_path: 入力動画パス
            output_format: 出力形式 (horizontal=16:9, vertical=9:16, both=両方)
            genre: ジャンル (auto=自動検出)
            custom_style: カスタム編集スタイル
        
        Returns:
            出力ファイルパスのリスト
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Video not found: {input_path}")
        
        # ジャンル検出
        if genre is None:
            genre = self.detect_genre(input_path)
        
        style = custom_style or EDITING_STYLES.get(genre, EDITING_STYLES["tech"])
        logger.info(f"Editing video: {input_path.name} (genre: {genre})")
        
        outputs = []
        timestamp = get_timestamp()
        
        # 横動画 (16:9)
        if output_format in ["horizontal", "both"]:
            output_h = self.output_dir / f"{input_path.stem}_{timestamp}_16x9.mp4"
            self._apply_edits(input_path, output_h, style, aspect="16:9")
            outputs.append(output_h)
        
        # 縦動画 (9:16)
        if output_format in ["vertical", "both"]:
            output_v = self.output_dir / f"{input_path.stem}_{timestamp}_9x16.mp4"
            self._apply_edits(input_path, output_v, style, aspect="9:16")
            outputs.append(output_v)
        
        return outputs
    
    def _apply_edits(
        self,
        input_path: Path,
        output_path: Path,
        style: EditingStyle,
        aspect: str = "16:9"
    ):
        """FFmpegで編集を適用"""
        
        # アスペクト比設定
        if aspect == "16:9":
            scale = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        else:  # 9:16
            scale = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        
        # フィルターチェーン構築
        filters = [scale]
        
        # 速度調整
        if style.speed_factor != 1.0:
            filters.append(f"setpts={1/style.speed_factor}*PTS")
        
        # 色補正
        if style.color_correction:
            filters.append(style.color_correction)
        
        # フェード
        if style.fade_in > 0:
            filters.append(f"fade=t=in:st=0:d={style.fade_in}")
        if style.fade_out > 0:
            filters.append(f"fade=t=out:st={style.max_clip_duration - style.fade_out}:d={style.fade_out}")
        
        filter_complex = ",".join(filters)
        
        # 音声フィルター
        audio_filters = []
        if style.speed_factor != 1.0:
            audio_filters.append(f"atempo={style.speed_factor}")
        
        audio_filter = ",".join(audio_filters) if audio_filters else "anull"
        
        # FFmpegコマンド
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-t", str(style.max_clip_duration),
            "-vf", filter_complex,
            "-af", audio_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path)
        ]
        
        logger.info(f"Running FFmpeg: {aspect}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg failed for {aspect}")
        
        logger.info(f"Output saved: {output_path}")
    
    def batch_edit(
        self,
        input_dir: Path,
        output_format: str = "both"
    ) -> List[Path]:
        """フォルダ内の全動画を編集"""
        input_dir = Path(input_dir)
        all_outputs = []
        
        video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        
        for video_file in input_dir.iterdir():
            if video_file.suffix.lower() in video_extensions:
                try:
                    outputs = self.edit_video(video_file, output_format)
                    all_outputs.extend(outputs)
                except Exception as e:
                    logger.error(f"Failed to edit {video_file}: {e}")
        
        return all_outputs


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="動画自動編集")
    parser.add_argument("input", type=str, help="入力動画パス or フォルダ")
    parser.add_argument("--format", choices=["horizontal", "vertical", "both"], 
                        default="both", help="出力形式")
    parser.add_argument("--genre", choices=list(EDITING_STYLES.keys()),
                        help="ジャンル（省略時は自動検出）")
    
    args = parser.parse_args()
    
    editor = VideoEditor()
    input_path = Path(args.input)
    
    if input_path.is_dir():
        outputs = editor.batch_edit(input_path, args.format)
    else:
        outputs = editor.edit_video(input_path, args.format, args.genre)
    
    print(f"\n編集完了: {len(outputs)} ファイル")
    for out in outputs:
        print(f"  - {out}")
