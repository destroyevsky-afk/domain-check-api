from flask import Flask, request, jsonify
import whois
from flask_cors import CORS
from datetime import datetime, timezone
import cohere  # Cohere AI for AI-driven domain suggestions
import os

app = Flask(__name__)

# ✅ Enable CORS so the frontend can access the API
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

        # ✅ Ensure expiration_date is properly handled
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]  # Take the first value if it's a list

        if expiration_date and isinstance(expiration_date, datetime):
            # ✅ Make sure expiration_date is timezone-aware
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)  # ✅ Ensure 'now' is also timezone-aware
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
            prompt=f"Generate exactly 5 alternative domain names for {domain} that are available for registration. "
                   f"Do NOT provide explanations, just the domain names. "
                   f"Ensure they are safe for work and free of offensive, defamatory, or inappropriate words. "
                   f"Return only the domain names, each on a new line.",
            max_tokens=50,
            temperature=0.7
        )

        # Extract and clean up responses
        suggestions = response.generations[0].text.strip().split("\n")
        suggestions = [s.strip() for s in suggestions if s.strip()]  # Remove empty lines

        # ✅ Ensure exactly 5 results (if AI gives fewer, generate more manually)
        while len(suggestions) < 5:
            suggestions.append(generate_fallback_alternative(domain, len(suggestions)))

        return jsonify({"suggestions": suggestions[:5]})  # Only return 5

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_fallback_alternative(domain, count):
    """ Basic fallback generator if AI returns fewer than 5 suggestions. """
    suffixes = ["now", "hub", "site", "online", "pro"]
    base_name = domain.split('.')[0]  # Strip TLD from input domain
    return f"{base_name}{suffixes[count % len(suffixes)]}.com"


if __name__ == '__main__':
    app.run(debug=True)
