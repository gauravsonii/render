import os
import sys

# Set environment variable to suppress warnings at Python level (before any imports)
os.environ['PYTHONWARNINGS'] = 'ignore::SyntaxWarning'

import warnings

# Aggressively suppress SyntaxWarning from tweepy library BEFORE any imports
# This must be done at the very start to catch warnings during module import
# Python 3.12+ treats these warnings as errors in some environments like Vercel

# Set default action to ignore SyntaxWarnings
warnings.simplefilter('ignore', SyntaxWarning)

# Filter all SyntaxWarnings
warnings.filterwarnings('ignore', category=SyntaxWarning)
warnings.filterwarnings('ignore', message='.*invalid escape sequence.*')
warnings.filterwarnings('ignore', message='.*invalid.*escape.*')

# Patch warnings.showwarning to completely suppress SyntaxWarnings
_original_showwarning = warnings.showwarning

def _suppress_syntax_warnings(message, category, filename, lineno, file=None, line=None):
    # Only show warnings that are NOT SyntaxWarning
    if not issubclass(category, SyntaxWarning):
        try:
            _original_showwarning(message, category, filename, lineno, file, line)
        except Exception:
            pass  # Ignore any errors in warning display

warnings.showwarning = _suppress_syntax_warnings

# Suppress warnings during tweepy import
with warnings.catch_warnings():
    warnings.simplefilter('ignore', SyntaxWarning)
    warnings.filterwarnings('ignore', category=SyntaxWarning)
    import tweepy
import config
from auth import require_bearer_token
from flask import Flask, request, jsonify, render_template, send_from_directory
from ai import genText, genImage, getImagePrompt

app = Flask(__name__)

auth = tweepy.OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
auth.set_access_token(config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)

api = tweepy.API(auth)

client = tweepy.Client(
    config.BEARER_TOKEN,
    config.CONSUMER_KEY,
    config.CONSUMER_SECRET,
    config.ACCESS_TOKEN,
    config.ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True
)

SECRET_BEARER_TOKEN = config.SECRET_KEY


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/static/favicon.ico")
def fav():
    return send_from_directory(app.static_folder, 'favicon.ico')


@app.route('/tweet', methods=['POST'])
@require_bearer_token(SECRET_BEARER_TOKEN)
def tweet():
    try:
        generatedText = genText()
        imagePrompt = getImagePrompt(generatedText)
        generatedImage, generatedImageName = genImage(imagePrompt)

        api.verify_credentials()
        print("Authentication ✅")

        image_id = api.media_upload(
            filename=f"images/{generatedImageName}").media_id_string
        client.create_tweet(text=generatedText, media_ids=[image_id])

        response = {
            'image_id': image_id,
            'generatedText': generatedText,
            'imagePrompt': imagePrompt,
            'message': "Tweet posted successfully! ✅"
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
