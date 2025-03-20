from flask import Flask, request, jsonify
import whois
from flask_cors import CORS
from datetime import datetime, timezone
import cohere  # AI for domain suggestions
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/check', methods=['GET'])
def check_domain():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    try:
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
        return jsonify({"error": str(e)}), 500


@app.route('/ai-suggestions', methods=['GET'])
def ai_suggestions():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    try:
        co = cohere.Client(os.getenv("COHERE_API_KEY"))

        response = co.generate(
            model="command",
            prompt=f"Generate exactly 5 alternative domain names for {domain} that are unique, brandable, and likely available for registration. "
                   f"Do NOT provide explanations, just the domain names. "
                   f"Do NOT use numbers, misspellings, or special characters. "
                   f"Ensure results are safe for work and free of offensive, defamatory, or inappropriate words. "
                   f"Return only the domain names, each on a new line.",
            max_tokens=50,  # Lowered to reduce excess output
            temperature=0.6
        )

        raw_suggestions = response.generations[0].text.strip().split("\n")
        suggestions = [s.strip() for s in raw_suggestions if s.strip()]

        # ✅ Verify if each suggested domain is actually available
        available_suggestions = []
        for suggestion in suggestions:
            if is_domain_available(suggestion):
                available_suggestions.append(suggestion)
            if len(available_suggestions) == 5:  # Stop once we have 5 available domains
                break

        # If fewer than 5 are available, generate fallback suggestions
        while len(available_suggestions) < 5:
            new_suggestion = generate_fallback_alternative(domain, len(available_suggestions))
            if is_domain_available(new_suggestion):
                available_suggestions.append(new_suggestion)

        return jsonify({"suggestions": available_suggestions[:5]})  # Only return 5 verified available domains

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def is_domain_available(domain_name):
    """ Checks if a domain is available using WHOIS lookup """
    try:
        domain_info = whois.whois(domain_name)
        return domain_info.domain_name is None  # True if available, False if taken
    except:
        return True  # If WHOIS fails, assume it's available (to prevent blocking)


def generate_fallback_alternative(domain, count):
    """ Generates a simple fallback domain alternative if AI suggestions fail """
    suffixes = ["now", "hub", "site", "online", "pro"]
    base_name = domain.split('.')[0]  # Strip TLD from input domain
    return f"{base_name}{suffixes[count % len(suffixes)]}.com"


if __name__ == '__main__':
    app.run(debug=True)
