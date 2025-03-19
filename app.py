from flask import Flask, request, jsonify
import whois
from flask_cors import CORS
from datetime import datetime, timezone
import openai  # OpenAI API for AI-driven domain suggestions
import os

# Load OpenAI API Key from Render environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)

def time_until(expiration_date):
    """Calculate the time remaining until the expiration date in a fun way."""
    now = datetime.now(timezone.utc)

    if isinstance(expiration_date, list) and len(expiration_date) > 0:
        expiration_date = expiration_date[0]

    if not isinstance(expiration_date, datetime):
        return "⚠️ Expiration date unavailable"

    expiration_date = expiration_date.replace(tzinfo=timezone.utc)
    delta = expiration_date - now

    days_left = delta.days
    years = days_left // 365
    months = (days_left % 365) // 30
    days = (days_left % 365) % 30
    minutes = delta.total_seconds() // 60

    if days_left < 0:
        return "Oops! This domain has already expired!"

    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")

    readable_time = ", ".join(parts) if parts else "less than a day"
    return f"in {readable_time} (~{int(minutes)} minutes)"

def generate_ai_domain_suggestions(original_domain):
    """Use OpenAI's GPT model to generate alternative domain name suggestions."""
    prompt = f"""
    The domain "{original_domain}" is already taken. Suggest five alternative domain names that are:
    - Short, brandable, and catchy
    - Easy to spell and remember
    - Preferably using ".com", ".io", ".co", or ".ai" TLDs
    - Similar in theme to the original domain
    - Creative and unique
    Just list the domain names, one per line, without extra explanations.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use "gpt-4" if you have access
            messages=[{"role": "system", "content": prompt}],
            max_tokens=50
        )

        # Extract AI-generated suggestions from response
        suggestions = response["choices"][0]["message"]["content"].split("\n")
        return [s.strip() for s in suggestions if s.strip()]
    
    except Exception as e:
        print(f"AI generation error: {e}")
        return ["⚠️ AI is unavailable right now. Try again later!"]

@app.route("/check", methods=["GET"])
def check_domain():
    domain = request.args.get("domain")

    try:
        domain_info = whois.whois(domain)

        if domain_info and hasattr(domain_info, 'expiration_date') and domain_info.expiration_date:
            expiration_date = domain_info.expiration_date

            if isinstance(expiration_date, list) and len(expiration_date) > 0:
                expiration_date = expiration_date[0]

            if isinstance(expiration_date, datetime):
                formatted_expiration = expiration_date.strftime("%Y-%m-%d")
                countdown = time_until(expiration_date)

                # Get AI-generated domain name suggestions
                ai_suggestions = generate_ai_domain_suggestions(domain)

                return jsonify({
                    "message": f"🔒 {domain} is registered and expires on {formatted_expiration} ({countdown}).",
                    "alternatives": ai_suggestions
                })

        return jsonify({
            "message": f"🎉 {domain} is available! Hurry before someone else grabs it!"
        })

    except Exception as e:
        print(f"Error fetching WHOIS for {domain}: {e}")
        return jsonify({
            "message": f"⚠️ Unable to determine WHOIS status for {domain}. It may be protected or unavailable."
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
