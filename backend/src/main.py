from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/hallo', methods=['GET'])
def hallo():
    message = "Hallo Welt"
    print(message)  # Gibt "Hallo Welt" in der Server-Konsole aus
    return jsonify({'message': message})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
