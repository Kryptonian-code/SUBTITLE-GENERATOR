import os
import json
import requests
import pysrt
from utils.opensubtitles_client import OpenSubtitlesClient

CONFIG_PATH = 'config.json'
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

OS_CLIENT = OpenSubtitlesClient(CONFIG.get('OPEN_SUBTITLES_API_KEY'))

def find_official_subs(title, year=None, language='en'):
    results = OS_CLIENT.search_subtitles(title, year, language)
    if not results:
        return None
    for r in results:
        if year and 'Year' in r and str(r.get('Year')) == str(year):
            content = OS_CLIENT.download_subtitle(r)
            if content:
                return content
    return OS_CLIENT.download_subtitle(results[0])

def synthesize_from_plot(title, year=None, language='en'):
    omdb_key = CONFIG.get('OMDB_API_KEY')
    if not omdb_key:
        raise RuntimeError('OMDb API key required')
    params = {'t': title, 'y': year, 'apikey': omdb_key}
    r = requests.get('http://www.omdbapi.com/', params=params, timeout=10)
    if r.status_code != 200:
        raise RuntimeError('OMDb request failed')
    data = r.json()
    plot = data.get('Plot') or ''
    words = plot.split()
    chunk_size = 10
    subs = pysrt.SubRipFile()
    start_seconds = 0.0
    index = 1
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        start = start_seconds
        end = start_seconds + 3.5
        s = pysrt.SubRipItem(index=index,
                             start=pysrt.SubRipTime(seconds=int(start), milliseconds=int((start - int(start)) * 1000)),
                             end=pysrt.SubRipTime(seconds=int(end), milliseconds=int((end - int(end)) * 1000)),
                             text=chunk)
        subs.append(s)
        index += 1
        start_seconds = end
    return subs.to_string()

def asr_from_trailer(title, year=None, language='en'):
    if not CONFIG.get('ENABLE_WHISPER_FALLBACK'):
        return None
    import subprocess
    import tempfile
    import whisper
    model = CONFIG.get('WHISPER_MODEL', 'small')
    query = f"ytsearch1:{title} {year or ''} trailer"
    tmp_dir = tempfile.mkdtemp()
    out_template = os.path.join(tmp_dir, 'audio.%(ext)s')
    subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '-o', out_template, query], check=True)
    audio_file = None
    for f in os.listdir(tmp_dir):
        if f.endswith('.mp3') or f.endswith('.m4a'):
            audio_file = os.path.join(tmp_dir, f)
            break
    if not audio_file:
        return None
    w = whisper.load_model(model)
    result = w.transcribe(audio_file, language=language)
    segments = result.get('segments', [])
    subs = pysrt.SubRipFile()
    for i, seg in enumerate(segments, start=1):
        start = seg['start']
        end = seg['end']
        text = seg['text'].strip()
        s = pysrt.SubRipItem(index=i,
                             start=pysrt.SubRipTime(seconds=int(start), milliseconds=int((start - int(start)) * 1000)),
                             end=pysrt.SubRipTime(seconds=int(end), milliseconds=int((end - int(end)) * 1000)),
                             text=text)
        subs.append(s)
    return subs.to_string()

def generate_subtitles(title, year=None, language='en'):
    official = find_official_subs(title, year, language)
    if official:
        return official
    asr = asr_from_trailer(title, year, language)
    if asr:
        return asr
    return synthesize_from_plot(title, year, language)
