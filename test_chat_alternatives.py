from chat_service import handle_chat_message

def test_chat():
    print("Test 1: 'give me 5 alternatives'")
    res = handle_chat_message(1, "give me 5 alternatives to this corporate bond fund")
    print("Response:\n", res['response'])
    
    print("\nTest 2: 'replace my liquid fund'")
    res = handle_chat_message(1, "i want to replace my liquid fund")
    print("Response:\n", res['response'])

if __name__ == "__main__":
    test_chat()
