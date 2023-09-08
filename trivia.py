import requests
import json
import random

def fetchQuestions(api_url):
    res = []
    response = requests.get(api_url)

    if response.status_code == 200:
        questions = json.loads(response.text)
        for idx, q in enumerate(questions):
            insert_pos = random.randint(0, 3)
            q["incorrectAnswers"].insert(insert_pos, q["correctAnswer"])
            res.append(
                {
                    "id": idx,
                    "question": q["question"]["text"],
                    "correct": insert_pos,
                    "answers": q["incorrectAnswers"],
                }
            )

    else:
        print("Failed to retrieve questions")

    return res
