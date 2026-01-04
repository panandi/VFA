"""Test OpenAI API connection"""
import asyncio
from openai import AsyncOpenAI
from app.core.config import settings

async def test_openai_connection():
    """Test if OpenAI API is accessible"""
    print("Testing OpenAI API Connection...")
    print("=" * 60)

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=60.0
    )

    try:
        print(f"API Key configured: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
        print(f"Model: {settings.OPENAI_MODEL}")
        print("\nAttempting API call...")

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "user", "content": "Say 'Connection successful!'"}
            ],
            max_tokens=10
        )

        result = response.choices[0].message.content
        print(f"\n[SUCCESS] Response: {result}")
        print("\nOpenAI API connection is working properly!")
        return True

    except Exception as e:
        print(f"\n[FAILED] Error: {type(e).__name__}")
        print(f"Details: {str(e)}")

        # Additional diagnostics
        if "Connection" in str(e):
            print("\nDiagnostics:")
            print("  - This appears to be a network/proxy issue")
            print("  - Check if you need to configure HTTP_PROXY/HTTPS_PROXY")
            print("  - Verify your network can reach api.openai.com")

        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_connection())
    exit(0 if success else 1)
