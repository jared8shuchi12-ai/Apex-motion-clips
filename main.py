import os
import tempfile
import uuid
from fastapi import FastAPI, HTTPException
import ffmpeg
import yt_dlp
import imageio_ffmpeg

os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI(title="Apex Motion Split-Screen Engine")

def resolve_media_source(source_url_or_path: str, output_path: str) -> str:
    if source_url_or_path.startswith("http://") or source_url_or_path.startswith("https://"):
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'overwrites': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source_url_or_path])
        return output_path
    
    if os.path.exists(source_url_or_path):
        return source_url_or_path
    
    raise FileNotFoundError(f"Source file or URL not found: {source_url_or_path}")

@app.get("/")
def home():
    return {"message": "Apex Motion Clipper engine is running!"}

@app.post("/clip")
def create_split_screen(
    top_video_source: str,
    bottom_gameplay_source: str,
    output_filename: str = "output_split.mp4",
    duration: int = 15
):
    temp_dir = tempfile.gettempdir()
    unique_id = str(uuid.uuid4())[:8]

    local_top_path = os.path.join(temp_dir, f"top_{unique_id}.mp4")
    local_bottom_path = os.path.join(temp_dir, f"bottom_{unique_id}.mp4")
    final_output_path = os.path.join(temp_dir, f"{unique_id}_{output_filename}")

    try:
        resolved_top = resolve_media_source(top_video_source, local_top_path)
        resolved_bottom = resolve_media_source(bottom_gameplay_source, local_bottom_path)

        top_input = ffmpeg.input(resolved_top, t=duration)
        bottom_input = ffmpeg.input(resolved_bottom, t=duration)

        top_scaled = (
            top_input.video
            .filter('scale', 1080, 960, force_original_aspect_ratio='increase')
            .filter('crop', 1080, 960)
        )

        bottom_scaled = (
            bottom_input.video
            .filter('scale', 1080, 960, force_original_aspect_ratio='increase')
            .filter('crop', 1080, 960)
        )

        stacked = ffmpeg.filter([top_scaled, bottom_scaled], 'vstack')

        ffmpeg_cmd = ffmpeg.output(
            stacked,
            top_input.audio,
            final_output_path,
            vcodec='libx264',
            acodec='aac',
            preset='fast'
        )

        ffmpeg_cmd.run(cmd=imageio_ffmpeg.get_ffmpeg_exe(), overwrite_output=True)

        return {
            "status": "success",
            "file": final_output_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(local_top_path):
            os.remove(local_top_path)
        if os.path.exists(local_bottom_path):
            os.remove(local_bottom_path)
      
