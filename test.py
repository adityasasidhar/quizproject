from google import genai

client = genai.Client(api_key="AIzaSyBcS2vY-EFMfzPgzaidGk52LE-ImlOmRoI")

response = client.models.generate_content(model="gemini-2.5-flash", contents=["Hello world!"])
print(response.text)