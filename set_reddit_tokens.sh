#!/bin/bash

echo "🔧 Setting up Reddit tokens for Docker..."
echo "=========================================="

# Set your Reddit API credentials
export REDDIT_CLIENT_ID="3NFlIcb7GV-8upi42FG_4g"
export REDDIT_CLIENT_SECRET="5Yw0O7yD-KNrRGIMurFaT14yKajgbw"
export REDDIT_USER_AGENT="Social Media Agent v2/1.0 by u/SuspiciousPapaya3497"
export REDDIT_USERNAME="SuspiciousPapaya3497"

# Set your tokens (obtained from the authorization process)
export REDDIT_ACCESS_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6IlNIQTI1NjpzS3dsMnlsV0VtMjVmcXhwTU40cWY4MXE2OWFFdWFyMnpLMUdhVGxjdWNZIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyIiwiZXhwIjoxNzYwNjk1NzAwLjg0NjI0OSwiaWF0IjoxNzYwNjA5MzAwLjg0NjI0OSwianRpIjoicVVCMjVIcHdGOEVmSGhVNEJqOFQzWms0TmlyQW5nIiwiY2lkIjoiM05GbEljYjdHVi04dXBpNDJGR180ZyIsImxpZCI6InQyXzF6aGNycnhvdjIiLCJhaWQiOiJ0Ml8xemhjcnJ4b3YyIiwibGNhIjoxNzYwMDAxMzMzNzYwLCJzY3AiOiJlSndjeURFS2dEQU1oZUc3X0hOdUpBNldCTXhRaGVaMXlPMEYxLThnUElVeHVfWlk0WjRxak5wal9yN2ljb3owZUpScWpEdEw3MnJPTHdBQV9fOXhDQlNlIiwicmNpZCI6IlZUVUtHeXpEelJ0Nl9zR1ItTUc4VFgtZ3RBZUhfMHlwWC1OVjN1UU1paWMiLCJmbG8iOjh9.SHyWKYn_Ub8P3FBTCWLb0J3lFHUvWcKoMb5lwK8p7lG4PxHvWIZlyp6xzUz1VZoddio5G9xpLTWMuos7m4wGH0TizjaDJl9CH0GIzoTDyptV7H9-oeEqVW7iEJTtJCvJO8Ooryb8cTh5q_EpZmr7BOohNTOiELNtQ2xwawcUW-ecWVTqrIVl6m-z70m_5uybY1KCdO0tVmKQjZy2pzRyMO7_LHxURIcHljGVhCMmG5kf3WjSmQpwqY19HXsmNaTPqkQjo4ygJtsBauz2-YFdritPWT_oA9AeT95YO0bEwneb8380Cr7Jf9Vj2bHsQ-9cNpbng_eYfYmEYJ7ttuwO8w"
export REDDIT_REFRESH_TOKEN="201658795115294-9xGQLC0aRbn8cr4bL2AgsORc99O2gQ"

echo "✅ Reddit tokens set successfully!"
echo ""
echo "🚀 You can now run your Docker application:"
echo "   docker-compose down && docker-compose build --no-cache && docker-compose up"
echo ""
echo "💡 The system will automatically:"
echo "   - Use your access token (valid for ~24 hours)"
echo "   - Auto-refresh it when it expires"
echo "   - Keep working forever with your refresh token"
echo ""
echo "🎯 No more manual token management needed!"
