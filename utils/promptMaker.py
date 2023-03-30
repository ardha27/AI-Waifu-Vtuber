import json
import sys

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

outputNum = 20

def getIdentity(identityPath):  
    with open(identityPath, "r", encoding="utf-8") as f:
        identityContext = f.read()
    return {"role": "user", "content": identityContext}
    
def getPrompt():
    prompt = []
    total_len = 0
    prompt.append(getIdentity("characterConfig/Pina/identity.txt"))
    prompt.append({"role": "system", "content": f"Below is conversation history.\n"})

    with open("conversation.json", "r") as f:
        data = json.load(f)

    history = data["history"]

    for message in history[:-1]:
        prompt.append(message)

    prompt.append(
        {
            "role": "system",
            "content": f"Here is the latest conversation.\n*Make sure your response is within {outputNum} characters!\n",
        }
    )

    prompt.append(history[-1])

    for item in prompt:
        if isinstance(item, dict) and "content" in item:
            content = item["content"]
            total_len += len(content)
    
    while total_len > 4095:
        prompt.pop(2)

    # total_characters = sum(len(d['content']) for d in prompt)
    # print(f"Total characters: {total_characters}")

    return prompt

if __name__ == "__main__":
    prompt = getPrompt()
    print(prompt[2])
    print(len(prompt))