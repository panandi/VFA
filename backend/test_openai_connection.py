"""Test OpenAI API connection with SSL bypass"""
import asyncio
import httpx
from openai import AsyncOpenAI
from app.core.config import settings

async def test_openai_connection():
    """Test if OpenAI API is accessible"""
    print("Testing OpenAI API Connection...")
    print("=" * 60)

    # Suppress SSL warnings if urllib3 is available
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass

    # Create HTTP client with SSL bypass
    http_client = httpx.AsyncClient(
        verify=False,
        timeout=httpx.Timeout(60.0, connect=10.0)
    )

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=http_client
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
    finally:
        await http_client.aclose()

if __name__ == "__main__":
    success = asyncio.run(test_openai_connection())
    exit(0 if success else 1)
