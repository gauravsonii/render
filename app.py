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

SECRET_BEARER_TOKEN = config.SECRET_KEY

# Initialize Twitter API clients lazily to avoid errors if env vars are missing
# These will be initialized only when needed in the tweet route
def get_twitter_api():
    """Get initialized Twitter API v1.1 client"""
    if not config.CONSUMER_KEY or not config.CONSUMER_SECRET:
        raise ValueError("Twitter credentials (CONSUMER_KEY, CONSUMER_SECRET) are not configured")
    auth = tweepy.OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
    auth.set_access_token(config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)

def get_twitter_client():
    """Get initialized Twitter API v2 client"""
    if not config.BEARER_TOKEN or not config.CONSUMER_KEY:
        raise ValueError("Twitter credentials (BEARER_TOKEN, CONSUMER_KEY) are not configured")
    return tweepy.Client(
        config.BEARER_TOKEN,
        config.CONSUMER_KEY,
        config.CONSUMER_SECRET,
        config.ACCESS_TOKEN,
        config.ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True
    )


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
        # Initialize Twitter clients when needed
        api = get_twitter_api()
        client = get_twitter_client()
        
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

    except ValueError as e:
        return jsonify({'error': f'Configuration error: {str(e)}. Please set environment variables in Vercel dashboard.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
