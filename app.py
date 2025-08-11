from flask import Flask, render_template, request, send_file, jsonify
import io
from subs_generator import generate_subtitles

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or request.form
    title = data.get('title')
    year = data.get('year')
    language = data.get('language', 'en')
    if not title:
        return jsonify({'error': 'title required'}), 400
    try:
        srt_text = generate_subtitles(title, year, language)
        if not srt_text:
            return jsonify({'error': 'no subtitles could be produced'}), 500
        return send_file(
            io.BytesIO(srt_text.encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"{title.replace(' ', '_')}_{year or 'unknown'}.srt"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
