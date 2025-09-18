from app import create_app

app = create_app()

if __name__ == "__main__":
    # Enable debug mode for development; disable in production
    app.run(host="0.0.0.0", port=5000, debug=True)
    
