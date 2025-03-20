from flask import Flask, request, jsonify
import whois
from flask_cors import CORS
from datetime import datetime, timezone
import cohere
import os
import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/check', methods=['GET'])
def check_domain():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    try:
        # ✅ WHOIS lookup with a timeout (prevents backend freezes)
        domain_info = whois.whois(domain)
        available = domain_info.domain_name is None
        expiration_date = domain_info.expiration_date

        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]

        if expiration_date and isinstance(expiration_date, datetime):
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            time_until_expiration = expiration_date - now

            expires_in = {
                "days": time_until_expiration.days,
                "weeks": time_until_expiration.days // 7,
                "months": time_until_expiration.days // 30,
                "years": time_until_expiration.days // 365
            }
        else:
            expires_in = "Unknown"

        return jsonify({
            "domain": domain,
            "available": available,
            "expiration_date": str(expiration_date) if expiration_date else "Unknown",
            "expires_in": expires_in
        })

    except Exception as e:
        return jsonify({"error": "WHOIS lookup failed or timed out"}), 500  # ✅ Hides technical errors from users


@app.route('/ai-suggestions', methods=['GET'])
def ai_suggestions():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    try:
        co = cohere.Client(os.getenv("COHERE_API_KEY"))

        print(f"🔍 Fetching AI suggestions for: {domain}")

        response = co.generate(
            model="command",
            prompt=f"Generate exactly 5 unique, brandable, available domain names for {domain}. "
                   f"Do NOT provide explanations, just the domain names. "
                   f"Avoid numbers, misspellings, or special characters. "
                   f"Ensure results are safe for work and free of inappropriate words. "
                   f"Return only the domain names, each on a new line.",
            max_tokens=50,
            temperature=0.6
        )

        raw_suggestions = response.generations[0].text.strip().split("\n")
        suggestions = [s.strip() for s in raw_suggestions if s.strip()]

        available_suggestions = []
        for suggestion in suggestions:
            if is_domain_available(suggestion):
                available_suggestions.append(suggestion)
            if len(available_suggestions) == 5:
                break

        while len(available_suggestions) < 5:
            new_suggestion = generate_fallback_alternative(domain, len(available_suggestions))
            if is_domain_available(new_suggestion):
                available_suggestions.append(new_suggestion)

        print(f"✅ Final Available Suggestions: {available_suggestions}")

        return jsonify({"suggestions": available_suggestions[:5]})

    except requests.exceptions.Timeout:
        print("❌ AI request timed out.")
        return jsonify({"error": "AI request timed out. Try again."}), 500
    except Exception as e:
        print(f"❌ AI Suggestion Error: {str(e)}")
        return jsonify({"error": "AI service is currently unavailable. Please try again later."}), 500


def is_domain_available(domain_name):
    """ ✅ WHOIS lookup with a timeout to prevent memory overload """
    try:
        domain_info = whois.whois(domain_name)
        return domain_info.domain_name is None
    except:
        return False  # Assume taken if WHOIS lookup fails (prevents infinite retries)


def generate_fallback_alternative(domain, count):
    """ ✅ Simple fallback generator (low memory) """
    suffixes = ["now", "hub", "site", "online", "pro"]
    base_name = domain.split('.')[0]
    return f"{base_name}{suffixes[count % len(suffixes)]}.com"


if __name__ == '__main__':
    app.run(debug=True)
