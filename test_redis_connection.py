#!/usr/bin/env python3
import redis
import sys

# Redis connection settings
REDIS_HOST = 'capsagamecache.redis.cache.windows.net'
REDIS_PORT = 6380
REDIS_PASSWORD = 'UG7gX2plA0IUVi2OT5nnKiNYOJ8IiVkPJAzCaIIqC8s='
REDIS_DB = 0

def test_redis_connection():
    print("Testing Redis connection to Azure Cache for Redis...")
    print(f"Host: {REDIS_HOST}")
    print(f"Port: {REDIS_PORT}")
    print(f"Password: {REDIS_PASSWORD[:10]}...")  # Only show first 10 chars for security
    
    # Test different connection methods
    methods = [
        {
            "name": "With username 'default'",
            "config": {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "username": "default",
                "password": REDIS_PASSWORD,
                "ssl": True,
                "decode_responses": True,
                "socket_connect_timeout": 10,
                "socket_timeout": 10
            }
        },
        {
            "name": "Without username",
            "config": {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "password": REDIS_PASSWORD,
                "ssl": True,
                "decode_responses": True,
                "socket_connect_timeout": 10,
                "socket_timeout": 10
            }
        },
        {
            "name": "Connection string format",
            "config": {
                "url": f"rediss://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                "decode_responses": True,
                "socket_connect_timeout": 10,
                "socket_timeout": 10
            }
        }
    ]
    
    for method in methods:
        print(f"\n--- Testing {method['name']} ---")
        try:
            if "url" in method["config"]:
                client = redis.from_url(**method["config"])
            else:
                client = redis.StrictRedis(**method["config"])
            
            # Test ping
            response = client.ping()
            print(f"✅ SUCCESS: Ping response: {response}")
            
            # Test basic operations
            client.set("test_key", "test_value")
            value = client.get("test_key")
            print(f"✅ SUCCESS: Set/Get test passed: {value}")
            
            client.delete("test_key")
            print(f"✅ SUCCESS: Delete test passed")
            
            print(f"🎉 {method['name']} works perfectly!")
            return client
            
        except redis.exceptions.AuthenticationError as e:
            print(f"❌ AUTHENTICATION ERROR: {e}")
        except redis.exceptions.ConnectionError as e:
            print(f"❌ CONNECTION ERROR: {e}")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
    
    print("\n❌ All connection methods failed!")
    print("\nTroubleshooting tips:")
    print("1. Check if your Azure Redis password is correct")
    print("2. Verify the Redis host and port are correct")
    print("3. Ensure your Azure Redis instance is running")
    print("4. Check if your IP is whitelisted in Azure Redis firewall")
    print("5. Try using the Azure Portal to get the connection string")
    return None

if __name__ == "__main__":
    client = test_redis_connection()
    if client:
        print("\n✅ Redis connection test successful! You can now run your main application.")
    else:
        print("\n❌ Redis connection test failed. Please fix the connection issues first.")
        sys.exit(1) 