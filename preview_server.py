from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/preview')
def preview():
    with open('dashboard_preview.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return content

if __name__ == '__main__':
    app.run(port=5001, debug=True)