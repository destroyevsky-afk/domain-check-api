from flask import Flask, request, jsonify
import whois
from flask_cors import CORS
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

def time_until(expiration_date):
    """Calculate the time remaining until the expiration date in a fun way."""
    now = datetime.now(timezone.utc)
    
    # Handle cases where WHOIS returns multiple expiration dates
    if isinstance(expiration_date, list):
        expiration_date = expiration_date[0]

    # Convert to UTC timezone
    expiration_date = expiration_date.replace(tzinfo=timezone.utc)

    delta = expiration_date - now

    # Calculate remaining time in different units
    days_left = delta.days
    years = days_left // 365
    months = (days_left % 365) // 30
    days = (days_left % 365) % 30
    minutes = delta.total_seconds() // 60

    # Build a whimsical response
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

@app.route("/check", methods=["GET"])
def check_domain():
    domain = request.args.get("domain")
    
    try:
        domain_info = whois.whois(domain)
        
        if domain_info.expiration_date:
            expiration_date = domain_info.expiration_date

            # Format expiration date
            formatted_expiration = expiration_date.strftime("%Y-%m-%d")

            # Get fun countdown
            countdown = time_until(expiration_date)

            return jsonify({"message": f"🔒 {domain} is registered and expires on {formatted_expiration} ({countdown})."})
        else:
            return jsonify({"message": f"🎉 {domain} is available! Hurry before someone else grabs it!"})

    except:
        return jsonify({"message": f"🎉 {domain} is available! Hurry before someone else grabs it!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
