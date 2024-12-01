# APPtitude - Mental Math Practice

APPtitude is an interactive web application designed to help students improve their mental math skills through adaptive practice challenges. The app provides a dynamic learning experience with questions that adapt to the user's skill level.

## Features

- 5 difficulty levels (Easy to Hard)
- Interactive test mechanics
- Real-time feedback and explanations
- Timer functionality
- Progress tracking
- Adaptive question generation using AI
- Comprehensive error handling

## Technical Stack

- Backend: Python Flask
- Frontend: HTML/JavaScript
- AI Integration: X.AI Grok API
- Production Server: Gunicorn

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file
   - Add your X.AI API key: `XAI_API_KEY=your_api_key_here`

4. Run the application:
   ```bash
   python app.py
   ```

## Deployment

The application is configured for deployment on Render.com:

1. Push code to GitHub
2. Create a new Web Service on Render
3. Connect your repository
4. Add environment variables
5. Deploy

## License

MIT License - Feel free to use and modify for your needs!
