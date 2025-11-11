import csv
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

question = input("Input the polymarket full question : ")
outcome = input("Input the desired outcome : ")

def recommend_similar_questions(user_input, rewards, top_n=3, threshold=0.3):
    """
    Recommends semantically similar questions from the rewards list.
    """
    reward_questions = [r["question"] for r in rewards]

    # Encode both input and database of questions
    input_embedding = model.encode(user_input, convert_to_tensor=True)
    reward_embeddings = model.encode(reward_questions, convert_to_tensor=True)

    # Compute cosine similarity
    similarities = util.cos_sim(input_embedding, reward_embeddings)[0]

    # Sort by similarity score
    ranked = sorted(
        zip(reward_questions, similarities),
        key=lambda x: x[1],
        reverse=True
    )

    # Filter by threshold and return top N
    suggestions = [
        (q, float(score))
        for q, score in ranked[:top_n]
        if score >= threshold
    ]

    return suggestions

for reward in all_rewards:
    if reward['question'].lower() == question.lower() and any(
        outcome.lower() in o.lower() for o in reward['outcomes']
    ):
        print(f"market id = {market_id}")
        
        insert_into_file = input("do you want to put the above into file? (Y/N)")
        
        if insert_into_file.lower == "y":
            new_row = [market_id,outcome]
            with open("market.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(new_row)
            print(f"new row added for market{market_id} with outcome {outcome}")
            
    else:
        print("market not found in rewards, finding closes matches")
        results = recommend_similar_questions(user_input, rewards, top_n=5)
        if results:
            print("\n🔍 Closest matches found:")
            for q, score in results:
                print(f"• {q}  (similarity: {score:.2f})")
                
        else:
            print("❌ No similar questions found.")