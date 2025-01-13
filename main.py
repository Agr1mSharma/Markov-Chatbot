from pathlib import Path
import pandas as pd
import re
from fuzzywuzzy import fuzz
import random
from collections import defaultdict

def process_chat_file(file_path, sender_name, receiver_name, output_df):
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        raw_data = raw_data.replace(b"\r", b"\n")
        decoded_data = raw_data.decode('utf-8', errors='ignore')
        
        cleaned_data = decoded_data.replace(r'\n', '\n')
        cleaned_data = re.sub(r'\[\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}:\d{2}[\u2000-\u206F]?(AM|PM)?\] ', '', cleaned_data)
        cleaned_data = re.sub(rf"{sender_name}:.*Messages and calls are end-to-end encrypted.*\r?\n", "", cleaned_data)
        
        previous_message = []
        your_response = []
        sender_message = ""
        receiver_message = ""
        current_sender = None

        for line in cleaned_data.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(sender_name):
                if current_sender == receiver_name and receiver_message:
                    your_response.append(receiver_message.strip())
                    receiver_message = ""
                sender_message += line[len(sender_name) + 1:].strip() + " "
                current_sender = sender_name
                
            elif line.startswith(receiver_name):
                if current_sender == sender_name and sender_message:
                    previous_message.append(sender_message.strip())
                    sender_message = ""
                receiver_message += line[len(receiver_name) + 1:].strip() + " "
                current_sender = receiver_name

        if sender_message:
            previous_message.append(sender_message.strip())
        if receiver_message:
            your_response.append(receiver_message.strip())

        max_len = max(len(previous_message), len(your_response))
        previous_message.extend([''] * (max_len - len(previous_message)))
        your_response.extend([''] * (max_len - len(your_response)))

        new_df = pd.DataFrame({
            'previous_message': previous_message,
            'your_response': your_response
        })
        
        return pd.concat([output_df, new_df], ignore_index=True)
        
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return output_df

def find_similar_responses(input_text, df, threshold=60):
    if not isinstance(input_text, str):
        return []
    
    similarities = []
    for idx, row in df.iterrows():
        if not isinstance(row['previous_message'], str):
            continue
            
        score = fuzz.token_set_ratio(input_text, row['previous_message'])
        if score >= threshold:
            similarities.append({
                'previous_message': row['previous_message'],
                'your_response': row['your_response'],
                'weight': score/100
            })
    
    return similarities

def build_weighted_markov(similar_responses):
    transitions = defaultdict(lambda: defaultdict(float))
    
    for item in similar_responses:
        response = item['your_response']
        if not isinstance(response, str):
            continue
            
        weight = item['weight']
        words = response.split()
        words = ['<START>'] + words + ['<END>']
        
        for i in range(len(words)-1):
            transitions[words[i]][words[i+1]] += weight
    
    return transitions

def generate_response(transitions):
    if not transitions:
        return "I'm not sure how to respond to that."
    
    response = []
    current = '<START>'
    max_length = 30  # Prevent infinite loops
    
    while current != '<END>' and len(response) < max_length:
        if current not in transitions:
            break
            
        next_words = transitions[current]
        if not next_words:
            break
            
        total_weight = sum(next_words.values())
        probabilities = {word: weight/total_weight for word, weight in next_words.items()}
        
        next_word = random.choices(
            list(probabilities.keys()),
            weights=list(probabilities.values())
        )[0]
        
        if next_word != '<END>':
            response.append(next_word)
        current = next_word
    
    return ' '.join(response) if response else "I'm not sure how to respond to that."

def chat(input_text, df):
    similar_responses = find_similar_responses(input_text, df)
    transitions = build_weighted_markov(similar_responses)
    return generate_response(transitions)

df_combined = pd.DataFrame(columns=['previous_message', 'your_response'])

chat_files = [
    ("C:\\Projects\\Chatbot\\Chats\\Monish_chat.txt", "Monish M Purdue", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Meowstogi_chat.txt", "Shivam Rastogi Purdue", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Devansh_chat.txt", "Devansh Khandelwal Purdue", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Irfan_chat.txt", "Irfan Firosh Purdue", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Raghav_chat.txt", "‪+1 (765) 543‑6656", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Shlok_chat.txt", "Shlok Sheth Purdue", "Agrim Sharma"),
    ("C:\\Projects\\Chatbot\\Chats\\Vipul_chat.txt", "Vipul Konnur Purdue", "Agrim Sharma")
]

for file_path, sender_name, receiver_name in chat_files:
    df_combined = process_chat_file(file_path, sender_name, receiver_name, df_combined)

df_combined.to_csv('combined_conversation_data.csv', index=False)


def chat_loop(df):
    print("Chat started! Type 'end' to exit.")
    print("-" * 50)
    while True:
        input_text = input("You: ").strip()
        
        if input_text.lower() == 'end':
            print("Chat ended. Goodbye!")
            break
            
        response = chat(input_text, df)
        print(f"Bot: {response}")
        print("-" * 50)


if __name__ == "__main__":
    chat_loop(df_combined)
