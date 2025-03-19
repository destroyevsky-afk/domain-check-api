from flask_cors import CORS

from flask import Flask, request, jsonify
import whois

app = Flask(__name__)
CORS(app)  # Allow API requests from anywhere

@app.route("/check", methods=["GET"])
def check_domain():
    domain = request.args.get("domain")
    
    try:
        domain_info = whois.whois(domain)
        if domain_info.expiration_date:
            return jsonify({"message": f"{domain} is registered and expires on {domain_info.expiration_date}"})
        else:
            return jsonify({"message": f"{domain} is available!"})
    except:
        return jsonify({"message": f"{domain} is available!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
