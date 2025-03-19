from flask import Flask, request, jsonify
import whois
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/check", methods=["GET"])
def check_domain():
    domain = request.args.get("domain")
    
    try:
        domain_info = whois.whois(domain)

        # Check if expiration_date is a list (sometimes WHOIS returns multiple dates)
        if isinstance(domain_info.expiration_date, list):
            expiration_date = domain_info.expiration_date[0].strftime("%Y-%m-%d")
        else:
            expiration_date = domain_info.expiration_date.strftime("%Y-%m-%d")

        return jsonify({"message": f"{domain} is registered and expires on {expiration_date}"})
    
    except:
        return jsonify({"message": f"{domain} is available!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
