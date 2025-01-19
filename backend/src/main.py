from flask import Flask, render_template, request, jsonify
from prompt import prompt_theme_intro, prompt_a, prompt_b
from aio_straico import straico_client
import os
import json
import markdown
import bleach

app = Flask(__name__, static_folder='static', template_folder='../../frontend')
straico_api_key = os.getenv('STRAICO_API_KEY')

# Definiere erlaubte HTML-Tags und Attribute für die Sanitierung
ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    'p', 'pre', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br'
})
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
}


def generate_theme_intro(frage):
    """
    Generiert eine Antwort auf die gegebene Frage unter Verwendung des Sprachmodells.
    """
    llm_theme_intro = 'openai/gpt-4o-2024-08-06'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_theme_intro = client.prompt_completion(llm_theme_intro, prompt_theme_intro + frage)
        return reply_theme_intro


def generate_reply_a(diss_stream_md):
    """
    Generiert eine Antwort auf die gegebene Frage unter Verwendung des Sprachmodells.
    """
    llm_a = 'openai/gpt-4o-2024-08-06'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_a = client.prompt_completion(llm_a, diss_stream_md + prompt_a)
        return reply_a


def generate_reply_b(diss_stream_md):
    """
    Generiert eine Antwort auf die gegebene Frage unter Verwendung des Sprachmodells.
    """
    llm_b = 'openai/gpt-4o-2024-08-06'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_b = client.prompt_completion(llm_b, diss_stream_md + prompt_b)
        return reply_b


def convert_markdown_to_html(markdown_text):
    """
    Konvertiert Markdown in HTML und sanitisiert das Ergebnis.
    """
    # Konvertiere Markdown zu HTML
    html = markdown.markdown(markdown_text, extensions=['fenced_code', 'codehilite'])
    # Sanitisiere das HTML
    clean_html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return clean_html


import os
import json


def log_to_json(file_path, quest, disc_stream):
    """
    Speichert die Frage und die Diskussion in einer JSON-Datei.
    Erstellt den Pfad oder die Datei, falls diese nicht existieren.
    """
    log_entry = {
        "question": quest,
        "discussion": disc_stream,
    }

    # Extrahiere das Verzeichnis aus dem file_path
    directory = os.path.dirname(file_path)

    # Erstelle das Verzeichnis, falls es nicht existiert
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []

    data.append(log_entry)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


@app.route('/', methods=['GET'])
def index():
    """
    Render die Hauptseite der Anwendung.
    """
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask():
    """
    Verarbeitung der AJAX-Anfrage zur Beantwortung einer Frage.
    """
    data = request.get_json()
    frage = data.get('frage', '')
    disc_stream = ""
    responses = []

    if frage:
        print("frage:", frage)

        # Generiere das Diskussionsthema
        reply_theme_intro = generate_theme_intro(frage)
        reply_theme_intro_md = "#### Diskussionsthema: " + reply_theme_intro['completion']['choices'][0]['message'][
            'content']
        reply_theme_intro_html = convert_markdown_to_html(reply_theme_intro_md)
        disc_stream += reply_theme_intro_md
        responses.append(reply_theme_intro_html)
        print("reply_theme_intro_md: ", reply_theme_intro_md)

        # Generiere Antwort A
        reply_a = generate_reply_a(disc_stream)
        reply_a_md = "#### Beitrag bibeltreu: " + reply_a['completion']['choices'][0]['message']['content']
        reply_a_html = convert_markdown_to_html(reply_a_md)
        disc_stream += reply_a_md
        responses.append(reply_a_html)
        print("reply_a_md:", reply_a_md)

        # Generiere Antwort B
        reply_b = generate_reply_b(disc_stream)
        reply_b_md = "#### Beitrag historisch-kritisch: " + reply_b['completion']['choices'][0]['message']['content']
        reply_b_html = convert_markdown_to_html(reply_b_md)
        disc_stream += reply_b_md
        responses.append(reply_b_html)
        print("reply_b_md:", reply_b_md)

        # Logge die Daten (optional kannst du hier die Markdown- oder HTML-Antwort loggen)
        log_to_json('../../log/llm_talk_log.json', frage, disc_stream)

        # Rückgabe der Antworten als Liste
        return jsonify({
            'responses': responses
        })

    return jsonify({'antwort': 'Keine Frage gestellt.'}), 400


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
