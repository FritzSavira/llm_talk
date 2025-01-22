from flask import Flask, render_template, request, jsonify, Response
from prompt import prompt_theme_intro, persona_a, prompt_a, persona_b, prompt_b, prompt_tag
from aio_straico import straico_client
import os
import json
import markdown
import bleach
import time
import random



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


def generate_reply_a(disc_stream_md):
    """
    Generiert eine Antwort auf die gegebene Frage unter Verwendung des Sprachmodells.
    """
    llm_a = 'openai/o1-preview'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_a = client.prompt_completion(llm_a, disc_stream_md + prompt_a)
        return reply_a


def generate_reply_b(disc_stream_md):
    """
    Generiert eine Antwort auf die gegebene Frage unter Verwendung des Sprachmodells.
    """
    llm_b = 'openai/o1-preview'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_b = client.prompt_completion(llm_b, disc_stream_md + prompt_b)
        return reply_b

def generate_reply_tag(reply_md):
    """
    Findet Tags für die Antwort unter Verwendung des Sprachmodells.
    """
    llm_tag = 'openai/gpt-4o-2024-08-06'
    with straico_client(API_KEY=straico_api_key) as client:
        reply_tag = client.prompt_completion(llm_tag, prompt_tag + reply_md)
        return reply_tag


def convert_markdown_to_html(markdown_text):
    """
    Konvertiert Markdown in HTML und sanitisiert das Ergebnis.
    """
    # Konvertiere Markdown zu HTML
    html = markdown.markdown(markdown_text, extensions=['fenced_code', 'codehilite'])
    # Sanitisiere das HTML
    clean_html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return clean_html


def log_to_json(file_path, id, quest, disc_stream):
    """
    Speichert die Frage und die Diskussion in einer JSON-Datei.
    Erstellt den Pfad oder die Datei, falls diese nicht existieren.
    """
    log_entry = {
        "id": id,
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


def generate_unique_id():
    timestamp = int(time.time())
    random_part = random.randint(1000, 9999)
    return f"{timestamp}_{random_part}"



@app.route('/', methods=['GET'])
def index():
    """
    Render die Hauptseite der Anwendung.
    """
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    frage = data.get('frage', '')
    disc_stream = ""
    id = generate_unique_id()


    if frage:

        def generate():
            nonlocal disc_stream  # Erlaubt die Modifikation von disc_stream innerhalb der Funktion

            try:
                # Generiere das Diskussionsthema
                reply_theme_intro = generate_theme_intro(frage)
                reply_theme_intro_md = reply_theme_intro['completion']['choices'][0]['message']['content']
                reply_theme_intro_html = convert_markdown_to_html(reply_theme_intro_md)

                # Generiere Parameter zum Diskussionsthema
                reply_theme_intro_model = reply_theme_intro['completion']['model']
                reply_theme_intro_price = reply_theme_intro['price']
                reply_theme_intro_words = reply_theme_intro['words']

                # Generiere Tags zum Diskussionsthema
                reply_tag = generate_reply_tag(reply_theme_intro_md)
                reply_tag_md = reply_tag['completion']['choices'][0]['message']['content']
                reply_tag_html = convert_markdown_to_html(reply_tag_md)

                # Generiere Parameter zu den Tags des Diskussionsthemas
                reply_theme_intro_tag_model = reply_tag['completion']['model']
                reply_theme_intro_tag_price = reply_tag['price']
                reply_theme_intro_tag_words = reply_tag['words']

                yield json.dumps({'html': reply_theme_intro_html}) + '\n'
                yield json.dumps({'html': reply_tag_html}) + '\n'

                if "mögen berufenere sich des themas annehmen." in reply_theme_intro_md.lower():
                    return

                disc_stream += reply_theme_intro_md


                # Initialisiere den Abwechselungsindikator
                is_a_turn = True

                # Schleife für abwechselnde Antworten
                max_iterations = 4
                iteration = 0

                while iteration < max_iterations:
                    if is_a_turn:
                        # Generiere Antwort A
                        reply_a = generate_reply_a(disc_stream)
                        reply_a_md = "#### Beitrag bibeltreu: " + "\n" + reply_a['completion']['choices'][0]['message']['content']
                        reply_a_html = convert_markdown_to_html(reply_a_md)

                        # Generiere Parameter zu der Antwort A
                        reply_a_model = reply_a['completion']['model']
                        reply_a_price = reply_a['price']
                        reply_a_words = reply_a['words']

                        reply_tag = generate_reply_tag(reply_a_md)
                        reply_tag_md = "*Tags: *" + reply_tag['completion']['choices'][0]['message']['content']
                        reply_tag_html = convert_markdown_to_html(reply_tag_md)

                        # Generiere Parameter zu den Tags der Antwort A
                        reply_a_tag_model = reply_tag['completion']['model']
                        reply_a_tag_price = reply_tag['price']
                        reply_a_tag_words = reply_tag['words']

                        yield json.dumps({'html': reply_a_html}) + '\n'
                        yield json.dumps({'html': reply_tag_html}) + '\n'
                        disc_stream += reply_a_md

                    else:
                        # Generiere Antwort B
                        reply_b = generate_reply_b(disc_stream)
                        reply_b_md = "#### Beitrag historisch-kritisch: " + "\n" + reply_b['completion']['choices'][0]['message']['content']
                        reply_b_html = convert_markdown_to_html(reply_b_md)

                        # Generiere Parameter zu der Antwort B
                        reply_b_model = reply_b['completion']['model']
                        reply_b_created = reply_b['completion']['created']
                        reply_b_price = reply_b['price']
                        reply_b_words = reply_b['words']

                        reply_tag = generate_reply_tag(reply_b_md)
                        reply_tag_md = "*Tags: *" + reply_tag['completion']['choices'][0]['message']['content']
                        reply_tag_html = convert_markdown_to_html(reply_tag_md)

                        # Generiere Parameter zu den Tags der Antwort B
                        reply_b_tag_model = reply_tag['completion']['model']
                        reply_b_tag_created = reply_tag['completion']['created']
                        reply_b_tag_price = reply_tag['price']
                        reply_b_tag_words = reply_tag['words']

                        yield json.dumps({'html': reply_b_html}) + '\n'
                        yield json.dumps({'html': reply_tag_html}) + '\n'
                        disc_stream += reply_b_md

                    # Wechsle die Runde
                    is_a_turn = not is_a_turn
                    iteration += 1

            except GeneratorExit:
                # Handle the client disconnecting
                print("Client hat die Verbindung getrennt.")
            finally:
                # Logge die Daten, wenn die Schleife endet
                log_to_json('../../log/llm_talk_log.json', id, frage, disc_stream)

        return Response(generate(), mimetype='text/plain')

    return jsonify({'antwort': 'Keine Frage gestellt.'}), 400


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
